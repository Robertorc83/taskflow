import type { TaskListParams, TaskOrdering, TaskScope, TaskStatus } from "@/api/types";

export const DEFAULT_PAGE_SIZE = 10;
export const DEFAULT_ORDERING: TaskOrdering = "-created_at";

export const STATUS_OPTIONS: { value: TaskStatus; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "in_progress", label: "In progress" },
  { value: "completed", label: "Completed" },
];

export const SCOPE_OPTIONS: { value: TaskScope; label: string }[] = [
  { value: "all", label: "All" },
  { value: "owned", label: "Mine" },
  { value: "assigned", label: "Assigned to me" },
];

export const ORDERING_OPTIONS: { value: TaskOrdering; label: string }[] = [
  { value: "-created_at", label: "Newest first" },
  { value: "created_at", label: "Oldest first" },
  { value: "due_date", label: "Due date (soonest)" },
  { value: "-due_date", label: "Due date (latest)" },
];

const isOneOf = <T extends string>(options: { value: T }[], value: string | null): value is T =>
  value !== null && options.some((option) => option.value === value);

const isIsoDate = (value: string | null): value is string =>
  value !== null && /^\d{4}-\d{2}-\d{2}$/.test(value);

function positiveInt(
  value: string | null,
  fallback: number,
  max = Number.MAX_SAFE_INTEGER,
): number {
  const parsed = Number.parseInt(value ?? "", 10);
  return Number.isInteger(parsed) && parsed >= 1 ? Math.min(parsed, max) : fallback;
}

/** Parses list params from the URL, ignoring anything malformed (URLs are user input). */
export function parseTaskParams(search: URLSearchParams): TaskListParams {
  const status = search.get("status");
  const scope = search.get("scope");
  const ordering = search.get("ordering");
  const dueFrom = search.get("due_from");
  const dueTo = search.get("due_to");
  return {
    status: isOneOf(STATUS_OPTIONS, status) ? status : undefined,
    scope: isOneOf(SCOPE_OPTIONS, scope) ? scope : "all",
    due_from: isIsoDate(dueFrom) ? dueFrom : undefined,
    due_to: isIsoDate(dueTo) ? dueTo : undefined,
    ordering: isOneOf(ORDERING_OPTIONS, ordering) ? ordering : DEFAULT_ORDERING,
    page: positiveInt(search.get("page"), 1),
    size: positiveInt(search.get("size"), DEFAULT_PAGE_SIZE, 100),
  };
}

/** Serialises params back to the URL, omitting defaults to keep links short. */
export function serializeTaskParams(params: TaskListParams): URLSearchParams {
  const search = new URLSearchParams();
  if (params.status) search.set("status", params.status);
  if (params.scope && params.scope !== "all") search.set("scope", params.scope);
  if (params.due_from) search.set("due_from", params.due_from);
  if (params.due_to) search.set("due_to", params.due_to);
  if (params.ordering && params.ordering !== DEFAULT_ORDERING)
    search.set("ordering", params.ordering);
  if (params.page > 1) search.set("page", String(params.page));
  if (params.size !== DEFAULT_PAGE_SIZE) search.set("size", String(params.size));
  return search;
}

export function hasActiveFilters(params: TaskListParams): boolean {
  return Boolean(
    params.status || params.due_from || params.due_to || (params.scope && params.scope !== "all"),
  );
}
