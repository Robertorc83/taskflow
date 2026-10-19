/** App-wide query keys. Feature-specific keys live with their feature (e.g. features/tasks/queryKeys). */
export const queryKeys = {
  me: ["users", "me"] as const,
  users: ["users", "list"] as const,
};
