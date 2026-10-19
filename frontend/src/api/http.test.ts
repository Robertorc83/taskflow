import { http, HttpResponse } from "msw";

import { db } from "@/test/db";
import { problem } from "@/test/handlers";
import { signInAsAlice } from "@/test/render";
import { server } from "@/test/server";

import { ApiError, request } from "./http";
import { tokenStorage } from "./tokenStorage";

describe("Given an authenticated session", () => {
  beforeEach(signInAsAlice);

  it("when I call the API, then the bearer token is attached", async () => {
    const me = await request<{ email: string }>("/users/me");
    expect(me.email).toBe("alice@example.com");
  });

  it("when the access token has expired, then it is refreshed once and the request retried", async () => {
    db.validAccessTokens.delete("access-alice");

    const me = await request<{ email: string }>("/users/me");

    expect(me.email).toBe("alice@example.com");
    expect(db.refreshCalls).toBe(1);
    expect(tokenStorage.getAccessToken()).not.toBe("access-alice");
  });

  it("when several requests hit a 401 at once, then they share a single refresh", async () => {
    db.validAccessTokens.delete("access-alice");

    await Promise.all([request("/users/me"), request("/users/me"), request("/users")]);

    expect(db.refreshCalls).toBe(1);
  });

  it("when the refresh endpoint is rate limited, then the session is kept and the original error surfaces", async () => {
    db.validAccessTokens.delete("access-alice");
    server.use(http.post("*/api/v1/auth/refresh", () => problem(429, "Too Many Requests")));

    await expect(request("/users/me")).rejects.toMatchObject({ status: 401 });
    expect(tokenStorage.hasSession()).toBe(true);
  });

  it("when the refresh request fails on the network, then the session is kept", async () => {
    db.validAccessTokens.delete("access-alice");
    server.use(http.post("*/api/v1/auth/refresh", () => HttpResponse.error()));

    await expect(request("/users/me")).rejects.toMatchObject({ status: 401 });
    expect(tokenStorage.hasSession()).toBe(true);
  });

  it("when the refresh endpoint fails with a server error, then the session is kept", async () => {
    db.validAccessTokens.delete("access-alice");
    server.use(http.post("*/api/v1/auth/refresh", () => problem(503, "Service Unavailable")));

    await expect(request("/users/me")).rejects.toMatchObject({ status: 401 });
    expect(tokenStorage.hasSession()).toBe(true);
  });

  it("when the refresh token is rejected too, then the session is cleared", async () => {
    db.validAccessTokens.delete("access-alice");
    db.refreshTokens.clear();

    await expect(request("/users/me")).rejects.toMatchObject({ status: 401 });
    expect(tokenStorage.hasSession()).toBe(false);
  });
});

describe("Given any API call", () => {
  it("when the server answers with problem+json, then an ApiError carries the problem and Retry-After", async () => {
    server.use(
      http.get("*/api/v1/users/me", () => {
        const response = problem(429, "Too Many Requests", { detail: "Slow down" });
        response.headers.set("Retry-After", "42");
        return response;
      }),
    );

    const error = await request("/users/me", { auth: false }).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 429, retryAfter: 42, message: "Slow down" });
  });

  it("when the error body is not JSON, then a generic problem is built from the status", async () => {
    server.use(http.get("*/api/v1/users/me", () => new HttpResponse("boom", { status: 502 })));

    const error = await request("/users/me", { auth: false }).catch((e: unknown) => e);

    expect(error).toMatchObject({ status: 502, retryAfter: null });
  });

  it("when a request is sent, then it carries the user's IANA time zone", async () => {
    let timeZone: string | null = null;
    server.use(
      http.get("*/api/v1/things", ({ request: req }) => {
        timeZone = req.headers.get("X-Timezone");
        return HttpResponse.json([]);
      }),
    );

    await request("/things", { auth: false });

    expect(timeZone).toBe(Intl.DateTimeFormat().resolvedOptions().timeZone);
    expect(timeZone).toBeTruthy();
  });

  it("when the time zone cannot be resolved, then the header is omitted", async () => {
    const spy = vi.spyOn(Intl, "DateTimeFormat").mockImplementation(() => {
      throw new Error("no Intl");
    });
    let seen: string | null = "unset";
    server.use(
      http.get("*/api/v1/things", ({ request: req }) => {
        seen = req.headers.get("X-Timezone");
        return HttpResponse.json([]);
      }),
    );

    await request("/things", { auth: false });

    spy.mockRestore();
    expect(seen).toBeNull();
  });

  it("when the server returns 204, then the result is undefined", async () => {
    server.use(http.delete("*/api/v1/things/1", () => new HttpResponse(null, { status: 204 })));

    await expect(request("/things/1", { method: "DELETE", auth: false })).resolves.toBeUndefined();
  });

  it("when query values are empty, then they are left out of the URL", async () => {
    let seen = "";
    server.use(
      http.get("*/api/v1/things", ({ request: req }) => {
        seen = new URL(req.url).search;
        return HttpResponse.json([]);
      }),
    );

    await request("/things", {
      auth: false,
      query: { page: 2, status: undefined, due_from: "", scope: null },
    });

    expect(seen).toBe("?page=2");
  });
});
