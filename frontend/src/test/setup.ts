import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";

import { tokenStorage } from "@/api/tokenStorage";

import { resetDb } from "./db";
import { server } from "./server";

// React Router's data router builds a fetch `Request` with jsdom's AbortSignal, which Node's undici
// rejects ("Expected signal to be an instance of AbortSignal"). Strip the signal in tests only.
class JsdomSafeRequest extends Request {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(input, init && { ...init, signal: undefined });
  }
}
globalThis.Request = JsdomSafeRequest;

// SPEC-007 F16: any React/library warning fails the test that caused it.
const failOnConsole =
  (level: "error" | "warn") =>
  (...args: unknown[]) => {
    throw new Error(`console.${level} called during test: ${args.map(String).join(" ")}`);
  };

beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
  vi.spyOn(console, "error").mockImplementation(failOnConsole("error"));
  vi.spyOn(console, "warn").mockImplementation(failOnConsole("warn"));
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
  resetDb();
  tokenStorage.clear();
});

afterAll(() => {
  server.close();
  vi.restoreAllMocks();
});
