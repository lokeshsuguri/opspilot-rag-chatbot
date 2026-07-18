"""
Document metadata registry.

Chroma stores chunk-level data but has no concept of "a document with a
status." This lightweight registry tracks per-document metadata (filename,
page/chunk counts, processing status) and persists it to a JSON file so the
document list survives a backend restart on the same disk. This is
intentionally simple for a pilot — a real production system would use a
proper database (Postgres) instead of a JSON file.
"""
import json
import logging
import os
import threading
from datetime import datetime, timezone

from app.config import get_settings
from app.core.exceptions import DocumentNotFoundError
from app.models.schemas import DocumentInfo, DocumentStatus

logger = logging.getLogger(__name__)
settings = get_settings()

_REGISTRY_FILE = os.path.join(settings.upload_dir, "_registry.json")
_lock = threading.Lock()
_documents: dict[str, DocumentInfo] = {}
_loaded = False


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    os.makedirs(settings.upload_dir, exist_ok=True)
    if os.path.exists(_REGISTRY_FILE):
        try:
            with open(_REGISTRY_FILE, "r") as f:
                raw = json.load(f)
            for doc_id, data in raw.items():
                _documents[doc_id] = DocumentInfo(**data)
        except Exception as exc:
            logger.warning("Could not load document registry: %s", exc)
    _loaded = True


def _persist() -> None:
    with open(_REGISTRY_FILE, "w") as f:
        json.dump({k: json.loads(v.model_dump_json()) for k, v in _documents.items()}, f, default=str)


def create_pending(document_id: str, filename: str) -> DocumentInfo:
    _ensure_loaded()
    info = DocumentInfo(
        document_id=document_id,
        filename=filename,
        page_count=0,
        chunk_count=0,
        status=DocumentStatus.PROCESSING,
        uploaded_at=datetime.now(timezone.utc),
    )
    with _lock:
        _documents[document_id] = info
        _persist()
    return info


def mark_ready(document_id: str, page_count: int, chunk_count: int) -> None:
    _ensure_loaded()
    with _lock:
        info = _documents.get(document_id)
        if info is None:
            return
        info.page_count = page_count
        info.chunk_count = chunk_count
        info.status = DocumentStatus.READY
        _persist()


def mark_failed(document_id: str, error_message: str) -> None:
    _ensure_loaded()
    with _lock:
        info = _documents.get(document_id)
        if info is None:
            return
        info.status = DocumentStatus.FAILED
        info.error_message = error_message
        _persist()


def get(document_id: str) -> DocumentInfo:
    _ensure_loaded()
    info = _documents.get(document_id)
    if info is None:
        raise DocumentNotFoundError(document_id)
    return info


def list_all() -> list[DocumentInfo]:
    _ensure_loaded()
    return sorted(_documents.values(), key=lambda d: d.uploaded_at, reverse=True)


def list_ready_ids() -> list[str]:
    _ensure_loaded()
    return [d.document_id for d in _documents.values() if d.status == DocumentStatus.READY]


def delete(document_id: str) -> None:
    _ensure_loaded()
    with _lock:
        if document_id not in _documents:
            raise DocumentNotFoundError(document_id)
        del _documents[document_id]
        _persist()


def count() -> int:
    _ensure_loaded()
    return len(_documents)
