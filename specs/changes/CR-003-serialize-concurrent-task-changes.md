# CR-003: Serialize concurrent changes to a task

| Field          | Value |
|----------------|-------|
| Date           | 2026-10-19 |
| Type           | bugfix |
| Specs affected | SPEC-004 |
| Status         | Implemented |
| Source         | Multi-agent review (architecture, security, modularity, bug hunt), findings reproduced before fixing |

## Motivation

The bug reviewer sent 6 parallel `POST /complete` requests for one task. Up to **5 returned 200**,
which meant 5 `TaskCompleted` events and duplicate notifications. That contradicts R5 (completing
twice is a 409) and R7.

The cause: the use case read the row with a plain SELECT, checked `status` in memory, then wrote it
back. Every request saw `pending`.

## Decision

- **New rule R10:** changes to one task are serialized.
- `TaskRepository.get(task_id, *, for_update=False)`. The SQLAlchemy adapter uses
  `SELECT … FOR UPDATE`.
- Every mutating use case locks the row: update, delete, assign, complete, reopen.
- Reads stay lock-free.

A conditional `UPDATE … WHERE status <> 'completed'` was rejected. It would move the rule from the
domain into SQL.

## Verification

- [x] `tests/integration/test_database.py::test_concurrent_completions_succeed_exactly_once`: 8
  concurrent completes on real Postgres. Red (8×ok), then green (1 ok, 7 conflicts, exactly one
  event).
