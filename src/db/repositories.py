"""Thin repository layer over SQLModel. Each function opens its own session.

Callers should treat these as the only blessed CRUD entry points for the new
domain tables (documents / ingestion_jobs / question_citations).
"""

from datetime import datetime
from typing import Iterable, Optional

from sqlmodel import select

from .engine import session
from .models_citations import QuestionCitation
from .models_documents import Document
from .models_ingestion import IngestionJob


# ==========================================
# DocumentRepo
# ==========================================

class DocumentRepo:
    @staticmethod
    def upsert(
        document_id: str,
        filename: str,
        file_path: str,
        file_size: int,
        page_count: int,
        chunk_count: int,
        owner_id: Optional[int],
        owner_username: str,
        status: str = "indexed",
        indexed_at: Optional[datetime] = None,
    ) -> Document:
        now = indexed_at or datetime.utcnow()
        with session() as s:
            existing = s.exec(
                select(Document).where(Document.document_id == document_id)
            ).first()
            if existing is None:
                doc = Document(
                    document_id=document_id,
                    filename=filename,
                    file_path=file_path,
                    file_size=file_size,
                    page_count=page_count,
                    chunk_count=chunk_count,
                    owner_id=owner_id,
                    owner_username=owner_username,
                    status=status,
                    indexed_at=now,
                )
                s.add(doc)
            else:
                existing.filename = filename
                existing.file_path = file_path
                existing.file_size = file_size
                existing.page_count = page_count
                existing.chunk_count = chunk_count
                existing.owner_id = owner_id
                existing.owner_username = owner_username
                existing.status = status
                existing.indexed_at = now
                existing.deleted_at = None
                s.add(existing)
                doc = existing
            s.commit()
            s.refresh(doc)
            return doc

    @staticmethod
    def get_by_document_id(document_id: str) -> Optional[Document]:
        with session() as s:
            return s.exec(
                select(Document).where(Document.document_id == document_id)
            ).first()

    @staticmethod
    def list_by_owner(owner_id: int, include_deleted: bool = False) -> list[Document]:
        with session() as s:
            stmt = select(Document).where(Document.owner_id == owner_id)
            if not include_deleted:
                stmt = stmt.where(Document.status != "deleted")
            stmt = stmt.order_by(Document.uploaded_at.desc())
            return list(s.exec(stmt))

    @staticmethod
    def list_by_owner_username(
        username: str, include_deleted: bool = False
    ) -> list[Document]:
        with session() as s:
            stmt = select(Document).where(Document.owner_username == username)
            if not include_deleted:
                stmt = stmt.where(Document.status != "deleted")
            stmt = stmt.order_by(Document.uploaded_at.desc())
            return list(s.exec(stmt))

    @staticmethod
    def list_all(include_deleted: bool = False) -> list[Document]:
        with session() as s:
            stmt = select(Document)
            if not include_deleted:
                stmt = stmt.where(Document.status != "deleted")
            stmt = stmt.order_by(Document.owner_username, Document.filename)
            return list(s.exec(stmt))

    @staticmethod
    def count_active() -> int:
        with session() as s:
            return len(
                list(
                    s.exec(
                        select(Document.id).where(Document.status == "indexed")
                    )
                )
            )

    @staticmethod
    def mark_deleted(document_id: str) -> Optional[Document]:
        with session() as s:
            doc = s.exec(
                select(Document).where(Document.document_id == document_id)
            ).first()
            if doc is None:
                return None
            doc.status = "deleted"
            doc.deleted_at = datetime.utcnow()
            s.add(doc)
            s.commit()
            s.refresh(doc)
            return doc

    @staticmethod
    def update_chunk_count(document_id: str, chunk_count: int) -> None:
        with session() as s:
            doc = s.exec(
                select(Document).where(Document.document_id == document_id)
            ).first()
            if doc is None:
                return
            doc.chunk_count = chunk_count
            s.add(doc)
            s.commit()


# ==========================================
# IngestionRepo
# ==========================================

class IngestionRepo:
    @staticmethod
    def start_job(
        filename: str,
        owner_id: Optional[int],
        owner_username: Optional[str],
        document_id: Optional[str] = None,
    ) -> int:
        job = IngestionJob(
            document_id=document_id,
            filename=filename,
            owner_id=owner_id,
            owner_username=owner_username,
            status="started",
        )
        with session() as s:
            s.add(job)
            s.commit()
            s.refresh(job)
            return int(job.id)  # type: ignore[arg-type]

    @staticmethod
    def mark_success(
        job_id: int, chunks_indexed: int, document_id: Optional[str]
    ) -> None:
        with session() as s:
            job = s.get(IngestionJob, job_id)
            if job is None:
                return
            job.status = "success"
            job.chunks_indexed = chunks_indexed
            if document_id is not None:
                job.document_id = document_id
            job.finished_at = datetime.utcnow()
            s.add(job)
            s.commit()

    @staticmethod
    def mark_failed(job_id: int, error_message: str) -> None:
        with session() as s:
            job = s.get(IngestionJob, job_id)
            if job is None:
                return
            job.status = "failed"
            job.error_message = (error_message or "")[:2000]
            job.finished_at = datetime.utcnow()
            s.add(job)
            s.commit()

    @staticmethod
    def list_recent(
        owner_id: Optional[int] = None, limit: int = 50
    ) -> list[IngestionJob]:
        with session() as s:
            stmt = select(IngestionJob)
            if owner_id is not None:
                stmt = stmt.where(IngestionJob.owner_id == owner_id)
            stmt = stmt.order_by(IngestionJob.started_at.desc()).limit(limit)
            return list(s.exec(stmt))


# ==========================================
# CitationRepo
# ==========================================

class CitationRepo:
    @staticmethod
    def bulk_create_for_question(
        question_log_id: int, citations: Iterable
    ) -> int:
        rows: list[QuestionCitation] = []
        for c in citations:
            rows.append(
                QuestionCitation(
                    question_log_id=question_log_id,
                    document_id=_doc_id_from_chunk(getattr(c, "chunk_id", None)),
                    filename=getattr(c, "filename", "") or "",
                    page=int(getattr(c, "page", 0) or 0),
                    chunk_id=getattr(c, "chunk_id", None),
                    source_marker=getattr(c, "source_marker", None),
                )
            )
        if not rows:
            return 0
        with session() as s:
            for r in rows:
                s.add(r)
            s.commit()
        return len(rows)

    @staticmethod
    def list_by_question(question_log_id: int) -> list[QuestionCitation]:
        with session() as s:
            stmt = select(QuestionCitation).where(
                QuestionCitation.question_log_id == question_log_id
            )
            return list(s.exec(stmt))

    @staticmethod
    def count_by_document(document_id: str) -> int:
        with session() as s:
            return len(
                list(
                    s.exec(
                        select(QuestionCitation.id).where(
                            QuestionCitation.document_id == document_id
                        )
                    )
                )
            )


def _doc_id_from_chunk(chunk_id: Optional[str]) -> str:
    """Citations carry chunk_id of form '<doc_id>:<page>:<idx>'."""
    if not chunk_id:
        return ""
    return chunk_id.split(":", 1)[0]
