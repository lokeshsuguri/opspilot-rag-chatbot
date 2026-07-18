"""
Chunking strategy.

We chunk per-page (rather than concatenating the whole document first) so
that every chunk can retain an accurate page_number in its metadata for
citations. RecursiveCharacterTextSplitter is used because it tries to break
on paragraph -> sentence -> word boundaries in order, which keeps chunks
semantically coherent instead of cutting mid-sentence.

Chunk size 800 / overlap 150 (~19%) balances two failure modes:
- Too small -> answers lose surrounding context (e.g. a clause number
  defined one sentence above the penalty amount).
- Too large -> irrelevant text dilutes the embedding, hurting retrieval
  precision, and costs more tokens per LLM call.
This range is a well-tested default for dense, prose-heavy operational
documents like SOPs and contracts (as opposed to code or tabular data).
"""
import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings
from app.services.pdf_service import PageContent

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentChunk:
    __slots__ = ("text", "page_number", "chunk_index")

    def __init__(self, text: str, page_number: int, chunk_index: int):
        self.text = text
        self.page_number = page_number
        self.chunk_index = chunk_index


def chunk_pages(pages: list[PageContent]) -> list[DocumentChunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[DocumentChunk] = []
    chunk_index = 0
    for page in pages:
        for piece in splitter.split_text(page.text):
            if piece.strip():
                chunks.append(
                    DocumentChunk(text=piece, page_number=page.page_number, chunk_index=chunk_index)
                )
                chunk_index += 1

    logger.info("Split %d pages into %d chunks", len(pages), len(chunks))
    return chunks
