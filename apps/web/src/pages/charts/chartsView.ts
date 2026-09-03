import type { AbsenceReason } from '../../components/AbsentModule.tsx';
import type { WidgetSize, WidgetVariant } from '../../components/widgets/Widget.tsx';

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
  /** Span de composition sur la planche — jamais une apparence (ADR-017). */
  readonly size: WidgetSize;
  /** Variante visuelle du vocabulaire fermé de WIDGET_LIBRARY.md. */
  readonly variant: WidgetVariant;
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
    size: 'XL',
    variant: 'dominant',
    title: 'Espace graphique',
    question: 'Que publie le serveur de la série de cet instrument ?',
    status: { kind: 'served', contract: ANALYSIS_CONTRACT },
  },
  {
    id: 'volume',
    size: 'S',
    variant: 'support',
    title: 'Volume',
    question: 'Quel volume accompagne chaque barre publiée ?',
    status: { kind: 'served', contract: ANALYSIS_CONTRACT },
  },
  {
    id: 'served-indicators',
    size: 'S',
    variant: 'support',
    title: 'Indicateurs servis',
    question: 'Quelles mesures le moteur serveur publie-t-il sur cette série ?',
    status: { kind: 'served', contract: ANALYSIS_CONTRACT },
  },
  {
    // LOT-S6, fusionné le 2026-09-03. Ces trois modules déclaraient « aucun
    // calcul … n'est déclaré au registre des calculs ni publié par un
    // snapshot ». C'était exact avant S6 ; ça ne l'est plus. Le worker publie
    // `indicators.overlays.{sma, ema, bollinger_bands}` et
    // `indicators.oscillators.{rsi, macd}`, chacun avec sa série RENDUE par
    // le serveur, sa méthode, ses paramètres et sa lignée. Une absence qui a
    // cessé d'être vraie n'est plus une prudence : c'est un mensonge.
    id: 'overlays',
    size: 'M',
    variant: 'support',
    title: 'Overlays (moyennes mobiles)',
    question: 'Quelles moyennes mobiles superposer à la série ?',
    status: { kind: 'served', contract: ANALYSIS_CONTRACT },
  },
  {
    id: 'rsi',
    size: 'S',
    variant: 'support',
    title: 'RSI',
    question: 'Où se situe la force relative de la série sur sa fenêtre ?',
    status: { kind: 'served', contract: ANALYSIS_CONTRACT },
  },
  {
    id: 'macd',
    size: 'M',
    variant: 'support',
    title: 'MACD',
    question: 'Comment évoluent les moyennes mobiles convergentes et divergentes ?',
    status: { kind: 'served', contract: ANALYSIS_CONTRACT },
  },
  {
    // LOT-S2, 2026-09-03. `market.rebased_series` était approuvé au registre et
    // implémenté dans vertex_core SANS aucun appelant : ce module était donc
    // déclaré `SERVER_CONTRACT_MISSING`. Le dossier d'analyse publie désormais
    // le bloc `indicators.rebased_comparison` — deux séries ramenées à la même
    // base sur leurs seules séances communes, alignées PAR LE SERVEUR. La page
    // n'a plus rien à rebaser, ce qui reste interdit ici.
    id: 'comparison',
    size: 'L',
    variant: 'support',
    title: 'Comparaison base 100',
    question: 'Comment cette série se compare-t-elle à d’autres, ramenées à une base commune ?',
    status: { kind: 'served', contract: ANALYSIS_CONTRACT },
  },
  {
    id: 'synchronized',
    size: 'M',
    variant: 'support',
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
    size: 'S',
    variant: 'support',
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
    size: 'S',
    variant: 'support',
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
    size: 'S',
    variant: 'support',
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
    size: 'S',
    variant: 'support',
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

/**
 * UN module du catalogue, par identifiant. Échoue visiblement sur un
 * identifiant inconnu : une planche qui compose un module absent du catalogue
 * est un défaut de composition, pas un cas d'affichage.
 */
export function chartsModule(id: string): ChartsModule {
  const module = CHARTS_MODULES.find((candidate) => candidate.id === id);
  if (module === undefined) {
    throw new Error(`Unknown charts module: ${id}`);
  }
  return module;
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

// ---------------------------------------------------------------------------
// Overlays et oscillateurs — LECTURE des blocs servis (LOT-S6)
// ---------------------------------------------------------------------------

/**
 * Une LIGNE d'indicateur servie : son nom publié, ses séances et ses valeurs.
 *
 * Le serveur rend déjà chaque valeur en chaîne décimale et aligne la série sur
 * la FIN des séances (première fenêtre complète). Cette vue ne fait que la
 * nommer : aucune moyenne, aucun lissage, aucun remplissage de trou.
 */
export interface IndicatorLineView {
  readonly key: string;
  /** Nom SERVI de la ligne ou de la bande (`lower`, `macd`, `value`…). */
  readonly label: string;
  readonly tradingDays: readonly string[];
  readonly values: readonly string[];
  readonly last: string;
}

export type IndicatorBlockView =
  | {
      readonly kind: 'served';
      readonly id: string;
      readonly unit: string;
      readonly method: string | null;
      /** Paramètres SERVIS du calcul (fenêtre, écarts-types, fenêtres MACD). */
      readonly parameters: readonly { readonly label: string; readonly value: string }[];
      readonly lines: readonly IndicatorLineView[];
      /**
       * Les lignes partagent-elles EXACTEMENT les mêmes séances servies ?
       *
       * C'est une CONSTATATION, jamais un alignement : les bandes de Bollinger
       * sortent d'une même liste de points et partagent donc leurs séances,
       * tandis que les trois lignes du MACD commencent à des séances
       * différentes (leurs fenêtres diffèrent). Superposer les secondes
       * exigerait de les réaligner dans le navigateur — ce que
       * `references/charts.md` interdit. La page lit ce fait et choisit sa
       * forme ; elle ne le corrige pas.
       */
      readonly aligned: boolean;
      readonly lastTradingDay: string | null;
      readonly calculationId: string | null;
      readonly engineVersion: string | null;
    }
  | {
      readonly kind: 'refused';
      readonly id: string;
      /** Statut SERVI (`INSUFFICIENT_SAMPLE`, `REFUSED`), repris tel quel. */
      readonly status: string;
      readonly detail: string | null;
    }
  | { readonly kind: 'unreadable'; readonly id: string }
  | { readonly kind: 'none'; readonly id: string };

/** Points `{trading_day, <nom>}` d'une ligne servie. `null` si illisible. */
function ligneDePoints(
  points: readonly unknown[],
  nom: string,
  key: string,
): IndicatorLineView | null {
  const jours: string[] = [];
  const valeurs: string[] = [];
  for (const brut of points) {
    const point = objetOuNull(brut);
    const jour = point === null ? null : texteOuNull(point['trading_day']);
    const valeur = point === null ? null : texteOuNull(point[nom]);
    if (jour === null || valeur === null) {
      return null;
    }
    jours.push(jour);
    valeurs.push(valeur);
  }
  const dernier = valeurs[valeurs.length - 1];
  if (dernier === undefined) {
    return null;
  }
  return { key, label: nom, tradingDays: jours, values: valeurs, last: dernier };
}

/** Noms SERVIS des lignes d'un bloc (`bands` ou `lines`), sinon `null`. */
function nomsServis(bloc: Readonly<Record<string, unknown>>, cle: string): readonly string[] | null {
  const brut = bloc[cle];
  if (!Array.isArray(brut)) {
    return null;
  }
  const noms = brut.flatMap((entree) => {
    const nom = texteOuNull(entree);
    return nom === null ? [] : [nom];
  });
  return noms.length === brut.length && noms.length > 0 ? noms : null;
}

/** Paramètres SERVIS du bloc, à plat, verbatim. */
function parametresServis(
  bloc: Readonly<Record<string, unknown>>,
): readonly { readonly label: string; readonly value: string }[] {
  const sortie: { label: string; value: string }[] = [];
  const fenetre = nombreOuNull(bloc['window']);
  if (fenetre !== null) {
    sortie.push({ label: 'fenêtre', value: String(fenetre) });
  }
  const ecarts = texteOuNull(bloc['num_std']) ?? nombreOuNull(bloc['num_std']);
  if (ecarts !== null) {
    sortie.push({ label: 'écarts-types', value: String(ecarts) });
  }
  const fenetres = objetOuNull(bloc['windows']);
  if (fenetres !== null) {
    for (const [nom, valeur] of Object.entries(fenetres)) {
      const nombre = nombreOuNull(valeur);
      if (nombre !== null) {
        sortie.push({ label: `fenêtre ${nom}`, value: String(nombre) });
      }
    }
  }
  return sortie;
}

/**
 * Lit UN bloc d'`indicators.overlays` ou d'`indicators.oscillators`.
 *
 * Trois formes servies, toutes reconnues sans en deviner aucune :
 *   - `points: [{trading_day, value}]` — une ligne (SMA, EMA, RSI) ;
 *   - `points: [{trading_day, lower, middle, upper}]` + `bands` — trois lignes
 *     sur LES MÊMES séances, par construction du serveur ;
 *   - `series: {macd: [...], signal: [...], histogram: [...]}` + `lines` —
 *     trois lignes sur des séances DIFFÉRENTES, que le serveur n'a pas
 *     alignées et que la page n'alignera pas.
 *
 * Un statut autre que `OK` est relayé TEL QUEL avec son détail : une fenêtre
 * plus longue que l'historique (`INSUFFICIENT_SAMPLE`) n'est pas une panne, et
 * l'afficher sur une fenêtre partielle produirait une valeur que le moteur a
 * refusé de calculer.
 */
export function indicatorBlockOf(
  famille: Readonly<Record<string, unknown>> | null | undefined,
  id: string,
): IndicatorBlockView {
  if (famille === null || famille === undefined) {
    return { kind: 'none', id };
  }
  const bloc = objetOuNull(famille[id]);
  if (bloc === null) {
    return { kind: 'none', id };
  }
  const statut = texteOuNull(bloc['status']);
  if (statut === null) {
    return { kind: 'unreadable', id };
  }
  if (statut !== 'OK') {
    return {
      kind: 'refused',
      id,
      status: statut,
      detail: texteOuNull(bloc['detail']) ?? texteOuNull(bloc['reason']),
    };
  }

  const unit = texteOuNull(bloc['unit']);
  if (unit === null) {
    return { kind: 'unreadable', id };
  }

  const lignes: IndicatorLineView[] = [];
  const points = bloc['points'];
  const series = objetOuNull(bloc['series']);
  if (Array.isArray(points) && points.length > 0) {
    const bandes = nomsServis(bloc, 'bands');
    for (const nom of bandes ?? ['value']) {
      const ligne = ligneDePoints(points, nom, nom);
      if (ligne === null) {
        return { kind: 'unreadable', id };
      }
      lignes.push(ligne);
    }
  } else if (series !== null) {
    const noms = nomsServis(bloc, 'lines');
    if (noms === null) {
      return { kind: 'unreadable', id };
    }
    for (const nom of noms) {
      const brut = series[nom];
      if (!Array.isArray(brut) || brut.length === 0) {
        return { kind: 'unreadable', id };
      }
      const ligne = ligneDePoints(brut, 'value', nom);
      if (ligne === null) {
        return { kind: 'unreadable', id };
      }
      lignes.push({ ...ligne, label: nom });
    }
  } else {
    return { kind: 'unreadable', id };
  }

  const premiere = lignes[0];
  if (premiere === undefined) {
    return { kind: 'unreadable', id };
  }
  const aligned = lignes.every(
    (ligne) =>
      ligne.tradingDays.length === premiere.tradingDays.length &&
      ligne.tradingDays.every((jour, index) => jour === premiere.tradingDays[index]),
  );
  const calcul = objetOuNull(bloc['calculation']);
  const dernierJour = premiere.tradingDays[premiere.tradingDays.length - 1] ?? null;

  return {
    kind: 'served',
    id,
    unit,
    method: texteOuNull(bloc['method']),
    parameters: parametresServis(bloc),
    lines: lignes,
    aligned,
    lastTradingDay: dernierJour,
    calculationId: calcul === null ? null : texteOuNull(calcul['calculation_id']),
    engineVersion: calcul === null ? null : texteOuNull(calcul['engine_version']),
  };
}

/** Les blocs d'une famille servie (`overlays` ou `oscillators`), dans l'ordre déclaré. */
export function indicatorFamilyOf(
  indicators: Readonly<Record<string, unknown>> | null | undefined,
  famille: 'overlays' | 'oscillators',
  ids: readonly string[],
): readonly IndicatorBlockView[] {
  const bloc = indicators === null || indicators === undefined ? null : objetOuNull(indicators[famille]);
  return ids.map((id) => indicatorBlockOf(bloc, id));
}
