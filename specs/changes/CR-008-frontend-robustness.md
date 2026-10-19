# CR-008: Frontend robustness and module boundaries

| Field          | Value |
|----------------|-------|
| Date           | 2026-10-19 |
| Type           | bugfix / refactor |
| Specs affected | SPEC-007 |
| Status         | Implemented |
| Source         | Multi-agent review (architecture, security, modularity, bug hunt), findings reproduced before fixing |

## Motivation (bug-hunt findings)

- Deleting the last task on page N > 1 showed "No tasks yet" with no pagination.
- **Any** refresh failure logged the user out, including a 429 or a network error, even when the
  refresh token was still valid.
- When an edit half-failed (PATCH succeeded, then the assignee PUT failed), the caches stayed
  stale.
- Modularity:
  - `lib/` knew about task query keys;
  - `useUsers` lived inside `useTasks`;
  - validation limits were magic numbers;
  - nothing enforced import boundaries.

## Decision

- **Pagination:** a page past the end redirects to the last real page, with a replace navigation.
- **Refresh:** tokens are cleared only when `/auth/refresh` answers 400, 401 or 422.
- **Edit:** the edit mutation invalidates the task queries in `onSettled`.
- **Boundaries:** ESLint `no-restricted-imports` rules:
  - `components/ui` cannot import from `features` or `api`;
  - `api` cannot import from `features` or `components`;
  - `lib` cannot import from `features` or `components`.
- **Structure:** limits live in `lib/limits.ts`, query keys in `features/tasks`, `buttonClasses()`
  next to `Button`.

## Verification

- [x] 12 new or updated Given/When/Then tests (66 in total). Statement coverage is 97%.
- [x] lint, typecheck, format and build are clean, with zero warnings
