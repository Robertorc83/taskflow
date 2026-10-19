import { tokenStorage } from "./tokenStorage";
import type { ProblemDetails, TokenPair } from "./types";

export const API_PREFIX = "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly problem: ProblemDetails;
  readonly retryAfter: number | null;

  constructor(problem: ProblemDetails, retryAfter: number | null = null) {
    super(problem.detail ?? problem.title);
    this.name = "ApiError";
    this.status = problem.status;
    this.problem = problem;
    this.retryAfter = retryAfter;
  }
}

type Query = Record<string, string | number | undefined | null>;

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  query?: Query;
  /** Send the bearer token and transparently refresh it on 401. Defaults to true. */
  auth?: boolean;
}

function buildUrl(path: string, query?: Query): string {
  const url = new URL(`${API_PREFIX}${path}`, window.location.origin);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

async function toApiError(response: Response): Promise<ApiError> {
  let problem: ProblemDetails = {
    title: response.statusText || "Request failed",
    status: response.status,
  };
  try {
    const body = (await response.json()) as Partial<ProblemDetails>;
    problem = { ...problem, ...body, status: response.status };
  } catch {
    // Non-JSON error body: keep the generic problem.
  }
  const retryAfterHeader = response.headers.get("Retry-After");
  const retryAfter = retryAfterHeader === null ? null : Number.parseInt(retryAfterHeader, 10);
  return new ApiError(problem, Number.isNaN(retryAfter) ? null : retryAfter);
}

/** The user's IANA time zone; the server uses it to decide what "today" is (past dates, overdue). */
export function currentTimeZone(): string | null {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null;
  } catch {
    return null;
  }
}

function send(path: string, options: RequestOptions, token: string | null): Promise<Response> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  const timeZone = currentTimeZone();
  if (timeZone) headers["X-Timezone"] = timeZone;
  if (token) headers.Authorization = `Bearer ${token}`;
  return fetch(buildUrl(path, options.query), {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
}

/**
 * - `refreshed`: new tokens stored.
 * - `rejected`: the server says the refresh token is invalid; the session is over.
 * - `unavailable`: rate limited, server or network error; the session may still be valid.
 */
export type RefreshOutcome = "refreshed" | "rejected" | "unavailable";

const SESSION_REJECTED_STATUSES = new Set([400, 401, 422]);

let refreshInFlight: Promise<RefreshOutcome> | null = null;

/** Exchanges the refresh token once; concurrent callers share the same attempt. */
export function refreshSession(): Promise<RefreshOutcome> {
  refreshInFlight ??= (async (): Promise<RefreshOutcome> => {
    const refreshToken = tokenStorage.getRefreshToken();
    if (!refreshToken) return "rejected";
    try {
      const response = await send(
        "/auth/refresh",
        { method: "POST", body: { refresh_token: refreshToken } },
        null,
      );
      if (SESSION_REJECTED_STATUSES.has(response.status)) return "rejected";
      if (!response.ok) return "unavailable";
      tokenStorage.save((await response.json()) as TokenPair);
      return "refreshed";
    } catch {
      return "unavailable";
    }
  })().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const useAuth = options.auth ?? true;
  let response = await send(path, options, useAuth ? tokenStorage.getAccessToken() : null);

  if (response.status === 401 && useAuth) {
    const outcome = await refreshSession();
    if (outcome === "refreshed") {
      response = await send(path, options, tokenStorage.getAccessToken());
    }
    // Only a definitive rejection ends the session; transient refresh failures keep the tokens.
    if (outcome === "rejected" || (outcome === "refreshed" && response.status === 401)) {
      tokenStorage.clear();
    }
  }

  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
