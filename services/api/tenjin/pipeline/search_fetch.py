"""Search-time augmentation: hit query-aware sources, persist results.

Best-effort. Any failure (cache, lock, adapters, persistence) is logged and
swallowed. Search itself returns DB results regardless.
"""

import asyncio
import hashlib

import structlog

from tenjin.db.redis import get_redis
from tenjin.db.session import SessionLocal
from tenjin.pipeline.persist import persist_items
from tenjin.sources.base import RawItem
from tenjin.sources.google_news import GoogleNewsSearchAdapter
from tenjin.sources.hackernews import HackerNewsSearchAdapter

log = structlog.get_logger(__name__)

_CACHE_TTL_SECONDS = 300  # 5 min
_LOCK_TTL_SECONDS = 10


def _q_hash(q: str) -> str:
    # Collapse internal whitespace too, so "shooting arizona" and
    # "shooting  arizona" (two spaces) hit the same cache entry.
    norm = " ".join(q.lower().split()).encode()
    return hashlib.sha256(norm).hexdigest()[:16]


def _cache_key(q: str) -> str:
    return f"search:q:{_q_hash(q)}"


def _lock_key(q: str) -> str:
    return f"search:lock:{_q_hash(q)}"


async def fetch_for_query(q: str) -> None:
    """Best-effort: hit query-aware sources for q, persist new articles."""
    if not q.strip():
        return

    try:
        redis = get_redis()
        if await redis.get(_cache_key(q)):
            return
        acquired = await redis.set(_lock_key(q), "1", nx=True, ex=_LOCK_TTL_SECONDS)
        if not acquired:
            return
    except Exception as e:
        log.warning("search_fetch.redis_unavailable", q=q, error=str(e))
        # Continue without cache/lock — degraded but functional.

    try:
        items = await _gather_search_items(q)
        if items:
            async with SessionLocal() as session:
                await persist_items(session, items)
    except Exception as e:
        log.warning("search_fetch.fetch_or_persist_failed", q=q, error=str(e))
        # Intentionally don't release the lock on failure: it expires in 10 s,
        # and during that window concurrent callers should back off rather
        # than retry the same failing path immediately.
        return

    try:
        redis = get_redis()
        await redis.set(_cache_key(q), "1", ex=_CACHE_TTL_SECONDS)
        await redis.delete(_lock_key(q))
    except Exception as e:
        log.warning("search_fetch.cache_set_failed", q=q, error=str(e))


async def _gather_search_items(q: str) -> list[RawItem]:
    google = GoogleNewsSearchAdapter()
    hn = HackerNewsSearchAdapter()
    results = await asyncio.gather(google.search(q), hn.search(q), return_exceptions=True)

    items: list[RawItem] = []
    for r in results:
        if isinstance(r, Exception):
            log.warning("search_fetch.adapter_failed", q=q, error=str(r))
            continue
        items.extend(r)
    return items
