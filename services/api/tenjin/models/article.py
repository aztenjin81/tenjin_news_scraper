import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from tenjin.models.base import Base, Timestamped


class Article(Base, Timestamped):
    __tablename__ = "articles"
    __table_args__ = (
        Index("ix_articles_canonical_url", "canonical_url", unique=True),
        Index("ix_articles_published_at", "published_at"),
        Index("ix_articles_fetched_at", "fetched_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    outlet: Mapped[str] = mapped_column(String(128), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="wire")
    author: Mapped[str | None] = mapped_column(String(256))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    snippet: Mapped[str | None] = mapped_column(Text)
    lang: Mapped[str | None] = mapped_column(String(8))
    paywall: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
