# CR-010: Request tracing and structured logs

| Field          | Value |
|----------------|-------|
| Date           | 2026-10-19 |
| Type           | operability |
| Specs affected | SPEC-000 (NFR-10) |
| Status         | Implemented |
| Source         | Self-audit: CLAUDE.md promised it, the code didn't do it |

## Motivation

`CLAUDE.md` §11 promises "structured logging with request IDs", but the code used
`logging.basicConfig` with no correlation. Two related gaps turned up while testing this:
- the CORS policy did not allow the `X-Timezone` header added in CR-005, which would break any
  cross-origin client;
- uvicorn's own access log duplicated ours and wasn't structured.

## Decision

- **Correlation:** `infrastructure/logging.py` holds a context variable and a log-record factory,
  so *every* record (including Celery and library logs) carries `request_id`. Output is a JSON
  formatter, or text locally.
- **Middleware:** `presentation/middleware.py` is a plain ASGI middleware (not
  `BaseHTTPMiddleware`). It accepts a caller's `X-Request-ID` only if it matches
  `[A-Za-z0-9._-]{1,64}`, because it is untrusted input written to logs. Otherwise it generates
  one, echoes it on every response, and writes one access line with method, path, status and
  duration.
- **CORS:** allows `X-Timezone` and `X-Request-ID`, and exposes `X-Request-ID`.
- **Image:** `LOG_FORMAT=json`; uvicorn runs with `--no-access-log`; the worker keeps our handler
  (`worker_hijack_root_logger=False`).

## Behavior change (Gherkin, `observability.feature`)

```gherkin
  Scenario: Every response carries a request ID
  Scenario: A caller-supplied request ID is propagated   (and appears in the access log)
  Scenario: An unsafe request ID is replaced
  Scenario: Cross-origin clients may send the time zone and read the request ID
```

## Verification

- [x] 4 scenarios red, then green. Unit: the JSON line carries `request_id` and extras;
  `configure_logging` is idempotent.
- [x] A first draft used `"evil\nINFO fake"` as the unsafe ID. HTTP clients refuse to send that,
  so the scenario would have failed for the wrong reason. Replaced with
  `"x; level=ERROR msg=forged"`.
