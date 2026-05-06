"""SSE endpoints. Subscribes to Redis pubsub and forwards messages to clients."""

import asyncio
import json
from collections.abc import AsyncIterator

import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from tenjin.db.redis import get_redis
from tenjin.pipeline.publish import channel_for

router = APIRouter()
log = structlog.get_logger(__name__)

# Send a comment frame this often when there's no real traffic so that
# proxies / load balancers don't kill the connection on idle timeout.
_KEEPALIVE_SECONDS = 15


def sse(data: dict) -> bytes:
    return f"data: {json.dumps(data)}\n\n".encode()


def sse_event(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


async def _topic_events(slug: str) -> AsyncIterator[bytes]:
    """Subscribe to `topic:{slug}` and yield SSE frames as articles arrive.

    Cleans up the Redis subscription on client disconnect (FastAPI cancels the
    generator, which triggers the `finally` block).
    """
    channel = channel_for(slug)
    client = get_redis()
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe(channel)
    except Exception as e:
        log.warning("stream.subscribe_failed", channel=channel, error=str(e))
        # Even on failure, keep the connection open with keepalives so the
        # client doesn't reconnect-storm us. Redis will recover.
        while True:
            yield b": redis-unavailable\n\n"
            await asyncio.sleep(_KEEPALIVE_SECONDS)

    yield sse_event("ready", {"topic": slug})

    try:
        while True:
            try:
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=_KEEPALIVE_SECONDS
                )
            except Exception as e:
                log.warning("stream.read_failed", channel=channel, error=str(e))
                yield b": redis-error\n\n"
                await asyncio.sleep(_KEEPALIVE_SECONDS)
                continue

            if msg is None:
                # Quiet period — keep the connection warm.
                yield b": keepalive\n\n"
                continue

            if msg.get("type") != "message":
                continue

            try:
                payload = json.loads(msg["data"])
            except (TypeError, ValueError):
                log.warning("stream.bad_payload", channel=channel)
                continue

            yield sse_event("article", payload)
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
        except Exception:
            pass


@router.get("/topic/{slug}")
async def topic_stream(slug: str) -> StreamingResponse:
    return StreamingResponse(
        _topic_events(slug),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering if anyone fronts us
        },
    )
