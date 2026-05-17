from typing import Optional

from sqlmodel import Field, SQLModel


class QuestionCitation(SQLModel, table=True):
    __tablename__ = "question_citations"

    id: Optional[int] = Field(default=None, primary_key=True)
    question_log_id: int = Field(foreign_key="question_logs.id", index=True)
    document_id: str = Field(index=True)
    filename: str
    page: int
    chunk_id: Optional[str] = Field(default=None, index=True)
    source_marker: Optional[str] = None
