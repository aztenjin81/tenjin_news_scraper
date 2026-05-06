"""DB bootstrap — sync topic presets into the topics table at startup."""

from sqlalchemy.dialects.postgresql import insert as pg_insert

from tenjin.db.session import SessionLocal
from tenjin.models import Topic
from tenjin.topics import presets, registry


async def install_topics() -> None:
    presets.install()
    async with SessionLocal() as session:
        for t in registry.all_topics():
            stmt = (
                pg_insert(Topic)
                .values(slug=t.slug, label=t.label, query=t.query)
                .on_conflict_do_update(
                    index_elements=["slug"],
                    set_={"label": t.label, "query": t.query},
                )
            )
            await session.execute(stmt)
        await session.commit()
