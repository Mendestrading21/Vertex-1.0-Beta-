import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';

import { buildRouteObjects } from '../app/routes.tsx';

/** Monte l'application complète (shell + routes) sur un chemin initial. */
export function renderApp(initialPath: string) {
  const router = createMemoryRouter(buildRouteObjects(), {
    initialEntries: [initialPath],
  });
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const view = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { ...view, router };
}
