import { Suspense, lazy } from 'react';
import { Navigate } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';

import { DataStateBoundary } from '../components/DataStateBoundary.tsx';
import { NotFoundPage } from '../components/NotFoundPage.tsx';
import { NotInstalledPage } from '../components/NotInstalledPage.tsx';
import { AuthPage } from '../pages/AuthPage.tsx';
import { SourcesReportsPage } from '../pages/SourcesReportsPage.tsx';
import { TodayPage } from '../pages/TodayPage.tsx';
import { AppShell } from '../shell/AppShell.tsx';
import { ALL_PAGES, DEFAULT_PATH } from './pages.ts';
import type { PageDef } from './pages.ts';

/**
 * Table de routes du shell. Une page réelle ne remplace l'entrée « Lot non
 * installé » que lorsque ses routes, données, états et tests existent
 * (docs/07-delivery/FOLDER_BY_FOLDER_PROGRAM.md).
 *
 * Les douze destinations du rail sont installées : Aujourd'hui, Opportunités,
 * Analyse, Options, Simulateur, Calendrier, Marchés, Graphiques, Portefeuille,
 * Risques, Catalyseurs et Sources & Rapports. S'y ajoute /auth, hors rail :
 * c'est une route de session, pas une destination du blueprint.
 *
 * `NotInstalledPage` ne sert AUCUNE entrée du rail. Graphiques (LOT-A2) est
 * une composition complète dont les modules sans source sont DÉCLARÉS absents
 * (`AbsentModule`), ce qui n'est pas une façade : la géométrie est réelle, le
 * motif est nommé, aucune valeur n'est inventée.
 *
 * Toutes les pages sauf Aujourd'hui et Sources & Rapports sont chargées
 * PARESSEUSEMENT (React.lazy) : leurs chunks — et les chunks moteurs
 * importés dynamiquement (ECharts pour /markets, /simulator et le module
 * Performance de /portfolio ; Lightweight Charts pour /analysis) — ne
 * grossissent pas le bundle initial (CHART_STANDARD : un moteur de graphique
 * par route, jamais dans le bundle initial).
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

const LazyCatalystsPage = lazy(async () => {
  const module = await import('../pages/catalysts/CatalystsPage.tsx');
  return { default: module.CatalystsPage };
});

const LazyCalendarPage = lazy(async () => {
  const module = await import('../pages/calendar/CalendarPage.tsx');
  return { default: module.CalendarPage };
});

const LazyRiskPage = lazy(async () => {
  const module = await import('../pages/risk/RiskPage.tsx');
  return { default: module.RiskPage };
});

const LazyChartsPage = lazy(async () => {
  const module = await import('../pages/charts/ChartsPage.tsx');
  return { default: module.ChartsPage };
});

const LazyOpportunitiesPage = lazy(async () => {
  const module = await import('../pages/opportunities/OpportunitiesPage.tsx');
  return { default: module.OpportunitiesPage };
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

function CatalystsRoute() {
  return (
    <Suspense fallback={<DataStateBoundary state="loading" />}>
      <LazyCatalystsPage />
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

function RiskRoute() {
  return (
    <Suspense fallback={<DataStateBoundary state="loading" />}>
      <LazyRiskPage />
    </Suspense>
  );
}

function ChartsRoute() {
  return (
    <Suspense fallback={<DataStateBoundary state="loading" />}>
      <LazyChartsPage />
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

const INSTALLED_PAGES: Readonly<Record<string, () => React.JSX.Element>> = {
  today: TodayPage,
  markets: MarketsRoute,
  'sources-reports': SourcesReportsPage,
  options: OptionsRoute,
  analysis: AnalysisRoute,
  simulator: SimulatorRoute,
  portfolio: PortfolioRoute,
  risks: RiskRoute,
  catalysts: CatalystsRoute,
  calendar: CalendarRoute,
  opportunities: OpportunitiesRoute,
  charts: ChartsRoute,
};

/** Définition de la page d'accès (hors navigation, hors blueprint des 12). */
export const AUTH_PAGE: PageDef = {
  key: 'auth',
  title: 'Accès',
  navPath: '/auth',
  routePath: '/auth',
  question: 'Ouvrir une session locale par passkey — aucun mot de passe, aucun repli.',
  lot: 'LOT-14',
  // La page d'accès ne lit aucun snapshot, et le flux SSE ne vit qu'en session
  // authentifiée : il n'y a rien à signaler ici, donc rien à prétendre suivre.
  live: null,
};

/**
 * Anciennes routes → destination absorbée, d'après
 * `docs/05-design/PAGE_ARBITRATION.md`.
 *
 * `/system` est devenu `/sources-reports` : la page portait déjà la santé des
 * quatorze sources, la cible y ajoute lignage, incidents et rapports.
 *
 * `/performance` a rejoint `/portfolio` : le contrat des douze pages range
 * l'« historique » du registre parmi les widgets de Portefeuille, et les deux
 * vues lisent le MÊME portefeuille manuel.
 *
 * `/follow-up` a rejoint `/catalysts` : §10 du contrat donne à Catalyseurs la
 * question « quels événements vérifiés peuvent modifier LA THÈSE et quand ? ».
 * Une thèse est mise en revue parce qu'un catalyseur l'a touchée.
 *
 * `/ai` n'a plus de destination : le contrat serveur ne connaît que trois
 * sujets explicables, qui sont les dossiers d'Analyse et de Portefeuille.
 * L'explication vit donc dans l'inspecteur de ces deux pages.
 *
 * Les routes API `/api/v1/system/capabilities` et `/api/v1/performance/{id}`
 * ne bougent PAS — seule la composition d'interface change, et
 * `.claude/rules/architecture.md` interdit de déplacer une responsabilité
 * serveur sans ADR.
 */
const LEGACY_REDIRECTS: ReadonlyArray<readonly [string, string]> = [
  ['/system', '/sources-reports'],
  ['/performance', '/portfolio'],
  ['/follow-up', '/catalysts'],
  // `/ai` n'a plus de destination propre : l'explication vit dans
  // l'inspecteur des pages qui portent un dossier explicable. Analyse est la
  // plus proche continuation — c'était le sujet par défaut de l'ancienne page.
  ['/ai', '/analysis'],
];

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
        // Redirections des destinations ABSORBÉES (docs/05-design/PAGE_ARBITRATION.md).
        // Une route retirée sans redirection casserait un signet ou un lien
        // profond existant : la règle 5 du document d'arbitrage l'interdit.
        ...LEGACY_REDIRECTS.map(
          ([from, to]): RouteObject => ({ path: from, element: <Navigate to={to} replace /> }),
        ),
        { path: '*', element: <NotFoundPage /> },
      ],
    },
  ];
}
