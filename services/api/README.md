# tenjin-api

FastAPI service + scraper workers for Tenjin News.

## Run locally

```bash
# from repo root
docker compose -f infra/docker-compose.yml up -d

cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium

# migrate
alembic upgrade head

# api
uvicorn tenjin.api.app:app --reload

# workers (in a separate terminal)
rq worker scrape
```

## Test

```bash
pytest
ruff check .
mypy tenjin
```

See `CLAUDE.md` for module map and conventions.
