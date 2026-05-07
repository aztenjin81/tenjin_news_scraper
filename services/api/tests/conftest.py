"""Test session setup.

Windows: psycopg's async mode is incompatible with the ProactorEventLoop that
asyncio uses by default on Windows. Set the SelectorEventLoop policy at
collection time so tests that rely on `_db_reachable()` and other async DB
work see a real connection instead of falling through the except clause.

No-op on Linux/macOS, where the default event loop is already compatible.
"""

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
