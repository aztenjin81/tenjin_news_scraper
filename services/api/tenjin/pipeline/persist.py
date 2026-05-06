"""Upsert normalized articles into the DB and link them to matching topics."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import literal_column, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from tenjin.models import Article, Topic, TopicMatch
from tenjin.pipeline.normalize import normalize
from tenjin.pipeline.topic_match import match_topics
from tenjin.sources.base import RawItem
from tenjin.topics.registry import all_topics as registry_topics

# Articles older than this are dropped at the pipeline boundary. We're a news
# aggregator, not an archive — and broken/stale RSS feeds (e.g. abandoned
# state-media endpoints) routinely emit headlines from years ago.
MAX_AGE = timedelta(days=30)


async def persist_items(session: AsyncSession, items: list[RawItem]) -> int:
    """Upsert each item and matched topic links. Returns count of newly-inserted articles."""
    if not items:
        return 0

    topic_id_by_slug = await _topic_ids_by_slug(session)
    topics = registry_topics()

    now = datetime.now(UTC)
    cutoff = now - MAX_AGE

    new_count = 0
    for raw in items:
        if not raw.url or not raw.title:
            continue

        # Drop ancient items that broken/abandoned feeds keep emitting.
        # Items without a pubDate are kept (we trust they're roughly current
        # since we just fetched them).
        if raw.published_at is not None and raw.published_at < cutoff:
            continue

        article_data = normalize(raw)
        article_data["fetched_at"] = now
        article_data["source_kind"] = raw.source_kind
        article_data["paywall"] = raw.paywall
        article_data["snippet"] = _short(raw.body)

        article_id, was_new = await _upsert_article(session, article_data)
        if was_new:
            new_count += 1

        matched_slugs = match_topics(article_data, topics)
        for slug in matched_slugs:
            topic_id = topic_id_by_slug.get(slug)
            if topic_id is not None:
                await _upsert_topic_match(session, topic_id, article_id)

    await session.commit()
    return new_count


async def _topic_ids_by_slug(session: AsyncSession) -> dict[str, UUID]:
    rows = (await session.execute(select(Topic.slug, Topic.id))).all()
    return {slug: tid for slug, tid in rows}


async def _upsert_article(session: AsyncSession, data: dict) -> tuple[UUID, bool]:
    """ON CONFLICT (canonical_url) DO UPDATE — refreshes mutable fields, returns id + new flag.

    Uses Postgres `xmax = 0` to reliably detect insert vs update: xmax is 0 on a
    freshly-inserted row and nonzero on a row that was updated in this txn.
    """
    stmt = pg_insert(Article).values(**data)
    update_cols = {
        "fetched_at": stmt.excluded.fetched_at,
        "title": stmt.excluded.title,
        "snippet": stmt.excluded.snippet,
        "outlet": stmt.excluded.outlet,
        "source_kind": stmt.excluded.source_kind,
        "paywall": stmt.excluded.paywall,
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["canonical_url"],
        set_=update_cols,
    ).returning(Article.id, literal_column("(xmax = 0)").label("inserted"))
    row = (await session.execute(stmt)).one()
    return row.id, bool(row.inserted)


async def _upsert_topic_match(session: AsyncSession, topic_id: UUID, article_id: UUID) -> None:
    stmt = (
        pg_insert(TopicMatch)
        .values(topic_id=topic_id, article_id=article_id)
        .on_conflict_do_nothing(index_elements=["topic_id", "article_id"])
    )
    await session.execute(stmt)


def _short(body: str | None, n: int = 240) -> str | None:
    if not body:
        return None
    text = body.strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"
