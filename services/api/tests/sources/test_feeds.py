"""Smoke tests for the FEEDS registry — every adapter must be uniquely named
and emit a valid source_kind so the SourcePill component can render it."""

from collections import Counter

from tenjin.sources.feeds import FEEDS

VALID_KINDS = {"wire", "regional", "primary", "social", "analysis", "state"}


def test_all_feeds_have_unique_names():
    names = [f.name for f in FEEDS]
    duplicates = [n for n, c in Counter(names).items() if c > 1]
    assert not duplicates, f"duplicate adapter names: {duplicates}"


def test_all_feeds_emit_known_source_kind():
    for f in FEEDS:
        kind = getattr(f, "source_kind", None)
        assert kind in VALID_KINDS, f"{f.name}: invalid source_kind {kind!r}"


def test_at_least_one_feed_per_kind():
    """Make sure we don't silently lose an entire category in a refactor."""
    kinds = Counter(getattr(f, "source_kind", None) for f in FEEDS)
    for kind in VALID_KINDS:
        assert kinds[kind] >= 1, f"no feeds with source_kind={kind!r}"
