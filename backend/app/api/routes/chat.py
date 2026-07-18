import logging

from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse
from app.services import rag_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    answer, citations, grounded = rag_service.chat(
        message=request.message,
        session_id=request.session_id,
        document_ids=request.document_ids,
    )
    return ChatResponse(
        answer=answer,
        citations=citations,
        session_id=request.session_id,
        grounded=grounded,
    )
