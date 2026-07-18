from fastapi import APIRouter

from app.models.schemas import DeleteResponse, DocumentListResponse
from app.services import document_registry, ingestion_service

router = APIRouter(tags=["documents"])


@router.get("/documents", response_model=DocumentListResponse)
def list_documents() -> DocumentListResponse:
    documents = document_registry.list_all()
    return DocumentListResponse(documents=documents, total=len(documents))


@router.delete("/documents/{document_id}", response_model=DeleteResponse)
def delete_document(document_id: str) -> DeleteResponse:
    ingestion_service.delete_document(document_id)
    return DeleteResponse(document_id=document_id, message="Document deleted successfully.")
