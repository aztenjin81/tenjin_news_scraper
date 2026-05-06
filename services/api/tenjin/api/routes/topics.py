from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class TopicOut(BaseModel):
    slug: str
    label: str
    query: str
    article_count_24h: int = 0


@router.get("", response_model=list[TopicOut])
async def list_topics() -> list[TopicOut]:
    # TODO: read from topics registry + 24h counts
    return []


@router.get("/{slug}", response_model=TopicOut)
async def get_topic(slug: str) -> TopicOut:
    # TODO: load from registry
    raise HTTPException(status_code=404, detail="topic not found")
