import { Link } from "react-router-dom";

import type { Task } from "@/api/types";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import { formatDate } from "@/lib/dates";

import { StatusBadge } from "./StatusBadge";

export interface TaskCardProps {
  task: Task;
  currentUserId: string | undefined;
  editHref: string;
  onComplete: (task: Task) => void;
  onReopen: (task: Task) => void;
  onDelete: (task: Task) => void;
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

export function TaskCard({
  task,
  currentUserId,
  editHref,
  onComplete,
  onReopen,
  onDelete,
}: TaskCardProps) {
  const isOwner = currentUserId === task.owner.id;
  const isAssignee = currentUserId !== undefined && currentUserId === task.assignee?.id;
  const canChangeStatus = isOwner || isAssignee;
  const isCompleted = task.status === "completed";

  return (
    <article
      aria-label={task.title}
      className="group flex flex-col gap-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200 transition hover:shadow-md sm:flex-row sm:items-start sm:gap-4"
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3
            className={cn(
              "truncate text-sm font-semibold text-slate-900",
              isCompleted && "text-slate-500 line-through decoration-slate-300",
            )}
          >
            {task.title}
          </h3>
          <StatusBadge status={task.status} />
          {task.is_overdue && <Badge tone="rose">Overdue</Badge>}
        </div>
        {task.description && (
          <p className="mt-1 line-clamp-2 text-sm text-slate-500">{task.description}</p>
        )}
        <dl className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-slate-500">
          <div className="flex items-center gap-1.5">
            <dt className="sr-only">Due date</dt>
            <svg
              className="h-4 w-4 text-slate-400"
              viewBox="0 0 20 20"
              fill="currentColor"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M5.75 2a.75.75 0 0 1 .75.75V4h7V2.75a.75.75 0 0 1 1.5 0V4h.25A2.75 2.75 0 0 1 18 6.75v8.5A2.75 2.75 0 0 1 15.25 18H4.75A2.75 2.75 0 0 1 2 15.25v-8.5A2.75 2.75 0 0 1 4.75 4H5V2.75A.75.75 0 0 1 5.75 2Zm-1 5.5c-.69 0-1.25.56-1.25 1.25v6.5c0 .69.56 1.25 1.25 1.25h10.5c.69 0 1.25-.56 1.25-1.25v-6.5c0-.69-.56-1.25-1.25-1.25H4.75Z"
                clipRule="evenodd"
              />
            </svg>
            <dd className={cn(task.is_overdue && "font-medium text-rose-600")}>
              {task.due_date ? formatDate(task.due_date) : "No due date"}
            </dd>
          </div>
          <div className="flex items-center gap-1.5">
            <dt className="sr-only">Assignee</dt>
            <dd className="flex items-center gap-1.5">
              {task.assignee ? (
                <>
                  <span
                    aria-hidden="true"
                    className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100 text-[10px] font-semibold text-indigo-700"
                  >
                    {initials(task.assignee.full_name)}
                  </span>
                  {isAssignee ? "You" : task.assignee.full_name}
                </>
              ) : (
                "Unassigned"
              )}
            </dd>
          </div>
          {!isOwner && (
            <div className="flex items-center gap-1.5">
              <dt>Owner</dt>
              <dd className="text-slate-700">{task.owner.full_name}</dd>
            </div>
          )}
        </dl>
      </div>

      <div className="flex shrink-0 flex-wrap items-center gap-1.5 sm:justify-end">
        {canChangeStatus &&
          (isCompleted ? (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onReopen(task)}
              aria-label={`Reopen ${task.title}`}
            >
              Reopen
            </Button>
          ) : (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onComplete(task)}
              aria-label={`Complete ${task.title}`}
            >
              <svg
                className="h-4 w-4 text-emerald-600"
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
                  clipRule="evenodd"
                />
              </svg>
              Complete
            </Button>
          ))}
        {isOwner && (
          <>
            <Link
              to={editHref}
              aria-label={`Edit ${task.title}`}
              className="inline-flex h-8 items-center rounded-lg px-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
            >
              Edit
            </Link>
            <Button
              variant="ghost"
              size="sm"
              className="text-rose-600 hover:bg-rose-50 hover:text-rose-700"
              onClick={() => onDelete(task)}
              aria-label={`Delete ${task.title}`}
            >
              Delete
            </Button>
          </>
        )}
      </div>
    </article>
  );
}
