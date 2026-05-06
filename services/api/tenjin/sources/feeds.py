"""
Active feed instances. The scrape worker iterates this list.

When the DB-backed source_configs table is built (admin workstream),
this module will be replaced by a query against that table. For now
it acts as the single source of truth for configured feeds.
"""

from tenjin.sources.hackernews import HackerNewsAdapter
from tenjin.sources.rss import RssAdapter

_REDDIT_BASE = "https://www.reddit.com/r"

FEEDS = [
    # ── HackerNews ────────────────────────────────────────────────────────────
    HackerNewsAdapter(limit=50),

    # ── Reddit ────────────────────────────────────────────────────────────────
    # General news
    RssAdapter(name="reddit-worldnews",  feed_url=f"{_REDDIT_BASE}/worldnews/.rss",  outlet="r/worldnews"),
    RssAdapter(name="reddit-news",       feed_url=f"{_REDDIT_BASE}/news/.rss",       outlet="r/news"),
    RssAdapter(name="reddit-geopolitics",feed_url=f"{_REDDIT_BASE}/geopolitics/.rss",outlet="r/geopolitics"),

    # Tech
    RssAdapter(name="reddit-technology", feed_url=f"{_REDDIT_BASE}/technology/.rss", outlet="r/technology"),
    RssAdapter(name="reddit-science",    feed_url=f"{_REDDIT_BASE}/science/.rss",    outlet="r/science"),

    # Finance / economics
    RssAdapter(name="reddit-economics",  feed_url=f"{_REDDIT_BASE}/economics/.rss",  outlet="r/economics"),
    RssAdapter(name="reddit-finance",    feed_url=f"{_REDDIT_BASE}/finance/.rss",    outlet="r/finance"),

    # Environment / climate
    RssAdapter(name="reddit-environment",feed_url=f"{_REDDIT_BASE}/environment/.rss",outlet="r/environment"),
    RssAdapter(name="reddit-climate",    feed_url=f"{_REDDIT_BASE}/climate/.rss",    outlet="r/climate"),
]
