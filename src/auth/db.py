"""Backward-compatible re-export.

Historical import path: `from src.auth.db import get_engine, init_db, session`.
The real implementation now lives in `src.db.engine`.
"""

from ..db.engine import get_engine, init_db, session

__all__ = ["get_engine", "init_db", "session"]
