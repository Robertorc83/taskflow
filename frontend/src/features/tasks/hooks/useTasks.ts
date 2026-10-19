import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { tasksApi } from "@/api/tasks";
import type { TaskListParams } from "@/api/types";

import { taskQueryKeys } from "../queryKeys";

export function useTasks(params: TaskListParams) {
  return useQuery({
    queryKey: taskQueryKeys.list(params),
    queryFn: () => tasksApi.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useTask(id: string | undefined) {
  return useQuery({
    queryKey: taskQueryKeys.detail(id ?? ""),
    queryFn: () => tasksApi.get(id ?? ""),
    enabled: Boolean(id),
  });
}
