# SPEC-000: Architecture & Non-Functional Requirements

| Field    | Value    |
|----------|----------|
| Status   | Done     |
| Stories  | all      |
| Features | —        |

## Context

The system is a small multi-user task manager. The real goal is a codebase that a review panel
can open at any file and see a clear reason for where that code sits. That is why we use Clean
Architecture (ports and adapters) and BDD from the outside in.

## System context

```
 ┌──────────┐   HTTPS/JSON + JWT   ┌──────────────────────┐   SQL    ┌────────────┐
 │  React   │ ───────────────────► │  FastAPI  (api)      │ ───────► │ PostgreSQL │
 │  (web)   │ ◄─────────────────── │  presentation layer  │          └────────────┘
 └──────────┘                      │  ─ use cases ─       │  enqueue ┌────────────┐
                                   │  ─ domain ─          │ ───────► │   Redis    │
                                   └──────────────────────┘          │ broker +   │
                                   ┌──────────────────────┐ consume  │ rate limit │
                                   │  Celery (worker)     │ ◄─────── └────────────┘
                                   │  same use cases      │
                                   └──────────────────────┘
```

The API and the worker are two **composition roots** over the same domain and application
layers. Only the adapters differ.

## Layers (dependency rule: inner layers never import outer ones)

| Layer           | Package                         | May import                       | Contains |
|-----------------|---------------------------------|----------------------------------|----------|
| Domain          | `taskmanager.domain`            | stdlib                           | Entities (`Task`, `User`), value objects (`TaskStatus`), domain events, domain errors |
| Application     | `taskmanager.application`       | domain                           | Use cases, ports (`Protocol`s), DTOs, application errors |
| Infrastructure  | `taskmanager.infrastructure`    | application, domain, 3rd party   | SQLAlchemy repos and Unit of Work, JWT, Argon2, Celery, rate limiter, settings |
| Presentation    | `taskmanager.presentation`      | application, domain, infra (wiring only) | FastAPI routers, Pydantic schemas, error mapping, DI |

`import-linter` enforces this with contracts in `backend/pyproject.toml`. A violation fails CI.

## Ports (application layer)

| Port              | Purpose                                   | Adapter (prod)               | Adapter (tests)           |
|-------------------|-------------------------------------------|------------------------------|---------------------------|
| `UnitOfWork`      | Transaction boundary, exposes repositories | `SqlAlchemyUnitOfWork`      | `InMemoryUnitOfWork`      |
| `TaskRepository`  | Persist and query tasks                   | `SqlAlchemyTaskRepository`   | `InMemoryTaskRepository`  |
| `UserRepository`  | Persist and query users                   | `SqlAlchemyUserRepository`   | `InMemoryUserRepository`  |
| `PasswordHasher`  | Hash and verify passwords                 | `Argon2PasswordHasher`       | `PlainTextPasswordHasher` |
| `TokenService`    | Issue and verify JWTs                     | `JwtTokenService`            | real (pure, fast)         |
| `Clock`           | Current time (never `datetime.now()` in inner layers) | `SystemClock`    | `FixedClock`              |
| `EventPublisher`  | Dispatch domain events after commit       | `CeleryEventPublisher`       | `SpyEventPublisher`       |
| `Notifier`        | Deliver a notification to a user          | `LoggingNotifier`            | `RecordingNotifier`       |

## Cross-cutting decisions

- **Errors**: domain and application raise typed exceptions. Only the presentation layer maps them
  to HTTP, as RFC 9457 `application/problem+json`.
- **Transactions**: one Unit of Work per use case. Events are published **after** commit, so no
  notification goes out for a rolled-back change.
- **Time**: all timestamps are timezone-aware and serialized in UTC. Due dates are calendar
  dates, with no time zone. *(CR-005)* **"Today" is the caller's local date**: clients send
  `X-Timezone: <IANA zone>` (missing → UTC, unknown → 422), and the request's clock is expressed
  in that zone.
- **IDs**: UUIDv4, generated in the domain. Entities exist before they are persisted.
- **Visibility**: a user sees tasks they **own** or are **assigned to**. When a user cannot see a
  resource the API returns `404`, never `403`, so it does not reveal that the resource exists.
  `403` is only for a visible resource on which the action is not allowed.

## Non-functional requirements

| ID    | Requirement                                                                 | Verified by |
|-------|-----------------------------------------------------------------------------|-------------|
| NFR-1 | Backend line + branch coverage ≥ 80% (target ≥ 90%)                         | `pytest --cov-fail-under=80` |
| NFR-2 | `mypy --strict` and `ruff` clean, with no layer violations                  | `make lint`, pre-commit |
| NFR-3 | p95 list endpoint < 100 ms locally with 1k tasks (indexed filters, single count query) | manual / indexes in migration |
| NFR-4 | All config through environment variables; no secrets in the repo           | `config.py`, `.env.example` |
| NFR-5 | `docker compose up` brings up the full stack with seeded demo data         | SPEC-008 |
| NFR-6 | No errors or warnings in the browser console                               | SPEC-007 |
| NFR-7 | OpenAPI docs complete: schemas, auth, error responses                      | `/docs` |
| NFR-8 | Passwords hashed with Argon2; JWT secret ≥ 32 bytes outside dev            | SPEC-001 |
| NFR-10 | *(CR-010)* Every response has `X-Request-ID`; every log line carries `request_id`; container logs are JSON | `observability.feature` |
| NFR-9 | *(CR-002)* Fail closed: the image defaults to production, trusts only the configured proxy, publishes no data stores to the network | `docker compose ps`, CR-002 |
| NFR-11 | *(CR-012)* Traffic is served over TLS 1.2+ with HSTS; the web image refuses to start without a certificate unless TLS is explicitly delegated upstream | `make tls-check` |

## Revision history

| Rev | Date       | Change          | Reason | CR |
|-----|------------|-----------------|--------|----|
| 1   | 2026-10-19 | Initial version | —      | —  |
| 2 | 2026-10-19 | Time zone rule; NFR-9 fail-closed deployment | Review findings | [CR-005](changes/CR-005-user-time-zone.md) |
| 3 | 2026-10-19 | NFR-10 request tracing | CLAUDE.md promised it; code didn't | [CR-010](changes/CR-010-request-tracing-and-structured-logs.md) |
| 4 | 2026-10-19 | NFR-11 TLS | Production-readiness audit | [CR-012](changes/CR-012-tls-and-production-api-docs.md) |
