"""Job names: the contract between the API (which enqueues) and the worker (which runs)."""

TASK_ASSIGNED = "notifications.task_assigned"
TASK_COMPLETED = "notifications.task_completed"

# Message header that carries the enqueuing request's ID to the worker (CR-013).
REQUEST_ID_HEADER = "request_id"
