import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo, useSyncExternalStore, type ReactNode } from "react";

import { authApi } from "@/api/auth";
import { tokenStorage } from "@/api/tokenStorage";
import type { LoginInput, RegisterInput } from "@/api/types";
import { usersApi } from "@/api/users";
import { queryKeys } from "@/lib/queryKeys";

import { AuthContext, type AuthState } from "./authContext";

function useHasSession(): boolean {
  return useSyncExternalStore(
    (listener) => tokenStorage.subscribe(listener),
    () => tokenStorage.hasSession(),
  );
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const isAuthenticated = useHasSession();

  const me = useQuery({
    queryKey: queryKeys.me,
    queryFn: usersApi.me,
    enabled: isAuthenticated,
    staleTime: 5 * 60_000,
  });

  const login = useCallback(
    async (input: LoginInput) => {
      const tokens = await authApi.login(input);
      queryClient.clear();
      tokenStorage.save(tokens);
    },
    [queryClient],
  );

  const register = useCallback(
    async (input: RegisterInput) => {
      await authApi.register(input);
      await login({ email: input.email, password: input.password });
    },
    [login],
  );

  const logout = useCallback(() => {
    tokenStorage.clear();
    queryClient.clear();
  }, [queryClient]);

  const value = useMemo<AuthState>(
    () => ({
      isAuthenticated,
      user: isAuthenticated ? (me.data ?? null) : null,
      login,
      register,
      logout,
    }),
    [isAuthenticated, me.data, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
