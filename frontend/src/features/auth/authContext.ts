import { createContext, useContext } from "react";

import type { LoginInput, RegisterInput, User } from "@/api/types";

export interface AuthState {
  isAuthenticated: boolean;
  /** The current user, once `GET /users/me` has resolved. */
  user: User | null;
  login: (input: LoginInput) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
