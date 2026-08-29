import { Suspense, lazy } from 'react';
import { Navigate } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';

import { DataStateBoundary } from '../components/DataStateBoundary.tsx';
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
 * Aujourd'hui (/today), Marchés (/markets), Options (/options/:underlying?),
 * Analyse (/analysis/:instrument?), Simulateur (/simulator) et Système
 * (/system), plus la page d'accès /auth (hors rail — elle n'est pas une page
 * produit du blueprint). Vague 4 : Portefeuille (/portfolio), Suivi
 * (/follow-up) et Performance (/performance). Vague finale : Calendrier
 * (/calendar), Opportunités (/opportunities) et Vertex IA (/ai) — les 12
 * pages du blueprint sont désormais réelles.
 *
 * /markets, /options, /analysis et /simulator sont chargées PARESSEUSEMENT
 * (React.lazy) : leurs chunks — et les chunks moteurs qu'elles importent
 * dynamiquement (ECharts pour /markets et /simulator, Lightweight Charts
 * pour /analysis) — ne grossissent pas le bundle initial (CHART_STANDARD :
 * un moteur de graphique par route, jamais dans le bundle initial).
 *
 * Vague finale : Calendrier (/calendar), Opportunités (/opportunities) et
 * Vertex IA (/ai) sont réelles et chargées paresseusement elles aussi. Les
 * 12 pages du blueprint (13 routes avec /auth) sont donc installées ;
 * `NotInstalledPage` ne sert plus aucune page du rail, mais reste le rendu
 * par défaut de toute page future non encore livrée.
 */

const LazyMarketsPage = lazy(async () => {
  const module = await import('../pages/markets/MarketsPage.tsx');
  return { default: module.MarketsPage };
});

const LazyOptionsPage = lazy(async () => {
  const module = await import('../pages/options/OptionsPage.tsx');
  return { default: module.OptionsPage };
});

const LazyAnalysisPage = lazy(async () => {
  const module = await import('../pages/analysis/AnalysisPage.tsx');
  return { default: module.AnalysisPage };
});

const LazySimulatorPage = lazy(async () => {
  const module = await import('../pages/simulator/SimulatorPage.tsx');
  return { default: module.SimulatorPage };
});

const LazyPortfolioPage = lazy(async () => {
  const module = await import('../pages/portfolio/PortfolioPage.tsx');
  return { default: module.PortfolioPage };
});

const LazyFollowUpPage = lazy(async () => {
  const module = await import('../pages/follow-up/FollowUpPage.tsx');
  return { default: module.FollowUpPage };
});

const LazyPerformancePage = lazy(async () => {
  const module = await import('../pages/performance/PerformancePage.tsx');
  return { default: module.PerformancePage };
});

const LazyCalendarPage = lazy(async () => {
  const module = await import('../pages/calendar/CalendarPage.tsx');
  return { default: module.CalendarPage };
});

const LazyOpportunitiesPage = lazy(async () => {
  const module = await import('../pages/opportunities/OpportunitiesPage.tsx');
  return { default: module.OpportunitiesPage };
});

const LazyAiPage = lazy(async () => {
  const module = await import('../pages/ai/AiPage.tsx');
  return { default: module.AiPage };
});

function MarketsRoute() {
  return (
    <Suspense fallback={<DataStateBoundary state="loading" />}>
      <LazyMarketsPage />
    </Suspense>
  );
}

function OptionsRoute() {
  return (
    <Suspense fallback={<DataStateBoundary state="loading" />}>
      <LazyOptionsPage />
    </Suspense>
  );
}

function AnalysisRoute() {
  return (
    <Suspense fallback={<DataStateBoundary state="loading" />}>
      <LazyAnalysisPage />
    </Suspense>
  );
}

function SimulatorRoute() {
  return (
    <Suspense fallback={<DataStateBoundary state="loading" />}>
      <LazySimulatorPage />
    </Suspense>
  );
}

function PortfolioRoute() {
  return (
    <Suspense fallback={<DataStateBoundary state="loading" />}>
      <LazyPortfolioPage />
    </Suspense>
  );
}

function FollowUpRoute() {
  return (
    <Suspense fallback={<DataStateBoundary state="loading" />}>
      <LazyFollowUpPage />
    </Suspense>
  );
}

function PerformanceRoute() {
  return (
    <Suspense fallback={<DataStateBoundary state="loading" />}>
      <LazyPerformancePage />
    </Suspense>
  );
}

function CalendarRoute() {
  return (
    <Suspense fallback={<DataStateBoundary state="loading" />}>
      <LazyCalendarPage />
    </Suspense>
  );
}

function OpportunitiesRoute() {
  return (
    <Suspense fallback={<DataStateBoundary state="loading" />}>
      <LazyOpportunitiesPage />
    </Suspense>
  );
}

function AiRoute() {
  return (
    <Suspense fallback={<DataStateBoundary state="loading" />}>
      <LazyAiPage />
    </Suspense>
  );
}

const INSTALLED_PAGES: Readonly<Record<string, () => React.JSX.Element>> = {
  today: TodayPage,
  markets: MarketsRoute,
  system: SystemPage,
  options: OptionsRoute,
  analysis: AnalysisRoute,
  simulator: SimulatorRoute,
  portfolio: PortfolioRoute,
  'follow-up': FollowUpRoute,
  performance: PerformanceRoute,
  calendar: CalendarRoute,
  opportunities: OpportunitiesRoute,
  ai: AiRoute,
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
