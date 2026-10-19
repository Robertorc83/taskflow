import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";

import type { Task, User } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { InputField, SelectField, TextareaField } from "@/components/ui/Field";
import { errorMessage, fieldErrors } from "@/lib/errors";
import { todayIso } from "@/lib/dates";

import { taskFormSchema, type TaskFormValues } from "../schemas";

const FORM_FIELDS = ["title", "description", "due_date", "status", "assignee_id"] as const;
type FormField = (typeof FORM_FIELDS)[number];

export interface TaskFormProps {
  /** The task being edited; omit to create a new one. */
  task?: Task;
  users: User[];
  onSubmit: (values: TaskFormValues) => Promise<void>;
  onCancel: () => void;
}

function defaults(task?: Task): TaskFormValues {
  return {
    title: task?.title ?? "",
    description: task?.description ?? "",
    due_date: task?.due_date ?? "",
    status: task?.status ?? "pending",
    assignee_id: task?.assignee?.id ?? "",
  };
}

export function TaskForm({ task, users, onSubmit, onCancel }: TaskFormProps) {
  const isNew = task === undefined;
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<TaskFormValues>({
    resolver: zodResolver(taskFormSchema({ isNew, originalDueDate: task?.due_date })),
    defaultValues: defaults(task),
  });

  const submit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await onSubmit(values);
    } catch (error) {
      const mapped = fieldErrors(error).filter((e): e is { field: FormField; message: string } =>
        (FORM_FIELDS as readonly string[]).includes(e.field),
      );
      if (mapped.length > 0) {
        mapped.forEach(({ field, message }) => setError(field, { message }));
      } else {
        setFormError(errorMessage(error));
      }
    }
  });

  return (
    <form onSubmit={submit} noValidate className="space-y-4">
      {formError && (
        <div
          role="alert"
          className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700 ring-1 ring-rose-200"
        >
          {formError}
        </div>
      )}
      <InputField
        label="Title"
        placeholder="What needs to be done?"
        maxLength={200}
        data-autofocus
        error={errors.title?.message}
        {...register("title")}
      />
      <TextareaField
        label="Description"
        placeholder="Add more detail (optional)"
        maxLength={2000}
        error={errors.description?.message}
        {...register("description")}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <InputField
          label="Due date"
          type="date"
          min={isNew ? todayIso() : undefined}
          error={errors.due_date?.message}
          {...register("due_date")}
        />
        <SelectField
          label="Assignee"
          error={errors.assignee_id?.message}
          {...register("assignee_id")}
        >
          <option value="">Unassigned</option>
          {users.map((user) => (
            <option key={user.id} value={user.id}>
              {user.full_name} ({user.email})
            </option>
          ))}
        </SelectField>
      </div>
      {!isNew && (
        <SelectField label="Status" error={errors.status?.message} {...register("status")}>
          <option value="pending">Pending</option>
          <option value="in_progress">In progress</option>
          {task.status === "completed" && <option value="completed">Completed</option>}
        </SelectField>
      )}
      <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={isSubmitting}>
          {isNew ? "Create task" : "Save changes"}
        </Button>
      </div>
    </form>
  );
}
