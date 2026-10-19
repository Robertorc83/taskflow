import type { TaskStatus } from "@/api/types";
import { Badge } from "@/components/ui/Badge";

const STATUS: Record<TaskStatus, { label: string; tone: "slate" | "indigo" | "emerald" }> = {
  pending: { label: "Pending", tone: "slate" },
  in_progress: { label: "In progress", tone: "indigo" },
  completed: { label: "Completed", tone: "emerald" },
};

export function StatusBadge({ status }: { status: TaskStatus }) {
  const { label, tone } = STATUS[status];
  return <Badge tone={tone}>{label}</Badge>;
}
