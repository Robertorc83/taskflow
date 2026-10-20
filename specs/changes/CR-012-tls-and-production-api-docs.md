# CR-012: TLS termination and production API docs

| Field          | Value |
|----------------|-------|
| Date           | 2026-10-19 |
| Type           | security hardening |
| Specs affected | SPEC-000 (NFR-11), SPEC-008 (D9, D11) |
| Status         | Implemented |
| Source         | Production-readiness audit before real traffic |

## Motivation

- **No TLS.** nginx listened on plain `:80` only, so tokens and passwords would cross the network
  in clear text. HSTS couldn't be sent without HTTPS.
- **API docs in every environment.** `/docs`, `/redoc` and `/openapi.json` were served in
  production too, which hands out a map of every endpoint.
- The CSP, `X-Frame-Options`, `nosniff` and `Referrer-Policy` headers were **already** in place
  (CR-002). The audit first reported them missing, because it only searched `nginx.conf` and not
  the included snippet.

## Decision

- **TLS ends at nginx and fails closed,** like the API image (CR-002). The web image defaults to
  `NGINX_TLS=true`. An entrypoint script (`nginx/select-config.sh`) links in `https.conf`, and the
  container **exits** if `/etc/nginx/certs/tls.crt` and `tls.key` aren't mounted.
  `NGINX_TLS=false` serves `http.conf`, for local compose or when a load balancer terminates TLS.
- **HTTPS server:** TLS 1.2 and 1.3 only, with the Mozilla "intermediate" ciphers, HTTP/2 and no
  session tickets. Port 80 redirects to HTTPS (`301`), except `/healthz`, so the container health
  check needs no certificate.
- **HSTS only over HTTPS:** `security-headers.conf` sends `Strict-Transport-Security: $hsts`. Each
  server sets `$hsts`, and it's empty on plain HTTP, so nginx omits it there. The application
  locations live once in `app.conf`, shared by both servers.
- **Local HTTPS:** `make certs` creates a self-signed certificate in `certs/` (git-ignored), and
  `make up-tls` layers `docker-compose.tls.yml` on the stack. The default `make up` stays on plain
  HTTP, so the demo and the E2E job are unchanged.
- **API docs:** a new setting, `API_DOCS_ENABLED`. When it's unset, docs are published everywhere
  except production. `create_app` passes `openapi_url=None` when the docs are off, which also
  removes `/docs` and `/redoc`. The OpenAPI *export* (`make types`) is unaffected.

## Behavior change

```gherkin
# api_documentation.feature
  Scenario: Documentation is published outside production
  Scenario: Documentation is hidden in production
  Scenario: Production can publish the documentation explicitly
```

`frontend/nginx/tls-check.sh` (`make tls-check`, and a CI step in the `e2e` job) runs the real image
and checks 11 behaviors: it fails closed without a certificate, HTTP redirects, `/healthz` stays on
HTTP, HTTPS serves the app with HSTS and the security headers, TLS 1.2 is accepted and 1.1 refused,
and with `NGINX_TLS=false` the app is served without HSTS.

## Verification

- [x] The docs scenario was red for the right reason (production served `/docs` with a 200), then
  green. A unit test covers the full setting matrix.
- [x] `tls-check.sh` was red against the old image: 5 failures. Two checks passed **for the wrong
  reason**, and were tightened before implementing:
  - `/healthz` returned 200 from the single-page-app fallback; it must now return `ok`.
  - "TLS 1.1 refused" passed only because nothing listened on 443; a "TLS 1.2 accepted" check now
    proves the listener exists.
- [x] All 11 checks green. Full stack with `make up-tls`: `:3000` redirects to `https://localhost`,
  login through nginx returns 200 over HTTP/2, and HSTS, CSP and `X-Frame-Options` are present.
- [x] Dev stack (`make up`) over HTTP: Playwright desktop and mobile pass. 201 backend tests pass
  at 97% coverage, `make lint` is clean, and the generated API types don't drift.
