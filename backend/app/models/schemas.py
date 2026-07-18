"""Pydantic models shared across API routes."""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DocumentInfo(BaseModel):
    """Metadata about a single uploaded document."""

    document_id: str
    filename: str
    page_count: int
    chunk_count: int
    status: DocumentStatus
    uploaded_at: datetime
    error_message: str | None = None


class UploadResponse(BaseModel):
    documents: list[DocumentInfo]
    message: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]
    total: int


class DeleteResponse(BaseModel):
    document_id: str
    message: str


class Citation(BaseModel):
    filename: str
    page_number: int
    document_id: str
    snippet: str = Field(description="Short excerpt of the chunk used to ground the answer")


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(
        default="default", description="Groups messages into one conversation thread"
    )
    document_ids: list[str] | None = Field(
        default=None,
        description="Optional filter: restrict retrieval to these document IDs only",
    )


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    session_id: str
    grounded: bool = Field(
        description="False when the model could not find relevant context and said so"
    )


class HealthResponse(BaseModel):
    status: str
    environment: str
    llm_configured: bool
    vector_store_ready: bool
    document_count: int


class ErrorResponse(BaseModel):
    error: str
    detail: str
