import re
from collections.abc import Iterable

from tenjin.topics.registry import Topic


def match_topics(article: dict, topics: Iterable[Topic]) -> list[str]:
    """Return slugs of topics whose query terms or entity rules apply to the article."""
    haystack = " ".join(
        filter(None, [article.get("title"), article.get("body"), article.get("outlet")])
    ).lower()
    matched: list[str] = []
    for t in topics:
        if any(re.search(rf"\b{re.escape(term.lower())}\b", haystack) for term in t.terms):
            matched.append(t.slug)
    return matched
