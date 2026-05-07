"""GET /sources — public coverage transparency. 30s in-process cache."""

import time
from typing import Any

from fastapi import APIRouter

from tenjin.api.deps import SessionDep
from tenjin.api.schemas.health import FeedHealthOut, FeedHealthReportOut
from tenjin.pipeline.health import compute_feed_health

router = APIRouter()

_CACHE_TTL_SECONDS = 30
_cache: dict[str, Any] = {"value": None, "expires_at": 0.0}


def _cache_clear() -> None:
    """Reset the in-process cache. Used by tests."""
    _cache["value"] = None
    _cache["expires_at"] = 0.0


@router.get("", response_model=FeedHealthReportOut)
async def get_sources(session: SessionDep) -> FeedHealthReportOut:
    now = time.monotonic()
    if _cache["value"] is not None and now < _cache["expires_at"]:
        return _cache["value"]

    report = await compute_feed_health(session)
    out = FeedHealthReportOut(
        summary=report.summary,
        feeds=[
            FeedHealthOut(
                name=f.name,
                label=f.label,
                kind=f.kind,
                cadence=f.cadence,
                last_item_at=f.last_item_at,
                items_24h=f.items_24h,
                status=f.status,
            )
            for f in report.feeds
        ],
        generated_at=report.generated_at,
    )

    _cache["value"] = out
    _cache["expires_at"] = now + _CACHE_TTL_SECONDS
    return out
