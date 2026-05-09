from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel, Field

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


def list_documents() -> list[DocumentInfo]:
    chunks = fetch_all_chunks()
    counts: dict[str, dict] = {}
    for chunk in chunks:
        doc_id = chunk.metadata.document_id
        if doc_id not in counts:
            counts[doc_id] = {
                "document_id": doc_id,
                "filename": chunk.metadata.filename,
                "chunk_count": 0,
            }
        counts[doc_id]["chunk_count"] += 1
    return [DocumentInfo(**v) for v in counts.values()]


# ==========================================
# Khởi tạo FastAPI & Định nghĩa các Endpoint (Trang 25 - 26)
# ==========================================

app = FastAPI(
    title="RAG Learning API",
    description="Grounded Q&A, summaries, quizzes, and flashcards over indexed PDFs.",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/documents", response_model=list[DocumentInfo])
def documents():
    return list_documents()


@app.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    result = save_and_ingest_pdf(content, file.filename or "")
    return UploadResponse(**result)


@app.post("/ask", response_model=RagAnswer)
def ask(req: AskRequest):
    return answer(req.question, k=req.k, filters=filters_to_dict(req.filters))


@app.post("/summarize", response_model=Summary)
def summarize(req: SummarizeRequest):
    return summarize_learning(
        document=req.document,
        query=req.query,
        filters=filters_to_dict(req.filters),
        k=req.k,
    )


@app.post("/quiz", response_model=QuizSet)
def quiz(req: QuizRequest):
    return generate_quiz(
        document=req.document,
        query=req.query,
        filters=filters_to_dict(req.filters),
        count=req.count,
        k=req.k,
    )


@app.post("/flashcards", response_model=FlashcardSet)
def flashcards(req: FlashcardsRequest):
    return generate_flashcards(
        document=req.document,
        query=req.query,
        filters=filters_to_dict(req.filters),
        count=req.count,
        k=req.k,
    )
