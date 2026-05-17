"""Backfill documents table from existing Qdrant payloads

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-17
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

log = logging.getLogger("alembic.backfill")


def _scan_qdrant_docs():
    """Yield (document_id, filename, source_path, owner_username, chunk_count) tuples.

    Returns empty list if Qdrant store isn't initialized or collection missing.
    """
    try:
        from src.config import settings
        from src.store import get_client
    except Exception as e:
        log.warning("Backfill skipped: cannot import store (%s)", e)
        return []

    try:
        client = get_client()
        name = settings.qdrant_collection
        if not client.collection_exists(name):
            log.info("Backfill skipped: collection %s does not exist", name)
            return []
    except Exception as e:
        log.warning("Backfill skipped: Qdrant client unavailable (%s)", e)
        return []

    seen: dict[str, dict] = {}
    offset = None
    try:
        while True:
            results, next_offset = client.scroll(
                collection_name=name,
                with_payload=True,
                with_vectors=False,
                offset=offset,
                limit=200,
            )
            for point in results or []:
                payload = point.payload or {}
                meta = payload.get("metadata") or {}
                doc_id = meta.get("document_id")
                if not doc_id:
                    continue
                if doc_id not in seen:
                    seen[doc_id] = {
                        "document_id": doc_id,
                        "filename": meta.get("filename") or "",
                        "source": meta.get("source") or "",
                        "owner_username": meta.get("owner_id"),
                        "chunk_count": 1,
                    }
                else:
                    seen[doc_id]["chunk_count"] += 1
            if next_offset is None:
                break
            offset = next_offset
    except Exception as e:
        log.warning("Backfill scroll failed: %s", e)
        return list(seen.values())

    return list(seen.values())


def upgrade() -> None:
    bind = op.get_bind()
    docs_tbl = sa.table(
        "documents",
        sa.column("document_id", sa.String),
        sa.column("filename", sa.String),
        sa.column("file_path", sa.String),
        sa.column("file_size", sa.Integer),
        sa.column("page_count", sa.Integer),
        sa.column("chunk_count", sa.Integer),
        sa.column("owner_id", sa.Integer),
        sa.column("owner_username", sa.String),
        sa.column("status", sa.String),
        sa.column("uploaded_at", sa.DateTime),
        sa.column("indexed_at", sa.DateTime),
    )

    items = _scan_qdrant_docs()
    if not items:
        return

    user_map: dict[str, int] = {}
    try:
        rows = bind.execute(sa.text("SELECT id, username FROM users")).fetchall()
        user_map = {username: int(uid) for uid, username in rows}
    except Exception as e:
        log.warning("Backfill: failed reading users (%s)", e)

    now = datetime.utcnow()
    inserted = 0
    for item in items:
        doc_id = item["document_id"]
        existing = bind.execute(
            sa.text("SELECT 1 FROM documents WHERE document_id = :did"),
            {"did": doc_id},
        ).first()
        if existing:
            continue

        owner_username = item.get("owner_username") or ""
        owner_id = user_map.get(owner_username) if owner_username else None
        status = "indexed" if owner_id is not None else "orphan"

        file_path = item.get("source") or ""
        file_size = 0
        try:
            if file_path:
                p = Path(file_path)
                if p.exists():
                    file_size = p.stat().st_size
        except Exception:
            file_size = 0

        bind.execute(
            docs_tbl.insert().values(
                document_id=doc_id,
                filename=item.get("filename") or "",
                file_path=file_path,
                file_size=file_size,
                page_count=0,
                chunk_count=int(item.get("chunk_count") or 0),
                owner_id=owner_id,
                owner_username=owner_username or "(unknown)",
                status=status,
                uploaded_at=now,
                indexed_at=now,
            )
        )
        inserted += 1

    log.info("Backfill inserted %d document rows", inserted)


def downgrade() -> None:
    # No-op: backfilled rows are indistinguishable from normal rows.
    pass
