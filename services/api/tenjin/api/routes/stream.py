import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()


async def _topic_events(slug: str) -> AsyncIterator[bytes]:
    # TODO: subscribe to redis pubsub channel `topic:{slug}` and yield SSE frames
    while True:
        await asyncio.sleep(15)
        yield b": keepalive\n\n"


@router.get("/topic/{slug}")
async def topic_stream(slug: str) -> StreamingResponse:
    return StreamingResponse(_topic_events(slug), media_type="text/event-stream")


def sse(data: dict) -> bytes:
    return f"data: {json.dumps(data)}\n\n".encode()
