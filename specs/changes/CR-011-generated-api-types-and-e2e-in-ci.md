# CR-011: Generated API types with a drift check; E2E in CI

| Field          | Value |
|----------------|-------|
| Date           | 2026-10-19 |
| Type           | quality gate |
| Specs affected | SPEC-007, SPEC-008 |
| Status         | Implemented |
| Source         | Self-audit: CLAUDE.md promised it, the code didn't do it |

## Motivation

- `CLAUDE.md` says the frontend types are generated from OpenAPI, but `types.ts` was hand-written.
  Nothing would catch the backend and frontend drifting apart.
- The Playwright journey only ran by hand.

## Decision

- **Export:** `python -m taskmanager.presentation.openapi` writes the OpenAPI document without a
  server. `make types` writes `frontend/openapi.json` and `src/api/schema.gen.ts`, and both are
  committed.
- **Types:** `src/api/types.ts` now only *aliases* generated schemas.
- **CI, frontend job:** regenerates both files and fails on any `git diff`.
- **CI, new `e2e` job:** `docker compose up --build --wait`, then Playwright on desktop and mobile.
  This also proves the images build. Logs and traces are uploaded on failure.
- **pre-commit:** hooks installed and run across the whole repository. All 13 pass.

## What the generated types caught immediately

- The client built its synthetic network-error `Problem` without `type`, which the API always
  sends.
- The UI's filter parameters didn't match the API's nullable query types.

## Verification

- [x] Drift check proven: adding a field to `TaskResponse` gives exit code 1 with a 10-line diff;
  regenerating gives exit code 0.
- [x] Running the CI command locally first showed `docker compose up --wait` **exits 1**, because the
  worker had its healthcheck disabled. The new E2E job would have failed on its first run. The
  worker now has a real healthcheck (a Celery `inspect ping` round-trip), and `--wait` exits 0.
- [x] The first local test of the drift check falsely passed, because `git diff` ignores
  untracked files. In CI the files are committed, so the check is real.
