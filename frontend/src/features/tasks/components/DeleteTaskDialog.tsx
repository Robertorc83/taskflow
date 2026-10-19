import type { Task } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";

export function DeleteTaskDialog({
  task,
  deleting,
  onCancel,
  onConfirm,
}: {
  task: Task;
  deleting: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <Modal
      title="Delete task?"
      description={`"${task.title}" will be permanently deleted. This cannot be undone.`}
      onClose={onCancel}
      size="sm"
    >
      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onCancel} data-autofocus>
          Cancel
        </Button>
        <Button variant="danger" onClick={onConfirm} loading={deleting}>
          Delete task
        </Button>
      </div>
    </Modal>
  );
}
