import { renderHook, waitFor } from "@testing-library/react";
import { http } from "msw";
import type { ReactNode } from "react";

import type { Page, Task } from "@/api/types";
import { Providers } from "@/app/Providers";
import { BOB, db } from "@/test/db";
import { problem } from "@/test/handlers";
import { createTestQueryClient, signInAsAlice } from "@/test/render";
import { server } from "@/test/server";

import { taskQueryKeys } from "../queryKeys";
import { useUpdateTask } from "./useTaskMutations";

describe("Given I edit a task's fields and its assignee", () => {
  beforeEach(signInAsAlice);

  it("when the field update succeeds but the assignment fails, then cached lists are refreshed anyway", async () => {
    server.use(
      http.put("*/api/v1/tasks/:id/assignee", () =>
        problem(422, "Unprocessable Entity", { detail: "Assignee must be an active user" }),
      ),
    );
    const client = createTestQueryClient();
    const task = db.tasks[0]!;
    const listKey = taskQueryKeys.list({ page: 1, size: 10 });
    client.setQueryData<Page<Task>>(listKey, {
      items: [task],
      total: 1,
      page: 1,
      size: 10,
      pages: 1,
    });
    const wrapper = ({ children }: { children: ReactNode }) => (
      <Providers client={client}>{children}</Providers>
    );
    const { result } = renderHook(() => useUpdateTask(), { wrapper });

    result.current.mutate({ id: task.id, changes: { title: "Renamed" }, assigneeId: BOB.id });

    await waitFor(() => expect(result.current.isError).toBe(true));
    // The PATCH was saved on the server, so the stale cached title must not survive.
    await waitFor(() => expect(client.getQueryState(listKey)?.isInvalidated).toBe(true));
    expect(db.requests.map((r) => r.method)).toEqual(["PATCH"]);
  });
});
