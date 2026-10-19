import { screen, waitFor, within } from "@testing-library/react";
import { http } from "msw";

import { BOB, db } from "@/test/db";
import { problem } from "@/test/handlers";
import { renderApp } from "@/test/render";
import { server } from "@/test/server";

const WRITE_REPORT_ID = "00000000-0000-4000-8000-000000000001";
const BOBS_ERRAND_ID = "00000000-0000-4000-8000-000000000005";

async function openNewTaskForm(path = "/tasks/new") {
  const view = renderApp(path);
  const dialog = await screen.findByRole("dialog", { name: "New task" });
  await within(dialog).findByLabelText("Title");
  return { ...view, dialog };
}

describe("Given I am creating a task", () => {
  it("when I submit without a title, then I am told it is required (F10)", async () => {
    const { user, dialog } = await openNewTaskForm();

    await user.click(within(dialog).getByRole("button", { name: "Create task" }));

    expect(await within(dialog).findByText("Title is required")).toBeInTheDocument();
    expect(db.requests.some((r) => r.method === "POST")).toBe(false);
  });

  it("when I pick a due date in the past, then it is rejected (F10)", async () => {
    const { user, dialog } = await openNewTaskForm();

    await user.type(within(dialog).getByLabelText("Title"), "Time travel");
    await user.type(within(dialog).getByLabelText("Due date"), "2020-01-01");
    await user.click(within(dialog).getByRole("button", { name: "Create task" }));

    expect(await within(dialog).findByText("Due date cannot be in the past")).toBeInTheDocument();
  });

  it("when I fill in the form, then the task is created and appears in my list (F10)", async () => {
    const { user, dialog, router } = await openNewTaskForm("/tasks/new?status=pending");

    await user.type(within(dialog).getByLabelText("Title"), "  Book flights  ");
    await user.type(within(dialog).getByLabelText("Description"), "Lisbon offsite");
    await user.type(within(dialog).getByLabelText("Due date"), "2099-12-01");
    await user.selectOptions(within(dialog).getByLabelText("Assignee"), BOB.id);
    await user.click(within(dialog).getByRole("button", { name: "Create task" }));

    expect(await screen.findByText("Task created")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(router.state.location.search).toBe("?status=pending");
    expect(db.requests.find((r) => r.method === "POST")?.body).toEqual({
      title: "Book flights",
      description: "Lisbon offsite",
      due_date: "2099-12-01",
      assignee_id: BOB.id,
    });
    expect(await screen.findByRole("article", { name: "Book flights" })).toBeInTheDocument();
  });

  it("when the server rejects a field, then the error is shown on that field (F11)", async () => {
    server.use(
      http.post("*/api/v1/tasks", () =>
        problem(422, "Validation failed", {
          errors: [{ field: "title", message: "Title is reserved" }],
        }),
      ),
    );
    const { user, dialog } = await openNewTaskForm();

    await user.type(within(dialog).getByLabelText("Title"), "admin");
    await user.click(within(dialog).getByRole("button", { name: "Create task" }));

    expect(await within(dialog).findByText("Title is reserved")).toBeInTheDocument();
    expect(within(dialog).getByLabelText("Title")).toHaveAttribute("aria-invalid", "true");
  });

  it("when the server fails without field details, then I see a form-level error", async () => {
    server.use(http.post("*/api/v1/tasks", () => problem(500, "Internal Server Error")));
    const { user, dialog } = await openNewTaskForm();

    await user.type(within(dialog).getByLabelText("Title"), "Anything");
    await user.click(within(dialog).getByRole("button", { name: "Create task" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Internal Server Error");
  });

  it("when I cancel, then the dialog closes without saving", async () => {
    const { user, dialog } = await openNewTaskForm();

    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("Given I am editing a task I own", () => {
  async function openEditForm(id = WRITE_REPORT_ID) {
    const view = renderApp(`/tasks/${id}/edit`);
    const dialog = await screen.findByRole("dialog", { name: "Edit task" });
    await within(dialog).findByLabelText("Title");
    return { ...view, dialog };
  }

  it("then the form is pre-filled with the task (F10)", async () => {
    const { dialog } = await openEditForm();

    expect(within(dialog).getByLabelText("Title")).toHaveValue("Write report");
    expect(within(dialog).getByLabelText("Description")).toHaveValue("Q3 numbers");
    expect(within(dialog).getByLabelText("Due date")).toHaveValue("2099-11-01");
    expect(within(dialog).getByLabelText("Status")).toHaveValue("pending");
  });

  it("when I change only the title and status, then only those fields are sent (PATCH)", async () => {
    const { user, dialog } = await openEditForm();

    const title = within(dialog).getByLabelText("Title");
    await user.clear(title);
    await user.type(title, "Write final report");
    await user.selectOptions(within(dialog).getByLabelText("Status"), "in_progress");
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));

    expect(await screen.findByText("Task updated")).toBeInTheDocument();
    expect(db.requests.find((r) => r.method === "PATCH")?.body).toEqual({
      title: "Write final report",
      status: "in_progress",
    });
    expect(db.requests.some((r) => r.method === "PUT")).toBe(false);
  });

  it("when I clear the due date and reassign, then null is sent and the assignee command is used", async () => {
    const { user, dialog } = await openEditForm();

    await user.clear(within(dialog).getByLabelText("Due date"));
    await user.selectOptions(within(dialog).getByLabelText("Assignee"), BOB.id);
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));

    await screen.findByText("Task updated");
    expect(db.requests.find((r) => r.method === "PATCH")?.body).toEqual({ due_date: null });
    expect(db.requests.find((r) => r.method === "PUT")).toMatchObject({
      path: `/api/v1/tasks/${WRITE_REPORT_ID}/assignee`,
      body: { assignee_id: BOB.id },
    });
  });

  it("when I only change the assignee, then no PATCH is sent", async () => {
    const { user, dialog } = await openEditForm();

    await user.selectOptions(within(dialog).getByLabelText("Assignee"), BOB.id);
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));

    await screen.findByText("Task updated");
    expect(db.requests.some((r) => r.method === "PATCH")).toBe(false);
    expect(db.requests.some((r) => r.method === "PUT")).toBe(true);
  });
});

describe("Given a task I do not own", () => {
  it("when I open its edit URL, then I am told only the owner can edit it (F12)", async () => {
    renderApp(`/tasks/${BOBS_ERRAND_ID}/edit`);

    const dialog = await screen.findByRole("dialog", { name: "Edit task" });
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "Only the owner can edit this task.",
    );
  });

  it("when the task does not exist, then I see the API error", async () => {
    renderApp("/tasks/does-not-exist/edit");

    const dialog = await screen.findByRole("dialog", { name: "Edit task" });
    await waitFor(() =>
      expect(within(dialog).getByRole("alert")).toHaveTextContent("Task not found"),
    );
  });
});
