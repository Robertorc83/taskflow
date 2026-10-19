# ADR-0006: JWT access + refresh tokens, Argon2 hashing

**Status:** Accepted · **Date:** 2026-10-19

## Context
The spec requires JWT. Tokens must be revocable in practice (short-lived) without a session store.

## Decision
HS256 access tokens (15 min) and refresh tokens (7 days), each with a `type` claim that is checked. Every request re-loads the user, so deactivation takes effect immediately. Passwords use Argon2 (pwdlib). Unknown-email logins still hash, to equalize timing.

## Consequences
+ Stateless; deactivated users lose access at their next request.
− No refresh-token rotation/revocation list (documented future work).
− Tokens in `localStorage` are readable by XSS; an httpOnly-cookie BFF would be the hardened option.
