import asyncio
import logging

from fastapi import APIRouter, File, UploadFile

from app.models.schemas import UploadResponse
from app.services import ingestion_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_documents(files: list[UploadFile] = File(...)) -> UploadResponse:
    """
    Accepts one or more PDF files. Each file is processed independently so a
    single bad file (corrupted, scanned-image-only, too large) doesn't block
    the others from succeeding.
    """
    results = []
    for upload in files:
        content = await upload.read()
        # ingest_file() is synchronous, CPU-bound (PDF parsing, chunking,
        # sentence-transformer inference) with no internal await points.
        # Calling it directly here would freeze the entire asyncio event
        # loop -- including /api/health and every other concurrent request
        # -- for the full duration. asyncio.to_thread runs it on a worker
        # thread instead, keeping the server responsive.
        info = await asyncio.to_thread(
            ingestion_service.ingest_file, content, upload.filename or "unnamed.pdf"
        )
        results.append(info)

    ready = sum(1 for r in results if r.status == "ready")
    failed = len(results) - ready
    message = f"{ready} document(s) processed successfully."
    if failed:
        message += f" {failed} document(s) failed — see individual error messages."

    return UploadResponse(documents=results, message=message)
