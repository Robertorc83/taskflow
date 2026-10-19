import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { tasksApi } from "@/api/tasks";
import type { TaskListParams } from "@/api/types";
import { usersApi } from "@/api/users";
import { queryKeys } from "@/lib/queryKeys";

export function useTasks(params: TaskListParams) {
  return useQuery({
    queryKey: queryKeys.taskList(params),
    queryFn: () => tasksApi.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useTask(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.task(id ?? ""),
    queryFn: () => tasksApi.get(id ?? ""),
    enabled: Boolean(id),
  });
}

export function useUsers() {
  return useQuery({
    queryKey: queryKeys.users,
    queryFn: () => usersApi.list(),
    staleTime: 5 * 60_000,
    select: (page) => page.items,
  });
}
