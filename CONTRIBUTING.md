# Contributing

Thanks for your interest in Tenjin News Scraper.

## Development Setup

1. Fork and clone the repo.
2. Create a virtual environment: `python -m venv .venv && source .venv/bin/activate`.
3. Install dev dependencies once they're defined: `pip install -r requirements-dev.txt`.
4. Create a feature branch: `git checkout -b your-name/short-description`.

## Pull Requests

- Keep PRs focused on a single change.
- Include tests for new behavior.
- Run lint and tests locally before pushing.
- Reference any related issue in the PR description.

## Adding a New Source

Once the scraper framework lands, each source will live under `tenjin_news_scraper/sources/<source_name>.py` and expose a `Scraper` class implementing the common interface. Until then, open an issue to discuss the source you'd like to add.

## Reporting Issues

Open a GitHub issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Environment details (OS, Python version)
