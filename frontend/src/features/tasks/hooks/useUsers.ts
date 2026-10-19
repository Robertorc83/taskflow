import { useQuery } from "@tanstack/react-query";

import { usersApi } from "@/api/users";
import { queryKeys } from "@/lib/queryKeys";

/** Active directory of users, for the assignee picker. */
export function useUsers() {
  return useQuery({
    queryKey: queryKeys.users,
    queryFn: () => usersApi.list(),
    staleTime: 5 * 60_000,
    select: (page) => page.items,
  });
}
