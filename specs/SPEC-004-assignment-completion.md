# SPEC-004: Assignment & Completion

| Field    | Value                           |
|----------|---------------------------------|
| Status   | Approved                        |
| Stories  | US-06, US-07                    |
| Features | `assignment_completion.feature` |

## Context

Work gets delegated and finished. Both actions have rules and side effects (notifications), so
they are explicit commands rather than generic PATCH fields.

## Business rules

- **R1** Only the **owner** may assign, reassign or unassign a task (`403` for the assignee,
  `404` for anyone else).
- **R2** The assignee must exist and be active, otherwise `422`. Assigning to yourself is allowed.
- **R3** `assignee_id: null` unassigns the task.
- **R4** The **owner or the assignee** may complete a task.
- **R5** A completed task cannot be completed again (`409`). Reopening is a status change through
  PATCH (SPEC-002 R5).
- **R6** Completing sets `status = completed` and `completed_at = now`.
- **R7** Each successful assignment to a user emits a `TaskAssigned` event. Each completion emits
  `TaskCompleted`. Events are published only after the transaction commits (SPEC-005).
- **R8** Creating a task with an `assignee_id` applies R2 and emits `TaskAssigned`.

## API contract

| Method | Path                            | Body                     | Success |
|--------|---------------------------------|--------------------------|---------|
| PUT    | `/api/v1/tasks/{id}/assignee`   | `{assignee_id: uuid \| null}` | `200` `Task` |
| POST   | `/api/v1/tasks/{id}/complete`   | —                        | `200` `Task` |

## Acceptance criteria (`assignment_completion.feature`)

| Rule | Scenarios |
|------|-----------|
| R1 | Only the owner can reassign a task |
| R2 | Assigning to a user that does not exist · Assigning to a deactivated user |
| R3 | Unassign a task |
| R4 | The owner completes a task · The assignee completes a task · A stranger cannot complete a task |
| R5 | A completed task cannot be completed again · Reopen a completed task |
| R6 | The owner completes a task |
| R7 | Assign a task to another user · The assignee completes a task |
| R8 | Create a task already assigned to someone |

## Design notes

- `Task.assign_to(user_id | None, now)` and `Task.complete(now)` are domain methods. Authorization
  ("who may do this") is checked in the use cases `AssignTask` and `CompleteTask`.
- Events are plain frozen dataclasses in `domain.events`. Use cases collect them and hand them to
  the `EventPublisher` port after `uow.commit()`.

## Revision history

| Rev | Date       | Change          | Reason | CR |
|-----|------------|-----------------|--------|----|
| 1   | 2026-10-19 | Initial version | —      | —  |
