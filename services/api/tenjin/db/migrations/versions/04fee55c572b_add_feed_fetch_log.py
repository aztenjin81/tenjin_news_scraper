"""add feed_fetch_log

Revision ID: 04fee55c572b
Revises: 0f42abaa8399
Create Date: 2026-05-06 22:21:52.125050

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04fee55c572b'
down_revision: Union[str, Sequence[str], None] = '0f42abaa8399'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feed_fetch_log",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error_kind", sa.String(length=16), nullable=False, server_default="none"),
        sa.Column("items_yielded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_persisted", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_feed_fetch_log_source_fetched_at",
        "feed_fetch_log",
        ["source", "fetched_at"],
    )
    op.create_index(
        "ix_feed_fetch_log_fetched_at",
        "feed_fetch_log",
        ["fetched_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_feed_fetch_log_fetched_at", table_name="feed_fetch_log")
    op.drop_index("ix_feed_fetch_log_source_fetched_at", table_name="feed_fetch_log")
    op.drop_table("feed_fetch_log")
