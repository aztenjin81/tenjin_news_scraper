"""Launch-vertical topic presets: Iran/US and the wider Middle East."""

from tenjin.topics.registry import Topic, register

PRESETS: list[Topic] = [
    Topic(
        slug="iran-us",
        label="Iran / US",
        query="iran us tensions",
        terms=("iran", "irgc", "tehran", "khamenei", "us-iran", "sanctions"),
    ),
    Topic(
        slug="israel-gaza",
        label="Israel / Gaza",
        query="israel gaza",
        terms=("israel", "gaza", "idf", "hamas", "west bank"),
    ),
    Topic(
        slug="houthis-red-sea",
        label="Houthis / Red Sea",
        query="houthis red sea shipping",
        terms=("houthi", "houthis", "red sea", "bab el-mandeb", "ansar allah"),
    ),
    Topic(
        slug="lebanon-hezbollah",
        label="Lebanon / Hezbollah",
        query="lebanon hezbollah",
        terms=("lebanon", "hezbollah", "beirut", "litani"),
    ),
    Topic(
        slug="syria",
        label="Syria",
        query="syria",
        terms=("syria", "damascus", "assad", "idlib"),
    ),
    Topic(
        slug="iraq",
        label="Iraq",
        query="iraq",
        terms=("iraq", "baghdad", "pmf", "kataib hezbollah"),
    ),
    Topic(
        slug="strait-of-hormuz",
        label="Strait of Hormuz",
        query="strait of hormuz incidents",
        terms=("hormuz", "strait of hormuz", "tanker", "irgc navy"),
    ),
]


def install() -> None:
    for t in PRESETS:
        register(t)
