"""
Vector store service.

Wraps a single persistent Chroma collection. Each chunk is stored with
metadata (document_id, filename, page_number) so retrieval results can be
turned directly into citations without a second lookup.

Embeddings use Google's Gemini embedding model. This is instantiated lazily
so the app can still boot (and /health can report a clear error) even if
GOOGLE_API_KEY is missing, rather than crashing at import time.
"""
import logging
import os

import chromadb
from langchain_huggingface import HuggingFaceEmbeddings

from app.config import get_settings
from app.core.exceptions import QuotaExceededError
from app.services.chunking_service import DocumentChunk

logger = logging.getLogger(__name__)
settings = get_settings()

_COLLECTION_NAME = "opspilot_documents"

_client: chromadb.ClientAPI | None = None
_embeddings: HuggingFaceEmbeddings | None = None

# Root cause of the upload 502: without this, HuggingFaceEmbeddings falls
# back to ~/.cache/huggingface, which is NOT on the persisted disk Render
# mounts (see render.yaml: only /app/data is a persistent volume). Every
# cold start / redeploy then re-downloads the ~90MB model from
# huggingface.co the first time a PDF is uploaded, synchronously, inside
# the request. Pointing the cache at the same persisted dir as Chroma means
# the download happens once and survives restarts.
os.makedirs(settings.hf_cache_dir, exist_ok=True)


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


def _get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings

    if _embeddings is None:
        logger.info("Loading local embedding model... (first run may take a minute)")

        _embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            cache_folder=settings.hf_cache_dir,
        )

    return _embeddings


def warm_up() -> None:
    """
    Force-load the embedding model and the Chroma client immediately.

    Call this once from a FastAPI startup hook (see main.py) instead of
    letting it happen lazily on a user's first upload request. This moves
    the slow, network-dependent, blocking work to container boot time,
    where a failure is visible in deploy logs and /api/health can report it
    -- rather than surfacing as a mid-request 502 with no diagnostic trail.
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
