"""
Ingestion pipeline: orchestrates PDF text extraction -> chunking ->
embedding/storage -> registry status updates for a single uploaded file.
"""
import logging
import os

from app.core.exceptions import OpsPilotError
from app.models.schemas import DocumentInfo
from app.services import chunking_service, document_registry, pdf_service, vectorstore_service
from app.utils.file_utils import build_storage_path, generate_document_id, validate_filename, validate_size

logger = logging.getLogger(__name__)


def ingest_file(file_bytes: bytes, filename: str) -> DocumentInfo:
    """
    Process one uploaded PDF end-to-end. Returns the resulting DocumentInfo
    (status READY on success, FAILED with error_message on failure). Never
    raises for per-file processing errors, so a batch upload of several
    files can partially succeed.
    """
    validate_filename(filename)
    validate_size(len(file_bytes), filename)

    document_id = generate_document_id()
    document_registry.create_pending(document_id, filename)
    storage_path = build_storage_path(document_id, filename)

    try:
        with open(storage_path, "wb") as f:
            f.write(file_bytes)

        pages = pdf_service.extract_pages(storage_path, filename)
        chunks = chunking_service.chunk_pages(pages)
        vectorstore_service.add_document_chunks(document_id, filename, chunks)

        document_registry.mark_ready(document_id, page_count=len(pages), chunk_count=len(chunks))
        logger.info("Successfully ingested '%s' as document %s", filename, document_id)

    except OpsPilotError as exc:
        document_registry.mark_failed(document_id, exc.message)
        logger.warning("Ingestion failed for '%s': %s", filename, exc.message)
    except Exception as exc:  # noqa: BLE001 - we want to catch and record any failure
        document_registry.mark_failed(document_id, f"Unexpected error: {exc}")
        logger.exception("Unexpected ingestion failure for '%s'", filename)
    finally:
        # Keep the original PDF on disk is not required for retrieval (text is
        # embedded in Chroma); remove it to save disk space on free-tier hosts.
        if os.path.exists(storage_path):
            os.remove(storage_path)

    return document_registry.get(document_id)


def delete_document(document_id: str) -> None:
    document_registry.get(document_id)  # raises DocumentNotFoundError if missing
    vectorstore_service.delete_document(document_id)
    document_registry.delete(document_id)
