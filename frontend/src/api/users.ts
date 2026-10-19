import { request } from "./http";
import type { Page, User } from "./types";

export const usersApi = {
  me: () => request<User>("/users/me"),
  list: (page = 1, size = 100) => request<Page<User>>("/users", { query: { page, size } }),
};
