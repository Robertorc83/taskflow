import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type Tone = "slate" | "amber" | "indigo" | "emerald" | "rose";

const tones: Record<Tone, string> = {
  slate: "bg-slate-100 text-slate-700 ring-slate-500/20",
  amber: "bg-amber-50 text-amber-800 ring-amber-600/20",
  indigo: "bg-indigo-50 text-indigo-700 ring-indigo-600/20",
  emerald: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  rose: "bg-rose-50 text-rose-700 ring-rose-600/20",
};

export function Badge({ tone = "slate", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}
