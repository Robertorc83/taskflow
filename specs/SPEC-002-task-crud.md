# SPEC-002: Task CRUD

| Field    | Value               |
|----------|---------------------|
| Status   | Done     |
| Stories  | US-02, US-05        |
| Features | `task_crud.feature` |

## Context

Users capture work as tasks and keep them accurate over time.

## Scope

**In:** create, read one, partial update (PATCH), delete, reopen a completed task.
**Out:** soft delete or archive, attachments, comments, labels.

## Domain model

```
Task
  id            UUID
  title         str      1–200 chars, trimmed, required
  description   str?     ≤ 2000 chars
  status        TaskStatus = pending | in_progress | completed
  due_date      date?
  owner_id      UUID     the creator; never changes
  assignee_id   UUID?    see SPEC-004
  created_at, updated_at   datetime (UTC)
  completed_at  datetime? set if and only if status == completed
```

## Business rules

- **R1** A new task starts as `pending`, and the caller becomes its owner.
- **R2** The title is required, and after trimming must be 1–200 characters.
- **R3** A due date, if given, cannot be in the past (compared with "today" from the `Clock`).
  The rule applies on create and whenever the due date is changed. A task whose date has since
  passed can still be edited without touching the date.
- **R4** Only the **owner** may update or delete a task. An assignee who tries gets `403`. Anyone
  else gets `404` (SPEC-000 visibility rule).
- **R5** PATCH may set `status` to `pending` or `in_progress` only. Completing a task goes through
  `POST /complete` (SPEC-004). Setting a completed task back to `pending` or `in_progress`
  **reopens** it and clears `completed_at`.
- **R6** PATCH is partial: omitted fields are left as they are, and sending `null` for
  `description` or `due_date` clears it.
- **R7** Every change updates `updated_at`.
- **R8** `is_overdue` is derived: `due_date < today` and status ≠ `completed`.

## API contract

| Method | Path                    | Body                                                            | Success |
|--------|-------------------------|-----------------------------------------------------------------|---------|
| POST   | `/api/v1/tasks`         | `{title, description?, due_date?, assignee_id?}`                | `201` `Task` |
| GET    | `/api/v1/tasks/{id}`    | —                                                               | `200` `Task` |
| PATCH  | `/api/v1/tasks/{id}`    | any of `{title, description, due_date, status}`                 | `200` `Task` |
| DELETE | `/api/v1/tasks/{id}`    | —                                                               | `204` |

```jsonc
// Task
{
  "id": "uuid",
  "title": "Write report",
  "description": "Q3 numbers",
  "status": "pending",
  "due_date": "2026-11-01",
  "is_overdue": false,
  "owner":    { "id": "uuid", "email": "alice@example.com", "full_name": "Alice Smith" },
  "assignee": { "id": "uuid", "email": "bob@example.com",   "full_name": "Bob Jones" } | null,
  "created_at": "…", "updated_at": "…", "completed_at": null
}
```

Errors: `401`, `403` (R4), `404`, `422` (R2, R3, R5, malformed UUID).

## Acceptance criteria (`task_crud.feature`)

| Rule | Scenarios |
|------|-----------|
| R1 | Create a task · Create a task with only a title |
| R2 | A task title is required · A blank task title is rejected · A title longer than 200 characters is rejected |
| R3 | A task cannot be created with a due date in the past · A due date cannot be moved into the past |
| R4 | Other users cannot see my tasks · Other users cannot update my tasks · Other users cannot delete my tasks · An assignee can view a task · An assignee cannot edit a task |
| R5 | A task cannot be completed through an update |
| R6 | Update a task · Clear a task's due date |
| —  | View a task I own · Delete a task · Requesting a task that does not exist |

## Design notes

- `Task.create(...)` is a factory that enforces R1–R3. `Task.update(...)` enforces R3, R5 and R7.
- The application layer uses an `UNSET` sentinel so that "not sent" and "sent as null" (R6) are
  different. The presentation layer builds the change set from Pydantic's `model_fields_set`.
- Responses embed `owner` and `assignee` summaries, so the UI never needs an N+1 lookup. Use cases
  batch-load the users they need in one query.

## Revision history

| Rev | Date       | Change          | Reason | CR |
|-----|------------|-----------------|--------|----|
| 1   | 2026-10-19 | Initial version | —      | —  |
