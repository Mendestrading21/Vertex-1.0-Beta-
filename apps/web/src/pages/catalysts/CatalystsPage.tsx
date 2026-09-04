import { useMemo, useState } from 'react';

import type { CalendarResponse } from '../../api/client.ts';
import { useCalendar } from '../../api/decisionApi.ts';
import { useFollowUpQueue } from '../../api/portfolioApi.ts';
import { pageStateOf } from '../../api/hooks.ts';
import type { PageDataState } from '../../api/hooks.ts';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { Card } from '../../components/Card.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import type { DataState } from '../../components/DataStateBoundary.tsx';
import type { ModuleState } from '../../components/moduleState.ts';
import { calendarEventsOf } from '../calendar/calendarView.ts';
import { CatalystInspector } from './CatalystInspector.tsx';
import {
  AbsentCatalystsModule,
  CategorySplitModule,
  ConflictsModule,
  FiltersModule,
  OrphanThesesModule,
  PortfolioExposureModule,
  RevisionsModule,
  SourcesFreshnessModule,
  UpcomingCountModule,
  WindowModule,
  applyCatalystFilters,
} from './CatalystsModules.tsx';
import type { CatalystFilters } from './CatalystsModules.tsx';
import { CatalystTimeline } from './CatalystTimeline.tsx';
import { catalystsModule } from './catalystsModules.ts';
import { selectCatalysts, selectedCatalystOf } from './catalystsView.ts';
import type { CatalystLink, CatalystSelectionView } from './catalystsView.ts';
import { ReviewQueueSection } from './review/ReviewQueueSection.tsx';
import { queueContentOf } from './review/followUpView.ts';
import type { QueueContentView } from './review/followUpView.ts';

/**
 * Page Catalyseurs (`TL / 10`) — question du contrat des douze pages :
 * « Quels événements vérifiés peuvent modifier la thèse et quand ? »
 *
 * Douzième destination du blueprint, créée au LOT-10. Elle n'invente aucune
 * donnée : elle CROISE deux snapshots déjà publiés et déjà servis —
 * `calendar/global` (agenda, avec son `event_context` qui nomme les thèses et
 * positions touchées) et `review_queue/global` (thèses, échéances,
 * information nouvelle). Aucun nouvel endpoint, aucun nouveau calcul.
 *
 * LOT-A7 — LA PLANCHE §10 EN ENTIER. `pages-09-10-risks-catalysts.png`
 * (moitié droite) compose dix-sept modules. Onze sont SERVIS : les
 * événements reliés (comptes), les révisions, les filtres locaux, la
 * chronologie en DOMINANTE, la répartition par catégorie, l'exposition du
 * registre aux événements, les sources et la fraîcheur, la fenêtre et les
 * deux snapshots, les conflits de version, les thèses sans catalyseur, et
 * la revue des thèses (module LOT-10 entier, inchangé). Six n'ont aucune
 * source : impact moyen, confiance, surprises, historique des surprises,
 * consensus, alertes d'événement — ils tiennent leur place avec le motif de
 * leur absence. Rien n'est pondéré, rien n'est prédit.
 *
 * Elle absorbe l'ancienne destination `/follow-up`
 * (docs/05-design/PAGE_ARBITRATION.md) : une thèse est mise en revue PARCE
 * QU'un catalyseur l'a touchée. La file de revue reste le module qui suit
 * la chronologie, et garde sa question (règle 4).
 *
 * Ne pas confondre avec Calendrier (§11) : Calendrier sert TOUT l'agenda dans
 * une fenêtre temporelle et son fuseau ; Catalyseurs n'en sert que la part
 * reliée à une thèse ou à une position. Un seul propriétaire de donnée, deux
 * questions — jamais deux vérités.
 *
 * L'inspecteur contextuel du shell (point 6) n'existe que si un catalyseur
 * est RÉELLEMENT sélectionné et toujours servi : aucune colonne morte, aucun
 * panneau par défaut sur cette page.
 *
 * Les deux requêtes sont INDÉPENDANTES et leurs états ne sont pas fondus :
 * si l'agenda répond et pas la file, la chronologie s'affiche et le module de
 * revue affiche SON état dégradé. Fondre les deux masquerait laquelle des
 * deux sources manque.
 */

/** État du cadre de la timeline, dérivé du seul snapshot d'agenda. */
export function catalystFrameStateOf(
  queryState: PageDataState,
  agendaState: string | undefined,
): DataState | 'auth-required' {
  if (queryState !== 'ready' && queryState !== 'refreshing') {
    return queryState;
  }
  if (agendaState === undefined) {
    return 'error';
  }
  if (agendaState === 'empty' || agendaState === 'empty_window') {
    return 'empty';
  }
  if (agendaState === 'stale') {
    return 'stale';
  }
  // Dégradation signalée PAR LE SERVEUR. `not_entitled` et `rejected` ne sont
  // pas des états « partiels » : rien n'est servi, donc rien n'est affiché.
  if (agendaState === 'not_entitled' || agendaState === 'rejected') {
    return 'error';
  }
  if (agendaState === 'degraded') {
    return 'partial';
  }
  return queryState;
}

const NO_FILTERS: CatalystFilters = { hiddenCategories: new Set(), hiddenLinks: new Set() };

function TimelineModule({
  data,
  frameState,
  selection,
  shown,
  selectedEventId,
  onSelect,
}: {
  readonly data: CalendarResponse | undefined;
  readonly frameState: DataState | 'auth-required';
  readonly selection: CatalystSelectionView | null;
  readonly shown: CatalystSelectionView['catalysts'];
  readonly selectedEventId: string | null;
  readonly onSelect: (eventId: string) => void;
}) {
  const module = catalystsModule('timeline');
  return (
    <Card
      rank="dominant"
      kicker="Ordre publié"
      title={module.title}
      titleId="vx-cat-timeline-title"
      className="vx-cat-timeline-card"
      aside={selection === null ? undefined : <>{shown.length} sur {selection.catalysts.length} événement(s) relié(s)</>}
      footer={<>seuls les événements que le snapshot relie à une thèse déclarée ou à une position du registre manuel figurent ici</>}
    >
      {frameState === 'empty' ? (
        <DataStateBoundary
          state="empty"
          detail={
            data?.reason !== null && data?.reason !== undefined
              ? `Aucun agenda publié — raison serveur : ${data.reason}`
              : "Aucun agenda publié par le worker : aucun catalyseur ne peut être relié."
          }
        />
      ) : selection === null ? (
        <DataStateBoundary
          state={frameState === 'auth-required' ? 'error' : frameState}
          {...(frameState === 'offline'
            ? { detail: "L'API locale est injoignable — aucun catalyseur affiché." }
            : frameState === 'error'
              ? { detail: "Agenda absent, refusé ou sans droit — rien n'est reconstruit à la place." }
              : {})}
        />
      ) : (
        <DataStateBoundary
          state={frameState === 'auth-required' ? 'error' : frameState}
          {...(frameState === 'partial'
            ? { detail: 'Couverture incomplète signalée par le serveur : la chronologie ne montre que les événements réellement servis.' }
            : {})}
          {...(data?.as_of !== null && data?.as_of !== undefined ? { asOfLabel: data.as_of } : {})}
        >
          <CatalystTimeline catalysts={shown} unlinkedCount={selection.unlinkedCount} selectedEventId={selectedEventId} onSelect={onSelect} />
        </DataStateBoundary>
      )}
    </Card>
  );
}

function CatalystsBoard({
  data,
  frameState,
  selection,
  queueView,
}: {
  readonly data: CalendarResponse | undefined;
  readonly frameState: DataState | 'auth-required';
  readonly selection: CatalystSelectionView | null;
  readonly queueView: QueueContentView | null;
}) {
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [filters, setFilters] = useState<CatalystFilters>(NO_FILTERS);
  const moduleState: ModuleState = frameState === 'auth-required' ? 'auth-required' : frameState;
  const shown = useMemo(() => (selection === null ? [] : applyCatalystFilters(selection.catalysts, filters)), [selection, filters]);
  const selected = selectedCatalystOf(selection, selectedEventId);

  function toggleCategory(category: string): void {
    setFilters((previous) => {
      const next = new Set(previous.hiddenCategories);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return { ...previous, hiddenCategories: next };
    });
  }

  function toggleLink(link: CatalystLink): void {
    setFilters((previous) => {
      const next = new Set(previous.hiddenLinks);
      if (next.has(link)) {
        next.delete(link);
      } else {
        next.add(link);
      }
      return { ...previous, hiddenLinks: next };
    });
  }

  return (
    <>
      <div className="vx-cat-grid vx-board" data-testid="catalysts-grid">
        <UpcomingCountModule selection={selection} state={moduleState} reason={data?.reason ?? null} />
        <AbsentCatalystsModule id="mean-impact" />
        <AbsentCatalystsModule id="confidence" />
        <RevisionsModule selection={selection} state={moduleState} />

        <FiltersModule selection={selection} state={moduleState} filters={filters} onToggleCategory={toggleCategory} onToggleLink={toggleLink} shown={shown.length} />
        <AbsentCatalystsModule id="surprises" />
        <AbsentCatalystsModule id="consensus" />

        <div data-module="timeline">
          <TimelineModule
            data={data}
            frameState={frameState}
            selection={selection}
            shown={shown}
            selectedEventId={selectedEventId}
            onSelect={(eventId) => {
              setSelectedEventId((previous) => (previous === eventId ? null : eventId));
            }}
          />
        </div>
        <CategorySplitModule selection={selection} state={moduleState} />
        <AbsentCatalystsModule id="surprise-history" />

        <PortfolioExposureModule selection={selection} state={moduleState} />
        <AbsentCatalystsModule id="event-alerts" />
        <SourcesFreshnessModule selection={selection} state={moduleState} />

        <WindowModule data={data} populationTheses={queueView?.populationTheses ?? null} state={moduleState} />
        <ConflictsModule selection={selection} state={moduleState} />
        <OrphanThesesModule theses={selection === null ? null : selection.thesesWithoutCatalyst} state={moduleState} />

        <div data-module="review">
          <ReviewQueueSection />
        </div>
      </div>

      {/*
        L'inspecteur n'existe que si un catalyseur est RÉELLEMENT
        sélectionné et toujours servi. Une sélection qui ne correspond
        plus à rien (snapshot rafraîchi, événement disparu) ne laisse
        pas un panneau figé : elle ne rend rien.
      */}
      {selected !== null ? <CatalystInspector catalyst={selected} /> : null}
    </>
  );
}

export function CatalystsPage() {
  const calendarQuery = useCalendar(null);
  const queueQuery = useFollowUpQueue();

  const calendarState = pageStateOf(calendarQuery);
  const frameState = catalystFrameStateOf(calendarState, calendarQuery.data?.state);

  // La file de revue est LUE ici pour l'appariement, mais son état reste
  // celui du module : une file absente ne fait pas disparaître la timeline.
  const queueView =
    queueQuery.data !== undefined && queueQuery.data.state !== 'empty'
      ? queueContentOf(queueQuery.data.content)
      : null;

  const selection: CatalystSelectionView | null =
    calendarQuery.data !== undefined && frameState !== 'empty' && frameState !== 'error'
      ? selectCatalysts(calendarEventsOf(calendarQuery.data.agenda), queueView?.theses ?? [])
      : null;

  return (
    <article className="vx-page" aria-labelledby="vx-page-title-catalysts">
      <div className="vx-page-header">
        <h1 id="vx-page-title-catalysts">Catalyseurs</h1>
        <p className="vx-page-question">
          Quels événements vérifiés peuvent modifier la thèse et quand ?
        </p>
      </div>

      {calendarState === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : (
        <CatalystsBoard data={calendarQuery.data} frameState={frameState} selection={selection} queueView={queueView} />
      )}
    </article>
  );
}
