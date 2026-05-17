"""High-level document operations spanning Qdrant + filesystem + SQL.

Kept out of src.rag and src.indexing on purpose: those modules represent the
read/write paths for the vector store. This module orchestrates cross-store
side effects (delete from Qdrant + delete file + soft-delete row).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from qdrant_client import models as qmodels

from .config import settings
from .db.repositories import DocumentRepo
from .store import get_client

logger = logging.getLogger(__name__)


class PermissionError_(Exception):
    pass


def delete_document(
    document_id: str,
    requester_user_id: int,
    requester_role: str,
    collection_name: Optional[str] = None,
) -> dict:
    """Atomic-ish delete: Qdrant points → filesystem → SQL soft-delete.

    Raises ValueError if document not found, PermissionError_ if requester
    is not the owner or admin. Returns a small summary dict.
    """
    doc = DocumentRepo.get_by_document_id(document_id)
    if doc is None:
        raise ValueError(f"Document {document_id} not found in DB")

    is_admin = requester_role == "admin"
    if not is_admin and doc.owner_id != requester_user_id:
        raise PermissionError_("Bạn không có quyền xóa tài liệu này.")

    name = collection_name or settings.qdrant_collection
    points_deleted = 0
    try:
        client = get_client()
        if client.collection_exists(name):
            client.delete(
                collection_name=name,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="metadata.document_id",
                                match=qmodels.MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
            )
            points_deleted = doc.chunk_count
    except Exception as e:
        logger.warning("Qdrant delete failed for %s: %s", document_id, e)

    file_removed = False
    try:
        if doc.file_path:
            p = Path(doc.file_path)
            if p.exists():
                p.unlink()
                file_removed = True
    except Exception as e:
        logger.warning("File delete failed for %s: %s", doc.file_path, e)

    DocumentRepo.mark_deleted(document_id)

    return {
        "document_id": document_id,
        "filename": doc.filename,
        "points_deleted": points_deleted,
        "file_removed": file_removed,
    }
