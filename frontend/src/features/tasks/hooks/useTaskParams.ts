import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import type { TaskListParams } from "@/api/types";

import { parseTaskParams, serializeTaskParams } from "../filters";

/** List params live in the URL so filtered views are shareable and back-button friendly. */
export function useTaskParams() {
  const [search, setSearch] = useSearchParams();
  const params = useMemo(() => parseTaskParams(search), [search]);

  const update = useCallback(
    (changes: Partial<TaskListParams>, options: { replace?: boolean } = {}) => {
      // Any filter change sends the user back to the first page.
      const resetsPage = !("page" in changes);
      setSearch(
        serializeTaskParams({ ...params, ...(resetsPage ? { page: 1 } : {}), ...changes }),
        {
          replace: options.replace ?? false,
        },
      );
    },
    [params, setSearch],
  );

  const clearFilters = useCallback(() => {
    setSearch(serializeTaskParams({ page: 1, size: params.size, ordering: params.ordering }));
  }, [params.ordering, params.size, setSearch]);

  return { params, update, clearFilters };
}
