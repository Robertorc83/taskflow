# CR-002: Security hardening from review

| Field          | Value |
|----------------|-------|
| Date           | 2026-10-19 |
| Type           | security bugfix |
| Specs affected | SPEC-001, SPEC-003, SPEC-006, SPEC-008 |
| Status         | Implemented |
| Source         | Multi-agent review (architecture, security, modularity, bug hunt), findings reproduced before fixing |

## Motivation

The security reviewer **confirmed these against the running stack**:

1. **Rate-limit bypass (high).** uvicorn ran with `--forwarded-allow-ips='*'`, and nginx *appended*
   to client-supplied `X-Forwarded-For` headers. Rotating a fake IP reset the per-IP login limit,
   which allows unlimited password guessing. I reproduced it: 10×401, 429, then a new fake IP got
   401 again.
2. **Public JWT secret accepted (high).** The image defaulted to `development`. The dev secret
   in the repo signed a token for Bob that `/users/me` accepted.
3. **Demo users seeded everywhere (high).** Their passwords are published on the login page.
4. **Postgres published on all interfaces (medium)** with default credentials.
5. **`page=999999999999999999` → 500 (low).** The database offset overflowed.
6. No security headers from nginx, and its version was disclosed.

## Decision

- **Trusted proxy only.** nginx overwrites `X-Forwarded-For` with `$remote_addr`. uvicorn trusts
  `FORWARDED_ALLOW_IPS`, which is just nginx's fixed IP in compose. The image default is
  `127.0.0.1`.
- **Fail-closed image.** The Dockerfile sets `ENVIRONMENT=production` and `SEED_DEMO_DATA=false`.
  Production refuses a missing, dev or short `JWT_SECRET`. The compose stack opts into
  development mode explicitly, and says so in a comment.
- **Seeding** requires `SEED_DEMO_DATA=true` and a non-production environment (`should_seed`).
  The demo panel renders only with `VITE_DEMO_MODE=true`, or in the dev server.
- **Ports:** db (55432) and redis (6380) are published on loopback only, on non-default ports so
  they can't clash with native installs. Port 8000 is loopback-only too.
- **Page bound:** `page ≤ 10 000`.
- **nginx:** `server_tokens off`, plus CSP, `X-Frame-Options`, `nosniff` and `Referrer-Policy`.

## Behavior change (Gherkin)

```gherkin
  @validation
  Scenario: Reject an absurd page number
    When I list my tasks with page 1000000 and size 10
    Then the response status should be 422
```

Unit tests cover config and seeding (`tests/unit/infrastructure/test_config_and_wiring.py`):
production refuses a default or weak secret, and demo data is seeded only when enabled outside
production.

## Verification (live stack)

- [x] Rotating a spoofed XFF **through nginx**: 10×401, then 429, 429
- [x] Rotating a spoofed XFF **directly on :8000**: 10×401, then 429, 429
- [x] `docker run` of the image with no env refuses to start (`JWT_SECRET must be set…`)
- [x] Security headers present; `Server: nginx` with no version
- [x] `docker compose ps`: db, redis and api bound to 127.0.0.1 only

## Accepted, documented

Tokens are kept in `localStorage`, and there is no refresh-token rotation (ADR-0006). `/docs` is
still served (useful for reviewers); disabling it in production is a follow-up.
