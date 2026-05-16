from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, min_length=3, max_length=64)
    email: Optional[str] = Field(default=None, max_length=255)
    password_hash: str
    role: str = Field(default="user", index=True)
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(default=None)


class QuestionLog(SQLModel, table=True):
    __tablename__ = "question_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="users.id")
    username: str = Field(index=True)
    question: str
    answer_preview: Optional[str] = None
    k: int = 5
    filenames: Optional[str] = None
    page_filter: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
