"""Initial schema: users and question_logs

Revision ID: 0001
Revises:
Create Date: 2026-05-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(bind, name: str) -> bool:
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("username", sa.String(length=64), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("role", sa.String(), nullable=False, server_default="user"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("last_login", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_users_username", "users", ["username"], unique=True)
        op.create_index("ix_users_role", "users", ["role"])

    if not _has_table(bind, "question_logs"):
        op.create_table(
            "question_logs",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("username", sa.String(), nullable=False),
            sa.Column("question", sa.String(), nullable=False),
            sa.Column("answer_preview", sa.String(), nullable=True),
            sa.Column("k", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("filenames", sa.String(), nullable=True),
            sa.Column("page_filter", sa.Integer(), nullable=True),
            sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("error_message", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_question_logs_user_id", "question_logs", ["user_id"])
        op.create_index("ix_question_logs_username", "question_logs", ["username"])
        op.create_index("ix_question_logs_created_at", "question_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_question_logs_created_at", table_name="question_logs")
    op.drop_index("ix_question_logs_username", table_name="question_logs")
    op.drop_index("ix_question_logs_user_id", table_name="question_logs")
    op.drop_table("question_logs")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
