# CR-014: No dead-end edit dialog

| Field          | Value |
|----------------|-------|
| Date           | 2026-10-19 |
| Type           | UX bugfix |
| Specs affected | SPEC-007 (F12) |
| Status         | Implemented |
| Source         | Manual QA on desktop and a 390 px phone viewport |

## Motivation

Opening `/tasks/:id/edit` for a task you can't see ("Task not found") or don't own ("Only the
owner can edit this task.") showed the message with **no button**. Escape and tapping the backdrop
did close it, but neither is discoverable, especially on a phone, where the dialog is a bottom
sheet.

## Decision

Both error states render a secondary **Back to tasks** button. It uses the dialog's existing
`close()`, so it returns to `/tasks` with the list's filters kept.

## Verification

- [x] New test, red first ("Unable to find role=button, name=Back to tasks"), then green. It
  asserts that the dialog closes and the URL keeps `?status=pending`.
- [x] Real browser, phone viewport, as Carol on Alice's private task: the button shows in the
  sheet, and tapping it lands on `/tasks?status=pending` with the dialog closed.
- [x] 67 frontend tests with no `act()` warnings; lint, typecheck and build are clean.
