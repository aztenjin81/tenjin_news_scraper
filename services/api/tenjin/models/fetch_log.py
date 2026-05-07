from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from tenjin.models.base import Base


class FeedFetchLog(Base):
    """One row per scrape-worker fetch attempt. Drives the public /sources page
    and (later) the internal /admin view. Pruned at 30 days by pipeline/prune.py.
    """

    __tablename__ = "feed_fetch_log"
    __table_args__ = (
        Index("ix_feed_fetch_log_source_fetched_at", "source", "fetched_at"),
        Index("ix_feed_fetch_log_fetched_at", "fetched_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    http_status: Mapped[int | None] = mapped_column(Integer)
    error_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    items_yielded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_persisted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
