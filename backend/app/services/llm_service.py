"""
LLM service: wraps the Groq chat model behind a small interface.
"""

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.config import get_settings
from app.core.exceptions import LLMServiceError, MissingAPIKeyError

logger = logging.getLogger(__name__)
settings = get_settings()

_llm: ChatGroq | None = None


def _get_llm() -> ChatGroq:
    global _llm

    if not settings.groq_api_key:
        raise MissingAPIKeyError()

    if _llm is None:
        _llm = ChatGroq(
            model=settings.chat_model,
            groq_api_key=settings.groq_api_key,
            temperature=0.1,
        )

    return _llm


def generate_answer(system_prompt: str, history: list[dict], user_message: str) -> str:
    llm = _get_llm()

    messages = [SystemMessage(content=system_prompt)]

    for turn in history:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))

    messages.append(HumanMessage(content=user_message))

    try:
        response = llm.invoke(messages)
        return response.content

    except Exception as exc:
        logger.exception("Groq API error")
        raise LLMServiceError(str(exc)) from exc