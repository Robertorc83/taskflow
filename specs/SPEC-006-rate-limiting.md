# SPEC-006: Rate Limiting

| Field    | Value                   |
|----------|-------------------------|
| Status   | Done     |
| Stories  | US-09                   |
| Features | `rate_limiting.feature` |

## Context

The API must be protected from abuse: credential stuffing on the auth endpoints, and runaway
clients on everything else.

## Business rules

- **R1** Auth endpoints (`register`, `login`, `refresh`) are limited **per client IP**. Default: 10/minute.
- **R2** Authenticated endpoints are limited **per user** (by the token subject). Default: 100/minute.
- **R3** Going over the limit returns `429` with a `Retry-After` header (seconds) and a problem body.
- **R4** Limits are shared across API processes (Redis storage) and are configurable through
  environment variables. They can be disabled for local debugging.
- **R5** Health and docs endpoints are not limited.
- **R6** *(CR-002)* The client IP comes only from a **trusted** reverse proxy
  (`FORWARDED_ALLOW_IPS`), and the proxy overwrites `X-Forwarded-For`. Clients cannot pick their
  own rate-limit key.

## Acceptance criteria (`rate_limiting.feature`)

| Rule | Scenarios |
|------|-----------|
| R1, R3 | Too many login attempts are throttled · Requests under the limit are not throttled |
| R2 | Authenticated API usage is limited per user · Limits are tracked per user |

## Design notes

- The `limits` library (the engine under slowapi) sits behind a small `RateLimiter` adapter, applied
  through FastAPI **dependencies** at router level. We chose this over slowapi decorators because
  slowapi needs a module-global limiter and a `request` parameter on every endpoint. The dependency
  approach keeps the limiter inside the app container, where it can be configured per test.
- Moving-window strategy: it is more accurate at window edges than fixed windows.
- The per-user key is taken from the authenticated user ID, after the token is verified, so
  clients cannot dodge the limit with forged tokens.

## Revision history

| Rev | Date       | Change          | Reason | CR |
|-----|------------|-----------------|--------|----|
| 1   | 2026-10-19 | Initial version | —      | —  |
| 2 | 2026-10-19 | R6 trusted proxy only | Spoofed X-Forwarded-For bypassed the auth limit | [CR-002](changes/CR-002-security-hardening.md) |
