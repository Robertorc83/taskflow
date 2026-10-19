import { useState } from "react";
import { Link, Outlet, useSearchParams } from "react-router-dom";

import type { Task } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pagination } from "@/components/ui/Pagination";
import { Spinner } from "@/components/ui/Spinner";
import { useToast } from "@/components/ui/toastContext";
import { useAuth } from "@/features/auth/authContext";
import { errorMessage } from "@/lib/errors";

import { DeleteTaskDialog } from "../components/DeleteTaskDialog";
import { TaskCard } from "../components/TaskCard";
import { TaskFilters } from "../components/TaskFilters";
import { TaskListSkeleton } from "../components/TaskListSkeleton";
import { hasActiveFilters } from "../filters";
import { useCompleteTask, useDeleteTask, useReopenTask } from "../hooks/useTaskMutations";
import { useTaskParams } from "../hooks/useTaskParams";
import { useTasks } from "../hooks/useTasks";

export function TaskListPage() {
  const { user } = useAuth();
  const toast = useToast();
  const [search] = useSearchParams();
  const { params, update, clearFilters } = useTaskParams();
  const tasks = useTasks(params);
  const completeTask = useCompleteTask();
  const reopenTask = useReopenTask();
  const deleteTask = useDeleteTask();
  const [pendingDelete, setPendingDelete] = useState<Task | null>(null);

  const withSearch = (pathname: string) => ({ pathname, search: search.toString() });

  const confirmDelete = () => {
    if (!pendingDelete) return;
    deleteTask.mutate(pendingDelete.id, {
      onSuccess: () => {
        toast.success("Task deleted");
        setPendingDelete(null);
      },
      onError: (error) => toast.error(`Could not delete the task: ${errorMessage(error)}`),
    });
  };

  let content;
  if (tasks.isPending) {
    content = <TaskListSkeleton />;
  } else if (tasks.isError) {
    content = (
      <div role="alert" className="rounded-xl bg-rose-50 p-6 text-center ring-1 ring-rose-200">
        <p className="text-sm font-medium text-rose-800">We couldn&apos;t load your tasks.</p>
        <p className="mt-1 text-sm text-rose-700">{errorMessage(tasks.error)}</p>
        <Button variant="secondary" size="sm" className="mt-4" onClick={() => void tasks.refetch()}>
          Try again
        </Button>
      </div>
    );
  } else if (tasks.data.items.length === 0) {
    content = hasActiveFilters(params) ? (
      <EmptyState
        title="No tasks match these filters"
        description="Try a different status or date range."
        action={
          <Button variant="secondary" onClick={clearFilters}>
            Clear filters
          </Button>
        }
      />
    ) : (
      <EmptyState
        title="No tasks yet"
        description="Create your first task to get started."
        action={
          <Link
            to={withSearch("/tasks/new")}
            className="inline-flex h-10 items-center rounded-lg bg-indigo-600 px-4 text-sm font-medium text-white shadow-sm hover:bg-indigo-500"
          >
            New task
          </Link>
        }
      />
    );
  } else {
    content = (
      <div className="space-y-4">
        <ul className="space-y-3" aria-label="Tasks">
          {tasks.data.items.map((task) => (
            <li key={task.id}>
              <TaskCard
                task={task}
                currentUserId={user?.id}
                editHref={`/tasks/${task.id}/edit?${search.toString()}`}
                onComplete={(t) => completeTask.mutate(t.id)}
                onReopen={(t) => reopenTask.mutate(t.id)}
                onDelete={setPendingDelete}
              />
            </li>
          ))}
        </ul>
        <Pagination
          page={tasks.data.page}
          pages={tasks.data.pages}
          total={tasks.data.total}
          onPageChange={(page) => update({ page })}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Tasks</h1>
          <p className="mt-1 text-sm text-slate-500">
            Everything you own or that&apos;s assigned to you.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          {tasks.isFetching && !tasks.isPending && (
            <Spinner className="h-4 w-4 text-slate-400" label="Refreshing" />
          )}
          <Link
            to={withSearch("/tasks/new")}
            className="inline-flex h-10 items-center gap-1.5 whitespace-nowrap rounded-lg bg-indigo-600 px-4 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
          >
            <span aria-hidden="true" className="text-base leading-none">
              +
            </span>{" "}
            New task
          </Link>
        </div>
      </div>

      <TaskFilters params={params} onChange={update} onClear={clearFilters} />

      {content}

      {pendingDelete && (
        <DeleteTaskDialog
          task={pendingDelete}
          deleting={deleteTask.isPending}
          onCancel={() => setPendingDelete(null)}
          onConfirm={confirmDelete}
        />
      )}

      <Outlet />
    </div>
  );
}
