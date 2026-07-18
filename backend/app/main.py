"""
OpsPilot backend entrypoint.

Run locally with:
    uvicorn app.main:app --reload --port 8000
"""
import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import chat, documents, health, upload
from app.config import get_settings
from app.core.exceptions import OpsPilotError
from app.core.logging_config import configure_logging
from app.services import vectorstore_service

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OpsPilot API",
    description="Document intelligence assistant — chat grounded strictly in uploaded PDFs.",
    version="1.0.0",
)


@app.on_event("startup")
async def warm_up_vector_store() -> None:
    """
    Load the embedding model and Chroma client once at boot, in a worker
    thread, instead of lazily on a user's first upload request.

    This was the root cause of the upload 502s: without this, the first
    call to embed_documents() happened synchronously inside the async
    /api/upload handler, blocking the entire single-worker event loop for
    the full model download + load duration (and, on Render, that model
    cache didn't even survive a redeploy — see vectorstore_service.py).
    A slow/failed warm-up now shows up clearly in deploy logs at boot
    instead of as an opaque request timeout.
    """
    try:
        await asyncio.to_thread(vectorstore_service.warm_up)
    except Exception:
        logger.exception(
            "Embedding model warm-up failed at startup — uploads will fail "
            "until this is resolved. Check network access to huggingface.co "
            "and the HF_CACHE_DIR / persisted disk configuration."
        )

origins = (
    ["*"] if settings.cors_allowed_origins.strip() == "*"
    else [o.strip() for o in settings.cors_allowed_origins.split(",")]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(OpsPilotError)
async def opspilot_error_handler(request: Request, exc: OpsPilotError) -> JSONResponse:
    logger.warning("Handled error on %s: %s", request.url.path, exc.message)
    return JSONResponse(status_code=exc.status_code, content={"error": exc.__class__.__name__, "detail": exc.message})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "InternalServerError", "detail": "An unexpected error occurred. Please try again."},
    )


app.include_router(health.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/")
def root() -> dict:
    return {"service": "OpsPilot API", "status": "running", "docs": "/docs"}
