"""
RAG (Retrieval-Augmented Generation) Module for Nova AI.

High-performance, lightweight RAG engine:
- Extracts text from PDFs using PyMuPDF (fitz) or fallback text parser.
- Chunks text into structured segments with page metadata.
- Persists chunks in the SQLite database (DocumentChunk model).
- Uses TF-IDF / lexical relevance ranking to retrieve the most pertinent chunks for Groq completions.
- Zero heavy dependencies (no giant torch/chromadb), fast on both Vercel Serverless and local environments.
"""
import io
import math
import re
from typing import List, Tuple, Optional, Dict
from sqlalchemy.orm import Session

from .models import DocumentChunk
from .database import SessionLocal


def extract_text_from_pdf(file_contents: bytes) -> List[Tuple[int, str]]:
    """
    Extract text from PDF file bytes page by page.
    Returns list of (page_number, text) tuples.
    """
    pages_text: List[Tuple[int, str]] = []

    # 1. Try PyMuPDF (fitz)
    try:
        import fitz
        doc = fitz.open(stream=file_contents, filetype="pdf")
        for i in range(len(doc)):
            page = doc.load_page(i)
            txt = page.get_text("text") or ""
            if txt.strip():
                pages_text.append((i + 1, txt.strip()))
        if pages_text:
            return pages_text
    except Exception:
        pass

    # 2. Fallback: simple text extraction if it's plain text or standard utf-8
    try:
        decoded = file_contents.decode("utf-8", errors="ignore")
        if decoded.strip():
            pages_text.append((1, decoded.strip()))
    except Exception:
        pass

    return pages_text


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> List[str]:
    """
    Split a block of text into overlapping chunks.
    """
    if not text:
        return []
    
    # Split by paragraphs / sentences when possible
    paragraphs = text.split("\n\n")
    chunks: List[str] = []
    current_chunk = ""

    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        
        if len(current_chunk) + len(p) <= chunk_size:
            current_chunk += ("\n\n" if current_chunk else "") + p
        else:
            if current_chunk:
                chunks.append(current_chunk)
            
            # If paragraph itself is longer than chunk_size, split by sliding window
            if len(p) > chunk_size:
                start = 0
                while start < len(p):
                    end = start + chunk_size
                    chunks.append(p[start:end])
                    start += chunk_size - overlap
                current_chunk = ""
            else:
                current_chunk = p

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def process_pdf(
    file_contents: bytes,
    filename: str,
    conversation_id: int,
    db: Optional[Session] = None
) -> int:
    """
    Parse a PDF, chunk it, and store chunks in the database for the given conversation.
    Returns the total number of chunks created.
    """
    pages = extract_text_from_pdf(file_contents)
    if not pages:
        return 0

    close_db_at_end = False
    if db is None:
        db = SessionLocal()
        close_db_at_end = True

    try:
        chunk_records = []
        for page_num, page_text in pages:
            chunks = chunk_text(page_text)
            for c in chunks:
                if c.strip():
                    chunk_records.append(
                        DocumentChunk(
                            conversation_id=conversation_id,
                            filename=filename,
                            page_number=page_num,
                            chunk_text=c.strip()
                        )
                    )

        if chunk_records:
            db.bulk_save_objects(chunk_records)
            db.commit()

        return len(chunk_records)
    finally:
        if close_db_at_end:
            db.close()


def _tokenize(text: str) -> List[str]:
    """Lowercase and extract alphanumeric words."""
    return re.findall(r"\b[a-zA-Z0-9_]{2,}\b", text.lower())


def _compute_relevance_score(query_tokens: List[str], chunk_text: str) -> float:
    """
    Compute BM25 / TF-IDF inspired keyword relevance score between query and chunk.
    """
    if not query_tokens or not chunk_text:
        return 0.0

    chunk_tokens = _tokenize(chunk_text)
    if not chunk_tokens:
        return 0.0

    chunk_len = len(chunk_tokens)
    token_freq: Dict[str, int] = {}
    for t in chunk_tokens:
        token_freq[t] = token_freq.get(t, 0) + 1

    score = 0.0
    for qt in query_tokens:
        if qt in token_freq:
            tf = token_freq[qt] / chunk_len
            # Reward exact matches and term frequency
            score += (tf * 10.0) + 1.0

    return score


def build_context(
    conversation_id: int,
    query: str,
    top_k: int = 5,
    db: Optional[Session] = None
) -> Tuple[str, List[str]]:
    """
    Retrieve the most relevant document chunks for a query in a conversation.
    Returns (formatted_context_string, list_of_citations).
    """
    if not query or not conversation_id:
        return "", []

    close_db_at_end = False
    if db is None:
        db = SessionLocal()
        close_db_at_end = True

    try:
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.conversation_id == conversation_id)
            .all()
        )

        if not chunks:
            return "", []

        query_tokens = _tokenize(query)
        scored_chunks = []

        for c in chunks:
            score = _compute_relevance_score(query_tokens, c.chunk_text)
            scored_chunks.append((score, c))

        # Sort by relevance descending
        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        # Pick top_k (or all if query is generic or few chunks exist)
        selected = [c for score, c in scored_chunks[:top_k]]
        # If no score matched (e.g. "summarize document"), provide first few chunks
        if scored_chunks[0][0] == 0.0 and len(chunks) > 0:
            selected = chunks[:top_k]

        context_parts: List[str] = []
        citations: List[str] = []
        seen_citations = set()

        for c in selected:
            context_parts.append(
                f"[Document: {c.filename}, Page {c.page_number}]\n{c.chunk_text}"
            )
            cit = f"{c.filename} (Page {c.page_number})"
            if cit not in seen_citations:
                citations.append(cit)
                seen_citations.add(cit)

        return "\n\n---\n\n".join(context_parts), citations
    except Exception:
        return "", []
    finally:
        if close_db_at_end:
            db.close()
