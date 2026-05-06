from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tenjin.api.routes import articles, health, stream, topics
from tenjin.config import get_settings
from tenjin.db.bootstrap import install_topics

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await install_topics()
        log.info("app.topics_installed")
    except Exception as e:
        log.warning("app.topic_install_failed", error=str(e))
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Tenjin News API", version="0.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(articles.router, prefix="/articles", tags=["articles"])
    app.include_router(topics.router, prefix="/topics", tags=["topics"])
    app.include_router(stream.router, prefix="/stream", tags=["stream"])

    return app


app = create_app()
