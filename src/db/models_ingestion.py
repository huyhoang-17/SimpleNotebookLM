from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class IngestionJob(SQLModel, table=True):
    __tablename__ = "ingestion_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: Optional[str] = Field(default=None, index=True)
    filename: str
    owner_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    owner_username: Optional[str] = Field(default=None, index=True)
    status: str = Field(default="started", index=True)
    chunks_indexed: int = 0
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    finished_at: Optional[datetime] = None
