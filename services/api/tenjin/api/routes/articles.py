from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel, HttpUrl

router = APIRouter()


class ArticleOut(BaseModel):
    id: str
    url: HttpUrl
    title: str
    outlet: str
    author: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime
    snippet: str | None = None
    lang: str | None = None
    topics: list[str] = []


@router.get("", response_model=list[ArticleOut])
async def list_articles(
    topic: str | None = Query(default=None, description="Topic slug to filter by"),
    limit: int = Query(default=50, ge=1, le=200),
    before: datetime | None = Query(default=None, description="Cursor: published_at upper bound"),
) -> list[ArticleOut]:
    # TODO: query the articles table joined to topic matches
    return []
