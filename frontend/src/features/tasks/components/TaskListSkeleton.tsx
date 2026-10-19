export function TaskListSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div role="status" aria-label="Loading tasks" className="space-y-3">
      {Array.from({ length: rows }, (_, index) => (
        <div
          key={index}
          className="animate-pulse rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200"
        >
          <div className="h-4 w-1/3 rounded bg-slate-200" />
          <div className="mt-3 h-3 w-2/3 rounded bg-slate-100" />
          <div className="mt-3 h-3 w-1/4 rounded bg-slate-100" />
        </div>
      ))}
    </div>
  );
}
