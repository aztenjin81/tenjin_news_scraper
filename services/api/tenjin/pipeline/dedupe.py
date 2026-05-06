from collections.abc import Iterable


def is_duplicate(canonical_url: str, recent_canonical_urls: Iterable[str]) -> bool:
    """v1: exact canonical-url match against the last 48h. v1.1: MinHash on title+body."""
    return canonical_url in set(recent_canonical_urls)
