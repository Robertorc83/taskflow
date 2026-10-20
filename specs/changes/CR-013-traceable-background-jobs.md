# CR-013: Traceable background jobs

| Field          | Value |
|----------------|-------|
| Date           | 2026-10-19 |
| Type           | operability |
| Specs affected | SPEC-005 (R8), SPEC-000 (NFR-10) |
| Status         | Implemented |
| Source         | Manual QA: worker log lines had `request_id: null` |

## Motivation

CR-010 gave every API request an ID and put it on every API log line. Background jobs run in
another process, though, so their lines all said `request_id: null`. Nothing linked "Bob was
notified" back to the request that assigned the task.

## Decision

- **Producer:** `CeleryEventPublisher` reads the current request ID and sends it as a Celery
  **message header** (`names.REQUEST_ID_HEADER`). The header is part of the API–worker contract,
  next to the job names; the job arguments stay purely business data.
- **Worker:** a `task_prerun` signal adopts the header into the logging context, so every line the
  job writes (ours, SQLAlchemy's, Celery's trace) carries the ID. `task_postrun` clears it, because
  a worker process runs many jobs and must never carry one ID into the next.
- **Honest eager mode:** eager mode (tests, local debugging) now runs the job in an **empty context**,
  like a separate worker process. Before, it ran in a thread that *inherited* the caller's context,
  so the new scenario **passed without any fix**. That proved nothing about the real boundary.
- Celery's own "Task received" line is written before the job starts, so it has no ID. The job
  ID on that line links it to the traced lines.

## Behavior change (Gherkin, `notifications.feature`)

```gherkin
  Scenario: A notification can be traced to the request that caused it
    When I assign the task to "bob@example.com" with request ID "assign-7"
    Then "bob@example.com" should receive a notification mentioning "Prepare demo"
    And the notification job should run under request ID "assign-7"
```

## Verification

- [x] The scenario first passed **for the wrong reason** (context inherited across the eager
  thread). Making eager mode run in an empty context turned it red for the right reason, and the
  header and signal made it green.
- [x] mypy caught a `None` header value. Fixing the generic `Task` annotation then broke *import*,
  because Celery's `Task` is generic only in its stubs. The full test run caught that, and the
  annotation is now quoted.
- [x] Live, through the real Redis broker: an assignment sent with `X-Request-ID: qa-trace-001`
  produced worker lines under `qa-trace-001`. A following completion with a server-generated ID
  logged under that ID, with nothing left over from the first job. `grep qa-trace-001` across
  `api` and `worker` shows the request and its notification together.
- [x] 202 backend tests pass at 97% coverage, `make lint` is clean, and Playwright passes on
  desktop and mobile.
