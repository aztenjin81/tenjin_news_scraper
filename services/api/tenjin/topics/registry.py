from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Topic:
    slug: str
    label: str
    query: str
    terms: tuple[str, ...] = field(default_factory=tuple)


_TOPICS: dict[str, Topic] = {}


def register(topic: Topic) -> None:
    _TOPICS[topic.slug] = topic


def get(slug: str) -> Topic | None:
    return _TOPICS.get(slug)


def all_topics() -> list[Topic]:
    return list(_TOPICS.values())
