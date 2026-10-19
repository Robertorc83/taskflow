import { useState } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { Providers } from "./Providers";
import { createQueryClient } from "./queryClient";
import { providerFutureFlags, routerFutureFlags, routes } from "./routes";

const router = createBrowserRouter(routes, { future: routerFutureFlags });

export function App() {
  const [queryClient] = useState(createQueryClient);
  return (
    <Providers client={queryClient}>
      <RouterProvider router={router} future={providerFutureFlags} />
    </Providers>
  );
}
