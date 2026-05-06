from datetime import UTC, datetime

from fastapi import APIRouter, Query
from sqlalchemy import func, or_, select

from tenjin.api.deps import SessionDep
from tenjin.api.schemas.article import ArticleOut, to_article_out
from tenjin.models import Article, Topic, TopicMatch

router = APIRouter()

_MAX_TERMS = 8
_MIN_TERM_LEN = 2


@router.get("", response_model=list[ArticleOut])
async def list_articles(
    session: SessionDep,
    topic: str | None = Query(default=None, description="Topic slug to filter by"),
    q: str | None = Query(default=None, description="Free-text search across title and snippet"),
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

    if q:
        terms = _parse_query(q)
        for term in terms:
            pattern = f"%{term}%"
            stmt = stmt.where(
                or_(
                    Article.title.ilike(pattern),
                    Article.snippet.ilike(pattern),
                )
            )
        # If after parsing nothing remains (e.g. the query was just punctuation),
        # short-circuit: a too-broad query shouldn't return everything.
        if not terms:
            return []

    if before:
        stmt = stmt.where(display_at < before)

    stmt = stmt.order_by(display_at.desc()).limit(limit)

    rows = (await session.execute(stmt)).scalars().all()
    now = datetime.now(UTC)
    return [to_article_out(a, now) for a in rows]


def _parse_query(q: str) -> list[str]:
    """Split free-text search into ILIKE terms.

    - Whitespace-tokenized and lowercased
    - Tokens shorter than _MIN_TERM_LEN are dropped so a stray 'a' or 'i'
      doesn't match every row
    - Capped at _MAX_TERMS to keep the query plan cheap

    Users who include literal `%` or `_` in their search will get LIKE wildcard
    behavior — fine for a search box (you'd have to type those deliberately).
    """
    return [t for t in q.lower().split() if len(t) >= _MIN_TERM_LEN][:_MAX_TERMS]
