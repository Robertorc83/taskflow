import type { TokenPair } from "./types";

const ACCESS_KEY = "taskflow.access_token";
const REFRESH_KEY = "taskflow.refresh_token";

type Listener = () => void;
const listeners = new Set<Listener>();

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string | null): void {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    // Storage can be unavailable (private mode, blocked site data); the session then lives in memory only.
  }
}

let memoryAccess: string | null = null;
let memoryRefresh: string | null = null;

export const tokenStorage = {
  getAccessToken(): string | null {
    return memoryAccess ?? read(ACCESS_KEY);
  },
  getRefreshToken(): string | null {
    return memoryRefresh ?? read(REFRESH_KEY);
  },
  hasSession(): boolean {
    return this.getAccessToken() !== null;
  },
  save(tokens: Pick<TokenPair, "access_token" | "refresh_token">): void {
    memoryAccess = tokens.access_token;
    memoryRefresh = tokens.refresh_token;
    write(ACCESS_KEY, tokens.access_token);
    write(REFRESH_KEY, tokens.refresh_token);
    listeners.forEach((listener) => listener());
  },
  clear(): void {
    memoryAccess = null;
    memoryRefresh = null;
    write(ACCESS_KEY, null);
    write(REFRESH_KEY, null);
    listeners.forEach((listener) => listener());
  },
  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
};
