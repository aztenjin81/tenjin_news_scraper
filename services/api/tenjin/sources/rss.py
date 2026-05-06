from dataclasses import dataclass
from datetime import UTC, datetime

import feedparser
import httpx
import structlog

from tenjin.sources.base import RawItem, SourceAdapter
from tenjin.sources.registry import register

log = structlog.get_logger(__name__)


_DEFAULT_UA = "tenjin-news-bot/1.0 (news aggregator; +https://tenjin.us)"


@dataclass
@register("rss")
class RssAdapter(SourceAdapter):
    """Generic RSS/Atom adapter. One instance per feed URL."""

    name: str
    feed_url: str
    outlet: str
    source_kind: str = "wire"
    paywall: bool = False
    user_agent: str = _DEFAULT_UA

    async def fetch(self) -> list[RawItem]:
        headers = {"User-Agent": self.user_agent}
        try:
            async with httpx.AsyncClient(timeout=15, headers=headers) as client:
                resp = await client.get(self.feed_url)
                resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
        except Exception as e:
            log.warning("rss.fetch_failed", url=self.feed_url, error=str(e))
            return []

        items: list[RawItem] = []
        for entry in parsed.entries:
            published = _parse_date(entry.get("published") or entry.get("updated"))
            items.append(
                RawItem(
                    url=entry.get("link", ""),
                    title=entry.get("title", "").strip(),
                    outlet=self.outlet,
                    source_kind=self.source_kind,
                    paywall=self.paywall,
                    published_at=published,
                    author=entry.get("author"),
                    body=entry.get("summary"),
                )
            )
        return items


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    from email.utils import parsedate_to_datetime

    try:
        dt = parsedate_to_datetime(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None
