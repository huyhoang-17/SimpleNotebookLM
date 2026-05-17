from functools import lru_cache

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from ..config import settings


def _build_url() -> str:
    if settings.db_url:
        return settings.db_url
    db_path = settings.app_db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = _build_url()
    if _is_sqlite(url):
        engine = create_engine(
            url,
            echo=False,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
            finally:
                cursor.close()

        return engine

    return create_engine(url, echo=False, pool_pre_ping=True)


def init_db() -> None:
    """Fallback bootstrap when RAG_DB_AUTO_MIGRATE=False.

    In normal operation, src.db.migrate.run_migrations() handles schema.
    """
    from . import base  # noqa: F401 - ensure all models are imported

    SQLModel.metadata.create_all(get_engine())


def session() -> Session:
    return Session(get_engine())
