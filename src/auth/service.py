import logging
import secrets
from datetime import datetime
from typing import Optional

from sqlmodel import select

from ..config import settings
from .db import init_db, session
from .models import User
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
    with session() as s:
        user = s.get(User, user_id)
        if user is None:
            return
        s.delete(user)
        s.commit()


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
