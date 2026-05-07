from datetime import datetime

from pydantic import BaseModel


class FeedHealthOut(BaseModel):
    name: str
    label: str
    kind: str
    cadence: str
    last_item_at: datetime | None
    items_24h: int
    status: str


class FeedHealthReportOut(BaseModel):
    summary: dict[str, int]
    feeds: list[FeedHealthOut]
    generated_at: datetime
