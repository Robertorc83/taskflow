import { screen } from "@testing-library/react";

import type { Task } from "@/api/types";
import { ALICE, BOB, makeTask, toSummary } from "@/test/db";
import { renderWithProviders } from "@/test/render";

import { TaskCard } from "./TaskCard";

function renderCard(task: Task, currentUserId: string) {
  const handlers = { onComplete: vi.fn(), onReopen: vi.fn(), onDelete: vi.fn() };
  const view = renderWithProviders(
    <TaskCard
      task={task}
      currentUserId={currentUserId}
      editHref={`/tasks/${task.id}/edit`}
      {...handlers}
    />,
  );
  return { ...view, ...handlers };
}

describe("Given a task I own", () => {
  const task = makeTask({
    title: "Write report",
    due_date: "2099-11-01",
    assignee: toSummary(BOB),
  });

  it("then I see its status, due date and assignee", () => {
    renderCard(task, ALICE.id);

    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByText("Nov 1, 2099")).toBeInTheDocument();
    expect(screen.getByText("Bob Jones")).toBeInTheDocument();
  });

  it("then I can complete, edit and delete it (F12)", async () => {
    const { user, onComplete, onDelete } = renderCard(task, ALICE.id);

    await user.click(screen.getByRole("button", { name: "Complete Write report" }));
    await user.click(screen.getByRole("button", { name: "Delete Write report" }));

    expect(onComplete).toHaveBeenCalledWith(task);
    expect(onDelete).toHaveBeenCalledWith(task);
    expect(screen.getByRole("link", { name: "Edit Write report" })).toHaveAttribute(
      "href",
      `/tasks/${task.id}/edit`,
    );
  });
});

describe("Given a task assigned to me by someone else", () => {
  const task = makeTask({
    title: "Bob's errand",
    owner: toSummary(BOB),
    assignee: toSummary(ALICE),
  });

  it("then I can complete it but not edit or delete it (F12)", () => {
    renderCard(task, ALICE.id);

    expect(screen.getByRole("button", { name: "Complete Bob's errand" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Edit/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Delete/ })).not.toBeInTheDocument();
    expect(screen.getByText("You")).toBeInTheDocument();
    expect(screen.getByText("Bob Jones")).toBeInTheDocument();
  });
});

describe("Given a completed task", () => {
  it("when I click reopen, then the reopen handler is called (F8)", async () => {
    const task = makeTask({ title: "Deploy", status: "completed" });
    const { user, onReopen } = renderCard(task, ALICE.id);

    expect(screen.queryByRole("button", { name: /Complete/ })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Reopen Deploy" }));

    expect(onReopen).toHaveBeenCalledWith(task);
  });
});

describe("Given an overdue task", () => {
  it("then it is flagged as overdue (F5)", () => {
    renderCard(
      makeTask({ title: "Renew passport", due_date: "2020-01-01", is_overdue: true }),
      ALICE.id,
    );

    expect(screen.getByText("Overdue")).toBeInTheDocument();
  });
});

describe("Given a task without a due date or assignee", () => {
  it("then the card says so", () => {
    renderCard(makeTask({ title: "Someday" }), ALICE.id);

    expect(screen.getByText("No due date")).toBeInTheDocument();
    expect(screen.getByText("Unassigned")).toBeInTheDocument();
  });
});
