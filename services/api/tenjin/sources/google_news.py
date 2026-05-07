"""Google News query-aware source. Hits the unofficial RSS search endpoint.

URL: https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en

Each item carries:
- A Google News redirect URL in <link> (CBMi-encoded). We use it as-is. Multiple
  queries that surface the same article share the same redirect URL, so the
  existing canonical_url dedup still collapses them — the URL identifies the
  *article* even if it's a Google redirect, not the publisher's URL. Decoding
  to the publisher URL is a follow-up; not v1.
- A <source url="..."> per entry with the actual publisher name. We extract
  this and use it as RawItem.outlet so users see "AZCentral" / "Reuters" /
  etc., not a flat "Google News".
- A title formatted "<actual title> - <outlet>". We strip the trailing
  " - <outlet>" once we know the outlet.
"""

import calendar
import time
import urllib.parse
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import feedparser
import httpx
import structlog

from tenjin.sources.base import RawItem

log = structlog.get_logger(__name__)

_DEFAULT_UA = "tenjin-news-bot/1.0 (news aggregator; +https://tenjin.us)"
_FALLBACK_OUTLET = "Google News"
_TIMEOUT_SECONDS = 3.0


@dataclass
class GoogleNewsSearchAdapter:
    """Query-aware adapter satisfying SearchAdapter protocol."""

    name: str = "google-news"
    source_kind: str = "wire"
    user_agent: str = _DEFAULT_UA

    async def search(self, q: str) -> list[RawItem]:
        q = q.strip()
        if not q:
            return []

        url = (
            "https://news.google.com/rss/search?"
            f"q={urllib.parse.quote_plus(q)}&hl=en-US&gl=US&ceid=US:en"
        )

        headers = {"User-Agent": self.user_agent}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, headers=headers) as client:
                resp = await client.get(url)
                resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
        except Exception as e:
            log.warning("google_news.search_failed", q=q, error=str(e))
            return []

        items: list[RawItem] = []
        for entry in parsed.entries:
            outlet = _extract_outlet(entry)
            title = _strip_outlet_suffix(entry.get("title", "").strip(), outlet)
            published = _to_datetime(entry.get("published_parsed") or entry.get("updated_parsed"))
            link = entry.get("link", "")
            if not link or not title:
                continue
            items.append(
                RawItem(
                    url=link,
                    title=title,
                    outlet=outlet,
                    source_kind=self.source_kind,
                    published_at=published,
                    body=entry.get("summary"),
                )
            )
        return items


def _extract_outlet(entry: Any) -> str:
    """feedparser exposes <source>Outlet Name</source> as entry.source, a
    FeedParserDict whose `title` attribute is the text content. Fall back to
    a flat label if the element is missing.
    """
    source = entry.get("source")
    if source is None:
        return _FALLBACK_OUTLET
    title = source.get("title") if isinstance(source, dict) else getattr(source, "title", None)
    return title.strip() if title else _FALLBACK_OUTLET


def _strip_outlet_suffix(title: str, outlet: str) -> str:
    suffix = f" - {outlet}"
    if title.endswith(suffix):
        return title[: -len(suffix)]
    return title


def _to_datetime(parsed: time.struct_time | None) -> datetime | None:
    """feedparser hands us struct_time in UTC. Convert to aware datetime."""
    if parsed is None:
        return None
    return datetime.fromtimestamp(calendar.timegm(parsed), tz=UTC)
