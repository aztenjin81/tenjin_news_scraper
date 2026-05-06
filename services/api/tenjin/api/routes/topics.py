from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select

from tenjin.api.deps import SessionDep
from tenjin.models import Article, Topic, TopicMatch

router = APIRouter()


class TopicOut(BaseModel):
    slug: str
    label: str
    query: str
    article_count_24h: int = 0


@router.get("", response_model=list[TopicOut])
async def list_topics(session: SessionDep) -> list[TopicOut]:
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    counts_q = (
        select(Topic.slug, func.count(TopicMatch.article_id).label("c"))
        .select_from(Topic)
        .join(TopicMatch, TopicMatch.topic_id == Topic.id, isouter=True)
        .join(
            Article,
            (Article.id == TopicMatch.article_id) & (Article.fetched_at >= cutoff),
            isouter=True,
        )
        .group_by(Topic.slug)
    )
    counts = {slug: c for slug, c in (await session.execute(counts_q)).all()}

    rows = (await session.execute(select(Topic).order_by(Topic.label))).scalars().all()
    return [
        TopicOut(slug=t.slug, label=t.label, query=t.query, article_count_24h=counts.get(t.slug, 0))
        for t in rows
    ]


@router.get("/{slug}", response_model=TopicOut)
async def get_topic(session: SessionDep, slug: str) -> TopicOut:
    row = (await session.execute(select(Topic).where(Topic.slug == slug))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="topic not found")

    cutoff = datetime.now(UTC) - timedelta(hours=24)
    count_q = (
        select(func.count(TopicMatch.article_id))
        .join(Article, Article.id == TopicMatch.article_id)
        .where(TopicMatch.topic_id == row.id, Article.fetched_at >= cutoff)
    )
    count = (await session.execute(count_q)).scalar_one()
    return TopicOut(slug=row.slug, label=row.label, query=row.query, article_count_24h=count)
