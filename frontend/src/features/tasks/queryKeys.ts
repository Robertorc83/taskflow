import type { TaskListParams } from "@/api/types";

/** Query keys owned by the tasks feature. Lists and details share the `tasks` root for invalidation. */
export const taskQueryKeys = {
  all: ["tasks"] as const,
  lists: ["tasks", "list"] as const,
  list: (params: TaskListParams) => ["tasks", "list", params] as const,
  detail: (id: string) => ["tasks", "detail", id] as const,
};
