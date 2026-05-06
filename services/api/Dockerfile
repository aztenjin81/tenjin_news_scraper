FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

# psycopg[binary] needs no extra system libs but we install curl for healthchecks.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

FROM base AS deps
COPY services/api/pyproject.toml ./
RUN pip install --upgrade pip && pip install -e ".[dev]"

FROM deps AS runtime
COPY services/api ./
RUN useradd --system --create-home --uid 1001 tenjin && \
    chown -R tenjin:tenjin /app
USER tenjin
EXPOSE 8000
CMD ["uvicorn", "tenjin.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
