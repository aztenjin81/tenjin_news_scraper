import json
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://tenjin:tenjin@localhost:5432/tenjin"
    redis_url: str = "redis://localhost:6379/0"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # NoDecode skips pydantic-settings' automatic JSON parsing for this list type
    # so we can accept comma-separated values from .env (humans love commas, hate JSON).
    api_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    @field_validator("api_cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("["):
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    newsapi_key: str | None = None
    x_bearer_token: str | None = None
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    telegram_api_id: str | None = None
    telegram_api_hash: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
