from functools import lru_cache

from sqlmodel import Session, SQLModel, create_engine

from ..config import settings
from . import models  # noqa: F401 - ensure tables are registered with SQLModel.metadata


@lru_cache(maxsize=1)
def get_engine():
    db_path = settings.auth_db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )


def init_db() -> None:
    SQLModel.metadata.create_all(get_engine())


def session() -> Session:
    return Session(get_engine())
