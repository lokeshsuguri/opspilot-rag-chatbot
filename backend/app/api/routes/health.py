from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import HealthResponse
from app.services import document_registry, vectorstore_service

router = APIRouter(tags=["health"])
settings = get_settings()





@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "environment": settings.environment,
        "llm_configured": bool(settings.groq_api_key),
        "vector_store_ready": vectorstore_service.is_ready(),
        "document_count": document_registry.count(),
    }