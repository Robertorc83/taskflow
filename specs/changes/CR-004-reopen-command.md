# CR-004: Explicit reopen command for owner or assignee

| Field          | Value |
|----------------|-------|
| Date           | 2026-10-19 |
| Type           | feature / spec conflict |
| Specs affected | SPEC-004, SPEC-007 |
| Status         | Implemented |
| Source         | Multi-agent review (architecture, security, modularity, bug hunt), findings reproduced before fixing |

## Motivation

The specs disagreed:
- SPEC-007 F12 showed **Reopen** to the assignee;
- SPEC-002 R4 made every PATCH, including the status change behind reopen, owner-only.

The result was that an assignee's Reopen click always got a 403. Two reviewers reproduced it
independently.

The original brief only asks to "mark tasks as completed". Decision taken with the user: whoever
may complete a task may undo that.

## Decision

- **New rule SPEC-004 R9:** `POST /tasks/{id}/reopen`. Allowed for the owner or the assignee.
  409 if the task is not completed, 404 if it isn't visible.
- **Domain:** `Task.reopen()` raises `TaskNotCompletedError`. `Task.can_be_completed_by()` makes
  the completion permission explicit instead of relying on visibility.
- PATCH keeps working for owners (SPEC-002 R5).
- The frontend's Reopen calls the new endpoint.

## Behavior change (Gherkin)

```gherkin
  Scenario: The assignee reopens a completed task
  Scenario: Reopening a task that is not completed is a conflict
  Scenario: A stranger cannot reopen a task
```

## Verification

- [x] The first two scenarios were red before the change (the endpoint didn't exist). The third
  was vacuously green, then meaningfully green.
- [x] Unit: `TestReopenTask`, `TestReopening`, `test_only_owner_and_assignee_can_complete`
- [x] Frontend: the reopen tests assert `POST …/reopen` and that no PATCH is sent
