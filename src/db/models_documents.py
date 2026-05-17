from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: str = Field(index=True, unique=True, max_length=32)
    filename: str = Field(index=True)
    file_path: str
    file_size: int = 0
    page_count: int = 0
    chunk_count: int = 0
    owner_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    owner_username: str = Field(index=True)
    status: str = Field(default="indexed", index=True)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    indexed_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
