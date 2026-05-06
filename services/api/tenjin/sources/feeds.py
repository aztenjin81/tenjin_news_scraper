"""
Active feed instances. The scrape worker iterates this list.

When the DB-backed source_configs table is built (admin workstream),
this module will be replaced by a query against that table. For now
it acts as the single source of truth for configured feeds.

Errors per-adapter are normal: feeds change URLs, get retired, or
rate-limit. The adapter logs a warning and returns []; the worker
keeps going.
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


def _rss(name: str, url: str, outlet: str, kind: str) -> RssAdapter:
    return RssAdapter(name=name, feed_url=url, outlet=outlet, source_kind=kind)


FEEDS = [
    # ── Social aggregators ────────────────────────────────────────────────────
    HackerNewsAdapter(limit=50),
    _reddit("worldnews"),
    _reddit("news"),
    _reddit("geopolitics"),
    _reddit("technology"),
    _reddit("science"),
    _reddit("economics"),
    _reddit("finance"),
    _reddit("environment"),
    _reddit("climate"),
    # ── Wire (international news agencies) ────────────────────────────────────
    _rss(
        "bbc-world",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "BBC World",
        "wire",
    ),
    _rss(
        "bbc-middle-east",
        "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
        "BBC Middle East",
        "wire",
    ),
    _rss(
        "ap-world",
        "https://apnews.com/index.rss",
        "AP",
        "wire",
    ),
    # ── Regional outlets ──────────────────────────────────────────────────────
    _rss(
        "al-jazeera",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "Al Jazeera",
        "regional",
    ),
    _rss(
        "times-of-israel",
        "https://www.timesofisrael.com/feed/",
        "Times of Israel",
        "regional",
    ),
    _rss(
        "haaretz",
        "https://www.haaretz.com/srv/htz-latest-headlines",
        "Haaretz",
        "regional",
    ),
    _rss(
        "arab-news",
        "https://www.arabnews.com/rss.xml",
        "Arab News",
        "regional",
    ),
    _rss(
        "the-cradle",
        "https://thecradle.co/feed",
        "The Cradle",
        "regional",
    ),
    # ── State media ───────────────────────────────────────────────────────────
    # Including these is a deliberate editorial choice for transparency on
    # competing narratives. The `state` source_kind makes them visually obvious
    # in the SourcePill component. Treat them as primary sources of *what
    # state X officially says*, not as neutral reporting.
    _rss(
        "tehran-times",
        "https://www.tehrantimes.com/rss",
        "Tehran Times",
        "state",
    ),
    _rss(
        "press-tv",
        "https://www.presstv.ir/rss.xml",
        "Press TV",
        "state",
    ),
    _rss(
        "irna",
        "https://en.irna.ir/rss",
        "IRNA",
        "state",
    ),
    _rss(
        "tass",
        "https://tass.com/rss/v2.xml",
        "TASS",
        "state",
    ),
    _rss(
        "rt",
        "https://www.rt.com/rss/news/",
        "RT",
        "state",
    ),
    _rss(
        "xinhua",
        "http://www.xinhuanet.com/english/rss/worldrss.xml",
        "Xinhua",
        "state",
    ),
    _rss(
        "al-mayadeen",
        "https://english.almayadeen.net/rss",
        "Al Mayadeen",
        "state",
    ),
    # ── Primary (government / IGO press) ──────────────────────────────────────
    _rss(
        "us-state-dept",
        "https://www.state.gov/rss-feeds/press-releases-feed/",
        "US State Department",
        "primary",
    ),
    _rss(
        "us-centcom",
        "https://www.centcom.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=836&max=20",
        "US CENTCOM",
        "primary",
    ),
    _rss(
        "us-dod",
        "https://www.defense.gov/_api/rss/Default.aspx",
        "US Department of Defense",
        "primary",
    ),
    _rss(
        "reliefweb",
        "https://reliefweb.int/rss.xml",
        "UN OCHA ReliefWeb",
        "primary",
    ),
    _rss(
        "iaea",
        "https://www.iaea.org/news/feed",
        "IAEA",
        "primary",
    ),
    # ── Analysis ──────────────────────────────────────────────────────────────
    _rss(
        "isw",
        "https://www.understandingwar.org/news/feed",
        "Institute for the Study of War",
        "analysis",
    ),
    _rss(
        "brookings-foreign-policy",
        "https://www.brookings.edu/topic/foreign-policy/feed/",
        "Brookings",
        "analysis",
    ),
]
