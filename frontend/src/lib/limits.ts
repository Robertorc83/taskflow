/** Validation limits shared by forms; they mirror the backend domain rules (SPEC-001 R2–R3, SPEC-002 R2). */
export const LIMITS = {
  taskTitleMax: 200,
  taskDescriptionMax: 2000,
  fullNameMax: 100,
  passwordMin: 8,
  passwordMax: 128,
} as const;
