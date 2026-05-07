from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class FeedHealthOut(BaseModel):
    name: str
    label: str
    kind: str
    cadence: Literal["fast", "normal", "slow", "rare"]
    last_item_at: datetime | None
    items_24h: int
    status: Literal["ok", "lagging", "silent"]


class FeedHealthReportOut(BaseModel):
    summary: dict[str, int]
    feeds: list[FeedHealthOut]
    generated_at: datetime
