import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider, createBrowserRouter } from 'react-router-dom';

import './styles/fonts.css';
import './design/tokens.css';
import './styles/global.css';

import { buildRouteObjects } from './app/routes.tsx';

/**
 * Client React Query du shell. Aucune requête n'est encore déclarée : le socle
 * n'invente aucune donnée. Les pages consommeront ce client quand un backend
 * réel exposera des snapshots bornés.
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
});

const rootElement = document.getElementById('root');
if (rootElement === null) {
  throw new Error('Missing #root element');
}

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={createBrowserRouter(buildRouteObjects())} />
    </QueryClientProvider>
  </StrictMode>,
);
