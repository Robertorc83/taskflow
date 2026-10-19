# SPEC-001: Registration & JWT Authentication

| Field    | Value                    |
|----------|--------------------------|
| Status   | Done     |
| Stories  | US-01                    |
| Features | `authentication.feature` |

## Context

Every task belongs to a user, so the API needs identities. The spec requires JWT authentication.
We use stateless access tokens with a short life and refresh tokens with a longer one.

## Scope

**In:** register, log in, refresh, current-user profile, user directory (for the assignee picker).
**Out:** password reset, email verification, roles/admin UI, token revocation lists.

## Business rules

- **R1** Emails are unique and case-insensitive. They are stored lower-cased and trimmed.
- **R2** Passwords are 8–128 characters. They are stored only as an Argon2 hash and never returned.
- **R3** Full name is required, 1–100 characters after trimming.
- **R4** Login with an unknown email or a wrong password returns the same `401`. This prevents
  user enumeration.
- **R5** Inactive users cannot log in or use their existing tokens (`401`).
- **R6** Access tokens expire after 15 min and refresh tokens after 7 days (configurable). Each
  token carries a `type` claim, and one type is never accepted where the other is expected.
- **R7** Any malformed, expired or tampered token is rejected with `401` and a `WWW-Authenticate: Bearer` header.

## API contract

| Method | Path                    | Auth | Body / Query                              | Success |
|--------|-------------------------|------|-------------------------------------------|---------|
| POST   | `/api/v1/auth/register` | —    | `{email, full_name, password}`            | `201` `User` |
| POST   | `/api/v1/auth/login`    | —    | `{email, password}`                       | `200` `TokenPair` |
| POST   | `/api/v1/auth/refresh`  | —    | `{refresh_token}`                         | `200` `TokenPair` |
| GET    | `/api/v1/users/me`      | ✔    | —                                         | `200` `User` |
| GET    | `/api/v1/users`         | ✔    | `?page=1&size=20` (size ≤ 100)            | `200` `Page<User>` |

```jsonc
// User
{ "id": "uuid", "email": "alice@example.com", "full_name": "Alice Smith", "is_active": true, "created_at": "2026-10-19T10:00:00Z" }
// TokenPair
{ "access_token": "…", "refresh_token": "…", "token_type": "bearer", "expires_in": 900 }
```

Errors: `409` duplicate email, `422` validation, `401` bad credentials or token, `429` rate limited (SPEC-006).

## Acceptance criteria (`authentication.feature`)

| Rule | Scenarios |
|------|-----------|
| R1   | Register a new account · Registering with an email that is already taken |
| R2, R3 | Registration input is validated (outline) · Register a new account (no password in response) |
| R4   | Log in with valid credentials · Log in with a wrong password · Log in with an unknown email |
| R5   | An inactive user cannot log in |
| R6   | Refresh an access token · An access token cannot be used as a refresh token |
| R7   | Protected endpoints reject missing tokens · Protected endpoints reject a tampered token |

## Design notes

- Use cases: `RegisterUser`, `AuthenticateUser`, `RefreshTokens`, `GetUser`, `ListUsers`.
- `TokenService` port: `issue(user_id) -> TokenPair`, `verify(token, expected_type) -> UUID`.
  `JwtTokenService` uses HS256 with `pyjwt` and adds `sub`, `type`, `iat`, `exp` and `jti` claims.
- Swagger uses the `HTTPBearer` scheme, so the "Authorize" button takes a pasted access token.
- Argon2 hashing is deliberately slow. Unit tests use a plain-text fake hasher; acceptance tests
  use the real one.

## Revision history

| Rev | Date       | Change          | Reason | CR |
|-----|------------|-----------------|--------|----|
| 1   | 2026-10-19 | Initial version | —      | —  |
