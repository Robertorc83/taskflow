import type { Task, User } from "@/api/types";

/** In-memory backend state used by the MSW handlers; reset after every test. */
export const ALICE: User = {
  id: "11111111-1111-4111-8111-111111111111",
  email: "alice@example.com",
  full_name: "Alice Smith",
  is_active: true,
  created_at: "2026-10-01T09:00:00Z",
};

export const BOB: User = {
  id: "22222222-2222-4222-8222-222222222222",
  email: "bob@example.com",
  full_name: "Bob Jones",
  is_active: true,
  created_at: "2026-10-01T09:00:00Z",
};

export const PASSWORDS: Record<string, string> = {
  [ALICE.email]: "Alice123!",
  [BOB.email]: "Bob12345!",
};

const summary = ({ id, email, full_name }: User) => ({ id, email, full_name });

let sequence = 0;

export function makeTask(overrides: Partial<Task> & { title: string }): Task {
  sequence += 1;
  const created = new Date(Date.UTC(2026, 9, 1, 9, sequence)).toISOString();
  return {
    id: `00000000-0000-4000-8000-${String(sequence).padStart(12, "0")}`,
    description: null,
    status: "pending",
    due_date: null,
    is_overdue: false,
    owner: summary(ALICE),
    assignee: null,
    created_at: created,
    updated_at: created,
    completed_at: null,
    ...overrides,
  };
}

function seedTasks(): Task[] {
  return [
    makeTask({ title: "Write report", due_date: "2099-11-01", description: "Q3 numbers" }),
    makeTask({
      title: "Review PR",
      status: "in_progress",
      due_date: "2099-10-25",
      assignee: summary(BOB),
    }),
    makeTask({
      title: "Renew passport",
      due_date: "2020-01-01",
      is_overdue: true,
    }),
    makeTask({
      title: "Deploy release",
      status: "completed",
      completed_at: "2026-10-02T10:00:00Z",
    }),
    makeTask({ title: "Bob's errand", owner: summary(BOB), assignee: summary(ALICE) }),
  ];
}

export const db = {
  users: [ALICE, BOB],
  tasks: seedTasks(),
  /** Every request the handlers saw, for asserting on what the UI sent. */
  requests: [] as { method: string; path: string; body: unknown }[],
  validAccessTokens: new Set<string>(["access-alice"]),
  tokenOwner: new Map<string, User>([["access-alice", ALICE]]),
  refreshTokens: new Map<string, User>([["refresh-alice", ALICE]]),
  refreshCalls: 0,
};

export function resetDb(): void {
  sequence = 0;
  db.users = [ALICE, BOB];
  db.tasks = seedTasks();
  db.requests = [];
  db.validAccessTokens = new Set(["access-alice"]);
  db.tokenOwner = new Map([["access-alice", ALICE]]);
  db.refreshTokens = new Map([["refresh-alice", ALICE]]);
  db.refreshCalls = 0;
}

export const toSummary = summary;
