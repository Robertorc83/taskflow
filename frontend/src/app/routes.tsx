import { Navigate, type RouteObject } from "react-router-dom";

import { LoginPage } from "@/features/auth/LoginPage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { RedirectIfAuthenticated, RequireAuth } from "@/features/auth/RequireAuth";
import { TaskFormDialog } from "@/features/tasks/components/TaskFormDialog";
import { TaskListPage } from "@/features/tasks/pages/TaskListPage";

import { AppShell } from "./AppShell";
import { NotFoundPage } from "./NotFoundPage";

export const routes: RouteObject[] = [
  {
    element: <RedirectIfAuthenticated />,
    children: [
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },
    ],
  },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "/", element: <Navigate to="/tasks" replace /> },
          {
            path: "/tasks",
            element: <TaskListPage />,
            children: [
              { path: "new", element: <TaskFormDialog /> },
              { path: ":taskId/edit", element: <TaskFormDialog /> },
            ],
          },
        ],
      },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
];

/** Opt into React Router v7 behaviours now, which also silences the v6 deprecation warnings. */
export const routerFutureFlags = {
  v7_relativeSplatPath: true,
  v7_fetcherPersist: true,
  v7_normalizeFormMethod: true,
  v7_partialHydration: true,
  v7_skipActionErrorRevalidation: true,
} as const;

export const providerFutureFlags = { v7_startTransition: true } as const;
