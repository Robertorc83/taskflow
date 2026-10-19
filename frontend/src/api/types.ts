// Hand-written mirror of the backend contract (specs/SPEC-001..004).
// Reconcile with `npm run gen:types` once the API is running.

export type TaskStatus = "pending" | "in_progress" | "completed";
export type TaskScope = "all" | "owned" | "assigned";
export type TaskOrdering = "-created_at" | "created_at" | "due_date" | "-due_date";

export interface UserSummary {
  id: string;
  email: string;
  full_name: string;
}

export interface User extends UserSummary {
  is_active: boolean;
  created_at: string;
}

export interface Task {
  id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  due_date: string | null;
  is_overdue: boolean;
  owner: UserSummary;
  assignee: UserSummary | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface FieldError {
  field: string;
  message: string;
}

/** RFC 9457 problem details. */
export interface ProblemDetails {
  type?: string;
  title: string;
  status: number;
  detail?: string;
  errors?: FieldError[];
}

export interface TaskListParams {
  status?: TaskStatus;
  scope?: TaskScope;
  due_from?: string;
  due_to?: string;
  ordering?: TaskOrdering;
  page: number;
  size: number;
}

export interface CreateTaskInput {
  title: string;
  description?: string | null;
  due_date?: string | null;
  assignee_id?: string | null;
}

export interface UpdateTaskInput {
  title?: string;
  description?: string | null;
  due_date?: string | null;
  status?: Exclude<TaskStatus, "completed">;
}

export interface RegisterInput {
  email: string;
  full_name: string;
  password: string;
}

export interface LoginInput {
  email: string;
  password: string;
}
