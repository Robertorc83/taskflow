import { screen, waitFor, within } from "@testing-library/react";
import { http } from "msw";

import { ALICE, BOB, db, makeTask } from "@/test/db";
import { problem } from "@/test/handlers";
import { renderApp } from "@/test/render";
import { server } from "@/test/server";

const taskList = () => screen.findByRole("list", { name: "Tasks" });
const titles = (list: HTMLElement) =>
  within(list)
    .getAllByRole("article")
    .map((article) => article.getAttribute("aria-label"));

describe("Given I am on the task list", () => {
  it("then I see the tasks I own or am assigned to, newest first (F5)", async () => {
    renderApp("/tasks");

    const list = await taskList();

    expect(titles(list)).toEqual([
      "Bob's errand",
      "Deploy release",
      "Renew passport",
      "Review PR",
      "Write report",
    ]);
    expect(within(list).getByText("Overdue")).toBeInTheDocument();
  });

  it("when I filter by Completed, then only completed tasks are shown and the URL is updated (F6)", async () => {
    const { user, router } = renderApp("/tasks");
    await taskList();

    await user.selectOptions(screen.getByLabelText("Status"), "completed");

    await waitFor(async () => expect(titles(await taskList())).toEqual(["Deploy release"]));
    expect(router.state.location.search).toBe("?status=completed");
  });

  it("when I open a filtered URL, then the filters are restored from it (F6)", async () => {
    renderApp("/tasks?status=in_progress&ordering=due_date");

    expect(titles(await taskList())).toEqual(["Review PR"]);
    expect(screen.getByLabelText("Status")).toHaveValue("in_progress");
    expect(screen.getByLabelText("Sort by")).toHaveValue("due_date");
  });

  it("when I choose 'Assigned to me', then only those tasks are listed (F6)", async () => {
    const { user } = renderApp("/tasks");
    await taskList();

    await user.click(screen.getByRole("button", { name: "Assigned to me" }));

    await waitFor(async () => expect(titles(await taskList())).toEqual(["Bob's errand"]));
    expect(screen.getByRole("button", { name: "Assigned to me" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("when I set a due date range, then it is sent to the API (F6)", async () => {
    const { user } = renderApp("/tasks");
    await taskList();

    await user.type(screen.getByLabelText("Due from"), "2099-10-01");
    await user.type(screen.getByLabelText("Due to"), "2099-10-31");

    await waitFor(async () => expect(titles(await taskList())).toEqual(["Review PR"]));
    expect(db.requests.at(-1)?.path).toContain("due_from=2099-10-01&due_to=2099-10-31");
  });

  it("when no task matches, then I see an empty state and can clear the filters (F7)", async () => {
    const { user } = renderApp("/tasks?due_from=2199-01-01");

    expect(await screen.findByText("No tasks match these filters")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear filters" }));

    expect(await taskList()).toBeInTheDocument();
  });

  it("when there are more tasks than fit on a page, then I can page through them (F5)", async () => {
    const { user, router } = renderApp("/tasks?size=2");
    await taskList();

    expect(screen.getByText(/Page/)).toHaveTextContent("Page 1 of 3 · 5 tasks");
    await user.click(screen.getByRole("button", { name: "Next" }));

    await waitFor(() => expect(screen.getByText(/Page/)).toHaveTextContent("Page 2 of 3"));
    expect(router.state.location.search).toBe("?page=2&size=2");
  });

  it("when the API fails, then I see an error and can retry (F7)", async () => {
    server.use(
      http.get("*/api/v1/tasks", () => problem(500, "Internal Server Error"), { once: true }),
    );
    const { user } = renderApp("/tasks");

    expect(await screen.findByRole("alert")).toHaveTextContent("We couldn't load your tasks.");
    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect(await taskList()).toBeInTheDocument();
  });

  it("when I complete a task, then it shows as completed immediately (F8)", async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => (release = resolve));
    server.use(
      http.post("*/api/v1/tasks/:id/complete", async () => {
        await gate;
        // Returning nothing falls through to the default handler, which completes the task.
        return undefined;
      }),
    );
    const { user } = renderApp("/tasks");
    const list = await taskList();

    await user.click(within(list).getByRole("button", { name: "Complete Write report" }));

    // Optimistic: the badge flips before the server has answered.
    const card = within(list).getByRole("article", { name: "Write report" });
    expect(within(card).getByText("Completed")).toBeInTheDocument();
    release();
    expect(await screen.findByText("Task completed")).toBeInTheDocument();
  });

  it("when completing fails, then the change is rolled back and I see why (F8)", async () => {
    server.use(
      http.post("*/api/v1/tasks/:id/complete", () =>
        problem(409, "Conflict", { detail: "Already done" }),
      ),
    );
    const { user } = renderApp("/tasks");
    const list = await taskList();

    await user.click(within(list).getByRole("button", { name: "Complete Write report" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not complete the task: Already done",
    );
    const card = within(await taskList()).getByRole("article", { name: "Write report" });
    expect(within(card).getByText("Pending")).toBeInTheDocument();
  });

  it("when I reopen a completed task, then it goes back to pending (F8)", async () => {
    const { user } = renderApp("/tasks");
    const list = await taskList();

    await user.click(within(list).getByRole("button", { name: "Reopen Deploy release" }));

    expect(await screen.findByText("Task reopened")).toBeInTheDocument();
    expect(db.requests.some((r) => r.method === "POST" && r.path.endsWith("/reopen"))).toBe(true);
    expect(db.requests.some((r) => r.method === "PATCH")).toBe(false);
  });

  it("when I reopen a completed task that was assigned to me, then it goes back to pending (F8, F12)", async () => {
    db.tasks.push(
      makeTask({
        title: "Bob's finished errand",
        status: "completed",
        completed_at: "2026-10-03T10:00:00Z",
        owner: { id: BOB.id, email: BOB.email, full_name: BOB.full_name },
        assignee: { id: ALICE.id, email: ALICE.email, full_name: ALICE.full_name },
      }),
    );
    const { user } = renderApp("/tasks");
    const list = await taskList();

    await user.click(within(list).getByRole("button", { name: "Reopen Bob's finished errand" }));

    expect(await screen.findByText("Task reopened")).toBeInTheDocument();
    const card = within(await taskList()).getByRole("article", { name: "Bob's finished errand" });
    await waitFor(() => expect(within(card).getByText("Pending")).toBeInTheDocument());
  });

  it("when reopening fails, then the change is rolled back and I see why (F8)", async () => {
    server.use(
      http.post("*/api/v1/tasks/:id/reopen", () =>
        problem(409, "Conflict", { detail: "Task is not completed" }),
      ),
    );
    const { user } = renderApp("/tasks");
    const list = await taskList();

    await user.click(within(list).getByRole("button", { name: "Reopen Deploy release" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not reopen the task: Task is not completed",
    );
    const card = within(await taskList()).getByRole("article", { name: "Deploy release" });
    expect(within(card).getByText("Completed")).toBeInTheDocument();
  });

  it("when the page in the URL is past the end, then I am taken to the last page instead of an empty list (F7)", async () => {
    const { router } = renderApp("/tasks?page=4");

    const list = await taskList();

    expect(titles(list)).toContain("Write report");
    expect(screen.queryByText("No tasks yet")).not.toBeInTheDocument();
    await waitFor(() => expect(router.state.location.search).not.toContain("page=4"));
  });

  it("when I delete the only task on the last page, then I land on the previous page (F7, F9)", async () => {
    for (let i = 0; i < 6; i += 1) db.tasks.push(makeTask({ title: `Extra ${i}` }));
    const { user } = renderApp("/tasks?page=2");
    const list = await taskList();
    const [lastTitle] = titles(list);
    expect(titles(list)).toHaveLength(1);

    await user.click(within(list).getByRole("button", { name: `Delete ${lastTitle ?? ""}` }));
    await user.click(
      within(screen.getByRole("dialog", { name: "Delete task?" })).getByRole("button", {
        name: "Delete task",
      }),
    );

    await waitFor(async () => expect(titles(await taskList())).toHaveLength(10));
    expect(screen.queryByText("No tasks yet")).not.toBeInTheDocument();
  });

  it("when I delete a task and confirm, then it disappears (F9)", async () => {
    const { user } = renderApp("/tasks");
    const list = await taskList();

    await user.click(within(list).getByRole("button", { name: "Delete Write report" }));
    const dialog = screen.getByRole("dialog", { name: "Delete task?" });
    await user.click(within(dialog).getByRole("button", { name: "Delete task" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(await screen.findByText("Task deleted")).toBeInTheDocument();
    await waitFor(async () => expect(titles(await taskList())).not.toContain("Write report"));
  });

  it("when I cancel the delete confirmation, then nothing is deleted (F9)", async () => {
    const { user } = renderApp("/tasks");
    const list = await taskList();

    await user.click(within(list).getByRole("button", { name: "Delete Write report" }));
    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(db.requests.some((r) => r.method === "DELETE")).toBe(false);
  });

  it("when I have no tasks at all, then I am invited to create one (F7)", async () => {
    db.tasks = [];
    renderApp("/tasks");

    expect(await screen.findByText("No tasks yet")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /New task/ })).toHaveLength(2);
  });
});

describe("Given I am on a small screen", () => {
  it("when I open the filters drawer, then I can filter and close it (F14)", async () => {
    const { user } = renderApp("/tasks");
    await taskList();

    await user.click(screen.getByRole("button", { name: "Filters" }));
    const drawer = screen.getByRole("dialog", { name: "Filters" });
    await user.selectOptions(within(drawer).getByLabelText("Status"), "pending");
    await user.click(within(drawer).getByRole("button", { name: "Show results" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await waitFor(async () =>
      expect(titles(await taskList())).toEqual(["Bob's errand", "Renew passport", "Write report"]),
    );
  });
});
