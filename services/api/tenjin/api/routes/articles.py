from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Query
from pydantic import BaseModel, HttpUrl
from sqlalchemy import func, select

from tenjin.api.deps import SessionDep
from tenjin.models import Article, Topic, TopicMatch

router = APIRouter()

_LABELS = {
    "wire": "Wire",
    "regional": "Regional",
    "primary": "Primary",
    "social": "Social",
    "analysis": "Analysis",
    "state": "State media",
}
_BREAKING_THRESHOLD = timedelta(minutes=20)


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


@router.get("", response_model=list[ArticleOut])
async def list_articles(
    session: SessionDep,
    topic: str | None = Query(default=None, description="Topic slug to filter by"),
    limit: int = Query(default=50, ge=1, le=200),
    before: datetime | None = Query(default=None, description="Cursor: display-time upper bound"),
) -> list[ArticleOut]:
    # Display order: most-recently-published first, falling back to fetched time
    # when the feed didn't supply a pubDate. Sorting by fetched_at alone clusters
    # results by feed (the scheduler processes feeds sequentially, so each feed's
    # items share a fetched_at within microseconds of each other).
    display_at = func.coalesce(Article.published_at, Article.fetched_at)

    stmt = select(Article)

    if topic:
        stmt = (
            stmt.join(TopicMatch, TopicMatch.article_id == Article.id)
            .join(Topic, Topic.id == TopicMatch.topic_id)
            .where(Topic.slug == topic)
        )

    if before:
        stmt = stmt.where(display_at < before)

    stmt = stmt.order_by(display_at.desc()).limit(limit)

    rows = (await session.execute(stmt)).scalars().all()
    now = datetime.now(UTC)
    return [_to_out(a, now) for a in rows]


def _to_out(a: Article, now: datetime) -> ArticleOut:
    fetched = a.fetched_at if a.fetched_at.tzinfo else a.fetched_at.replace(tzinfo=UTC)
    return ArticleOut(
        id=str(a.id),
        url=a.url,
        title=a.title,
        outlet=a.outlet,
        source_kind=a.source_kind,
        source_label=_LABELS.get(a.source_kind, a.source_kind.title()),
        author=a.author,
        published_at=a.published_at,
        fetched_at=fetched,
        snippet=a.snippet,
        lang=a.lang,
        is_breaking=(now - fetched) < _BREAKING_THRESHOLD,
        paywall=a.paywall,
    )
