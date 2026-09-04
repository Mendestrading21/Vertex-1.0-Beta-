import { useCallback, useState } from 'react';
import { Outlet, useMatches } from 'react-router-dom';

import type { PageDef } from '../app/pages.ts';
import { WorkspaceProvider } from '../app/workspace.tsx';
import { CommandPalette, useCommandPalette } from './CommandPalette.tsx';
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
 * Les douze codes sont attribués. `08 charts` l'est depuis le LOT-A2
 * (2026-09-02) : sa dominante est servie par le contrat Analyse et chaque
 * module sans source est déclaré absent — voir
 * `docs/05-design/PAGE_ARBITRATION.md`. `09 risks` l'est depuis le
 * 2026-09-01 (`GET /api/v1/risk/matrix`).
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
  charts: 'TL / 08',
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
  const palette = useCommandPalette();

  const toggle = useCallback(() => {
    setCollapsed((previous) => {
      const next = !previous;
      writeStoredCollapsed(next);
      return next;
    });
  }, []);

  return (
    /*
      Le contexte de travail enveloppe la COQUILLE, sous le routeur : les pages
      doivent pouvoir l'adopter depuis leurs paramètres d'URL, et le bandeau
      doit pouvoir le lire. Le poser au-dessus du routeur l'aurait coupé des
      paramètres de route ; le poser dans chaque page en aurait fait autant
      d'états séparés — le défaut qu'il corrige.
    */
    <WorkspaceProvider>
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
          {/*
            Le déclencheur est VISIBLE, et pas seulement un raccourci : un
            raccourci que rien n'annonce n'existe que pour qui le connaît déjà.
            Le bouton porte la combinaison, et il est atteignable à la
            tabulation comme n'importe quel autre contrôle du bandeau.
          */}
          <button
            type="button"
            className="vx-palette-trigger"
            onClick={() => {
              palette.setOpen(true);
            }}
          >
            <span className="vx-palette-trigger-label">Rechercher une destination ou un instrument</span>
            <kbd className="vx-palette-kbd">⌘K</kbd>
          </button>
          <ShellTicker />
        </div>
        <CommandPalette
          open={palette.open}
          onClose={() => {
            palette.setOpen(false);
          }}
        />
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
          {/*
            `tabIndex` : le nœud porte `max-height: 100vh; overflow-y: auto`,
            donc c'est une RÉGION DÉFILANTE — mesurée à 6367 px de contenu pour
            900 px visibles sur `/analysis/SYN-TECH-01`. Une région défilante
            doit être atteignable au clavier (axe `scrollable-region-focusable`,
            impact « serious », seuil déclaré à zéro), exactement comme la bande
            de ticker au LOT-14.

            CE QUE CETTE LIGNE RÉPARE, ET POURQUOI PERSONNE NE L'AVAIT VU. La
            règle passait déjà — mais par ACCIDENT, parce que le panneau monté
            contient des liens de citation. Entre l'instant où le nœud devient
            défilant et celui où ces liens existent, la région était
            inatteignable. La campagne d'accessibilité a fini par tomber dessus
            une fois sur trois viewports ; une sonde l'a reproduite sur la
            baseline comme sur le LOT-A1. Un `tabIndex` explicite retire la
            joignabilité du domaine du hasard : elle ne dépend plus de ce que
            la page a eu le temps de rendre.

            Masqué, le nœud n'est pas focalisable : `hidden` s'en charge.
          */}
          <aside
            id={INSPECTOR_SLOT_ID}
            className="vx-inspector"
            aria-label="Inspecteur contextuel"
            hidden={!occupied}
            tabIndex={0}
          />
        </div>
      </div>
    </div>
    </WorkspaceProvider>
  );
}
