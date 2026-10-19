import type { TaskListParams } from "@/api/types";

export const queryKeys = {
  me: ["users", "me"] as const,
  users: ["users", "list"] as const,
  tasks: ["tasks"] as const,
  taskLists: ["tasks", "list"] as const,
  taskList: (params: TaskListParams) => ["tasks", "list", params] as const,
  task: (id: string) => ["tasks", "detail", id] as const,
};
