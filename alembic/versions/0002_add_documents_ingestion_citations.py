"""Add documents, ingestion_jobs, question_citations

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("document_id", sa.String(length=32), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("owner_username", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="indexed"),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_documents_document_id", "documents", ["document_id"], unique=True)
    op.create_index("ix_documents_filename", "documents", ["filename"])
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])
    op.create_index("ix_documents_owner_username", "documents", ["owner_username"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_uploaded_at", "documents", ["uploaded_at"])

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("document_id", sa.String(length=32), nullable=True),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("owner_username", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="started"),
        sa.Column("chunks_indexed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ingestion_jobs_document_id", "ingestion_jobs", ["document_id"])
    op.create_index("ix_ingestion_jobs_owner_id", "ingestion_jobs", ["owner_id"])
    op.create_index("ix_ingestion_jobs_owner_username", "ingestion_jobs", ["owner_username"])
    op.create_index("ix_ingestion_jobs_status", "ingestion_jobs", ["status"])
    op.create_index("ix_ingestion_jobs_started_at", "ingestion_jobs", ["started_at"])

    op.create_table(
        "question_citations",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "question_log_id",
            sa.Integer(),
            sa.ForeignKey("question_logs.id"),
            nullable=False,
        ),
        sa.Column("document_id", sa.String(length=32), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunk_id", sa.String(), nullable=True),
        sa.Column("source_marker", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_question_citations_question_log_id",
        "question_citations",
        ["question_log_id"],
    )
    op.create_index(
        "ix_question_citations_document_id",
        "question_citations",
        ["document_id"],
    )
    op.create_index(
        "ix_question_citations_chunk_id",
        "question_citations",
        ["chunk_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_question_citations_chunk_id", table_name="question_citations")
    op.drop_index("ix_question_citations_document_id", table_name="question_citations")
    op.drop_index("ix_question_citations_question_log_id", table_name="question_citations")
    op.drop_table("question_citations")

    op.drop_index("ix_ingestion_jobs_started_at", table_name="ingestion_jobs")
    op.drop_index("ix_ingestion_jobs_status", table_name="ingestion_jobs")
    op.drop_index("ix_ingestion_jobs_owner_username", table_name="ingestion_jobs")
    op.drop_index("ix_ingestion_jobs_owner_id", table_name="ingestion_jobs")
    op.drop_index("ix_ingestion_jobs_document_id", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")

    op.drop_index("ix_documents_uploaded_at", table_name="documents")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_owner_username", table_name="documents")
    op.drop_index("ix_documents_owner_id", table_name="documents")
    op.drop_index("ix_documents_filename", table_name="documents")
    op.drop_index("ix_documents_document_id", table_name="documents")
    op.drop_table("documents")
