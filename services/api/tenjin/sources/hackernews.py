import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import quote_plus, urlparse

import httpx
import structlog

from tenjin.sources.base import RawItem, SourceAdapter
from tenjin.sources.registry import register

log = structlog.get_logger(__name__)

_BASE = "https://hacker-news.firebaseio.com/v0"
_OUTLET = "Hacker News"


@dataclass
@register("hackernews")
class HackerNewsAdapter(SourceAdapter):
    """Top stories from the Hacker News Firebase API. No credentials required."""

    name: str = "hackernews"
    source_kind: str = "social"
    cadence: str = "fast"
    limit: int = field(default=50)

    async def fetch(self) -> list[RawItem]:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                ids = await _top_ids(client, self.limit)
                stories = await asyncio.gather(
                    *[_fetch_item(client, sid) for sid in ids], return_exceptions=True
                )
        except Exception as e:
            log.warning("hackernews.fetch_failed", error=str(e))
            return []

        items: list[RawItem] = []
        for result in stories:
            if isinstance(result, Exception):
                log.warning("hackernews.item_failed", error=str(result))
                continue
            if result is None:
                continue
            items.append(result)

        log.info("hackernews.fetched", count=len(items))
        return items


async def _top_ids(client: httpx.AsyncClient, limit: int) -> list[int]:
    resp = await client.get(f"{_BASE}/topstories.json")
    resp.raise_for_status()
    return resp.json()[:limit]


async def _fetch_item(client: httpx.AsyncClient, item_id: int) -> RawItem | None:
    resp = await client.get(f"{_BASE}/item/{item_id}.json")
    resp.raise_for_status()
    data = resp.json()

    if not data or data.get("type") != "story" or data.get("dead") or data.get("deleted"):
        return None

    url = data.get("url") or f"https://news.ycombinator.com/item?id={data['id']}"
    published_at = datetime.fromtimestamp(data["time"], tz=UTC) if data.get("time") else None

    return RawItem(
        url=url,
        title=data.get("title", "").strip(),
        outlet=_OUTLET,
        source_kind=HackerNewsAdapter.source_kind,
        author=data.get("by"),
        published_at=published_at,
        body=data.get("text"),
        extra={"score": data.get("score"), "comments": data.get("descendants", 0)},
    )


_ALGOLIA = "https://hn.algolia.com/api/v1/search"
_ALGOLIA_TIMEOUT = 3.0


@dataclass
class HackerNewsSearchAdapter:
    """Query-aware HN adapter using the public Algolia search endpoint.

    No auth required, well-documented, free. Returns story-tagged hits only.
    The outlet is the publisher's domain prefixed with 'via Hacker News' so
    users understand HN was the discovery channel, not the publisher.
    """

    name: str = "hackernews-search"
    source_kind: str = "social"

    async def search(self, q: str) -> list[RawItem]:
        q = q.strip()
        if not q:
            return []

        url = f"{_ALGOLIA}?query={quote_plus(q)}&tags=story&hitsPerPage=50"

        try:
            async with httpx.AsyncClient(timeout=_ALGOLIA_TIMEOUT) as client:
                resp = await client.get(url)
                resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log.warning("hackernews.search_failed", q=q, error=str(e))
            return []

        items: list[RawItem] = []
        for hit in data.get("hits", []):
            link = hit.get("url")
            if not link:
                # Ask HN / Show HN with no external link — skip; we don't want
                # results that point at HN's internal item pages.
                continue
            title = (hit.get("title") or "").strip()
            if not title:
                continue
            host = urlparse(link).netloc.lower() or "Hacker News"
            outlet = f"{host} via Hacker News"
            published = _parse_algolia_date(hit.get("created_at"))
            items.append(
                RawItem(
                    url=link,
                    title=title,
                    outlet=outlet,
                    source_kind=self.source_kind,
                    author=hit.get("author") or hit.get("by"),
                    published_at=published,
                    extra={
                        "score": hit.get("points"),
                        "comments": hit.get("num_comments", 0),
                    },
                )
            )
        log.info("hackernews.searched", q=q, count=len(items))
        return items


def _parse_algolia_date(raw: str | None) -> datetime | None:
    """Algolia uses ISO 8601 with millisecond suffix, e.g. '2026-05-01T16:00:00.000Z'."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None
