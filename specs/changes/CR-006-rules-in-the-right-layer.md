# CR-006: Business rules in the right layer

| Field          | Value |
|----------------|-------|
| Date           | 2026-10-19 |
| Type           | architecture / bugfix |
| Specs affected | SPEC-001, SPEC-002 |
| Status         | Implemented |
| Source         | Multi-agent review (architecture, security, modularity, bug hunt), findings reproduced before fixing |

## Motivation

- **Password length (SPEC-001 R2)** was enforced only by the Pydantic schema. Any other caller
  could skip it, and the seed already did: `Bob123!` is 7 characters. Two reviewers found this.
- **`PATCH {"title": null}`** reported its error on the field `body`, so the frontend couldn't
  attach it to the title input (SPEC-007 F11).

## Decision

- The constants `PASSWORD_MIN/MAX_LENGTH` live in the domain. `RegisterUser` enforces them, raising
  `InvalidInputError(field="password")`. The schema reuses the constants for OpenAPI.
- The demo password is now `Bob12345!` everywhere: seed, README, login panel, test fixtures.
- Null-rejection became a `field_validator`, so the error loc is the field itself.

## Verification

- [x] Unit: `test_password_length_is_a_use_case_rule` (red, then green)
- [x] Scenario: "The title cannot be cleared" asserts the error is about `title` (red, then green)
