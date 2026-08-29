import { Navigate } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';

import { NotFoundPage } from '../components/NotFoundPage.tsx';
import { NotInstalledPage } from '../components/NotInstalledPage.tsx';
import { AuthPage } from '../pages/AuthPage.tsx';
import { SystemPage } from '../pages/SystemPage.tsx';
import { TodayPage } from '../pages/TodayPage.tsx';
import { AppShell } from '../shell/AppShell.tsx';
import { ALL_PAGES, DEFAULT_PATH } from './pages.ts';
import type { PageDef } from './pages.ts';

/**
 * Table de routes du shell. Une page réelle ne remplace l'entrée « Lot non
 * installé » que lorsque ses routes, données, états et tests existent
 * (docs/07-delivery/FOLDER_BY_FOLDER_PROGRAM.md). Pages réelles installées :
 * Aujourd'hui (/today) et Système (/system), plus la page d'accès /auth
 * (hors rail — elle n'est pas une page produit du blueprint).
 */

const INSTALLED_PAGES: Readonly<Record<string, () => React.JSX.Element>> = {
  today: TodayPage,
  system: SystemPage,
};

/** Définition de la page d'accès (hors navigation, hors blueprint des 12). */
export const AUTH_PAGE: PageDef = {
  key: 'auth',
  title: 'Accès',
  navPath: '/auth',
  routePath: '/auth',
  question: 'Ouvrir une session locale par passkey — aucun mot de passe, aucun repli.',
  lot: 'LOT-14',
  shortLabel: 'Acc',
};

export function buildRouteObjects(): RouteObject[] {
  return [
    {
      element: <AppShell />,
      children: [
        { index: true, element: <Navigate to={DEFAULT_PATH} replace /> },
        ...ALL_PAGES.map((page): RouteObject => {
          const Installed = INSTALLED_PAGES[page.key];
          return {
            path: page.routePath,
            element: Installed !== undefined ? <Installed /> : <NotInstalledPage page={page} />,
            handle: { page },
          };
        }),
        { path: AUTH_PAGE.routePath, element: <AuthPage />, handle: { page: AUTH_PAGE } },
        { path: '*', element: <NotFoundPage /> },
      ],
    },
  ];
}
