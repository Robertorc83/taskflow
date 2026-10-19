# SPEC-003: Listing, Pagination & Filtering

| Field    | Value                  |
|----------|------------------------|
| Status   | Done     |
| Stories  | US-03, US-04           |
| Features | `task_listing.feature` |

## Context

Users need to see what is on their plate and narrow it down by status and due date, even when the
list grows large.

## Business rules

- **R1** The list contains only tasks the caller owns or is assigned to.
- **R2** `scope` narrows that further: `all` (default), `owned`, `assigned`.
- **R3** `status` filters by exact status. Unknown values give `422`.
- **R4** `due_from` and `due_to` are inclusive calendar dates; either may be omitted. Tasks with no
  due date never match a date filter. If `due_from > due_to` the API returns `422`.
- **R5** Filters combine with AND.
- **R6** Pagination is page-based: `1 ≤ page ≤ 10 000` *(CR-002)*, `1 ≤ size ≤ 100`, default `size = 20`. A page past
  the end returns an empty `items` list, not an error.
- **R7** `ordering` ∈ `created_at`, `-created_at` (default), `due_date`, `-due_date`. When sorting
  by due date, tasks without a due date always come **last**. Ties break on `created_at`, then
  `id`, so pagination is stable.

## API contract

`GET /api/v1/tasks?scope=all&status=pending&due_from=2026-10-01&due_to=2026-10-31&ordering=due_date&page=1&size=20`

```jsonc
// Page<Task>
{ "items": [Task, …], "total": 42, "page": 1, "size": 20, "pages": 3 }
```

`pages` is `ceil(total / size)`, and is `0` when `total` is 0.

## Acceptance criteria (`task_listing.feature`)

| Rule | Scenarios |
|------|-----------|
| R1 | List all my tasks · Tasks assigned to me are listed · Other users' tasks are never listed |
| R2 | Only tasks assigned to me · Only tasks I own |
| R3 | Filter by status (outline) · Reject an invalid status filter |
| R4 | Filter by due date range · Filter by due date from · Reject an inverted date range |
| R5 | Combine status and due date filters |
| R6 | Paginate results · A page past the end is empty · Reject a page size above the maximum · Reject an absurd page number |
| R7 | Order by due date |

## Design notes

- `TaskFilters` and `PageRequest` are application DTOs that validate themselves (R4, R6), so the
  same rules hold for any delivery mechanism.
- The repository runs a single `COUNT(*)` and a single `SELECT … LIMIT/OFFSET`. Indexes cover
  `(owner_id, status)`, `(assignee_id, status)` and `due_date`.
- Offset pagination is good enough at this scale. Cursor pagination is a documented future
  option (ADR-0008).

## Revision history

| Rev | Date       | Change          | Reason | CR |
|-----|------------|-----------------|--------|----|
| 1   | 2026-10-19 | Initial version | —      | —  |
| 2 | 2026-10-19 | Upper bound on page | page=1e18 caused a 500 | [CR-002](changes/CR-002-security-hardening.md) |
