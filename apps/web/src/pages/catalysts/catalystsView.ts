/**
 * Sélection des catalyseurs — la SEULE logique propre à cette page.
 *
 * Contrat des douze pages, §10 : « quels événements vérifiés peuvent modifier
 * LA THÈSE et quand ? ». Un catalyseur est donc un événement de l'agenda
 * publié qui touche une thèse déclarée ou une position du registre manuel.
 *
 * Ce module ne fait qu'une chose : FILTRER et APPARIER. Il ne calcule aucune
 * importance, aucun score, aucune probabilité, ne réordonne rien et
 * n'invente aucun lien. L'ordre servi par le worker est conservé tel quel —
 * `.claude/rules/frontend.md` interdit de reconstruire un classement côté
 * navigateur, et `.claude/rules/architecture.md` réserve toute autorité de
 * calcul à `vertex_core`.
 *
 * Distinction avec Calendrier (§11, « que se passe-t-il dans ma fenêtre
 * temporelle et dans quel fuseau ? ») : Calendrier sert TOUT l'agenda ;
 * Catalyseurs n'en sert que la part reliée à une thèse ou une position. Même
 * donnée, même propriétaire, deux questions — jamais deux vérités.
 */
import type { CalendarEventView } from '../calendar/calendarView.ts';
import type { ThesisEntryView } from './review/followUpView.ts';

/** Motif par lequel un événement est retenu comme catalyseur. */
export type CatalystLink = 'thesis' | 'position';

export interface CatalystThesisView {
  readonly thesisId: number | null;
  readonly title: string | null;
  readonly status: string | null;
  /**
   * `true` quand la thèse citée par l'événement est aussi présente dans la
   * file de revue publiée. `false` quand elle ne l'est pas : l'événement
   * nomme alors une thèse que le snapshot de revue ne contient pas, et c'est
   * dit, jamais comblé.
   */
  readonly knownInQueue: boolean;
  /** Échéance de revue EFFECTIVE, telle que publiée. Jamais recalculée. */
  readonly effectiveReviewDueAt: string | null;
  /** La revue est-elle due ? Drapeau serveur, jamais dérivé d'une date ici. */
  readonly isDue: boolean;
  /** Information nouvelle signalée PAR LE SERVEUR sur cette thèse. */
  readonly hasNewInformation: boolean;
}

export interface CatalystView {
  readonly event: CalendarEventView;
  /** Motifs de rétention, dans l'ordre `thesis` puis `position`. */
  readonly links: readonly CatalystLink[];
  readonly theses: readonly CatalystThesisView[];
  readonly positions: readonly number[];
}

export interface CatalystSelectionView {
  readonly catalysts: readonly CatalystView[];
  /** Événements de l'agenda servis mais NON reliés — comptés, jamais montrés. */
  readonly unlinkedCount: number;
  /** Thèses de la file qu'AUCUN événement servi ne touche. */
  readonly thesesWithoutCatalyst: readonly ThesisEntryView[];
}

/**
 * Apparie l'agenda publié et la file de revue publiée.
 *
 * `theses` peut être vide : la page reste alors honnête — aucun catalyseur ne
 * sera retenu par le motif `thesis`, et rien n'est inventé pour compenser.
 */
export function selectCatalysts(
  events: readonly CalendarEventView[],
  theses: readonly ThesisEntryView[],
): CatalystSelectionView {
  const queueById = new Map<number, ThesisEntryView>();
  for (const entry of theses) {
    queueById.set(entry.id, entry);
  }

  const catalysts: CatalystView[] = [];
  const touchedThesisIds = new Set<number>();
  let unlinkedCount = 0;

  for (const event of events) {
    const links: CatalystLink[] = [];
    if (event.context.theses.length > 0) {
      links.push('thesis');
    }
    if (event.context.positions.length > 0) {
      links.push('position');
    }
    if (links.length === 0) {
      unlinkedCount += 1;
      continue;
    }

    const liees = event.context.theses.map((reference): CatalystThesisView => {
      const known = reference.thesisId === null ? undefined : queueById.get(reference.thesisId);
      if (reference.thesisId !== null && known !== undefined) {
        touchedThesisIds.add(reference.thesisId);
      }
      return {
        thesisId: reference.thesisId,
        // Le titre et le statut viennent de l'ÉVÉNEMENT. Ils ne sont pas
        // remplacés par ceux de la file : deux snapshots distincts peuvent
        // diverger, et masquer la divergence serait fabriquer une cohérence.
        title: reference.title,
        status: reference.status,
        knownInQueue: known !== undefined,
        effectiveReviewDueAt: known?.effectiveReviewDueAt ?? null,
        isDue: known?.isDue ?? false,
        hasNewInformation: known?.hasNewInformation ?? false,
      };
    });

    catalysts.push({
      event,
      links,
      theses: liees,
      positions: event.context.positions,
    });
  }

  return {
    catalysts,
    unlinkedCount,
    thesesWithoutCatalyst: theses.filter((entry) => !touchedThesisIds.has(entry.id)),
  };
}

/** Libellé du motif de rétention — jamais une couleur seule. */
export const LINK_LABELS: Readonly<Record<CatalystLink, string>> = {
  thesis: 'thèse liée',
  position: 'position liée',
};

/**
 * Résout l'identifiant sélectionné en catalyseur SERVI, ou `null`.
 *
 * La page ne mémorise qu'un identifiant, jamais un objet : si le snapshot est
 * rafraîchi et que l'événement n'y est plus, il n'y a plus rien à inspecter —
 * et l'inspecteur ne doit pas rester figé sur une donnée qui n'est plus
 * servie. Garder l'objet aurait affiché indéfiniment un état périmé sans le
 * dire, ce que l'article 17 interdit.
 */
export function selectedCatalystOf(
  selection: CatalystSelectionView | null,
  selectedEventId: string | null,
): CatalystView | null {
  if (selection === null || selectedEventId === null) {
    return null;
  }
  return selection.catalysts.find((entry) => entry.event.eventId === selectedEventId) ?? null;
}
