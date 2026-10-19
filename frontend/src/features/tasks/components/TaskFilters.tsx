import { useState } from "react";

import type { TaskListParams, TaskOrdering, TaskStatus } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { InputField, SelectField } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { cn } from "@/lib/cn";

import { hasActiveFilters, ORDERING_OPTIONS, SCOPE_OPTIONS, STATUS_OPTIONS } from "../filters";

interface TaskFiltersProps {
  params: TaskListParams;
  onChange: (changes: Partial<TaskListParams>) => void;
  onClear: () => void;
}

function FilterFields({ params, onChange }: Omit<TaskFiltersProps, "onClear">) {
  return (
    <>
      <SelectField
        label="Status"
        value={params.status ?? ""}
        onChange={(event) =>
          onChange({ status: (event.target.value || undefined) as TaskStatus | undefined })
        }
      >
        <option value="">All statuses</option>
        {STATUS_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </SelectField>
      <InputField
        label="Due from"
        type="date"
        value={params.due_from ?? ""}
        max={params.due_to}
        onChange={(event) => onChange({ due_from: event.target.value || undefined })}
      />
      <InputField
        label="Due to"
        type="date"
        value={params.due_to ?? ""}
        min={params.due_from}
        onChange={(event) => onChange({ due_to: event.target.value || undefined })}
      />
      <SelectField
        label="Sort by"
        value={params.ordering}
        onChange={(event) => onChange({ ordering: event.target.value as TaskOrdering })}
      >
        {ORDERING_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </SelectField>
    </>
  );
}

export function TaskFilters({ params, onChange, onClear }: TaskFiltersProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const active = hasActiveFilters(params);

  return (
    <section aria-label="Task filters" className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div role="group" aria-label="Scope" className="inline-flex rounded-lg bg-slate-100 p-1">
          {SCOPE_OPTIONS.map((option) => {
            const selected = (params.scope ?? "all") === option.value;
            return (
              <button
                key={option.value}
                type="button"
                aria-pressed={selected}
                onClick={() => onChange({ scope: option.value })}
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600",
                  selected
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-600 hover:text-slate-900",
                )}
              >
                {option.label}
              </button>
            );
          })}
        </div>
        <Button
          variant="secondary"
          size="sm"
          className="md:hidden"
          onClick={() => setDrawerOpen(true)}
        >
          Filters{active ? " •" : ""}
        </Button>
      </div>

      <div className="hidden items-end gap-3 md:grid md:grid-cols-[repeat(4,minmax(0,1fr))_auto]">
        <FilterFields params={params} onChange={onChange} />
        <Button variant="ghost" onClick={onClear} disabled={!active}>
          Clear
        </Button>
      </div>

      {drawerOpen && (
        <Modal title="Filters" onClose={() => setDrawerOpen(false)}>
          <div className="space-y-4">
            <FilterFields params={params} onChange={onChange} />
            <div className="flex gap-2 pt-2">
              <Button variant="secondary" className="flex-1" onClick={onClear} disabled={!active}>
                Clear
              </Button>
              <Button className="flex-1" onClick={() => setDrawerOpen(false)}>
                Show results
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </section>
  );
}
