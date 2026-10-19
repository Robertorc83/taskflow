# CR-007: Decouple the API from the worker; honest job tests

| Field          | Value |
|----------------|-------|
| Date           | 2026-10-19 |
| Type           | architecture / bugfix |
| Specs affected | SPEC-005 |
| Status         | Implemented |
| Source         | Multi-agent review (architecture, security, modularity, bug hunt), findings reproduced before fixing |

## Motivation

1. **The API imported the worker's code.** The publisher imported `jobs`, which pulled in
   `runtime` (the worker composition root). `celery_app.py` configured a global app from the
   environment **at import time**. `Container.build` mutated that same global, so the last app
   built won.
2. **Any new event type would fail as a "broker error".** The `match` had no default, so an
   `UnboundLocalError` was swallowed by the broad `except`.
3. **Retries on everything:** `autoretry_for=(Exception,)` retried bad UUIDs and bugs.
4. **Tests passed for the wrong reason.** "Nobody is notified" also passed when the job crashed.
   The outage scenario never checked that the failure was logged.
5. **Found while fixing (4): the test suite was leaking real jobs into the developer's own
   Redis.** Celery cached a producer connection to `localhost:6379` and reused it even after the
   broker URL was swapped. The outage scenario therefore "succeeded" against a real broker in the
   full run, and passed only in isolation. 13 test messages were found in the host's Redis.

## Decision

- **Jobs are sent by name.** `infrastructure/tasks/names.py` is the contract. The API builds its
  own producer-only `Celery` from `Settings` (`create_celery_app`). Only `worker.py` configures
  the worker app. There is no import-time side effect.
- **Unknown events raise `TypeError`.** Retries apply only to transient errors: `OperationalError`,
  `ConnectionError`, `TimeoutError`.
- **Tests never touch a real broker.** `celery_broker_url="memory://"`. The outage scenario builds
  its own app pointed at a dead broker, with no global mutation. The eager config is restored
  after each scenario.
- **New import-linter contracts** fail CI if the API imports the worker (strict, including
  indirect imports), or if presentation touches SQLAlchemy, Celery or crypto directly.

## Behavior change (Gherkin)

```gherkin
    And no background job should have failed        # added to both "nobody is notified" scenarios
    And the enqueue failure should be logged        # added to the broker-outage scenario
```

## Verification

- [x] The outage scenario failed in the full run (the leak), then passed after the fix
- [x] The Redis queue length stayed at 13 across later full runs (no new leaks)
- [x] `lint-imports`: 5 contracts kept
- [x] Unit: `test_publisher_rejects_unknown_events_loudly`
