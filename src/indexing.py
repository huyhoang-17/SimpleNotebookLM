import hashlib
import logging
import uuid
from collections import defaultdict
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import settings
from .db.repositories import DocumentRepo, IngestionRepo
from .schemas import ChunkMetadata
from .store import ensure_collection, get_vector_store

logger = logging.getLogger(__name__)


# ==========================================
# PHẦN 1: Đọc tài liệu và chia chunk (Trang 12 - 13)
# ==========================================

def _document_id(path):
    raw = f"{path.name}:{path.stat().st_size}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _chunk_id(doc_id, page, index):
    return f"{doc_id}:{page}:{index}"


def _load_pdf(path, owner_id=None):
    pages = PyPDFLoader(str(path)).load()
    doc_id = _document_id(path)

    for doc in pages:
        page_number = int(doc.metadata.get("page", 0)) + 1
        doc.metadata = {
            "document_id": doc_id,
            "filename": path.name,
            "source": str(path.resolve()),
            "page": page_number,
            "section": doc.metadata.get("section"),
            "owner_id": owner_id,
        }
    return pages


def _splitter(chunk_size=None, chunk_overlap=None):
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.chunk_size,
        chunk_overlap=chunk_overlap or settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        keep_separator=False,
    )


def discover_pdfs():
    return sorted(settings.data_dir.glob("*.pdf"))


def build_chunks(pdf_paths, chunk_size=None, chunk_overlap=None, chunker=None, owner_id=None):
    page_docs = []
    for path in pdf_paths:
        page_docs.extend(_load_pdf(path, owner_id=owner_id))

    splitter = chunker or _splitter(chunk_size, chunk_overlap)
    chunks = splitter.split_documents(page_docs)
    per_doc_counter = defaultdict(int)

    for chunk in chunks:
        doc_id = chunk.metadata["document_id"]
        idx = per_doc_counter[doc_id]
        per_doc_counter[doc_id] += 1

        meta = ChunkMetadata(
            document_id=doc_id,
            filename=chunk.metadata["filename"],
            source=chunk.metadata["source"],
            page=chunk.metadata["page"],
            chunk_id=_chunk_id(doc_id, chunk.metadata["page"], idx),
            section=chunk.metadata.get("section"),
            owner_id=chunk.metadata.get("owner_id"),
        )
        chunk.metadata = meta.model_dump()

    return chunks


# ==========================================
# PHẦN 2: Lưu trữ vào Qdrant (Trang 14 - 15)
# ==========================================

def index_chunks(chunks, collection_name=None):
    if not chunks:
        return 0

    ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, c.metadata["chunk_id"])) for c in chunks]
    get_vector_store(collection_name=collection_name).add_documents(chunks, ids=ids)
    return len(chunks)


def ingest(recreate=False, collection_name=None, chunker=None, chunk_size=None, chunk_overlap=None, owner_id=None):
    pdfs = discover_pdfs()
    ensure_collection(recreate=recreate, collection_name=collection_name)
    chunks = build_chunks(
        pdfs,
        chunker=chunker,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        owner_id=owner_id,
    )
    return index_chunks(chunks, collection_name=collection_name)


def save_and_ingest_pdf(file_bytes, filename, owner_id=None, owner_user_id=None):
    safe_name = Path(filename).name
    dest = settings.data_dir / safe_name
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(file_bytes)

    job_id = IngestionRepo.start_job(
        filename=safe_name,
        owner_id=owner_user_id,
        owner_username=owner_id,
    )

    try:
        ensure_collection(recreate=False)
        chunks = build_chunks([dest], owner_id=owner_id)

        doc_id = chunks[0].metadata["document_id"] if chunks else _document_id(dest)
        page_count = len({c.metadata.get("page") for c in chunks}) if chunks else 0

        chunks_indexed = index_chunks(chunks)

        DocumentRepo.upsert(
            document_id=doc_id,
            filename=safe_name,
            file_path=str(dest.resolve()),
            file_size=dest.stat().st_size,
            page_count=page_count,
            chunk_count=chunks_indexed,
            owner_id=owner_user_id,
            owner_username=owner_id or "(unknown)",
            status="indexed",
        )
        IngestionRepo.mark_success(
            job_id=job_id, chunks_indexed=chunks_indexed, document_id=doc_id
        )
        return {
            "filename": safe_name,
            "chunks_indexed": chunks_indexed,
            "document_id": doc_id,
        }
    except Exception as e:
        IngestionRepo.mark_failed(job_id=job_id, error_message=str(e))
        logger.exception("Ingest failed for %s", safe_name)
        raise
