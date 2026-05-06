"""Publish freshly-inserted articles to Redis pubsub channels per topic so SSE
subscribers can push them to connected clients in real time.

Failure mode: if Redis is unreachable, log and continue. Persistence must never
be blocked by a downstream pubsub problem.
"""

import json

import structlog

from tenjin.api.schemas.article import to_article_out
from tenjin.db.redis import get_redis
from tenjin.models import Article

log = structlog.get_logger(__name__)


def channel_for(topic_slug: str) -> str:
    return f"topic:{topic_slug}"


async def publish_article_to_topics(article: Article, topic_slugs: list[str]) -> None:
    """Publish a JSON-encoded ArticleOut payload to every topic channel that
    matched this article. No-op if topic_slugs is empty.
    """
    if not topic_slugs:
        return

    payload = to_article_out(article).model_dump(mode="json")
    body = json.dumps(payload, separators=(",", ":"))

    try:
        client = get_redis()
        for slug in topic_slugs:
            await client.publish(channel_for(slug), body)
    except Exception as e:
        # Don't propagate — pubsub is best-effort delivery.
        log.warning("publish.failed", article_id=str(article.id), error=str(e))
