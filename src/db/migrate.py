"""Programmatic Alembic runner used at app startup.

Activated by settings.db_auto_migrate (default True). When disabled, callers
should fall back to init_db() for create_all().
"""

from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ALEMBIC_INI = _PROJECT_ROOT / "alembic.ini"


def _build_config() -> Config:
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_PROJECT_ROOT / "alembic"))
    return cfg


def run_migrations() -> None:
    """Run `alembic upgrade head`. Safe to call repeatedly."""
    try:
        cfg = _build_config()
        command.upgrade(cfg, "head")
    except Exception as e:
        logger.exception("Alembic migration failed: %s", e)
        raise
