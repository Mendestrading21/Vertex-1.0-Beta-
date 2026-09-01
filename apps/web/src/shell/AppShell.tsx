import { useCallback, useState } from 'react';
import { Outlet, useMatches } from 'react-router-dom';

import type { PageDef } from '../app/pages.ts';
import { ContextBar } from './ContextBar.tsx';
import { INSPECTOR_SLOT_ID, useInspectorOccupied } from './inspector.tsx';
import { NavRail } from './NavRail.tsx';
import { ShellTicker } from './ShellTicker.tsx';

/** Clé localStorage de l'état replié du rail. */
export const RAIL_COLLAPSED_STORAGE_KEY = 'vx.rail.collapsed';

interface PageHandle {
  readonly page: PageDef;
}

function isPageHandle(handle: unknown): handle is PageHandle {
  return (
    typeof handle === 'object' &&
    handle !== null &&
    'page' in handle &&
    typeof (handle as { page?: { key?: unknown } }).page?.key === 'string'
  );
}

/**
 * Signatures Titanium Ledger, dans l'ordre des planches canoniques.
 *
 * `08 charts` reste RÉSERVÉ : la destination attend un contrat serveur (voir
 * `docs/05-design/PAGE_ARBITRATION.md`). Un code réservé n'est pas un code
 * cassé — la table saute déjà des numéros sans que rien n'en souffre, et
 * c'est précisément ce qui rend la réservation possible.
 *
 * `09 risks` ne l'est plus : son contrat serveur existe
 * (`GET /api/v1/risk/matrix`), avec sa route, ses données et ses tests.
 *
 * CES CODES DOIVENT SUIVRE `--vx-page-ledger` (styles/global.css). Ce sont
 * deux sources pour le même numéro : le 2026-09-01 cette table a été corrigée
 * SANS le CSS, et chaque page affichait `TL / 03` à côté de `LEDGER 02`. Un
 * test lit les deux fichiers et les compare — voir shell.test.tsx.
 */
export const LEDGER_CODE_BY_PAGE: Readonly<Record<string, string>> = {
  today: 'TL / 01',
  markets: 'TL / 02',
  opportunities: 'TL / 03',
  analysis: 'TL / 04',
  options: 'TL / 05',
  simulator: 'TL / 06',
  portfolio: 'TL / 07',
  // 08 charts — réservé, destination absente
  risks: 'TL / 09',
  catalysts: 'TL / 10',
  calendar: 'TL / 11',
  'sources-reports': 'TL / 12',
  auth: 'TL / ACCESS',
};

function readStoredCollapsed(): boolean {
  try {
    return window.localStorage.getItem(RAIL_COLLAPSED_STORAGE_KEY) === '1';
  } catch {
    // Stockage indisponible (navigation privée, quota) : état par défaut déployé.
    return false;
  }
}

function writeStoredCollapsed(collapsed: boolean): void {
  try {
    window.localStorage.setItem(RAIL_COLLAPSED_STORAGE_KEY, collapsed ? '1' : '0');
  } catch {
    // Persistance impossible : l'état reste valable pour la session en cours.
  }
}

/**
 * Coquille applicative desktop : lien d'évitement, rail de navigation
 * (landmark nav), barre de contexte (landmark header), contenu (landmark
 * main) et inspecteur contextuel (landmark complementary).
 *
 * Point 6 de l'anatomie canonique : « zone de travail dense avec une
 * dominante centrale et un inspecteur contextuel à droite ». L'inspecteur est
 * un EMPLACEMENT : son contenu vient de la page active, via
 * `InspectorPanel`. Le shell ne lit aucune donnée pour le remplir.
 *
 * Il n'occupe la grille que si une page y a monté quelque chose
 * (`data-inspector`). Une destination sans élément inspectable n'affiche donc
 * pas une colonne vide — ce serait de la chrome décorative.
 *
 * Desktop only — aucune variante téléphone (Mobile = LATER).
 */
export function AppShell() {
  const [collapsed, setCollapsed] = useState(readStoredCollapsed);
  const matches = useMatches();
  const pageMatch = [...matches].reverse().find((match) => isPageHandle(match.handle));
  const pageKey =
    pageMatch !== undefined && isPageHandle(pageMatch.handle) ? pageMatch.handle.page.key : 'unknown';

  const occupied = useInspectorOccupied();

  const toggle = useCallback(() => {
    setCollapsed((previous) => {
      const next = !previous;
      writeStoredCollapsed(next);
      return next;
    });
  }, []);

  return (
    <div
      className="vx-shell"
      data-rail={collapsed ? 'collapsed' : 'open'}
      data-inspector={occupied ? 'open' : 'empty'}
    >
      <a className="vx-skip-link" href="#vx-main">
        Aller au contenu principal
      </a>
      <NavRail collapsed={collapsed} onToggle={toggle} />
      <div className="vx-shell-body">
        {/*
          Point 4 de l'anatomie canonique : « ticker horizontal compact en
          haut, dans UNE SURFACE VITRÉE CONTINUE ». D'où l'enveloppe : la
          barre de contexte et le ticker ne forment qu'un seul bandeau, avec
          une seule arête basse et un seul plan collant. Deux éléments
          collants séparés auraient laissé le ticker défiler sous la barre —
          et une bordure entre les deux aurait cassé la continuité.
        */}
        <div className="vx-topbar">
          <ContextBar />
          <ShellTicker />
        </div>
        <div className="vx-work">
          <main
            id="vx-main"
            className="vx-main"
            tabIndex={-1}
            data-page={pageKey}
            data-ledger-code={LEDGER_CODE_BY_PAGE[pageKey] ?? 'TL / —'}
          >
            <Outlet />
          </main>
          {/*
            Le nœud d'accueil existe TOUJOURS dans le DOM : un portail a besoin
            d'une cible montée. C'est `hidden` qui décide de son affichage, pas
            un montage conditionnel — sinon la page ne pourrait jamais viser
            l'emplacement au premier rendu.
          */}
          <aside
            id={INSPECTOR_SLOT_ID}
            className="vx-inspector"
            aria-label="Inspecteur contextuel"
            hidden={!occupied}
          />
        </div>
      </div>
    </div>
  );
}
