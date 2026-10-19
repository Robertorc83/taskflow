import { request } from "./http";
import type { CreateTaskInput, Page, Task, TaskListParams, UpdateTaskInput } from "./types";

export const tasksApi = {
  list: (params: TaskListParams) =>
    request<Page<Task>>("/tasks", {
      query: { ...params, scope: params.scope === "all" ? undefined : params.scope },
    }),
  get: (id: string) => request<Task>(`/tasks/${id}`),
  create: (input: CreateTaskInput) => request<Task>("/tasks", { method: "POST", body: input }),
  update: (id: string, input: UpdateTaskInput) =>
    request<Task>(`/tasks/${id}`, { method: "PATCH", body: input }),
  remove: (id: string) => request<undefined>(`/tasks/${id}`, { method: "DELETE" }),
  complete: (id: string) => request<Task>(`/tasks/${id}/complete`, { method: "POST" }),
  reopen: (id: string) => request<Task>(`/tasks/${id}/reopen`, { method: "POST" }),
  assign: (id: string, assigneeId: string | null) =>
    request<Task>(`/tasks/${id}/assignee`, { method: "PUT", body: { assignee_id: assigneeId } }),
};
