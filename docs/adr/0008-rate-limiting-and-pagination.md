# ADR-0008: Rate limiting via `limits` dependencies; offset pagination

**Status:** Accepted · **Date:** 2026-10-19

## Context
The spec asks for rate limiting and paginated lists.

## Decision
Rate limiting uses the `limits` library (slowapi's engine) behind a small `RateLimiter` adapter applied as **router-level FastAPI dependencies**: per IP on `/auth/*`, per authenticated user elsewhere, with a Redis moving window. This avoids slowapi's module-global limiter and per-endpoint `request` parameters, and lets tests swap limits per scenario. Pagination is offset-based (`page`/`size ≤ 100`) with deterministic tie-breakers.

## Consequences
+ Limits are shared across workers; 429 carries `Retry-After`.
− Offset pagination degrades on very deep pages; keyset/cursor pagination is the upgrade path.
