import logging
import secrets
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Optional

from sqlmodel import delete, select

from ..config import settings
from .db import init_db, session
from .models import QuestionLog, User
from .security import hash_password, verify_password

logger = logging.getLogger(__name__)

VALID_ROLES = {"admin", "user"}


def _ensure_role(role: str) -> str:
    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")
    return role


def get_user_by_username(username: str) -> Optional[User]:
    if not username:
        return None
    with session() as s:
        return s.exec(select(User).where(User.username == username)).first()


def get_user_by_id(user_id: int) -> Optional[User]:
    with session() as s:
        return s.get(User, user_id)


def list_users() -> list[User]:
    with session() as s:
        return list(s.exec(select(User).order_by(User.id)))


def create_user(
    username: str,
    password: str,
    email: Optional[str] = None,
    role: str = "user",
    active: bool = True,
) -> User:
    _ensure_role(role)
    username = username.strip()
    if not username or len(username) < 3:
        raise ValueError("username must be at least 3 characters")
    if not password or len(password) < 6:
        raise ValueError("password must be at least 6 characters")
    if get_user_by_username(username) is not None:
        raise ValueError(f"User '{username}' already exists")

    user = User(
        username=username,
        email=(email or None),
        password_hash=hash_password(password),
        role=role,
        active=active,
    )
    with session() as s:
        s.add(user)
        s.commit()
        s.refresh(user)
    return user


def authenticate(username: str, password: str) -> Optional[User]:
    user = get_user_by_username(username)
    if user is None or not user.active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    with session() as s:
        db_user = s.get(User, user.id)
        if db_user is None:
            return None
        db_user.last_login = datetime.utcnow()
        s.add(db_user)
        s.commit()
        s.refresh(db_user)
        return db_user


def change_password(user_id: int, new_password: str) -> None:
    if not new_password or len(new_password) < 6:
        raise ValueError("password must be at least 6 characters")
    with session() as s:
        user = s.get(User, user_id)
        if user is None:
            raise ValueError("User not found")
        user.password_hash = hash_password(new_password)
        s.add(user)
        s.commit()


def set_role(user_id: int, role: str) -> User:
    _ensure_role(role)
    with session() as s:
        user = s.get(User, user_id)
        if user is None:
            raise ValueError("User not found")
        user.role = role
        s.add(user)
        s.commit()
        s.refresh(user)
        return user


def set_active(user_id: int, active: bool) -> User:
    with session() as s:
        user = s.get(User, user_id)
        if user is None:
            raise ValueError("User not found")
        user.active = active
        s.add(user)
        s.commit()
        s.refresh(user)
        return user


def update_email(user_id: int, email: Optional[str]) -> User:
    with session() as s:
        user = s.get(User, user_id)
        if user is None:
            raise ValueError("User not found")
        user.email = email or None
        s.add(user)
        s.commit()
        s.refresh(user)
        return user


def delete_user(user_id: int) -> None:
    delete_questions_by_user(user_id)
    with session() as s:
        user = s.get(User, user_id)
        if user is None:
            return
        s.delete(user)
        s.commit()


# ==========================================
# Question logging & statistics
# ==========================================

def log_question(
    user_id: int,
    username: str,
    question: str,
    answer_preview: Optional[str] = None,
    k: int = 5,
    filenames: Optional[str] = None,
    page_filter: Optional[int] = None,
    success: bool = True,
    error_message: Optional[str] = None,
) -> None:
    log = QuestionLog(
        user_id=user_id,
        username=username,
        question=question,
        answer_preview=answer_preview,
        k=k,
        filenames=filenames,
        page_filter=page_filter,
        success=success,
        error_message=error_message,
    )
    with session() as s:
        s.add(log)
        s.commit()


def list_questions_by_user(user_id: int, limit: int = 200) -> list[QuestionLog]:
    with session() as s:
        stmt = (
            select(QuestionLog)
            .where(QuestionLog.user_id == user_id)
            .order_by(QuestionLog.created_at.desc())
            .limit(limit)
        )
        return list(s.exec(stmt))


def count_questions_by_user(user_id: int) -> int:
    with session() as s:
        return len(list(s.exec(select(QuestionLog.id).where(QuestionLog.user_id == user_id))))


def delete_questions_by_user(user_id: int) -> int:
    with session() as s:
        rows = list(s.exec(select(QuestionLog).where(QuestionLog.user_id == user_id)))
        count = len(rows)
        if count:
            s.exec(delete(QuestionLog).where(QuestionLog.user_id == user_id))
            s.commit()
        return count


def list_all_questions(limit: int = 10000) -> list[QuestionLog]:
    with session() as s:
        stmt = (
            select(QuestionLog)
            .order_by(QuestionLog.created_at.desc())
            .limit(limit)
        )
        return list(s.exec(stmt))


def top_users_by_questions(limit: int = 10) -> list[tuple[str, int]]:
    with session() as s:
        rows = list(s.exec(select(QuestionLog.username)))
    counter = Counter(rows)
    return counter.most_common(limit)


def questions_per_day(days: int = 30) -> list[tuple[date, int]]:
    if days <= 0:
        return []
    today = date.today()
    cutoff = datetime.combine(today - timedelta(days=days - 1), datetime.min.time())
    with session() as s:
        stmt = select(QuestionLog.created_at).where(QuestionLog.created_at >= cutoff)
        timestamps = list(s.exec(stmt))

    counts: dict[date, int] = {}
    for i in range(days):
        counts[today - timedelta(days=days - 1 - i)] = 0
    for ts in timestamps:
        d = ts.date() if isinstance(ts, datetime) else ts
        if d in counts:
            counts[d] += 1
    return [(d, counts[d]) for d in sorted(counts.keys())]


def success_rate() -> tuple[int, int]:
    with session() as s:
        flags = list(s.exec(select(QuestionLog.success)))
    success_count = sum(1 for f in flags if f)
    error_count = len(flags) - success_count
    return success_count, error_count


def ensure_seed_admin() -> None:
    init_db()
    with session() as s:
        existing = s.exec(select(User)).first()
    if existing is not None:
        return

    username = (settings.admin_username or "admin").strip() or "admin"
    password = settings.admin_password
    generated = False
    if not password:
        password = secrets.token_urlsafe(12)
        generated = True

    create_user(username=username, password=password, role="admin", active=True)

    if generated:
        logger.warning(
            "RAG_ADMIN_PASSWORD not set; seeded admin '%s' with random password: %s",
            username,
            password,
        )
    else:
        logger.info("Seeded admin user '%s' from RAG_ADMIN_PASSWORD.", username)
