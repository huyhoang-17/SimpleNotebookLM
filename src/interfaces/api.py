from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, UploadFile
from pydantic import BaseModel, Field

from ..auth.deps import get_current_user, owner_filter_for
from ..auth.models import User
from ..auth.router import router as auth_router
from ..auth.service import ensure_seed_admin
from ..filters import MetadataFilter, filters_to_dict
from ..indexing import save_and_ingest_pdf
from ..learning import generate_flashcards, generate_quiz, summarize as summarize_learning
from ..rag import answer, fetch_all_chunks
from ..schemas import FlashcardSet, QuizSet, RagAnswer, Summary


# ==========================================
# Định nghĩa các Request / Response Schema (Trang 25)
# ==========================================

class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    owner_id: str | None = None


class UploadResponse(BaseModel):
    filename: str
    chunks_indexed: int


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    k: int | None = Field(default=None, ge=1, le=64)
    filters: MetadataFilter | None = None


class SummarizeRequest(BaseModel):
    document: str | None = None
    query: str | None = None
    filters: MetadataFilter | None = None
    k: int | None = Field(default=None, ge=1, le=64)


class QuizRequest(BaseModel):
    document: str | None = None
    query: str | None = None
    filters: MetadataFilter | None = None
    count: int | None = Field(default=None, ge=1, le=50)
    k: int | None = Field(default=None, ge=1, le=64)


class FlashcardsRequest(QuizRequest):
    pass


def _merge_filters(req_filters: MetadataFilter | None, user: User) -> dict | None:
    base = filters_to_dict(req_filters) or {}
    base.update(owner_filter_for(user))
    return base or None


def _list_documents_for(user: User) -> list[DocumentInfo]:
    chunks = fetch_all_chunks(filters=owner_filter_for(user) or None)
    counts: dict[str, dict] = {}
    for chunk in chunks:
        doc_id = chunk.metadata.document_id
        if doc_id not in counts:
            counts[doc_id] = {
                "document_id": doc_id,
                "filename": chunk.metadata.filename,
                "owner_id": chunk.metadata.owner_id,
                "chunk_count": 0,
            }
        counts[doc_id]["chunk_count"] += 1
    return [DocumentInfo(**v) for v in counts.values()]


# ==========================================
# Khởi tạo FastAPI & Định nghĩa các Endpoint (Trang 25 - 26)
# ==========================================


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_seed_admin()
    yield


app = FastAPI(
    title="RAG Learning API",
    description="Grounded Q&A, summaries, quizzes, and flashcards over indexed PDFs.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/documents", response_model=list[DocumentInfo])
def documents(user: User = Depends(get_current_user)):
    return _list_documents_for(user)


@app.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    content = await file.read()
    result = save_and_ingest_pdf(content, file.filename or "", owner_id=user.username)
    return UploadResponse(**result)


@app.post("/ask", response_model=RagAnswer)
def ask(req: AskRequest, user: User = Depends(get_current_user)):
    return answer(req.question, k=req.k, filters=_merge_filters(req.filters, user))


@app.post("/summarize", response_model=Summary)
def summarize(req: SummarizeRequest, user: User = Depends(get_current_user)):
    return summarize_learning(
        document=req.document,
        query=req.query,
        filters=_merge_filters(req.filters, user),
        k=req.k,
    )


@app.post("/quiz", response_model=QuizSet)
def quiz(req: QuizRequest, user: User = Depends(get_current_user)):
    return generate_quiz(
        document=req.document,
        query=req.query,
        filters=_merge_filters(req.filters, user),
        count=req.count,
        k=req.k,
    )


@app.post("/flashcards", response_model=FlashcardSet)
def flashcards(req: FlashcardsRequest, user: User = Depends(get_current_user)):
    return generate_flashcards(
        document=req.document,
        query=req.query,
        filters=_merge_filters(req.filters, user),
        count=req.count,
        k=req.k,
    )
