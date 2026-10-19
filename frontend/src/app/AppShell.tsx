import { Link, Outlet } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { Logo } from "@/components/ui/Logo";
import { useAuth } from "@/features/auth/authContext";

export function AppShell() {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link
            to="/tasks"
            aria-label="Taskflow home"
            className="rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600"
          >
            <Logo />
          </Link>
          <div className="flex items-center gap-3">
            {user && (
              <span className="hidden text-right text-sm sm:block">
                <span className="block font-medium text-slate-900">{user.full_name}</span>
                <span className="block text-xs text-slate-500">{user.email}</span>
              </span>
            )}
            <Button variant="secondary" size="sm" onClick={logout}>
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-10">
        <Outlet />
      </main>
    </div>
  );
}
