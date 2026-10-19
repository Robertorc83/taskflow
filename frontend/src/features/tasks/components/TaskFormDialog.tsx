import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import type { CreateTaskInput, Task, UpdateTaskInput } from "@/api/types";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { useToast } from "@/components/ui/toastContext";
import { useAuth } from "@/features/auth/authContext";
import { errorMessage } from "@/lib/errors";

import { useTask, useUsers } from "../hooks/useTasks";
import { useCreateTask, useUpdateTask } from "../hooks/useTaskMutations";
import type { TaskFormValues } from "../schemas";

import { TaskForm } from "./TaskForm";

const orNull = (value: string) => (value.trim() === "" ? null : value);

function toCreateInput(values: TaskFormValues): CreateTaskInput {
  return {
    title: values.title.trim(),
    description: orNull(values.description),
    due_date: orNull(values.due_date),
    assignee_id: orNull(values.assignee_id),
  };
}

/** Only send the fields that actually changed (PATCH semantics, SPEC-002 R6). */
function toUpdateInput(task: Task, values: TaskFormValues): UpdateTaskInput {
  const changes: UpdateTaskInput = {};
  const title = values.title.trim();
  if (title !== task.title) changes.title = title;
  if (orNull(values.description) !== task.description)
    changes.description = orNull(values.description);
  if (orNull(values.due_date) !== task.due_date) changes.due_date = orNull(values.due_date);
  if (values.status !== task.status && values.status !== "completed")
    changes.status = values.status;
  return changes;
}

/** Routed modal: /tasks/new and /tasks/:taskId/edit render on top of the list. */
export function TaskFormDialog() {
  const { taskId } = useParams();
  const [search] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { user } = useAuth();
  const users = useUsers();
  const existing = useTask(taskId);
  const createTask = useCreateTask();
  const updateTask = useUpdateTask();

  const isEdit = taskId !== undefined;
  const close = () => navigate({ pathname: "/tasks", search: search.toString() });

  const onSubmit = async (values: TaskFormValues) => {
    if (isEdit && existing.data) {
      await updateTask.mutateAsync({
        id: existing.data.id,
        changes: toUpdateInput(existing.data, values),
        assigneeId: orNull(values.assignee_id),
      });
      toast.success("Task updated");
    } else {
      await createTask.mutateAsync(toCreateInput(values));
      toast.success("Task created");
    }
    close();
  };

  const forbidden = Boolean(existing.data && user && existing.data.owner.id !== user.id);

  let body;
  if ((isEdit && existing.isPending) || users.isPending) {
    body = (
      <div className="flex justify-center py-10">
        <Spinner label={isEdit ? "Loading task" : "Loading form"} className="text-indigo-600" />
      </div>
    );
  } else if (isEdit && (existing.isError || forbidden)) {
    body = (
      <p role="alert" className="text-sm text-rose-700">
        {existing.isError ? errorMessage(existing.error) : "Only the owner can edit this task."}
      </p>
    );
  } else {
    body = (
      <TaskForm
        task={existing.data}
        users={users.data ?? []}
        onSubmit={onSubmit}
        onCancel={close}
      />
    );
  }

  return (
    <Modal title={isEdit ? "Edit task" : "New task"} onClose={close}>
      {body}
    </Modal>
  );
}
