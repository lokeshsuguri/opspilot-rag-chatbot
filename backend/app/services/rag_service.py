"""
Retrieval-Augmented Generation orchestration.

Responsible for:
1. Conversation memory: an in-memory per-session message history so
   follow-up questions ("and who does it apply to?") can be understood.
2. Query condensation: rewriting a follow-up into a standalone search query
   using the LLM, so retrieval isn't just embedding the bare follow-up
   ("and who does it apply to?") which would retrieve poorly on its own.
3. Retrieval: fetching the most relevant chunks from the vector store.
4. Grounded generation: instructing the LLM to answer strictly from the
   retrieved context and to say clearly when it cannot find the answer.

NOTE ON SCALING: session history is kept in-process memory, which is fine
for a single-instance pilot deployment but will not survive a restart or
work across multiple backend replicas. See README "Known Limitations".
"""
import logging
import threading

from app.config import get_settings
from app.core.exceptions import NoDocumentsUploadedError
from app.models.schemas import ChatMessage, Citation
from app.services import document_registry, llm_service, vectorstore_service

logger = logging.getLogger(__name__)
settings = get_settings()

_NOT_FOUND_MARKER = "could not find this information in the uploaded documents"

_MAX_HISTORY_TURNS = 6  # last N user/assistant turns kept for context

_sessions_lock = threading.Lock()
_sessions: dict[str, list[ChatMessage]] = {}


def _get_history(session_id: str) -> list[ChatMessage]:
    with _sessions_lock:
        return list(_sessions.get(session_id, []))


def _append_history(session_id: str, user_msg: str, assistant_msg: str) -> None:
    with _sessions_lock:
        history = _sessions.setdefault(session_id, [])
        history.append(ChatMessage(role="user", content=user_msg))
        history.append(ChatMessage(role="assistant", content=assistant_msg))
        # Keep only the most recent turns to bound prompt size
        if len(history) > _MAX_HISTORY_TURNS * 2:
            _sessions[session_id] = history[-_MAX_HISTORY_TURNS * 2 :]


def _condense_query(history: list[ChatMessage], follow_up: str) -> str:
    """Rewrite a follow-up question into a standalone search query."""
    if not history:
        return follow_up

    recent = history[-4:]  # last couple of turns is enough context
    transcript = "\n".join(f"{m.role}: {m.content}" for m in recent)

    system_prompt = (
        "You rewrite a follow-up question into a fully standalone question "
        "that makes sense without the conversation history. Only output the "
        "rewritten question, nothing else. If the follow-up is already "
        "standalone, return it unchanged."
    )
    prompt = f"Conversation so far:\n{transcript}\n\nFollow-up question: {follow_up}"

    try:
        rewritten = llm_service.generate_answer(system_prompt, [], prompt)
        return rewritten.strip() or follow_up
    except Exception as exc:
        logger.warning("Query condensation failed, falling back to raw query: %s", exc)
        return follow_up


def _build_context(chunks: list[dict]) -> str:
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        blocks.append(
            f"[Source {i}: {chunk['filename']}, page {chunk['page_number']}]\n{chunk['text']}"
        )
    return "\n\n".join(blocks)


def _build_system_prompt(context: str) -> str:
    return (
        "You are OpsPilot, an internal document assistant for an operations team. "
        "Answer the user's question using ONLY the CONTEXT below, which was retrieved "
        "from their uploaded documents. Follow these rules strictly:\n"
        "1. Do not use any outside knowledge or make assumptions beyond the context.\n"
        "2. If the context does not contain enough information to answer, respond "
        f"exactly with: \"I {_NOT_FOUND_MARKER}.\" Do not guess.\n"
        "3. When you do answer, cite the source(s) inline like (filename, page X).\n"
        "4. Be concise and direct — this is for a busy operations team.\n\n"
        f"CONTEXT:\n{context}"
    )


def chat(
    message: str,
    session_id: str,
    document_ids: list[str] | None,
) -> tuple[str, list[Citation], bool]:

    ready_ids = document_ids or document_registry.list_ready_ids()
    if not ready_ids:
        raise NoDocumentsUploadedError()

    history = _get_history(session_id)

    # Handle simple greetings
    greetings = {
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "thanks",
        "thank you",
    }

    if message.lower().strip() in greetings:
        answer = "Hello! 👋 I'm OpsPilot. Ask me anything about your uploaded documents."
        _append_history(session_id, message, answer)
        return answer, [], True

    search_query = _condense_query(history, message)

    chunks = vectorstore_service.similarity_search(
        query=search_query,
        top_k=settings.retrieval_top_k,
        document_ids=ready_ids,
    )

    if not chunks:
        answer = f"I {_NOT_FOUND_MARKER}."
        _append_history(session_id, message, answer)
        return answer, [], False

    context = _build_context(chunks)
    system_prompt = _build_system_prompt(context)

    history_dicts = [{"role": m.role, "content": m.content} for m in history]

    answer = llm_service.generate_answer(
        system_prompt,
        history_dicts,
        message,
    )

    grounded = _NOT_FOUND_MARKER not in answer.lower()

    citations = (
        [
            Citation(
                filename=c["filename"],
                page_number=c["page_number"],
                document_id=c["document_id"],
                snippet=(c["text"][:220] + "...") if len(c["text"]) > 220 else c["text"],
            )
            for c in chunks
        ]
        if grounded
        else []
    )

    _append_history(session_id, message, answer)
    return answer, citations, grounded


def clear_session(session_id: str) -> None:
    with _sessions_lock:
        _sessions.pop(session_id, None)
