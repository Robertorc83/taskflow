# Specifications

This folder holds the product and technical specs. Every line of production code traces back to
a spec, and every spec traces to executable Gherkin scenarios.

```
User story (CLAUDE.md §2) ──► SPEC-NNN.md ──► *.feature (executable) ──► step defs ──► code
                                   ▲
                 CR-NNN.md ────────┘  (every later change or fix is a Change Request)
```

## Lifecycle

| Status        | Meaning                                                                 |
|---------------|-------------------------------------------------------------------------|
| `Draft`       | Being written; may change freely.                                       |
| `Approved`    | Scope agreed; `.feature` files exist and fail (red).                    |
| `In Progress` | Implementation under way; some scenarios green.                         |
| `Done`        | All scenarios green, Definition of Done (CLAUDE.md §13) met.            |
| `Superseded`  | Replaced by a newer spec; kept for history.                             |

## Changing a spec after it is `Approved`

Never silently edit an approved spec. Instead:

1. Copy [`templates/change-request.md`](templates/change-request.md) to `changes/CR-NNN-short-title.md`.
2. Describe the motivation (new requirement, bug, review feedback, AI correction).
3. Update the affected `.feature` file first (red), then the code (green).
4. Add a row to the spec's **Revision history** that points to the CR, and to the log below.

That gives us a full audit trail of *why* the system changed, not only *what* changed.

## Index

| Spec | Title | Stories | Status | Feature file(s) |
|------|-------|---------|--------|-----------------|
| [SPEC-000](SPEC-000-architecture.md) | Architecture & non-functional requirements | all | Approved | — |
| [SPEC-001](SPEC-001-authentication.md) | Registration & JWT authentication | US-01 | Approved | `authentication.feature` |
| [SPEC-002](SPEC-002-task-crud.md) | Task CRUD | US-02, US-05 | Approved | `task_crud.feature` |
| [SPEC-003](SPEC-003-task-listing.md) | Listing, pagination & filtering | US-03, US-04 | Approved | `task_listing.feature` |
| [SPEC-004](SPEC-004-assignment-completion.md) | Assignment & completion | US-06, US-07 | Approved | `assignment_completion.feature` |
| [SPEC-005](SPEC-005-background-notifications.md) | Asynchronous notifications (Celery) | US-08 | Approved | `notifications.feature` |
| [SPEC-006](SPEC-006-rate-limiting.md) | Rate limiting | US-09 | Approved | `rate_limiting.feature` |
| [SPEC-007](SPEC-007-frontend.md) | Web frontend | US-01..07 | Approved | `frontend/src/**/*.test.tsx`, `frontend/e2e` |
| [SPEC-008](SPEC-008-delivery.md) | Delivery: Docker, seed data, docs, quality gates | — | Approved | — |

Feature files live in [`backend/tests/features/`](../backend/tests/features).

## Change log

| CR | Date | Title | Specs affected | Status |
|----|------|-------|----------------|--------|
| [CR-001](changes/CR-001-bound-latency-on-broker-outage.md) | 2026-10-19 | Bound request latency during a broker outage | SPEC-005 | Implemented |
