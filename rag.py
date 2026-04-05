from __future__ import annotations

import os
import hashlib
from pathlib import Path

# Older OpenTelemetry protobuf stubs bundled through Chroma can crash against
# newer protobuf runtimes unless we force the pure-Python implementation.
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

import chromadb
from chromadb.config import Settings

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
COLLECTION_NAME = "insurance_policies"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150


def _get_collection():
    client = chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end].strip())
        start += size - overlap
    return [c for c in chunks if c]


def _file_hash(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()


def extract_text_from_pdf(content: bytes) -> str:
    if not HAS_PYMUPDF:
        return ""
    doc = fitz.open(stream=content, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text())
    return "\n".join(pages)


def extract_text_from_docx(content: bytes) -> str:
    if not HAS_DOCX:
        return ""
    import io
    doc = DocxDocument(io.BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(content)
    if ext in (".docx", ".doc"):
        return extract_text_from_docx(content)
    if ext in (".txt", ".md"):
        return content.decode("utf-8", errors="ignore")
    return ""


def ingest_document(file_id: str, filename: str, content: bytes) -> int:
    text = extract_text(filename, content)
    if not text.strip():
        return 0

    chunks = _chunk_text(text)
    collection = _get_collection()

    ids = [f"{file_id}_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "file_id": file_id,
            "filename": filename,
            "chunk_index": i,
            "page_number": i + 1,
        }
        for i in range(len(chunks))
    ]

    existing = set(collection.get(ids=ids)["ids"])
    new_ids = [id_ for id_ in ids if id_ not in existing]
    if not new_ids:
        return 0

    idx_map = {id_: i for i, id_ in enumerate(ids)}
    new_chunks = [chunks[idx_map[id_]] for id_ in new_ids]
    new_meta = [metadatas[idx_map[id_]] for id_ in new_ids]

    collection.add(documents=new_chunks, metadatas=new_meta, ids=new_ids)
    return len(new_ids)


def delete_document(file_id: str) -> None:
    collection = _get_collection()
    results = collection.get(where={"file_id": file_id})
    if results["ids"]:
        collection.delete(ids=results["ids"])


def query_policies(query: str, file_ids: list[str] | None = None, n_results: int = 5) -> list[dict]:
    collection = _get_collection()
    total = collection.count()
    if total == 0:
        return []

    where = None
    if file_ids:
        if len(file_ids) == 1:
            where = {"file_id": file_ids[0]}
        else:
            where = {"$or": [{"file_id": fid} for fid in file_ids]}

    kwargs: dict = {"query_texts": [query], "n_results": min(n_results, total)}
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    output = []
    for doc, meta, dist in zip(docs, metas, distances):
        output.append(
            {
                "content": doc,
                "filename": meta.get("filename", "Unknown"),
                "page_number": meta.get("page_number"),
                "file_id": meta.get("file_id"),
                "relevance_score": round(1 - dist, 3),
            }
        )
    return output


def get_chunk_count(file_id: str) -> int:
    collection = _get_collection()
    results = collection.get(where={"file_id": file_id})
    return len(results["ids"])
