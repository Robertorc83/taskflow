import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 px-4 text-center">
      <p className="text-sm font-semibold text-indigo-600">404</p>
      <h1 className="text-2xl font-semibold text-slate-900">Page not found</h1>
      <Link to="/tasks" className="text-sm font-medium text-indigo-600 hover:text-indigo-500">
        Back to your tasks
      </Link>
    </main>
  );
}
