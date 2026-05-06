"""Single async Redis client shared by the publisher and SSE subscribers."""

import redis.asyncio as redis_async

from tenjin.config import get_settings

_client: redis_async.Redis | None = None


def get_redis() -> redis_async.Redis:
    """Lazy singleton — created on first call, reused thereafter.

    Uses the URL from `Settings.redis_url`. `decode_responses=True` so messages
    are str (matches our JSON-encoded payloads) rather than bytes.
    """
    global _client
    if _client is None:
        _client = redis_async.from_url(
            get_settings().redis_url,
            decode_responses=True,
            socket_keepalive=True,
        )
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
