import { z } from "zod";

import { todayIso } from "@/lib/dates";
import { LIMITS } from "@/lib/limits";

// Mirrors SPEC-002 R2/R3: required trimmed title, bounded description, due date not in the past.
export function taskFormSchema({
  isNew,
  originalDueDate,
}: {
  isNew: boolean;
  originalDueDate?: string | null;
}) {
  return z.object({
    title: z
      .string()
      .trim()
      .min(1, "Title is required")
      .max(LIMITS.taskTitleMax, `At most ${LIMITS.taskTitleMax} characters`),
    description: z
      .string()
      .max(LIMITS.taskDescriptionMax, `At most ${LIMITS.taskDescriptionMax} characters`),
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
