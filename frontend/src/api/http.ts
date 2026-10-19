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

function send(path: string, options: RequestOptions, token: string | null): Promise<Response> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  return fetch(buildUrl(path, options.query), {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
}

let refreshInFlight: Promise<boolean> | null = null;

/** Exchanges the refresh token once; concurrent callers share the same attempt. */
export function refreshSession(): Promise<boolean> {
  refreshInFlight ??= (async () => {
    const refreshToken = tokenStorage.getRefreshToken();
    if (!refreshToken) return false;
    try {
      const response = await send(
        "/auth/refresh",
        { method: "POST", body: { refresh_token: refreshToken } },
        null,
      );
      if (!response.ok) return false;
      tokenStorage.save((await response.json()) as TokenPair);
      return true;
    } catch {
      return false;
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
    if (await refreshSession()) {
      response = await send(path, options, tokenStorage.getAccessToken());
    }
    if (response.status === 401) {
      tokenStorage.clear();
    }
  }

  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
