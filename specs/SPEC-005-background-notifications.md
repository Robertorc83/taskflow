# SPEC-005: Asynchronous Notifications (Celery + Redis)

| Field    | Value                   |
|----------|-------------------------|
| Status   | Done     |
| Stories  | US-08                   |
| Features | `notifications.feature` |

## Context

When work is delegated or finished, the people involved should hear about it. Sending a
notification (email, Slack…) is slow and can fail, so it must never slow down or break the API
request. It runs in a background worker.

## Business rules

- **R1** On `TaskAssigned`, the new assignee is notified, unless they assigned the task to themselves.
- **R2** On `TaskCompleted`, the owner and the assignee are notified, **except** the person who
  completed the task.
- **R3** The notification text includes the task title and who acted.
- **R4** If the broker is down, the API request still succeeds. The failure is logged as an error.
- **R5** If delivery fails, the worker retries with exponential backoff, up to 3 times.
- **R6** Each job loads fresh state from the database (it is passed IDs, not entity snapshots). If
  the task was deleted in the meantime, the job is a no-op.
- **R7** *(CR-001)* Publishing waits at most `EVENT_PUBLISH_TIMEOUT_SECONDS` (default 2 s). An
  unreachable broker never adds more than that to a request's latency.

## Flow

```
Use case ──commit──► EventPublisher.publish(event)
                       │  CeleryEventPublisher: apply_async(retry=False) on a worker thread
                       ▼
                    Redis ──► Celery worker ──► NotifyTaskAssigned / NotifyTaskCompleted (use cases)
                                                    └──► Notifier port ──► LoggingNotifier (demo "email")
```

## Acceptance criteria (`notifications.feature`)

| Rule | Scenarios |
|------|-----------|
| R1, R3 | The assignee is notified when a task is assigned · Nobody is notified when I assign a task to myself |
| R2 | The owner is notified when the assignee completes the task · Nobody is notified when I complete my own unassigned task |
| R4, R7 | A broker outage does not fail the request (status 200, under 3 s) |
| R6 | Covered by unit tests (`test_notifications.py`) |
| R5 | Celery task configuration (`autoretry_for`, `retry_backoff`, `max_retries=3`) |

## Design notes

- The worker is a second composition root (`infrastructure/tasks/worker.py`). Celery tasks are thin
  adapters: they decode their arguments and run an application use case under `asyncio.run`.
- Acceptance tests run Celery in **eager** mode, so the whole chain (use case → publisher → Celery
  task → notify use case → notifier) is exercised in-process without a broker.
- `LoggingNotifier` writes a structured log line, which stands in for an email gateway. Swapping in
  SMTP or SES means adding one adapter.

## Revision history

| Rev | Date       | Change          | Reason | CR |
|-----|------------|-----------------|--------|----|
| 1   | 2026-10-19 | Initial version | —      | —  |
| 2   | 2026-10-19 | Added R7: bounded publish latency | Outage blocked requests ~6 s (redis-py retries) | [CR-001](changes/CR-001-bound-latency-on-broker-outage.md) |
| 3 | 2026-10-19 | Jobs sent by name; transient-only retries; loud unknown events; honest tests | API imported worker; tests leaked into a real Redis | [CR-007](changes/CR-007-background-job-wiring.md) |
