# CR-001: Bound request latency during a broker outage

| Field          | Value          |
|----------------|----------------|
| Date           | 2026-10-19     |
| Type           | bugfix         |
| Specs affected | SPEC-005       |
| Status         | Implemented    |

## Motivation

The scenario "A broker outage does not fail the request" passed, but the run took about 8 s.
A probe showed that `apply_async(retry=False)` against a refused Redis connection still blocks for
**about 6 s**. redis-py retries the connection with exponential backoff inside kombu, and kombu
exposes no transport option to turn that off.

In production, every request that publishes an event (create with assignee, assign, complete)
would hang for 6 s while Redis is down. SPEC-005 R4 was met to the letter ("the request still
succeeds") but not in spirit.

Found by reading the test timing and the coverage report while verifying the implementation.

## Decision

- Add **SPEC-005 R7**: publishing an event waits at most `EVENT_PUBLISH_TIMEOUT_SECONDS`
  (default 2 s). After that the request continues and the failure is logged.
- `CeleryEventPublisher` wraps the enqueue thread in `asyncio.wait_for(...)`.

### Rejected alternatives
- *Lower the socket connect timeout*: it doesn't help, because the time goes into retries, not
  into a single connect.
- *Transactional outbox* (write events to a table in the same transaction; a relay process
  enqueues them): this is the robust answer, because no event is ever lost. It is out of scope
  for this exercise and recorded as future work in ADR-0007.

## Behavior change (Gherkin)

```gherkin
  Scenario: A broker outage does not fail the request
    Given the background job broker is unavailable
    When I assign the task to "bob@example.com"
    Then the response status should be 200
    And the response should arrive within 3 seconds
```

## Verification

- [x] New step failed before the change (the response took about 6 s)
- [x] Passes after the change
- [x] `make lint test` green
- [x] SPEC-005 revision history updated
