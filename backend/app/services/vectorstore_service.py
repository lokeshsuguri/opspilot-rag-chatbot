"""
Vector store service.

Wraps a single persistent Chroma collection. Each chunk is stored with
metadata (document_id, filename, page_number) so retrieval results can be
turned directly into citations without a second lookup.

Embeddings are generated locally with FastEmbed (ONNX Runtime), not
PyTorch. This is a deliberate choice for deployment on memory-constrained
hosts like Render's free tier (512 MB RAM):

    torch + transformers + sentence-transformers routinely push RSS past
    600-900 MB just to import and load `all-MiniLM-L6-v2`. On a 512 MB
    box, the OS OOM-killer terminates the process the moment the model
    finishes loading -- which is exactly the symptom this replaces:
    the process printed "Load pretrained SentenceTransformer: ..." and
    was silently restarted, with no Python traceback, because the kill
    happens at the OS level, outside the interpreter.

    FastEmbed loads the same model ("sentence-transformers/all-MiniLM-L6-v2")
    but runs it through ONNX Runtime instead of PyTorch. There is no torch
    import, no autograd machinery, and a single quantized ONNX graph
    (~90 MB on disk) instead of the full transformers/sentence-transformers
    stack. Typical peak RSS for embedding a batch of chunks drops to
    roughly 150-250 MB, comfortably inside Render's free-tier limit.

    The output vectors are numerically equivalent (same base model, same
    384 dimensions), so this is a drop-in replacement: existing Chroma
    collections keep working and retrieval quality is unaffected.
"""
import logging
import os

import chromadb
from fastembed import TextEmbedding

from app.config import get_settings
from app.core.exceptions import QuotaExceededError
from app.services.chunking_service import DocumentChunk

logger = logging.getLogger(__name__)
settings = get_settings()

_COLLECTION_NAME = "opspilot_documents"

_client: chromadb.ClientAPI | None = None
_embeddings: "_FastEmbedEmbeddings | None" = None

# Cache the ONNX model weights on the same persisted disk as Chroma (see
# render.yaml: only /app/data is a persistent volume). Without this, the
# model would be re-downloaded from Hugging Face on every cold start /
# redeploy the first time a PDF is uploaded, synchronously, inside the
# request.
os.makedirs(settings.hf_cache_dir, exist_ok=True)


class _FastEmbedEmbeddings:
    """
    Minimal adapter around fastembed.TextEmbedding that exposes the same
    two methods the rest of this module relies on (embed_documents /
    embed_query), matching the interface previously provided by
    langchain_huggingface.HuggingFaceEmbeddings. Keeping this shim local
    (instead of pulling in a langchain integration package) avoids an
    extra dependency and keeps the call sites in this file unchanged.
    """

    def __init__(self, model_name: str, cache_dir: str) -> None:
        self._model = TextEmbedding(
            model_name=model_name,
            cache_dir=cache_dir,
            # Single worker thread: Render's free tier is a single vCPU,
            # so extra ONNX Runtime threads just add memory/context-switch
            # overhead without speeding anything up.
            threads=1,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # parallel=0 forces in-process, single-worker execution. Leaving
        # this unset lets fastembed spawn a multiprocessing pool, which
        # duplicates the loaded ONNX model across worker processes --
        # exactly the kind of memory spike we're trying to eliminate.
        return [vector.tolist() for vector in self._model.embed(texts, parallel=0)]

    def embed_query(self, text: str) -> list[float]:
        return next(self._model.embed([text], parallel=0)).tolist()


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            # chromadb 0.5.5's telemetry code throws
            # "capture() takes 1 positional argument but 3 were given"
            # against newer posthog versions on every startup. It's
            # internally swallowed (not your 502) but pollutes logs enough
            # to hide the real error. Turn it off outright.
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
    return _client


def _get_embeddings() -> _FastEmbedEmbeddings:
    global _embeddings

    if _embeddings is None:
        logger.info("Loading local embedding model... (first run may take a minute)")

        _embeddings = _FastEmbedEmbeddings(
            model_name=settings.embedding_model,
            cache_dir=settings.hf_cache_dir,
        )

    return _embeddings


def warm_up() -> None:
    """
    Force-load the embedding model and the Chroma client immediately.

    Call this once from a FastAPI startup hook (see main.py). FastEmbed's
    memory footprint is small enough that doing this at boot (rather than
    lazily on the first upload) no longer risks exceeding Render's 512 MB
    limit, and it means a broken deploy fails fast and visibly in the
    deploy logs instead of on a user's first request.
    """
    _get_embeddings().embed_query("warmup")
    _get_client()
    logger.info("Vector store warm-up complete (embedding model + Chroma client ready).")


def _get_collection():
    return _get_client().get_or_create_collection(name=_COLLECTION_NAME)


def add_document_chunks(
    document_id: str, filename: str, chunks: list[DocumentChunk]
) -> None:
    """Embed and persist all chunks for one document."""
    if not chunks:
        return

    embeddings_model = _get_embeddings()
    texts = [c.text for c in chunks]

    try:
        logger.info("Generating embeddings...")
        vectors = embeddings_model.embed_documents(texts)
        logger.info("Embeddings generated.")
    except Exception:
        logger.exception("Embedding failed")
        raise

    collection = _get_collection()

    ids = [f"{document_id}_{c.chunk_index}" for c in chunks]
    metadatas = [
        {
            "document_id": document_id,
            "filename": filename,
            "page_number": c.page_number,
        }
        for c in chunks
    ]

    logger.info(f"Chunks: {len(chunks)}")
    logger.info(f"Texts: {len(texts)}")
    logger.info(f"Vectors: {len(vectors)}")
    logger.info(f"IDs: {len(ids)}")
    logger.info(f"Metadata: {len(metadatas)}")

    try:
        logger.info("Before collection.add()")

        collection.add(
            ids=ids,
            embeddings=vectors,
            documents=texts,
            metadatas=metadatas,
        )

        logger.info("After collection.add()")

    except Exception:
        logger.exception("Chroma failed")
        raise

    logger.info(
        "Persisted %d chunks for document '%s' (%s)",
        len(chunks),
        filename,
        document_id,
    )

def similarity_search(
    query: str, top_k: int, document_ids: list[str] | None = None
) -> list[dict]:
    """
    Return the top_k most relevant chunks for a query, optionally scoped to
    a subset of document_ids. Each result is a dict with text, filename,
    page_number, document_id, and distance.
    """
    embeddings_model = _get_embeddings()
    query_vector = embeddings_model.embed_query(query)

    collection = _get_collection()
    where = {"document_id": {"$in": document_ids}} if document_ids else None

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        where=where,
    )

    hits: list[dict] = []
    if not results["ids"] or not results["ids"][0]:
        return hits

    for i in range(len(results["ids"][0])):
        metadata = results["metadatas"][0][i]
        hits.append(
            {
                "text": results["documents"][0][i],
                "filename": metadata["filename"],
                "page_number": metadata["page_number"],
                "document_id": metadata["document_id"],
                "distance": results["distances"][0][i] if results.get("distances") else None,
            }
        )
    return hits


def delete_document(document_id: str) -> None:
    collection = _get_collection()
    collection.delete(where={"document_id": document_id})
    logger.info("Deleted all chunks for document '%s'", document_id)


def count_chunks_for_document(document_id: str) -> int:
    collection = _get_collection()
    result = collection.get(where={"document_id": document_id})
    return len(result["ids"])


def is_ready() -> bool:
    try:
        _get_client()
        return True
    except Exception:
        return False
