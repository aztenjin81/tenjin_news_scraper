from datetime import UTC, datetime

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from tenjin.api.deps import SessionDep
from tenjin.api.schemas.article import ArticleOut, to_article_out
from tenjin.models import Article, Topic, TopicMatch

router = APIRouter()


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
    return [to_article_out(a, now) for a in rows]
