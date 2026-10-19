import { request } from "./http";
import type { LoginInput, RegisterInput, TokenPair, User } from "./types";

export const authApi = {
  login: (input: LoginInput) =>
    request<TokenPair>("/auth/login", { method: "POST", body: input, auth: false }),
  register: (input: RegisterInput) =>
    request<User>("/auth/register", { method: "POST", body: input, auth: false }),
};
