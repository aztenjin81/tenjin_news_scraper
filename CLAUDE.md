# CLAUDE.md

Guidance for Claude Code (and other AI assistants) when working in this repository.

## Project Overview

Tenjin News Scraper is a Python toolkit for scraping news articles from configurable sources, normalizing them into a common schema, and persisting the results.

## Conventions

- **Language**: Python 3.11+
- **Style**: PEP 8, type hints on all public functions
- **Formatting**: Use the formatter configured in `pyproject.toml` once it exists (likely `ruff format`)
- **Tests**: `pytest`, colocated under `tests/` mirroring the package layout
- **Commits**: Imperative mood, scoped subject (`scraper: handle redirects`)

## Working in this repo

- Prefer editing existing modules over creating new ones unless a clear new boundary is warranted.
- Do not commit scraped article payloads, API keys, or `.env` files.
- When adding a new source, follow the pattern in `CONTRIBUTING.md`.

## Useful commands

These commands are placeholders until the toolchain is wired up:

```bash
pytest                  # run tests
ruff check .            # lint
ruff format .           # format
```
