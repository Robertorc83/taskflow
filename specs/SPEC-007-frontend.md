# SPEC-007: Web Frontend

| Field    | Value                                              |
|----------|----------------------------------------------------|
| Status   | Done     |
| Stories  | US-01 … US-07                                      |
| Features | `frontend/src/**/*.test.tsx` (Given/When/Then), `frontend/e2e/*.spec.ts` |

## Context

A responsive single-page app that covers every backend use case. It should feel like a small,
polished product, not an admin scaffold.

## Stack

React 18 + TypeScript (strict) + Vite · React Router · TanStack Query · React Hook Form + Zod ·
Tailwind CSS · Vitest + Testing Library + MSW · Playwright (smoke E2E).

## Screens & behaviors

### Login / Register (`/login`, `/register`)
- **F1** Email and password form with inline validation that mirrors the backend (email format,
  password ≥ 8).
- **F2** On success, tokens are stored and the user is redirected to `/tasks` (or the page they
  originally asked for).
- **F3** Wrong credentials show a non-field error ("Invalid email or password"). A `429` shows
  "Too many attempts, try again in N s".
- **F4** The login page shows the demo credentials, for reviewers.

### Task list (`/tasks`)
- **F5** A paginated list showing title, status badge, due date (an overdue badge when
  `is_overdue`), and assignee.
- **F6** Filters: status (All/Pending/In progress/Completed), scope (All/Mine/Assigned to me),
  due from/to, and ordering. Filters and page live in the **URL query string**.
- **F7** Loading skeleton, empty state ("No tasks match these filters" + clear-filters action),
  and an error state with retry.
- **F8** Quick actions per task: complete (optimistic update, rolled back on error) and
  reopen. Owners also get edit and delete.
- **F9** Delete asks for confirmation in an in-app modal (no `window.confirm`).

### Create / edit task (modal or `/tasks/new`, `/tasks/:id/edit`)
- **F10** Fields: title (required, ≤ 200), description (≤ 2000), due date (not in the past on
  create), assignee (select filled from `GET /users`).
- **F11** Server validation errors (`422`) are mapped onto the matching fields.
- **F12** Only the owner sees edit, assign and delete controls. The assignee sees complete and reopen.

### Global
- **F13** An expired access token is refreshed once, transparently. If the refresh fails, the user
  is logged out and sent to `/login`.
- **F14** Responsive from 360 px wide. The filters collapse into a drawer on mobile.
- **F15** Accessible: labelled inputs, focus-visible styles, keyboard-operable modals, `aria-live`
  for toasts.
- **F16** **No errors or warnings in the browser console** (React StrictMode on).

## Structure

```
frontend/src/
  app/           App, router, providers
  api/           http client (auth header, refresh-on-401), endpoint functions, generated types
  features/auth/ pages, AuthProvider, useAuth
  features/tasks/ pages, components, hooks (useTasks, useTaskMutations), schemas, filters
  components/ui/ Button, Input, Select, Modal, Badge, Pagination, Spinner, EmptyState, Toast
  lib/           dates, query keys, cn()
  test/          MSW handlers, render helpers
```

## Acceptance criteria

Component and page tests are named in Given/When/Then form, for example
`describe("Given I am on the task list") → it("when I filter by Completed, then only completed tasks are shown")`.

| Behavior | Test |
|----------|------|
| F1–F3 | `LoginPage.test.tsx` |
| F5–F7 | `TaskListPage.test.tsx` |
| F8–F9 | `TaskListPage.test.tsx`, `TaskCard.test.tsx` |
| F10–F12 | `TaskForm.test.tsx` |
| F13 | `http.test.ts` |
| Full journey (login → create → filter → complete → delete) | `e2e/smoke.spec.ts` |

## Revision history

| Rev | Date       | Change          | Reason | CR |
|-----|------------|-----------------|--------|----|
| 1   | 2026-10-19 | Initial version | —      | —  |
