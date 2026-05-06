"""
Active feed instances. The scrape worker iterates this list.

When the DB-backed source_configs table is built (admin workstream),
this module will be replaced by a query against that table. For now
it acts as the single source of truth for configured feeds.
"""

from tenjin.sources.hackernews import HackerNewsAdapter
from tenjin.sources.rss import RssAdapter

_R = "https://www.reddit.com/r"

FEEDS = [
    # ── HackerNews ────────────────────────────────────────────────────────────
    HackerNewsAdapter(limit=50),
    # ── Reddit — general news ─────────────────────────────────────────────────
    RssAdapter(name="reddit-worldnews", feed_url=f"{_R}/worldnews/.rss", outlet="r/worldnews"),
    RssAdapter(name="reddit-news", feed_url=f"{_R}/news/.rss", outlet="r/news"),
    RssAdapter(
        name="reddit-geopolitics", feed_url=f"{_R}/geopolitics/.rss", outlet="r/geopolitics"
    ),
    # ── Reddit — tech & science ───────────────────────────────────────────────
    RssAdapter(name="reddit-technology", feed_url=f"{_R}/technology/.rss", outlet="r/technology"),
    RssAdapter(name="reddit-science", feed_url=f"{_R}/science/.rss", outlet="r/science"),
    # ── Reddit — finance & economics ──────────────────────────────────────────
    RssAdapter(name="reddit-economics", feed_url=f"{_R}/economics/.rss", outlet="r/economics"),
    RssAdapter(name="reddit-finance", feed_url=f"{_R}/finance/.rss", outlet="r/finance"),
    # ── Reddit — environment ──────────────────────────────────────────────────
    RssAdapter(
        name="reddit-environment", feed_url=f"{_R}/environment/.rss", outlet="r/environment"
    ),
    RssAdapter(name="reddit-climate", feed_url=f"{_R}/climate/.rss", outlet="r/climate"),
]
