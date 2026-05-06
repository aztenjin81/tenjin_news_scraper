# Security policy

## Reporting a vulnerability

If you believe you've found a security issue in Tenjin News, please **don't open a public issue or PR**. Instead, report it privately via GitHub's [security advisories](https://github.com/aztenjin81/tenjin_news_scraper/security/advisories/new) or email the repo owner.

We'll acknowledge within a few days, work with you on a fix, and credit you in the advisory if you'd like.

## Scope

In scope:

- The web app at `apps/web/` and any code it ships to the browser.
- The API service at `services/api/` once it's wired into production.
- The deploy pipeline under `.github/workflows/` and `infra/`.
- The production host configuration documented in `infra/DEPLOY.md`.

Out of scope:

- Vulnerabilities in third-party services (Cloudflare, GitHub Actions, OCI) — report those upstream.
- Issues that require physical access to the production host or compromise of GitHub itself.
- Bugs that don't have a security impact — open a regular issue.

## Operational posture

- The repo is public; the production host runs a self-hosted GitHub Actions runner.
- All workflow changes touching `.github/workflows/**`, `/infra/**`, or `apps/web/Dockerfile` require review from `@aztenjin81` (enforced by `CODEOWNERS`).
- The deploy workflow triggers on `push` to `main` only. PRs from forks cannot run it.
- Secret scanning and push protection are enabled at the repo level.
- Dependabot keeps github-actions, npm, and pip dependencies current.
