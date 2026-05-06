# Changelog

## [Unreleased]

### Added
- `SECURITY.md`, `CODEOWNERS`, and workflow `permissions: contents: read` hardening
- CI workflow: typecheck, lint, vitest, pytest, gitleaks secret scan
- Dependabot config for npm and GitHub Actions groups
- GitHub Actions pinned to immutable commit SHAs (ci.yml + deploy.yml); Dependabot will keep them current

### Fixed
- `pnpm install --frozen-lockfile` removed from CI so Dependabot npm PRs can pass (lockfile is updated on the branch, not pre-frozen)
- ruff B008 false positive for FastAPI `Query()` defaults suppressed via `ignore = ["B008"]`
- ruff UP017 auto-fixed (`timezone.utc` → `datetime.UTC`) in `services/api/tenjin/sources/rss.py`
- postcss XSS (GHSA-qx2v-qp2m-jg93): pnpm override forces `postcss>=8.5.10` to replace the vulnerable `8.4.31` Next.js 15 pulled in

### Confirmed live
- Ticker on tenjin.us shows live Yahoo Finance market data (not fixture values)
- Next.js 16.2.4: replaced `next lint` (removed in v16) with `eslint .`; migrated `.eslintrc.json` → `eslint.config.mjs` (ESLint flat config via `eslint-config-next/core-web-vitals`)
