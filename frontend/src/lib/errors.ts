import { ApiError } from "@/api/http";
import type { FieldError } from "@/api/types";

/** A human-readable message for any error thrown by the API client. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 429) {
      return error.retryAfter
        ? `Too many attempts, try again in ${error.retryAfter} s`
        : "Too many attempts, try again shortly";
    }
    return error.problem.detail ?? error.problem.title;
  }
  return "Something went wrong. Please try again.";
}

/** Field-level validation errors from a 422 problem response, keyed by request field name. */
export function fieldErrors(error: unknown): FieldError[] {
  if (!(error instanceof ApiError) || error.status !== 422) return [];
  return (error.problem.errors ?? []).map(({ field, message }) => ({
    // Tolerate dotted locations such as "body.title".
    field: field.split(".").pop() ?? field,
    message,
  }));
}
