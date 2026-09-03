import type { AbsenceReason } from '../../components/AbsentModule.tsx';

/**
 * Graphiques — vue pure : le CATALOGUE des modules de la planche canonique
 * (`pages-07-08-portfolio-charts.png`, moitié droite ; `references/pages.md`
 * §8) et, pour chacun, ce que le serveur publie aujourd'hui.
 *
 * POURQUOI UN CATALOGUE. La consigne produit est « affichage d'abord,
 * branchements ensuite ». Cet ordre n'est honnête qu'à une condition : chaque
 * module de la planche est PRÉSENT, à sa place, soit servi par un contrat,
 * soit déclaré absent avec un motif du vocabulaire fermé d'`AbsentModule`.
 * Un test lit ce catalogue et exige que la page rende les douze — servis ou
 * déclarés —, ce qu'une capture seule ne prouverait pas.
 *
 * Aucun chiffre ici, aucune donnée : des titres, des questions et des motifs.
 * Les valeurs viennent uniquement d'`AnalysisResponse`, dans la page.
 *
 * `comparisonViewOf` fait exception au « aucune donnée » — mais pas au « aucun
 * calcul » : elle LIT le bloc `rebased_comparison` publié par le serveur et le
 * nomme, sans rebaser, sans aligner, sans arrondir et sans compléter.
 */

export type ChartsModuleStatus =
  | { readonly kind: 'served'; readonly contract: string }
  | { readonly kind: 'absent'; readonly reason: AbsenceReason; readonly note: string };

export interface ChartsModule {
  /** Identifiant stable, utilisé par les tests et les `data-module`. */
  readonly id: string;
  readonly title: string;
  readonly question: string;
  readonly status: ChartsModuleStatus;
}

const ANALYSIS_CONTRACT = 'GET /api/v1/analysis/{instrument}';

/**
 * Les douze modules de la planche, dans son ordre de lecture.
 *
 * Les trois premiers sont servis par le contrat Analyse — même DTO, même
 * client, même composant de rendu que `/analysis`. Ce n'est pas un second
 * propriétaire de donnée : le propriétaire est le contrat, et cette page ne
 * fait que l'afficher sous SA question (« quelles relations puis-je explorer
 * sans perdre méthode et contexte ? »).
 *
 * Les neuf autres portent le motif EXACT de leur absence, mesuré dans le
 * dépôt le 2026-09-02 — jamais une promesse de livraison.
 */
export const CHARTS_MODULES: readonly ChartsModule[] = [
  {
    id: 'main-chart',
    title: 'Espace graphique',
    question: 'Que publie le serveur de la série de cet instrument ?',
    status: { kind: 'served', contract: ANALYSIS_CONTRACT },
  },
  {
    id: 'volume',
    title: 'Volume',
    question: 'Quel volume accompagne chaque barre publiée ?',
    status: { kind: 'served', contract: ANALYSIS_CONTRACT },
  },
  {
    id: 'served-indicators',
    title: 'Indicateurs servis',
    question: 'Quelles mesures le moteur serveur publie-t-il sur cette série ?',
    status: { kind: 'served', contract: ANALYSIS_CONTRACT },
  },
  {
    id: 'overlays',
    title: 'Overlays (moyennes mobiles)',
    question: 'Quelles moyennes mobiles superposer à la série ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun calcul de moyenne mobile n’est déclaré au registre des calculs ni publié par un snapshot.',
    },
  },
  {
    id: 'rsi',
    title: 'RSI',
    question: 'Où se situe la force relative de la série sur sa fenêtre ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun calcul RSI n’est déclaré au registre des calculs ni publié par un snapshot.',
    },
  },
  {
    id: 'macd',
    title: 'MACD',
    question: 'Comment évoluent les moyennes mobiles convergentes et divergentes ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun calcul MACD n’est déclaré au registre des calculs ni publié par un snapshot.',
    },
  },
  {
    // LOT-S2, 2026-09-03. `market.rebased_series` était approuvé au registre et
    // implémenté dans vertex_core SANS aucun appelant : ce module était donc
    // déclaré `SERVER_CONTRACT_MISSING`. Le dossier d'analyse publie désormais
    // le bloc `indicators.rebased_comparison` — deux séries ramenées à la même
    // base sur leurs seules séances communes, alignées PAR LE SERVEUR. La page
    // n'a plus rien à rebaser, ce qui reste interdit ici.
    id: 'comparison',
    title: 'Comparaison base 100',
    question: 'Comment cette série se compare-t-elle à d’autres, ramenées à une base commune ?',
    status: { kind: 'served', contract: ANALYSIS_CONTRACT },
  },
  {
    id: 'synchronized',
    title: 'Graphiques synchronisés',
    question: 'Quelles séries lire côte à côte sur le même calendrier ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Plusieurs séries alignées sur un calendrier commun exigent un contrat d’alignement que rien ne publie.',
    },
  },
  {
    id: 'selected-object',
    title: 'Objet sélectionné',
    question: 'Quels niveaux ou annotations ai-je posés sur cette série ?',
    status: {
      kind: 'absent',
      reason: 'DECISION_PENDING',
      note: 'Un objet dessiné est une donnée utilisateur persistée : le propriétaire n’a pas tranché où elle vit ni sous quel contrat.',
    },
  },
  {
    id: 'linked-alerts',
    title: 'Alertes liées',
    question: 'Quelles alertes surveillent cette série ?',
    status: {
      kind: 'absent',
      reason: 'DECISION_PENDING',
      note: '« Alertes » est une capacité globale de la barre supérieure, pas un module de page ; son contrat n’existe pas.',
    },
  },
  {
    id: 'layouts',
    title: 'Agencement',
    question: 'Comment disposer plusieurs vues de cette série ?',
    status: {
      kind: 'absent',
      reason: 'DECISION_PENDING',
      note: 'Un agencement enregistré est une préférence utilisateur persistée, sans propriétaire ni contrat décidés.',
    },
  },
  {
    id: 'saved-studies',
    title: 'Études sauvegardées',
    question: 'Quelles études ai-je enregistrées pour y revenir ?',
    status: {
      kind: 'absent',
      reason: 'DECISION_PENDING',
      note: 'Une étude sauvegardée est une donnée utilisateur persistée, sans propriétaire ni contrat décidés.',
    },
  },
];

export function servedModules(): readonly ChartsModule[] {
  return CHARTS_MODULES.filter((module) => module.status.kind === 'served');
}

export function absentModules(): readonly (ChartsModule & {
  readonly status: Extract<ChartsModuleStatus, { kind: 'absent' }>;
})[] {
  return CHARTS_MODULES.flatMap((module) =>
    module.status.kind === 'absent' ? [{ ...module, status: module.status }] : [],
  );
}

// ---------------------------------------------------------------------------
// Comparaison base 100 — LECTURE du bloc servi, jamais un recalcul
// ---------------------------------------------------------------------------

/**
 * Un point de la comparaison : SON jour et les DEUX valeurs de ce jour.
 *
 * Le serveur publie déjà cette forme. Deux listes parallèles auraient laissé
 * la page les apparier, donc les désaligner d'un décalage d'indice ; ici la
 * structure l'interdit.
 */
export interface ComparisonPoint {
  readonly tradingDay: string;
  readonly instrument: string;
  readonly benchmark: string;
}

export type ComparisonView =
  | {
      readonly kind: 'served';
      readonly benchmark: string;
      readonly unit: string;
      readonly baseValue: string;
      readonly currency: string | null;
      readonly adjustmentBasis: string | null;
      readonly commonSessions: number | null;
      readonly firstTradingDay: string | null;
      readonly lastTradingDay: string | null;
      readonly method: string | null;
      readonly points: readonly ComparisonPoint[];
    }
  | {
      readonly kind: 'absent';
      readonly status: string;
      readonly benchmark: string | null;
      readonly detail: string | null;
      /** Enregistrements que le serveur a ÉCARTÉS, avec leur motif. */
      readonly rejected: readonly string[];
    }
  /** Bloc publié dans une forme que cette page ne sait pas lire. */
  | { readonly kind: 'unreadable' }
  /** Aucun bloc publié — un dossier antérieur au contrat n'en porte pas. */
  | { readonly kind: 'none' };

function texteOuNull(valeur: unknown): string | null {
  return typeof valeur === 'string' && valeur !== '' ? valeur : null;
}

function nombreOuNull(valeur: unknown): number | null {
  return typeof valeur === 'number' && Number.isFinite(valeur) ? valeur : null;
}

function objetOuNull(valeur: unknown): Readonly<Record<string, unknown>> | null {
  return typeof valeur === 'object' && valeur !== null && !Array.isArray(valeur)
    ? (valeur as Readonly<Record<string, unknown>>)
    : null;
}

/**
 * Lit `indicators.rebased_comparison` d'`AnalysisResponse`.
 *
 * Quatre issues, toutes explicites : servie, refusée (le motif du serveur est
 * repris TEL QUEL), illisible, ou absente. Aucune valeur manquante n'est
 * complétée et aucun défaut n'est masqué : un bloc `OK` amputé de sa base, de
 * son unité ou de sa série est déclaré illisible plutôt qu'affiché à moitié —
 * une courbe base 100 dont on ignore la base ne se lit pas.
 */
export function comparisonViewOf(
  indicators: Readonly<Record<string, unknown>> | null | undefined,
): ComparisonView {
  if (indicators === null || indicators === undefined) {
    return { kind: 'none' };
  }
  const bloc = objetOuNull(indicators['rebased_comparison']);
  if (bloc === null) {
    return { kind: 'none' };
  }
  const statut = texteOuNull(bloc['status']);
  if (statut === null) {
    return { kind: 'unreadable' };
  }
  if (statut !== 'OK') {
    const brutes = bloc['rejected_records'];
    return {
      kind: 'absent',
      status: statut,
      benchmark: texteOuNull(bloc['benchmark']),
      detail: texteOuNull(bloc['detail']),
      rejected: Array.isArray(brutes)
        ? brutes.flatMap((brut) => {
            const rejet = objetOuNull(brut);
            const identifiant = rejet === null ? null : texteOuNull(rejet['event_id']);
            const motif = rejet === null ? null : texteOuNull(rejet['reason']);
            return identifiant === null || motif === null ? [] : [`${identifiant} — ${motif}`];
          })
        : [],
    };
  }

  const benchmark = texteOuNull(bloc['benchmark']);
  const unit = texteOuNull(bloc['unit']);
  const baseValue = texteOuNull(bloc['base_value']);
  const brutes = bloc['series'];
  if (benchmark === null || unit === null || baseValue === null || !Array.isArray(brutes)) {
    return { kind: 'unreadable' };
  }
  const points: ComparisonPoint[] = [];
  for (const brut of brutes) {
    const point = objetOuNull(brut);
    const jour = point === null ? null : texteOuNull(point['trading_day']);
    const actif = point === null ? null : texteOuNull(point['instrument']);
    const indice = point === null ? null : texteOuNull(point['benchmark']);
    if (jour === null || actif === null || indice === null) {
      return { kind: 'unreadable' };
    }
    points.push({ tradingDay: jour, instrument: actif, benchmark: indice });
  }
  const calcul = objetOuNull(bloc['calculation']);
  return {
    kind: 'served',
    benchmark,
    unit,
    baseValue,
    currency: texteOuNull(bloc['currency']),
    adjustmentBasis: texteOuNull(bloc['adjustment_basis']),
    commonSessions: nombreOuNull(bloc['common_sessions']),
    firstTradingDay: texteOuNull(bloc['first_trading_day']),
    lastTradingDay: texteOuNull(bloc['last_trading_day']),
    method: calcul === null ? null : texteOuNull(calcul['method']),
    points,
  };
}
