import { z } from "zod";

import { LIMITS } from "@/lib/limits";

// Mirrors SPEC-001 R1–R3.
export const loginSchema = z.object({
  email: z.string().trim().min(1, "Email is required").email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

export const registerSchema = z.object({
  full_name: z
    .string()
    .trim()
    .min(1, "Name is required")
    .max(LIMITS.fullNameMax, `At most ${LIMITS.fullNameMax} characters`),
  email: z.string().trim().min(1, "Email is required").email("Enter a valid email address"),
  password: z
    .string()
    .min(LIMITS.passwordMin, `Use at least ${LIMITS.passwordMin} characters`)
    .max(LIMITS.passwordMax, `At most ${LIMITS.passwordMax} characters`),
});

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
