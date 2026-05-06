"""Wire-format schema for articles. Used by both REST routes and SSE publishers
so a streamed payload is bit-for-bit identical to a polled one."""

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, HttpUrl

from tenjin.models import Article

SOURCE_LABELS = {
    "wire": "Wire",
    "regional": "Regional",
    "primary": "Primary",
    "social": "Social",
    "analysis": "Analysis",
    "state": "State media",
}

BREAKING_THRESHOLD = timedelta(minutes=20)


class ArticleOut(BaseModel):
    id: str
    url: HttpUrl
    title: str
    outlet: str
    source_kind: str
    source_label: str
    author: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime
    snippet: str | None = None
    lang: str | None = None
    is_breaking: bool = False
    paywall: bool = False


def to_article_out(a: Article, now: datetime | None = None) -> ArticleOut:
    """Convert a SQLAlchemy Article row to its wire format."""
    if now is None:
        now = datetime.now(UTC)
    fetched = a.fetched_at if a.fetched_at.tzinfo else a.fetched_at.replace(tzinfo=UTC)
    return ArticleOut(
        id=str(a.id),
        url=a.url,
        title=a.title,
        outlet=a.outlet,
        source_kind=a.source_kind,
        source_label=SOURCE_LABELS.get(a.source_kind, a.source_kind.title()),
        author=a.author,
        published_at=a.published_at,
        fetched_at=fetched,
        snippet=a.snippet,
        lang=a.lang,
        is_breaking=(now - fetched) < BREAKING_THRESHOLD,
        paywall=a.paywall,
    )
