// API types, derived from the backend's OpenAPI document (CR-011).
// Never edit schema.gen.ts by hand: run `make types`. CI fails if it drifts from the backend.

import type { components, operations } from "./schema.gen";

type Schemas = components["schemas"];

export type TaskStatus = Schemas["TaskStatus"];
export type TaskScope = Schemas["TaskScope"];
export type TaskOrdering = Schemas["TaskOrdering"];

export type UserSummary = Schemas["UserSummaryResponse"];
export type User = Schemas["UserResponse"];
export type Task = Schemas["TaskResponse"];
export type TokenPair = Schemas["TokenResponse"];
export type FieldError = Schemas["FieldError"];
/** RFC 9457 problem details. */
export type ProblemDetails = Schemas["Problem"];

/** The pagination envelope shared by every list endpoint. */
export type Page<T> = Omit<Schemas["PageResponse_TaskResponse_"], "items"> & { items: T[] };

type ListTasksQuery = NonNullable<operations["list_tasks_api_v1_tasks_get"]["parameters"]["query"]>;
/** Query parameters the UI always sends (page and size are explicit). */
export type TaskListParams = Omit<
  ListTasksQuery,
  "page" | "size" | "status" | "due_from" | "due_to"
> & {
  status?: TaskStatus;
  due_from?: string;
  due_to?: string;
  page: number;
  size: number;
};

export type CreateTaskInput = Schemas["TaskCreateRequest"];
export type UpdateTaskInput = Schemas["TaskUpdateRequest"];
export type RegisterInput = Schemas["RegisterRequest"];
export type LoginInput = Schemas["LoginRequest"];
