from urllib.parse import urlparse, urlunparse

from tenjin.sources.base import RawItem


def canonical_url(url: str) -> str:
    """Strip tracking params and fragments. Keep path + meaningful query."""
    parsed = urlparse(url)
    drop_params = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid"}
    if parsed.query:
        kept = [
            kv for kv in parsed.query.split("&") if kv.split("=", 1)[0].lower() not in drop_params
        ]
        query = "&".join(kept)
    else:
        query = ""
    return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path, "", query, ""))


def normalize(raw: RawItem) -> dict:
    """Convert a RawItem into the persisted shape. TODO: language detection, entity extraction."""
    return {
        "url": raw.url,
        "canonical_url": canonical_url(raw.url),
        "title": raw.title,
        "outlet": raw.outlet,
        "author": raw.author,
        "published_at": raw.published_at,
        "body": raw.body,
        "lang": raw.lang,
    }
