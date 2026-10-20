# Taskflow — Task Management API + Web App

[![CI](https://github.com/Robertorc83/taskflow/actions/workflows/ci.yml/badge.svg)](https://github.com/Robertorc83/taskflow/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A multi-user task manager. Users can create, assign, complete, filter and paginate tasks.

- **Backend:** FastAPI, built with **Clean Architecture** and **BDD**.
- **Frontend:** React + TypeScript.
- **Services:** PostgreSQL, Redis, and a Celery worker for notifications.

| | |
|---|---|
| **Backend tests** | 188 tests (79 Gherkin scenario runs, 104 unit, 5 integration), **97.1% line+branch coverage**, real Postgres |
| **Frontend tests** | 66 component tests (97.0% statements) + Playwright journey on desktop and mobile |
| **Static checks** | `mypy --strict` · ruff · 5 import-linter architecture contracts · ESLint strict with module-boundary rules · Prettier |

---

## Quick start

```bash
docker compose up --build        # or: make up
```

| URL | What |
|-----|------|
| http://localhost:3000 | Web app |
| http://localhost:8000/docs | Swagger UI (click **Authorize** and paste an `access_token`) |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/health | Health check, including the database |

### Demo credentials

The compose stack seeds these on API start (idempotent). The image itself never seeds demo users
and refuses the dev JWT secret: it defaults to `ENVIRONMENT=production` and fails closed (CR-002).

| Email | Password |
|-------|----------|
| `alice@example.com` | `Alice123!` |
| `bob@example.com` | `Bob12345!` |
| `carol@example.com` | `Carol123!` |

### HTTPS

```bash
make up-tls      # self-signed certificate in certs/, then the same stack on https://localhost
```

The web image terminates TLS itself (TLS 1.2+, HTTP/2, HSTS) and **refuses to start without a
certificate** (CR-012). The default `make up` opts out with `NGINX_TLS=false` so the demo needs no
certificate. In a real deployment, mount the CA-issued certificate and key at
`/etc/nginx/certs/tls.crt` and `tls.key`, or set `NGINX_TLS=false` when a load balancer terminates
TLS in front of it.

The seed creates 25 tasks across all statuses, including overdue ones and tasks assigned between
users, so filters and pagination have something to show. To watch notifications as you assign or
complete tasks, run `make logs`.

### Local development (without Docker for the app)

Requirements: Python 3.12 + [uv](https://docs.astral.sh/uv/), Node 22+, Docker (for Postgres and
Redis, and for the test database).

```bash
make install                              # uv sync, npm ci, pre-commit hooks
docker compose up -d db redis             # infrastructure only (loopback: db 55432, redis 6380)
cp .env.example backend/.env
cd backend && uv run alembic upgrade head && uv run python -m taskmanager.seed
uv run uvicorn taskmanager.main:app --reload                               # API on :8000
uv run celery -A taskmanager.infrastructure.tasks.worker worker -l INFO     # worker
cd ../frontend && npm run dev                                              # web on :5173
```

### Commands

```bash
make test        # backend: all tests + coverage gate (starts a throwaway Postgres container)
make test-bdd    # backend: Gherkin scenarios only, verbose
make test-unit   # backend: unit tests, no database (< 1 s)
make lint        # ruff, mypy --strict, import-linter, eslint, tsc, prettier
make web-test    # frontend tests + coverage
make types       # regenerate frontend API types from the backend's OpenAPI document
make e2e         # Playwright against the running stack
make tls-check   # black-box TLS checks on the web image
make help        # everything else
```

---

## How this project was built: specs → BDD → code

```
User story ──► specs/SPEC-NNN.md ──► backend/tests/features/*.feature ──► step defs ──► code
                    ▲                (written first, run red)
   specs/changes/CR-NNN.md  ── every later change or fix is a Change Request
```

- [`specs/`](specs/README.md) holds one spec per capability. Each spec has numbered business
  rules (R1…), an API contract, acceptance criteria and a revision history.
- The `.feature` files are the executable side of each spec. Step definitions talk to the API only
  over HTTP.
- After a spec is approved, changes go through a **Change Request**.
  [CR-001](specs/changes/CR-001-bound-latency-on-broker-outage.md) is a real one from this build.
  A passing test still hid a 6-second hang during a broker outage. The fix went spec → red
  scenario → fix → green.
- [`CLAUDE.md`](CLAUDE.md) is the engineering rulebook. It also serves as the standing prompt for
  AI assistance.

## Architecture

```
backend/src/taskmanager/
├── domain/           Task, User entities (invariants), TaskStatus, domain events, errors
├── application/      use cases, ports (Protocols), DTOs, application errors
├── infrastructure/   SQLAlchemy repos + Unit of Work, Alembic, JWT, Argon2, Celery, rate limiter
├── presentation/     FastAPI routers, Pydantic schemas, RFC 9457 error mapping, DI wiring
├── main.py           API composition root
└── seed.py           demo data
```

- **Dependency rule.** Code depends inward only. The domain and application layers import no
  frameworks. **import-linter enforces this in CI** (`pyproject.toml → [tool.importlinter]`).
- **Two composition roots over the same use cases.** The API (`infrastructure/container.py`) and
  the Celery worker (`infrastructure/tasks/runtime.py`).
- **Authorization lives in use cases, not routers.**
  - A task you can't see returns **404**, so the API doesn't reveal that it exists.
  - A task you can see but may not change returns **403**.
  - The owner may edit, assign and delete; the assignee may view and complete.
- **Events are published after commit**, so a rolled-back change never sends a notification.
  Publishing has a time limit, so a broker outage can't stall requests.

```
frontend/src/
├── app/              router, providers, shell
├── api/              typed HTTP client (bearer + single-flight refresh), endpoints, types
├── features/auth/    login/register pages, AuthProvider
├── features/tasks/   list page, card, form, filters, hooks (TanStack Query), zod schemas
├── components/ui/    design-system primitives (Button, Field, Modal, Badge, Pagination…)
└── lib/              dates, errors, query keys
```

- **Server state** lives only in TanStack Query.
- **Filters, scope, sorting and page** live in the URL, so a view can be shared and the back
  button works.
- **"Complete" is optimistic** and rolls back if the request fails.
- **Server 422 errors** are mapped onto the matching form fields.

### API overview

All endpoints are under `/api/v1`. Errors use `application/problem+json`.

| Method & path | Who | Notes |
|---------------|-----|-------|
| `POST /auth/register` · `/auth/login` · `/auth/refresh` | anyone | rate limited per IP |
| `GET /users/me` · `GET /users` | authenticated | user list feeds the assignee picker |
| `GET /tasks` | authenticated | `scope`, `status`, `due_from`, `due_to`, `ordering`, `page`, `size ≤ 100` |
| `POST /tasks` | authenticated | optional `assignee_id` |
| `GET /tasks/{id}` | owner or assignee | |
| `PATCH /tasks/{id}` | owner | partial update; `null` clears a field; setting status back to pending reopens a completed task |
| `DELETE /tasks/{id}` | owner | |
| `PUT /tasks/{id}/assignee` | owner | `{"assignee_id": null}` unassigns |
| `POST /tasks/{id}/complete` | owner or assignee | completing twice returns 409; concurrent completes serialize (row lock) |
| `POST /tasks/{id}/reopen` | owner or assignee | reopening an open task returns 409 |

Send `X-Timezone: <IANA zone>` (the web app does) so "today" and `is_overdue` follow the user's calendar.

## Key decisions

Each decision has an Architecture Decision Record (ADR) in [`docs/adr/`](docs/adr):

| ADR | Decision |
|-----|----------|
| [0001](docs/adr/0001-fastapi.md) | FastAPI over DRF: OpenAPI from types, async, explicit DI |
| [0002](docs/adr/0002-clean-architecture.md) | Ports and adapters, **enforced** by import-linter |
| [0003](docs/adr/0003-bdd-outside-in.md) | pytest-bdd outside-in; fakes over mocks |
| [0004](docs/adr/0004-real-postgres-in-tests.md) | Real Postgres in tests, built by running the migrations, with a drift check |
| [0005](docs/adr/0005-explicit-action-endpoints.md) | Separate endpoints for complete and assign |
| [0006](docs/adr/0006-jwt-argon2.md) | JWT access + refresh tokens with a `type` claim; Argon2 hashing |
| [0007](docs/adr/0007-celery-notifications.md) | Celery notifications after commit (outbox as future work) |
| [0008](docs/adr/0008-rate-limiting-and-pagination.md) | `limits`-based rate-limit dependencies; offset pagination |

## Testing strategy

| Layer | Where | Runs against |
|-------|-------|--------------|
| Acceptance (BDD) | `backend/tests/features` + `tests/step_defs` | Real HTTP app + Postgres (testcontainers), Celery in eager mode |
| Application unit | `tests/unit/application` | In-memory fakes (`tests/fakes.py`) |
| Domain unit | `tests/unit/domain` | Pure Python |
| Integration | `tests/integration` | Postgres: migration drift, seed, DB constraints, race conditions |
| Frontend components | `frontend/src/**/*.test.tsx` | Vitest + Testing Library + MSW; **any console warning fails a test** |
| End-to-end | `frontend/e2e/smoke.spec.ts` | Full Docker stack; desktop + mobile; asserts a clean browser console |

Two settings keep the backend suite honest:
- **Warnings are errors** (`filterwarnings = error`), so deprecated APIs surface immediately.
- **Coverage counts branches and is read, not just thresholded.** That is how the hidden 6-second
  hang behind CR-001 was found.

## Independent review round

After the first version, four review sub-agents audited **clean architecture, security,
modularity and correctness** in parallel. They worked read-only, and every claim had to come with
evidence. I reproduced the main findings myself before fixing them. Each fix went through a change
request, CR-002 to CR-009, with a failing test first. Highlights:

- **Rate-limit bypass:** a spoofed `X-Forwarded-For` reset the login limit. Fixed with
  trusted-proxy-only settings, verified live.
- **Unsafe defaults:** the public dev JWT secret was accepted, and demo users were seeded in every
  environment. The image now fails closed.
- **Race condition:** parallel `complete` calls all succeeded. Fixed with a row lock and a
  concurrency test on real Postgres.
- **Contradicting specs:** an assignee's Reopen button always got a 403. Fixed with an explicit
  reopen command (CR-004).
- **Time zones:** "today" differed between browser and server. Fixed with the `X-Timezone` header
  (CR-005).
- **Leaking tests:** the test suite was quietly sending real jobs to the developer's local Redis.
  Found while fixing a test that passed for the wrong reason (CR-007).

## GenAI usage

See **[docs/ai-usage.md](docs/ai-usage.md)** for:
- the prompts used, including the constrained prompt given to the frontend sub-agent;
- representative output;
- how each output was validated;
- a table of **14 concrete defects in AI-generated code** and how each was caught and fixed;
- the edge cases covered, and an assessment of performance and idiomatic quality.

## Operations

- Every response carries an `X-Request-ID`. A caller can supply a safe one (`[A-Za-z0-9._-]{1,64}`);
  anything else is replaced, so untrusted input can't forge log lines.
- The request ID travels with background jobs in the message headers, so
  `docker compose logs api worker | grep <id>` shows a request and every notification it caused
  (CR-013).
- Containers log one JSON object per line, with `request_id`, `method`, `path`, `status` and
  `duration_ms`. Set `LOG_FORMAT=text` for readable local logs.
- **TLS** ends at nginx and fails closed without a certificate; plain HTTP only redirects, apart
  from `/healthz` for the container health check (CR-012).
- **API docs** (`/docs`, `/redoc`, `/openapi.json`) are off in production unless
  `API_DOCS_ENABLED=true`.
- CI runs three jobs: backend (lint, types, contracts, tests on Postgres), frontend (an **API type
  drift check** plus lint, types, tests and build), then **end-to-end**, where Playwright runs
  against the full docker compose stack, plus the TLS checks on the web image.

## Known limitations / next steps

- **Outbox:** a transactional outbox would guarantee event delivery if the broker goes down
  after a commit.
- **Refresh tokens:** no rotation or revocation list.
- **Token storage:** tokens sit in `localStorage`. An httpOnly-cookie backend-for-frontend would
  be the hardened option.
- **Pagination:** cursor pagination for very deep result sets.
- **Notifications:** they are log lines. A real email or Slack sender is one more `Notifier`
  adapter.
