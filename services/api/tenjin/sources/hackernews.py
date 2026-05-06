import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime

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
        author=data.get("by"),
        published_at=published_at,
        body=data.get("text"),
        extra={"score": data.get("score"), "comments": data.get("descendants", 0)},
    )
