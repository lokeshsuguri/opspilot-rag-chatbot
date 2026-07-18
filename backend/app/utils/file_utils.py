"""Small filesystem helpers used by the upload pipeline."""
import os
import uuid
from pathlib import Path

from app.config import get_settings
from app.core.exceptions import FileTooLargeError, InvalidPDFError

settings = get_settings()


def validate_filename(filename: str) -> None:
    """Raise if the filename doesn't have an allowed extension."""
    ext = Path(filename).suffix.lower()
    if ext not in settings.allowed_extensions:
        raise InvalidPDFError(
            f"'{filename}' has an unsupported extension. Only PDF files are accepted."
        )


def validate_size(size_bytes: int, filename: str) -> None:
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise FileTooLargeError(filename, settings.max_file_size_mb)


def generate_document_id() -> str:
    return uuid.uuid4().hex[:12]


def build_storage_path(document_id: str, original_filename: str) -> str:
    os.makedirs(settings.upload_dir, exist_ok=True)
    safe_name = f"{document_id}_{Path(original_filename).name}"
    return os.path.join(settings.upload_dir, safe_name)
