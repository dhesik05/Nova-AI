"""
RAG (Retrieval-Augmented Generation) module.

All heavy imports (fitz, chromadb, sentence-transformers) are lazy-loaded
so the app starts even if these optional packages are not installed.
Falls back to ("", []) silently when RAG dependencies are missing.
"""
import os
import uuid
from typing import List, Tuple


# Resolve paths
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
vector_dir = os.path.join(project_root, "backend", "vector_store")

_client = None
_embed_fn = None

# Flags set at first import attempt
_fitz_ok: bool | None = None
_chroma_ok: bool | None = None


def _check_deps() -> bool:
    """Return True if all RAG deps are available."""
    global _fitz_ok, _chroma_ok
    if _fitz_ok is None:
        try:
            import fitz  # noqa: F401
            _fitz_ok = True
        except ImportError:
            _fitz_ok = False
    if _chroma_ok is None:
        try:
            import chromadb  # noqa: F401
            _chroma_ok = True
        except ImportError:
            _chroma_ok = False
    return bool(_fitz_ok and _chroma_ok)


def get_chroma_client():
    global _client, _embed_fn
    if not _check_deps():
        return None, None

    import chromadb
    from chromadb.utils import embedding_functions
    from chromadb.config import Settings
    from .config import settings as app_settings

    if _client is None:
        IS_VERCEL = os.environ.get("VERCEL") == "1"
        if IS_VERCEL:
            _client = chromadb.Client(settings=Settings(anonymized_telemetry=False))
        else:
            _client = chromadb.PersistentClient(
                path=vector_dir,
                settings=Settings(anonymized_telemetry=False),
            )

    if _embed_fn is None:
        _embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=app_settings.embedding_model_name
        )

    return _client, _embed_fn


def process_pdf(file_contents: bytes, filename: str, conversation_id: int) -> int:
    """Parse a PDF, chunk it and store in ChromaDB. Returns chunk count."""
    if not _check_deps():
        raise RuntimeError(
            "RAG dependencies not installed. "
            "Run: pip install pymupdf chromadb sentence-transformers"
        )

    import fitz  # PyMuPDF

    doc = fitz.open(stream=file_contents, filetype="pdf")
    text_chunks: List[str] = []
    metadatas: List[dict] = []
    ids: List[str] = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        if not text.strip():
            continue

        chunk_size = 1000
        overlap = 150
        i = 0
        while i < len(text):
            chunk = text[i : i + chunk_size]
            if chunk.strip():
                text_chunks.append(chunk.strip())
                metadatas.append({
                    "conversation_id": conversation_id,
                    "page": page_num + 1,
                    "source": filename,
                })
                ids.append(str(uuid.uuid4()))
            i += chunk_size - overlap

    if not text_chunks:
        return 0

    chroma_client, embed_fn = get_chroma_client()
    if chroma_client is None:
        return 0

    collection = chroma_client.get_or_create_collection(
        name="chat_documents", embedding_function=embed_fn
    )

    batch_size = 100
    for i in range(0, len(text_chunks), batch_size):
        collection.add(
            documents=text_chunks[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
            ids=ids[i : i + batch_size],
        )

    return len(text_chunks)


def build_context(
    conversation_id: int, query: str, top_k: int = 5
) -> Tuple[str, List[str]]:
    """Query ChromaDB for relevant context. Returns (context_str, citations)."""
    if not query or not _check_deps():
        return "", []

    chroma_client, embed_fn = get_chroma_client()
    if chroma_client is None:
        return "", []

    try:
        collection = chroma_client.get_collection(
            name="chat_documents", embedding_function=embed_fn
        )
    except Exception:
        return "", []

    try:
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"conversation_id": conversation_id},
        )
    except Exception:
        return "", []

    if not results["documents"] or not results["documents"][0]:
        return "", []

    context_parts: List[str] = []
    citations: List[str] = []
    seen_citations: set = set()

    for doc, meta, _ in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        source = meta.get("source", "Unknown")
        page = meta.get("page", "?")
        context_parts.append(f"Document: {source}, Page {page}\n{doc}")
        cit = f"{source} (Page {page})"
        if cit not in seen_citations:
            citations.append(cit)
            seen_citations.add(cit)

    return "\n\n---\n\n".join(context_parts), citations
