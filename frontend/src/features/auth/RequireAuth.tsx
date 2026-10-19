import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "./authContext";

export function RequireAuth() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}

export function RedirectIfAuthenticated() {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) return <Navigate to="/tasks" replace />;
  return <Outlet />;
}
