"""
Active feed instances. The scrape worker iterates this list.

When the DB-backed source_configs table is built (admin workstream),
this module will be replaced by a query against that table. For now
it acts as the single source of truth for configured feeds.
"""

from tenjin.sources.hackernews import HackerNewsAdapter
from tenjin.sources.rss import RssAdapter

_R = "https://www.reddit.com/r"


def _reddit(slug: str) -> RssAdapter:
    return RssAdapter(
        name=f"reddit-{slug}",
        feed_url=f"{_R}/{slug}/.rss",
        outlet=f"r/{slug}",
        source_kind="social",
    )


FEEDS = [
    HackerNewsAdapter(limit=50),
    # General news
    _reddit("worldnews"),
    _reddit("news"),
    _reddit("geopolitics"),
    # Tech & science
    _reddit("technology"),
    _reddit("science"),
    # Finance & economics
    _reddit("economics"),
    _reddit("finance"),
    # Environment & climate
    _reddit("environment"),
    _reddit("climate"),
]
