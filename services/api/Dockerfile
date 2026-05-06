FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

FROM base AS runtime
COPY services/api/ ./
RUN pip install --upgrade pip && pip install .
RUN useradd --system --create-home --uid 1001 tenjin && \
    chown -R tenjin:tenjin /app
USER tenjin
EXPOSE 8000
CMD ["uvicorn", "tenjin.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
