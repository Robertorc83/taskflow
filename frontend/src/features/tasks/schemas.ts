import { z } from "zod";

import { todayIso } from "@/lib/dates";

// Mirrors SPEC-002 R2/R3: required trimmed title ≤ 200, description ≤ 2000, due date not in the past.
export function taskFormSchema({
  isNew,
  originalDueDate,
}: {
  isNew: boolean;
  originalDueDate?: string | null;
}) {
  return z.object({
    title: z.string().trim().min(1, "Title is required").max(200, "At most 200 characters"),
    description: z.string().max(2000, "At most 2000 characters"),
    due_date: z
      .string()
      .refine(
        (value) => !value || (!isNew && value === originalDueDate) || value >= todayIso(),
        "Due date cannot be in the past",
      ),
    status: z.enum(["pending", "in_progress", "completed"]),
    assignee_id: z.string(),
  });
}

export type TaskFormValues = z.infer<ReturnType<typeof taskFormSchema>>;
