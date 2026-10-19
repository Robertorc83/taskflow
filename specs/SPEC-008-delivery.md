# SPEC-008: Delivery — Docker, Seed Data, Docs & Quality Gates

| Field    | Value    |
|----------|----------|
| Status   | Approved |
| Stories  | —        |
| Features | —        |

## Requirements

- **D1** `docker compose up --build` starts `db` (Postgres 16), `redis` (Redis 7), `api`,
  `worker` and `web`. The API runs migrations and seeds data on start. Health checks gate
  start-up order.
- **D2** The seed is **idempotent** and creates demo users plus about 25 tasks, spread across
  statuses, due dates (including overdue ones) and assignments, so pagination and filters are
  visible straight away.

  | Email               | Password    |
  |---------------------|-------------|
  | `alice@example.com` | `Alice123!` |
  | `bob@example.com`   | `Bob123!`   |
  | `carol@example.com` | `Carol123!` |

- **D3** The backend `Dockerfile` is multi-stage (`uv sync --frozen`), runs as a non-root user,
  and does not install dev dependencies in the final image.
- **D4** `pyproject.toml` is the single place for configuration: dependencies (uv), ruff, mypy,
  pytest, coverage (`fail_under = 80`) and import-linter contracts.
- **D5** `.pre-commit-config.yaml` runs ruff, ruff-format, mypy, import-linter, frontend
  lint/format, and hygiene hooks.
- **D6** The root `Makefile` exposes `up`, `down`, `test`, `test-bdd`, `test-unit`, `lint`, `fmt`,
  `migrate`, `seed`, `web-test` and `e2e`.
- **D7** `README.md` covers the quick start, demo credentials, architecture overview, key
  decisions (links to `docs/adr`), testing strategy and the GenAI section.
- **D8** `docs/ai-usage.md` records prompts, how outputs were validated, and what was corrected.
- **D9** Swagger UI is at `/docs` and ReDoc at `/redoc`. Every endpoint documents its responses.
- **D10** A GitHub Actions workflow runs lint and tests (backend and frontend) on each push.

## Revision history

| Rev | Date       | Change          | Reason | CR |
|-----|------------|-----------------|--------|----|
| 1   | 2026-10-19 | Initial version | —      | —  |
