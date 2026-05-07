"""Scrape worker — fetches every adapter, persists results, records telemetry."""

import asyncio
import time
from datetime import UTC, datetime

import httpx
import structlog

from tenjin.db.session import SessionLocal
from tenjin.pipeline.health import record_fetch
from tenjin.pipeline.persist import persist_items
from tenjin.sources.base import SourceAdapter
from tenjin.sources.feeds import FEEDS
from tenjin.topics import presets, registry

log = structlog.get_logger(__name__)


async def run_adapter(adapter: SourceAdapter) -> int:
    """Fetch from an adapter, persist, record telemetry, return new article count."""
    started_at = datetime.now(UTC)
    started_mono = time.monotonic()
    error_kind = "none"
    http_status: int | None = None
    items_yielded = 0
    items_persisted = 0

    try:
        items = await adapter.fetch()
        items_yielded = len(items)
        log.info("adapter.fetched", source=adapter.name, count=items_yielded)

        if items:
            if not registry.all_topics():
                presets.install()
            async with SessionLocal() as session:
                items_persisted = await persist_items(session, items)
            log.info("adapter.persisted", source=adapter.name, new=items_persisted)
    except httpx.TimeoutException:
        error_kind = "timeout"
        log.warning("adapter.timeout", source=adapter.name)
    except httpx.HTTPStatusError as e:
        http_status = e.response.status_code
        error_kind = "http_4xx" if 400 <= http_status < 500 else "http_5xx"
        log.warning("adapter.http_error", source=adapter.name, status=http_status)
    except httpx.HTTPError:
        error_kind = "transport"
        log.warning("adapter.transport_error", source=adapter.name)
    except Exception:
        error_kind = "transport"
        log.exception("adapter.unhandled", source=adapter.name)
    finally:
        duration_ms = int((time.monotonic() - started_mono) * 1000)
        async with SessionLocal() as session:
            await record_fetch(
                session,
                source=adapter.name,
                fetched_at=started_at,
                duration_ms=duration_ms,
                http_status=http_status,
                error_kind=error_kind,
                items_yielded=items_yielded,
                items_persisted=items_persisted,
            )

    return items_persisted


async def run_all() -> dict[str, int]:
    """Run every configured feed in FEEDS sequentially. Returns {name: new_count}."""
    results: dict[str, int] = {}
    for adapter in FEEDS:
        try:
            results[adapter.name] = await run_adapter(adapter)
        except Exception as e:
            log.error("adapter.run_failed", source=adapter.name, error=str(e))
            results[adapter.name] = 0
    return results


def main() -> None:
    """Entry point for `python -m tenjin.workers.scrape` — single batch run."""
    results = asyncio.run(run_all())
    log.info("scrape.complete", results=results)


if __name__ == "__main__":
    main()
