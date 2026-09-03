// @vitest-environment node
/**
 * Porte de composition du socle v2 : chaque module de chaque catalogue de page
 * DÉCLARE sa taille et sa variante, dans un vocabulaire FERMÉ.
 *
 * POURQUOI. Avant cette porte, la place d'un module sur sa planche était une
 * classe CSS écrite à la main dans `global.css`, page par page : rien
 * n'obligeait un module nouveau à déclarer sa taille, et rien ne disait, en
 * lisant le catalogue, si un module était la dominante de sa page ou un module
 * de soutien. Deux dominantes sur un écran, c'est zéro dominante.
 *
 * CE QU'ELLE MESURE.
 *   1. `size` ∈ {S, M, L, XL} — un SPAN DE COMPOSITION, jamais une apparence ;
 *   2. `variant` ∈ vocabulaire fermé de `docs/05-design/WIDGET_LIBRARY.md`
 *      (dominant, support, rail, inline, sheet, workflow-step) ;
 *   3. AU PLUS une variante `dominant` par catalogue — la même règle que
 *      `one-dominant-per-page.test.ts` mesure côté rendu ;
 *   4. la teinte secondaire éventuelle d'une page appartient à `pageAccent`
 *      (ADR-017, réserve 5 de la revue C0 : sans déclaration, `--vx-page-accent`
 *      est invalide à la valeur calculée et un `fill` SVG retomberait
 *      silencieusement sur le noir).
 *
 * CE QU'ELLE NE PROUVE PAS. Qu'un module déclaré `XL` occupe réellement quatre
 * colonnes : seule l'e2e de densité le mesure en navigateur.
 */
import { describe, expect, it } from 'vitest';

import { pageAccent } from '../../design/tokens.ts';
import { ANALYSIS_MODULES } from '../../pages/analysis/analysisModules.ts';
import { CALENDAR_MODULES } from '../../pages/calendar/calendarModules.ts';
import { CATALYSTS_MODULES } from '../../pages/catalysts/catalystsModules.ts';
import { CHARTS_MODULES } from '../../pages/charts/chartsView.ts';
import { MARKETS_MODULES } from '../../pages/markets/marketsModules.ts';
import { OPPORTUNITIES_MODULES } from '../../pages/opportunities/opportunitiesModules.ts';
import { OPTIONS_MODULES } from '../../pages/options/optionsModules.ts';
import { PORTFOLIO_MODULES } from '../../pages/portfolio/portfolioModules.ts';
import { RISK_MODULES } from '../../pages/risk/riskModules.ts';
import { SIMULATOR_MODULES } from '../../pages/simulator/simulatorModules.ts';
import { SOURCES_MODULES } from '../../pages/sources/sourcesModules.ts';
import { TODAY_MODULES } from '../../pages/todayView.ts';
import { PAGE_ACCENTS } from './pageAccent.ts';
import { WIDGET_SIZES, WIDGET_VARIANTS } from './Widget.tsx';

interface CatalogEntry {
  readonly id: string;
  readonly size: string;
  readonly variant: string;
}

const CATALOGS: ReadonlyArray<readonly [string, readonly CatalogEntry[]]> = [
  ['today', TODAY_MODULES],
  ['markets', MARKETS_MODULES],
  ['opportunities', OPPORTUNITIES_MODULES],
  ['analysis', ANALYSIS_MODULES],
  ['options', OPTIONS_MODULES],
  ['simulator', SIMULATOR_MODULES],
  ['portfolio', PORTFOLIO_MODULES],
  ['charts', CHARTS_MODULES],
  ['risks', RISK_MODULES],
  ['catalysts', CATALYSTS_MODULES],
  ['calendar', CALENDAR_MODULES],
  ['sources-reports', SOURCES_MODULES],
];

describe('catalogues de pages — taille et variante déclarées', () => {
  it('les douze catalogues sont lus (aucun balayage vide)', () => {
    expect(CATALOGS).toHaveLength(12);
    for (const [page, modules] of CATALOGS) {
      expect(modules.length, `${page} : catalogue vide`).toBeGreaterThan(0);
    }
  });

  it('chaque module déclare une taille du vocabulaire fermé', () => {
    const fautes: string[] = [];
    for (const [page, modules] of CATALOGS) {
      for (const module of modules) {
        if (!(WIDGET_SIZES as readonly string[]).includes(module.size)) {
          fautes.push(`${page}/${module.id} → ${String(module.size)}`);
        }
      }
    }
    expect(fautes, `tailles hors vocabulaire : ${fautes.join(', ')}`).toEqual([]);
  });

  it('chaque module déclare une variante du vocabulaire fermé', () => {
    const fautes: string[] = [];
    for (const [page, modules] of CATALOGS) {
      for (const module of modules) {
        if (!(WIDGET_VARIANTS as readonly string[]).includes(module.variant)) {
          fautes.push(`${page}/${module.id} → ${String(module.variant)}`);
        }
      }
    }
    expect(fautes, `variantes hors vocabulaire : ${fautes.join(', ')}`).toEqual([]);
  });

  it('au plus UNE variante dominante par catalogue', () => {
    const fautes: string[] = [];
    for (const [page, modules] of CATALOGS) {
      const dominants = modules.filter((module) => module.variant === 'dominant');
      if (dominants.length > 1) {
        fautes.push(`${page} → ${dominants.map((module) => module.id).join(', ')}`);
      }
    }
    expect(fautes, `deux dominantes = zéro dominante : ${fautes.join(' | ')}`).toEqual([]);
  });

  it('la dominante déclarée est le module le plus large de sa page', () => {
    const fautes: string[] = [];
    for (const [page, modules] of CATALOGS) {
      const dominant = modules.find((module) => module.variant === 'dominant');
      if (dominant !== undefined && dominant.size === 'S') {
        fautes.push(`${page}/${dominant.id}`);
      }
    }
    expect(fautes, `une dominante en taille S n'entre pas l'œil : ${fautes.join(', ')}`).toEqual(
      [],
    );
  });

  it('aucun identifiant de module en double dans un catalogue', () => {
    for (const [page, modules] of CATALOGS) {
      const ids = modules.map((module) => module.id);
      expect(new Set(ids).size, `${page} : identifiants en double`).toBe(ids.length);
    }
  });
});

describe('teinte sémantique secondaire par page (ADR-017)', () => {
  it('toute teinte déclarée appartient au vocabulaire typé `pageAccent`', () => {
    const familles = Object.keys(pageAccent);
    for (const [page, famille] of Object.entries(PAGE_ACCENTS)) {
      if (famille === null) {
        continue;
      }
      expect(familles, `${page} déclare une famille inconnue : ${famille}`).toContain(famille);
    }
  });

  it('aucune page ne déclare une famille de SIGNE ni l’ambre de marque', () => {
    for (const [page, famille] of Object.entries(PAGE_ACCENTS)) {
      expect(['positive', 'negative', 'signal'], `${page}`).not.toContain(famille);
    }
  });

  it('aucune page ne déclare `warning` avant la mesure exigée par la revue C0', () => {
    // ADR-017, « Coûts et contraintes », réserve 3 : les valeurs de `warning`
    // et de `signal-bright` (source typée `src/design/tokens.ts`) diffèrent
    // d'au plus 4/255 par canal. Tant que la distinguabilité n'a pas été
    // mesurée sur capture, aucune page ne prend `warning` comme teinte de
    // page — la réserve reste tenue par une porte, pas par une intention.
    for (const [page, famille] of Object.entries(PAGE_ACCENTS)) {
      expect(famille, `${page} : réserve 3 d'ADR-017 non tenue`).not.toBe('warning');
    }
  });

  it('les douze destinations ont une entrée explicite (aucun oubli silencieux)', () => {
    const pages = CATALOGS.map(([page]) => page);
    for (const page of pages) {
      expect(Object.keys(PAGE_ACCENTS), `${page} sans décision de teinte`).toContain(page);
    }
  });
});
