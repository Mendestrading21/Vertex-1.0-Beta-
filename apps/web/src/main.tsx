import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider, createBrowserRouter } from 'react-router-dom';

import './styles/fonts.css';
import './design/tokens.css';
import './styles/global.css';
import './styles/widgets.css';

import { installSnapshotEvents } from './api/events.ts';
import { installSessionIsolation } from './api/sessionIsolation.ts';
import { buildRouteObjects } from './app/routes.tsx';

/**
 * Client React Query du shell. Les pages installées (Aujourd'hui, Sources & Rapports)
 * consomment les snapshots bornés de l'API locale ; l'abonnement SSE
 * signal-only invalide les clés de requête ciblées quand une tête de
 * snapshot change (le flux ne porte jamais la donnée).
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
});

// Le flux SSE ne vit que pendant une session authentifiée (sinon 401).
installSnapshotEvents(queryClient);
installSessionIsolation(queryClient);

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
