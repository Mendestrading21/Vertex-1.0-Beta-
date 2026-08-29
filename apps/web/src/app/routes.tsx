import { Navigate } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';

import { NotFoundPage } from '../components/NotFoundPage.tsx';
import { NotInstalledPage } from '../components/NotInstalledPage.tsx';
import { AppShell } from '../shell/AppShell.tsx';
import { ALL_PAGES, DEFAULT_PATH } from './pages.ts';

/**
 * Table de routes du shell. Chaque page cible rend pour l'instant la page
 * « Lot non installé » honnête ; une page réelle ne remplacera cette entrée
 * que lorsque ses routes, données, états et tests existeront
 * (docs/07-delivery/FOLDER_BY_FOLDER_PROGRAM.md, dossiers 15 à 24).
 */
export function buildRouteObjects(): RouteObject[] {
  return [
    {
      element: <AppShell />,
      children: [
        { index: true, element: <Navigate to={DEFAULT_PATH} replace /> },
        ...ALL_PAGES.map(
          (page): RouteObject => ({
            path: page.routePath,
            element: <NotInstalledPage page={page} />,
            handle: { page },
          }),
        ),
        { path: '*', element: <NotFoundPage /> },
      ],
    },
  ];
}
