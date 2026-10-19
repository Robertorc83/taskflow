import { useMutation, useQueryClient, type QueryKey } from "@tanstack/react-query";

import { tasksApi } from "@/api/tasks";
import type { CreateTaskInput, Page, Task, UpdateTaskInput } from "@/api/types";
import { useToast } from "@/components/ui/toastContext";
import { errorMessage } from "@/lib/errors";
import { queryKeys } from "@/lib/queryKeys";

export function useCreateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateTaskInput) => tasksApi.create(input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.tasks }),
  });
}

export interface SaveTaskInput {
  id: string;
  changes: UpdateTaskInput;
  /** `undefined` leaves the assignee untouched; `null` unassigns. */
  assigneeId?: string | null;
}

/** PATCH the editable fields, then change the assignee through its dedicated command (SPEC-004). */
export function useUpdateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, changes, assigneeId }: SaveTaskInput) => {
      let task =
        Object.keys(changes).length > 0
          ? await tasksApi.update(id, changes)
          : await tasksApi.get(id);
      if (assigneeId !== undefined && assigneeId !== (task.assignee?.id ?? null)) {
        task = await tasksApi.assign(id, assigneeId);
      }
      return task;
    },
    onSuccess: (task) => {
      queryClient.setQueryData(queryKeys.task(task.id), task);
      return queryClient.invalidateQueries({ queryKey: queryKeys.taskLists });
    },
  });
}

export function useDeleteTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => tasksApi.remove(id),
    onSuccess: (_data, id) => {
      queryClient.removeQueries({ queryKey: queryKeys.task(id) });
      return queryClient.invalidateQueries({ queryKey: queryKeys.taskLists });
    },
  });
}

type ListSnapshot = [QueryKey, Page<Task> | undefined][];

/**
 * Optimistically flips a task's status in every cached list, rolling back if the server disagrees.
 * Used for "complete" (POST /complete) and "reopen" (PATCH status=pending).
 */
function useOptimisticStatus(
  mutationFn: (id: string) => Promise<Task>,
  nextStatus: Task["status"],
  messages: { success: string; failure: string },
) {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn,
    onMutate: async (id: string) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.taskLists });
      const snapshot: ListSnapshot = queryClient.getQueriesData<Page<Task>>({
        queryKey: queryKeys.taskLists,
      });
      queryClient.setQueriesData<Page<Task>>(
        { queryKey: queryKeys.taskLists },
        (page) =>
          page && {
            ...page,
            items: page.items.map((task) =>
              task.id === id
                ? {
                    ...task,
                    status: nextStatus,
                    is_overdue: nextStatus === "completed" ? false : task.is_overdue,
                    completed_at: nextStatus === "completed" ? new Date().toISOString() : null,
                  }
                : task,
            ),
          },
      );
      return { snapshot };
    },
    onError: (error, _id, context) => {
      context?.snapshot.forEach(([key, data]) => queryClient.setQueryData(key, data));
      toast.error(`${messages.failure}: ${errorMessage(error)}`);
    },
    onSuccess: () => toast.success(messages.success),
    onSettled: () => queryClient.invalidateQueries({ queryKey: queryKeys.tasks }),
  });
}

export function useCompleteTask() {
  return useOptimisticStatus((id) => tasksApi.complete(id), "completed", {
    success: "Task completed",
    failure: "Could not complete the task",
  });
}

export function useReopenTask() {
  return useOptimisticStatus((id) => tasksApi.update(id, { status: "pending" }), "pending", {
    success: "Task reopened",
    failure: "Could not reopen the task",
  });
}
