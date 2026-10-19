import { http, HttpResponse, type DefaultBodyType, type StrictRequest } from "msw";

import type { CreateTaskInput, Task, UpdateTaskInput, User } from "@/api/types";

import { db, makeTask, PASSWORDS, toSummary } from "./db";

const API = "*/api/v1";

export function problem(status: number, title: string, extra: Record<string, unknown> = {}) {
  return HttpResponse.json({ type: "about:blank", title, status, ...extra }, { status });
}

async function record(request: StrictRequest<DefaultBodyType>) {
  const url = new URL(request.url);
  let body: unknown = null;
  if (request.method !== "GET" && request.method !== "DELETE") {
    body = await request
      .clone()
      .json()
      .catch(() => null);
  }
  db.requests.push({ method: request.method, path: url.pathname + url.search, body });
}

function currentUser(request: Request): User | null {
  const token = request.headers.get("Authorization")?.replace(/^Bearer /, "");
  if (!token || !db.validAccessTokens.has(token)) return null;
  return db.tokenOwner.get(token) ?? null;
}

const unauthorized = () => problem(401, "Not authenticated");

function visibleTo(user: User, task: Task): boolean {
  return task.owner.id === user.id || task.assignee?.id === user.id;
}

function issueTokens(user: User) {
  const n = db.validAccessTokens.size + 1;
  const access = `access-${n}`;
  const refresh = `refresh-${n}`;
  db.validAccessTokens.add(access);
  db.tokenOwner.set(access, user);
  db.refreshTokens.set(refresh, user);
  return { access_token: access, refresh_token: refresh, token_type: "bearer", expires_in: 900 };
}

export const handlers = [
  http.post(`${API}/auth/login`, async ({ request }) => {
    await record(request);
    const { email, password } = (await request.json()) as { email: string; password: string };
    const user = db.users.find((u) => u.email === email.toLowerCase());
    if (!user || PASSWORDS[user.email] !== password) return problem(401, "Invalid credentials");
    return HttpResponse.json(issueTokens(user));
  }),

  http.post(`${API}/auth/register`, async ({ request }) => {
    await record(request);
    const body = (await request.json()) as { email: string; full_name: string; password: string };
    const email = body.email.toLowerCase();
    if (db.users.some((u) => u.email === email)) return problem(409, "Email already registered");
    const user: User = {
      id: `99999999-9999-4999-8999-${String(db.users.length).padStart(12, "0")}`,
      email,
      full_name: body.full_name,
      is_active: true,
      created_at: new Date().toISOString(),
    };
    db.users.push(user);
    PASSWORDS[email] = body.password;
    return HttpResponse.json(user, { status: 201 });
  }),

  http.post(`${API}/auth/refresh`, async ({ request }) => {
    db.refreshCalls += 1;
    const { refresh_token } = (await request.json()) as { refresh_token: string };
    const user = db.refreshTokens.get(refresh_token);
    if (!user) return problem(401, "Invalid token");
    db.refreshTokens.delete(refresh_token);
    return HttpResponse.json(issueTokens(user));
  }),

  http.get(`${API}/users/me`, ({ request }) => {
    const user = currentUser(request);
    return user ? HttpResponse.json(user) : unauthorized();
  }),

  http.get(`${API}/users`, ({ request }) => {
    if (!currentUser(request)) return unauthorized();
    return HttpResponse.json({
      items: db.users,
      total: db.users.length,
      page: 1,
      size: 100,
      pages: 1,
    });
  }),

  http.get(`${API}/tasks`, async ({ request }) => {
    await record(request);
    const user = currentUser(request);
    if (!user) return unauthorized();
    const query = new URL(request.url).searchParams;
    const page = Number(query.get("page") ?? "1");
    const size = Number(query.get("size") ?? "20");
    const status = query.get("status");
    const scope = query.get("scope") ?? "all";
    const dueFrom = query.get("due_from");
    const dueTo = query.get("due_to");

    const items = db.tasks
      .filter((task) => visibleTo(user, task))
      .filter((task) => scope !== "owned" || task.owner.id === user.id)
      .filter((task) => scope !== "assigned" || task.assignee?.id === user.id)
      .filter((task) => !status || task.status === status)
      .filter((task) => !dueFrom || (task.due_date !== null && task.due_date >= dueFrom))
      .filter((task) => !dueTo || (task.due_date !== null && task.due_date <= dueTo))
      .sort((a, b) => b.created_at.localeCompare(a.created_at));

    return HttpResponse.json({
      items: items.slice((page - 1) * size, page * size),
      total: items.length,
      page,
      size,
      pages: Math.ceil(items.length / size),
    });
  }),

  http.get(`${API}/tasks/:id`, ({ request, params }) => {
    const user = currentUser(request);
    if (!user) return unauthorized();
    const task = db.tasks.find((t) => t.id === params.id);
    if (!task || !visibleTo(user, task)) return problem(404, "Task not found");
    return HttpResponse.json(task);
  }),

  http.post(`${API}/tasks`, async ({ request }) => {
    await record(request);
    const user = currentUser(request);
    if (!user) return unauthorized();
    const input = (await request.json()) as CreateTaskInput;
    const assignee = db.users.find((u) => u.id === input.assignee_id);
    const task = makeTask({
      title: input.title,
      description: input.description ?? null,
      due_date: input.due_date ?? null,
      owner: toSummary(user),
      assignee: assignee ? toSummary(assignee) : null,
      created_at: new Date(Date.UTC(2026, 9, 19)).toISOString(),
    });
    db.tasks.push(task);
    return HttpResponse.json(task, { status: 201 });
  }),

  http.patch(`${API}/tasks/:id`, async ({ request, params }) => {
    await record(request);
    const user = currentUser(request);
    if (!user) return unauthorized();
    const task = db.tasks.find((t) => t.id === params.id);
    if (!task || !visibleTo(user, task)) return problem(404, "Task not found");
    if (task.owner.id !== user.id) return problem(403, "Only the owner can edit this task");
    const changes = (await request.json()) as UpdateTaskInput;
    Object.assign(task, changes);
    if (changes.status) task.completed_at = null;
    return HttpResponse.json(task);
  }),

  http.put(`${API}/tasks/:id/assignee`, async ({ request, params }) => {
    await record(request);
    const user = currentUser(request);
    if (!user) return unauthorized();
    const task = db.tasks.find((t) => t.id === params.id);
    if (!task || !visibleTo(user, task)) return problem(404, "Task not found");
    const { assignee_id } = (await request.json()) as { assignee_id: string | null };
    const assignee = db.users.find((u) => u.id === assignee_id);
    task.assignee = assignee ? toSummary(assignee) : null;
    return HttpResponse.json(task);
  }),

  http.post(`${API}/tasks/:id/complete`, async ({ request, params }) => {
    await record(request);
    const user = currentUser(request);
    if (!user) return unauthorized();
    const task = db.tasks.find((t) => t.id === params.id);
    if (!task || !visibleTo(user, task)) return problem(404, "Task not found");
    if (task.status === "completed") return problem(409, "Task is already completed");
    Object.assign(task, {
      status: "completed",
      completed_at: "2026-10-19T10:00:00Z",
      is_overdue: false,
    });
    return HttpResponse.json(task);
  }),

  http.delete(`${API}/tasks/:id`, async ({ request, params }) => {
    await record(request);
    const user = currentUser(request);
    if (!user) return unauthorized();
    const index = db.tasks.findIndex((t) => t.id === params.id);
    const task = db.tasks[index];
    if (!task || !visibleTo(user, task)) return problem(404, "Task not found");
    db.tasks.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),
];
