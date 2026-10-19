# ADR-0005: Explicit endpoints for completing and assigning

**Status:** Accepted · **Date:** 2026-10-19

## Context
Completing and assigning carry rules (who may do it, idempotency) and side effects (notifications).

## Decision
`POST /tasks/{id}/complete` and `PUT /tasks/{id}/assignee` are separate commands. PATCH only edits plain fields and may move status between `pending` and `in_progress` (which reopens a completed task).

## Consequences
+ Each command maps 1:1 to a use case and a domain method that emits an event.
+ Authorization differs per action (assignee may complete, only owner may assign) without conditionals inside PATCH.
− Two extra endpoints; the edit form issues PATCH then PUT when both change.
