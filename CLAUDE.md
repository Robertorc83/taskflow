# CLAUDE.md — Task Management System

This is the operating manual for Claude Code (and humans) working in this repo.
Read it fully before writing code. When this file and your instincts disagree, this file wins;
if this file is wrong, propose an edit to it rather than silently diverging.

---

## 1. Mission

A full-stack task manager: a **FastAPI** REST API built on **Clean Architecture**, driven by
**BDD** (behavior first, then TDD inside), with a **React + TypeScript** frontend.

It is a take-home exercise that will be presented and code-reviewed by a panel. Every choice
must be **explainable in one sentence** during that review. Optimize for:

1. **Clean Architecture** — dependency rule enforced, frameworks at the edges.
2. **Tests** — behavior specified in Gherkin, ≥ 90% coverage target (80% is the hard floor in CI).
3. **Code quality** — typed, linted, small units, intention-revealing names.
4. **Functionality** — zero errors, **zero browser console warnings**.
5. **GenAI fluency** — every significant AI-generated change is logged and critically reviewed (§12).

Scope discipline: build what the spec asks for, well. No speculative features.

---

## 2. User Stories (source of truth for features)

| ID    | As a…          | I want to…                                         | So that…                              |
|-------|----------------|----------------------------------------------------|---------------------------------------|
| US-01 | visitor        | register and log in                                | I get a JWT to use the API            |
| US-02 | user           | create a task with title, description, due date    | I can track work                      |
| US-03 | user           | list my tasks, paginated                           | large lists stay fast and readable    |
| US-04 | user           | filter tasks by status and due-date range          | I can focus on what matters now       |
| US-05 | user           | update or delete a task I own                      | I can keep my list accurate           |
| US-06 | user           | assign a task to another user                      | work can be delegated                 |
| US-07 | assignee/owner | mark a task as completed                           | progress is visible                   |
| US-08 | system         | notify the assignee asynchronously on assignment   | the API stays fast                    |
| US-09 | system         | rate-limit clients                                 | the API is protected from abuse       |

Each story maps to **one `.feature` file** under `backend/tests/features/`. No story, no code.

---

## 3. Tech Stack (and the one-line "why")

| Concern            | Choice                                   | Why                                                        |
|--------------------|------------------------------------------|------------------------------------------------------------|
| API framework      | FastAPI                                  | Native OpenAPI/Swagger, Pydantic validation, async, DI     |
| Python / tooling   | Python 3.12, **uv**, `pyproject.toml`    | Fast, reproducible lockfile, single config file            |
| ORM / migrations   | SQLAlchemy 2.0 (async) + Alembic         | Typed mappings, explicit migrations                        |
| Database           | PostgreSQL 16 everywhere, including tests (see §8) | Prod parity |
| Auth               | JWT (access + refresh) via `pyjwt`, `argon2` hashing (`pwdlib`) | Stateless, modern hash             |
| Rate limiting      | `limits` (moving window, Redis) via FastAPI dependencies | Per-IP + per-user limits, shared across workers; no module-global limiter (ADR-0008) |
| Background jobs    | Celery + Redis                           | Spec requirement; retries & visibility                     |
| BDD                | `pytest-bdd` (Gherkin)                   | Executable specs, plain pytest fixtures                    |
| Unit/integration   | `pytest`, `pytest-asyncio`, Starlette `TestClient` (`httpx2`), hand-written fakes, `testcontainers` | Real Postgres in tests |
| Quality            | `ruff` (lint + format), `mypy --strict`, `pre-commit`, `import-linter` | Enforce style + **layer boundaries** |
| Frontend           | React 18 + TypeScript + Vite             | Fast DX, strict typing                                     |
| FE server state    | TanStack Query                           | Caching, pagination, mutations; no hand-rolled fetch state |
| FE forms / schema  | React Hook Form + Zod                    | Typed validation mirroring backend rules                   |
| FE UI              | Tailwind CSS                             | Responsive with minimal CSS surface                        |
| FE tests           | Vitest + Testing Library + MSW; Playwright for E2E | Behavior-level tests, mocked network          |
| Containers         | Docker + docker-compose                  | `api`, `worker`, `db`, `redis`, `web`                      |

Do **not** add dependencies outside this table without stating why in the PR/commit and in §14.

---

## 4. Clean Architecture

### 4.1 The dependency rule

```
presentation  ──►  application  ──►  domain
     │                  ▲
     ▼                  │ (implements ports)
infrastructure ─────────┘
```

- **domain** depends on *nothing* (stdlib only). No FastAPI, no SQLAlchemy, no Pydantic.
- **application** depends only on **domain**. It defines **ports** (abstract interfaces) that
  infrastructure implements.
- **infrastructure** implements ports (DB repos, JWT, password hasher, Celery dispatcher, clock).
- **presentation** (FastAPI routers, Pydantic schemas, dependency wiring) calls use cases and
  maps DTOs ↔ HTTP. It never touches the ORM directly.
- The **composition root** (`main.py` + `presentation/dependencies.py`) is the only place that
  knows concrete implementations.

Boundaries are enforced by `import-linter` contracts in `pyproject.toml`. A violation fails CI.

### 4.2 Backend layout

```
backend/
├── pyproject.toml              # uv, ruff, mypy, pytest, coverage, import-linter config
├── alembic/                    # migrations
├── src/taskmanager/
│   ├── domain/
│   │   ├── entities/           # Task, User — dataclasses with behavior (complete(), assign_to())
│   │   ├── value_objects/      # TaskStatus (enum), Email, TaskTitle, DueDate
│   │   ├── exceptions.py       # DomainError hierarchy (TaskAlreadyCompleted, InvalidDueDate…)
│   │   └── events.py           # TaskAssigned, TaskCompleted
│   ├── application/
│   │   ├── ports/              # TaskRepository, UserRepository, PasswordHasher,
│   │   │                       # TokenService, EventPublisher, Clock, UnitOfWork (Protocols/ABCs)
│   │   ├── use_cases/          # one class per use case: CreateTask, ListTasks, AssignTask…
│   │   ├── dto.py              # input/output dataclasses (TaskFilters, Page[T], TaskDTO)
│   │   └── exceptions.py       # NotFound, PermissionDenied, Conflict
│   ├── infrastructure/
│   │   ├── db/                 # SQLAlchemy models, session, SqlAlchemy*Repository, UoW
│   │   ├── security/           # JwtTokenService, Argon2PasswordHasher
│   │   ├── tasks/              # celery_app.py, CeleryEventPublisher, task handlers
│   │   ├── rate_limit.py
│   │   ├── container.py        # API composition root (adapters built from Settings)
│   │   └── config.py           # pydantic-settings; the ONLY place env vars are read
│   ├── presentation/
│   │   ├── api/v1/             # routers: auth.py, tasks.py, users.py
│   │   ├── schemas/            # Pydantic request/response models
│   │   ├── dependencies.py     # FastAPI Depends wiring (builds use cases per request)
│   │   ├── errors.py           # domain/app exceptions → HTTP problem responses
│   │   └── app.py              # create_app() factory
│   ├── seed.py                 # demo data + credentials
│   └── main.py                 # ASGI entry point
└── tests/
    ├── features/               # *.feature — Gherkin, one per user story
    ├── step_defs/              # pytest-bdd step implementations (API-level, via httpx)
    ├── unit/
    │   ├── domain/             # pure, no I/O, no mocks needed
    │   └── application/        # use cases with in-memory fakes of ports
    ├── integration/            # migrations, seed, DB constraints against real Postgres
    ├── fakes.py                # InMemoryUnitOfWork, FixedClock, SpyEventPublisher, …
    └── conftest.py
```

### 4.3 Rules of thumb

- **Entities hold invariants.** `task.complete()` raises `TaskAlreadyCompleted`; status is never
  set by assigning a string from the router.
- **One use case = one class with `execute()`**, constructor-injected ports. No use case calls
  another use case; extract a domain service instead.
- **Use cases return DTOs**, never ORM models or Pydantic models.
- **Authorization lives in the application layer** (e.g. "only owner can delete; owner or assignee
  can complete"), not in routers — so it is unit-testable without HTTP.
- **Time is a port** (`Clock`). Never call `datetime.now()` in domain/application code.
- **Prefer `Protocol` for ports**; use fakes, not `MagicMock`, in application tests.
- **Mappers** (ORM ↔ entity, entity ↔ schema) live at the boundary that owns the foreign type.
- **No business logic in SQLAlchemy models or Pydantic schemas.** Pydantic validates *shape*;
  the domain validates *rules*.

---

## 5. Domain Model

```
User:  id (UUID), email (unique), full_name, hashed_password, is_active, created_at
Task:  id (UUID), title (1–200), description (≤ 2000, optional),
       status: TaskStatus = pending | in_progress | completed,
       due_date (date, optional), owner_id → User, assignee_id → User (nullable),
       created_at, updated_at, completed_at (nullable)
```

Invariants (each one has a unit test **and** a Gherkin scenario):
- New tasks start `pending`; `completed_at` is set iff status is `completed`.
- A completed task cannot be completed again (409).
- `due_date` cannot be in the past **on creation** (422); updating an overdue task is allowed.
- Assignee must exist and be active (404 / 422).
- Only the owner may update, delete, or reassign. Owner **or** assignee may complete.
- Users see tasks they **own or are assigned to**.

Indexes: `(owner_id, status)`, `(assignee_id, status)`, `due_date`.

---

## 6. BDD Workflow — how every change is made

We work **outside-in**: spec → behavior → acceptance test → unit tests → code.

Specs live in `specs/` (see `specs/README.md`). After a spec is `Approved`, **every change or fix
is a Change Request** (`specs/changes/CR-NNN-*.md`): update the scenario first (red), then the code.

1. **Discover** — pick a user story (§2). Write/extend its `.feature` file with concrete examples.
   Cover the happy path, at least one validation failure, and one authorization failure.
2. **Red (acceptance)** — implement step definitions that hit the real HTTP API via
   `httpx.AsyncClient` against the app. Run → it must fail for the *right reason*.
3. **Red/Green/Refactor (inner TDD loop)** — drive domain entities and use cases with fast unit
   tests until the scenario goes green.
4. **Refactor** — clean names, remove duplication, keep the import-linter contracts green.
5. **Commit** — small, conventional commits (§11). Feature file + steps + code go together.

**Never write production code without a failing test that demands it.** If Claude is asked to
"just implement X", it must first produce (or point to) the scenario covering X.

### 6.1 Gherkin conventions

- Business language only. No URLs, JSON, or SQL in `.feature` files — that belongs in steps.
- `Background:` for shared setup (e.g. authenticated user). `Scenario Outline` for filter matrices.
- Tag scenarios: `@US-04`, `@auth`, `@validation`, `@wip` (wip is excluded from CI).
- Steps are reusable and parametrized; one step definition module per bounded area
  (`auth_steps.py`, `task_steps.py`, `common_steps.py`).

Example — `tests/features/filter_tasks.feature`:

```gherkin
@US-04
Feature: Filter tasks
  As a user
  I want to filter my tasks by status and due date
  So that I can focus on what matters now

  Background:
    Given I am logged in as "alice@example.com"
    And I own the following tasks:
      | title          | status      | due_date   |
      | Write report   | pending     | 2026-11-01 |
      | Review PR      | in_progress | 2026-10-25 |
      | Deploy release | completed   | 2026-10-20 |

  Scenario Outline: Filter by status
    When I list my tasks with status "<status>"
    Then I should see <count> task(s)
    And every task should have status "<status>"

    Examples:
      | status      | count |
      | pending     | 1     |
      | in_progress | 1     |
      | completed   | 1     |

  Scenario: Filter by due date range
    When I list my tasks due between "2026-10-21" and "2026-10-31"
    Then I should see only "Review PR"

  @validation
  Scenario: Reject an invalid status filter
    When I list my tasks with status "archived"
    Then the request should be rejected as invalid
```

### 6.2 Test layers & what each proves

| Layer                  | Location                 | Speed  | Dependencies           | Proves                               |
|------------------------|--------------------------|--------|------------------------|--------------------------------------|
| Domain unit            | `tests/unit/domain`      | ms     | none                   | invariants, entity behavior          |
| Application unit       | `tests/unit/application` | ms     | in-memory fakes        | orchestration, authorization rules   |
| Integration            | `tests/integration`      | ~s     | Postgres container     | SQL, mappings, filters, pagination   |
| Acceptance (BDD)       | `tests/features` + steps | ~s     | app + Postgres         | user-visible behavior end-to-end     |
| Frontend component     | `frontend/src/**/*.test.tsx` | ms | MSW                    | UI behavior per component/feature    |
| E2E (smoke)            | `frontend/e2e`           | slow   | full docker stack      | login → CRUD → filter happy path     |

Coverage: `pytest --cov=src/taskmanager --cov-branch --cov-fail-under=80`. Target ≥ 90%.
Celery tasks run with `task_always_eager=True` in tests; `EventPublisher` is faked in unit tests.

---

## 7. API Conventions

- Base path: `/api/v1`. Swagger at `/docs`, ReDoc at `/redoc`. Health at `/health`.
- Resources: `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `GET /users/me`,
  `GET /users` (for the assignee picker), `GET|POST /tasks`, `GET|PATCH|DELETE /tasks/{id}`,
  `POST /tasks/{id}/complete`, `PUT /tasks/{id}/assignee`.
  Completion and assignment are **explicit actions** (not PATCH fields) because they carry rules
  and side effects (events).
- **Pagination**: `?page=1&size=20` (size max 100). Response envelope:
  `{ "items": [...], "total": n, "page": p, "size": s, "pages": k }`.
- **Filtering**: `?status=pending&due_from=YYYY-MM-DD&due_to=YYYY-MM-DD`; also `?ordering=due_date|-due_date|created_at`.
- **Errors**: RFC 9457 problem details — `{ "type", "title", "status", "detail", "errors"? }`.
  Mapping: `NotFound→404`, `PermissionDenied→403`, `Conflict/DomainError→409`,
  validation→422, auth→401, rate-limit→429 (with `Retry-After`).
  Don't leak existence: a task the user cannot see returns **404**, not 403.
- **Auth**: `Authorization: Bearer <access>`; access TTL 15 min, refresh 7 days. Secret from env.
- **Rate limits**: auth endpoints 10/min per IP; default 100/min per user. Configurable via settings (SPEC-006).
- Every endpoint declares `response_model`, status codes, and `responses={...}` so Swagger is complete.

---

## 8. Persistence

- Async SQLAlchemy 2.0 with typed `Mapped[...]` columns. Session per request via a `UnitOfWork`.
- **Alembic for every schema change**; never `create_all()` outside tests.
- Integration tests run against **real Postgres** via `testcontainers` (filter/date semantics
  differ between SQLite and Postgres — we don't test on a different engine than we ship).
- `seed.py` is idempotent and creates demo users:
  - `alice@example.com` / `Alice123!`
  - `bob@example.com` / `Bob12345!`
  - `carol@example.com` / `Carol123!`
  plus 25 tasks across statuses/due dates so pagination and filters are demoable.

---

## 9. Frontend

```
frontend/src/
├── app/            # App.tsx, router, providers (QueryClient, Auth)
├── api/            # typed HTTP client (fetch wrapper), endpoints, token refresh interceptor
├── features/
│   ├── auth/       # LoginPage, useAuth, authStore
│   └── tasks/      # TaskListPage, TaskForm, TaskFilters, TaskCard, hooks (useTasks, useCreateTask…), schemas.ts
├── components/ui/  # dumb, reusable: Button, Input, Modal, Pagination, Badge, EmptyState
├── lib/            # utilities (dates, cn)
└── types/          # shared API types (generated from OpenAPI with openapi-typescript)
```

- **Feature-sliced**: a feature owns its pages, hooks, and components. `components/ui` knows
  nothing about tasks.
- **Server state in TanStack Query only**; local UI state with `useState`; auth in a small context.
  No Redux.
- **Filters & page live in the URL** (`useSearchParams`) — shareable, back-button friendly.
- Optimistic update for "mark complete"; invalidate list queries on mutations.
- API types generated from `/openapi.json` — never hand-write response types.
- Mobile-first, keyboard accessible, labeled inputs, loading/empty/error states for every list.
- **Zero console warnings**: unique `key`s, no act() warnings in tests, no uncontrolled→controlled
  switches, React StrictMode on. Check DevTools console before declaring a feature done.
- Frontend tests follow the same Given/When/Then shape in `describe`/`it` names.

---

## 10. Infrastructure & Commands

`docker-compose.yml` services: `db` (postgres:16), `redis` (redis:7), `api` (uvicorn, runs
migrations + seed on start), `worker` (celery), `web` (vite dev or nginx build). Healthchecks on
`db`/`redis`; `api` `depends_on` them with `condition: service_healthy`.
Dockerfile: multi-stage, `uv sync --frozen --no-dev`, non-root user.

A root `Makefile` is the single entry point:

```bash
make up            # docker compose up --build
make down
make seed          # run seed inside api container
make test          # backend: all tests + coverage gate
make test-bdd      # backend: pytest tests/step_defs -m "not wip"
make test-unit     # backend: fast unit tests only
make lint          # ruff check, ruff format --check, mypy, lint-imports, eslint, tsc
make fmt           # ruff format + ruff check --fix + prettier
make migrate       # alembic upgrade head
make migration m="msg"  # alembic revision --autogenerate
make web-test      # vitest run
make e2e           # playwright
```

Without Docker (backend): `cd backend && uv sync && uv run pytest`.

---

## 11. Code Standards

**Python**
- `mypy --strict` clean. No `Any` in domain/application. No `# type: ignore` without a reason comment.
- `ruff` rules: `E,F,I,B,UP,SIM,N,S,ASYNC,RUF,PT`; line length 100.
- Names say intent: `ListTasksForUser`, not `TaskService.get`. No abbreviations.
- Functions ≤ ~20 lines, one level of abstraction. Raise specific exceptions; never bare `except`.
- No print; structured logging via `logging` with request IDs.
- Config only via `infrastructure/config.py` (`pydantic-settings`). Secrets never committed;
  `.env.example` documents every variable.

**TypeScript**
- `strict: true`, no `any`, ESLint (react-hooks, jsx-a11y) + Prettier.
- Components are functions; props typed; hooks prefixed `use`.

**Git**
- Conventional commits: `feat(tasks): filter by due date range`, `test(bdd): ...`, `refactor(domain): ...`.
- Small commits; each one passes `make lint test`.
- `pre-commit` runs ruff, ruff-format, mypy, import-linter, eslint, prettier, and
  `check-added-large-files`/`detect-private-key`.

---

## 12. GenAI Usage Log (required deliverable)

The panel evaluates *how* AI was used. Maintain `docs/ai-usage.md` with, per significant change:

1. **Prompt** used (verbatim or summarized).
2. **What the AI produced** (link to commit or short excerpt).
3. **Validation** — which tests/linters/manual checks were run.
4. **Corrections** — what was wrong or non-idiomatic and how it was fixed
   (e.g. "AI put status checks in the router → moved to `Task.complete()`";
   "AI used `datetime.utcnow()` → replaced with `Clock` port").
5. **Edge cases** found (auth bypass, past due dates, pagination bounds, timezone handling).

Claude: when you make a non-trivial change, append an entry to `docs/ai-usage.md` describing
the above, honestly — including your own mistakes.

---

## 13. Definition of Done

A story is done when **all** are true:

- [ ] `.feature` scenarios (happy, validation, authorization) exist and pass.
- [ ] Domain + application unit tests cover the new rules.
- [ ] `make lint` clean (ruff, mypy strict, import-linter, eslint, tsc).
- [ ] Coverage ≥ 80% (target 90%) and did not drop.
- [ ] Swagger shows correct schemas, status codes, and examples.
- [ ] Frontend flow works on mobile and desktop widths; no console errors/warnings.
- [ ] README updated if setup/behavior changed; `docs/ai-usage.md` entry added.

---

## 14. Architecture Decision Records

Short ADRs live in `docs/adr/NNNN-title.md` (Context / Decision / Consequences). Seed list:

- 0001 FastAPI over Django REST Framework
- 0002 Clean Architecture with ports & adapters; import-linter enforcement
- 0003 BDD with pytest-bdd, outside-in TDD
- 0004 Real Postgres in tests via testcontainers
- 0005 Explicit action endpoints for complete/assign
- 0006 JWT access + refresh, Argon2 hashing
- 0007 Celery + Redis for assignment notifications; Redis-backed rate limiting

---

## 15. Instructions for Claude specifically

- **Start every feature from §6**: show the scenario first, then the failing run, then the code.
- Respect the dependency rule. If a change requires importing infrastructure into application or
  domain, stop — define a port instead.
- Run `make lint test` (or the relevant subset) before claiming something works. Report failures
  verbatim; never claim green without running.
- Prefer editing existing files over creating new ones; no new top-level dirs without updating §4.2.
- Don't add dependencies, change the stack, or relax lint/type/coverage settings without asking.
- Keep README, Swagger, and this file consistent with the code.
- When unsure about a product rule, check §2/§5; if still ambiguous, ask instead of guessing.
