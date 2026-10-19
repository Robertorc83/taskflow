import { QueryClient } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { createMemoryRouter, MemoryRouter, RouterProvider } from "react-router-dom";

import { tokenStorage } from "@/api/tokenStorage";
import { Providers } from "@/app/Providers";
import { providerFutureFlags, routerFutureFlags, routes } from "@/app/routes";

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 }, mutations: { retry: false } },
  });
}

export function signInAsAlice(): void {
  tokenStorage.save({ access_token: "access-alice", refresh_token: "refresh-alice" });
}

/** Renders the whole app (routes + providers) at `path`, backed by the MSW in-memory API. */
export function renderApp(path = "/tasks", { authenticated = true } = {}) {
  if (authenticated) signInAsAlice();
  const client = createTestQueryClient();
  const router = createMemoryRouter(routes, { initialEntries: [path], future: routerFutureFlags });
  const user = userEvent.setup();
  const view = render(
    <Providers client={client}>
      <RouterProvider router={router} future={providerFutureFlags} />
    </Providers>,
  );
  return { ...view, user, router, client };
}

/** Renders a single component with providers and a router, for component-level tests. */
export function renderWithProviders(ui: ReactElement) {
  const client = createTestQueryClient();
  const user = userEvent.setup();
  const view = render(
    <Providers client={client}>
      <MemoryRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
        {ui}
      </MemoryRouter>
    </Providers>,
  );
  return { ...view, user, client };
}
