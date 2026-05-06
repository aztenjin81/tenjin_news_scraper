from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(slots=True)
class RawItem:
    """Raw article-shaped item emitted by a source adapter, pre-normalization."""

    url: str
    title: str
    outlet: str
    published_at: datetime | None = None
    author: str | None = None
    body: str | None = None
    lang: str | None = None
    extra: dict | None = None


class SourceAdapter(Protocol):
    """One adapter per source family (rss, html-outlet, gdelt, x, reddit, ...).

    Adapters must not raise on transient errors. Log and return [] instead — the
    worker treats partial collection as normal.
    """

    name: str

    async def fetch(self) -> list[RawItem]: ...
