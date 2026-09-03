import { Link } from 'react-router-dom';

import type { CalendarResponse } from '../../api/client.ts';
import { AbsentModule } from '../../components/AbsentModule.tsx';
import { Card } from '../../components/Card.tsx';
import { CensusBars } from '../../components/CensusBars.tsx';
import type { CensusEntry } from '../../components/CensusBars.tsx';
import { Metric } from '../../components/Metric.tsx';
import { MODULE_STATE_LABELS } from '../../components/moduleState.ts';
import type { ModuleState } from '../../components/moduleState.ts';
import { AgendaLine } from '../../components/calendar/AgendaLine.tsx';
import { VERSION_STATE_CONFLICTING, categoryLabelOf } from '../calendar/calendarView.ts';
import { catalystsModule } from './catalystsModules.ts';
import { LINK_LABELS } from './catalystsView.ts';
import type { CatalystLink, CatalystSelectionView, CatalystView } from './catalystsView.ts';
import type { ThesisEntryView } from './review/followUpView.ts';

/**
 * Les modules SERVIS de la planche §10, hors la dominante (la chronologie,
 * portée par la page) et hors la revue des thèses (module LOT-10 entier,
 * conservé tel quel dans sa cellule). Tous lisent la même sélection —
 * l'agenda publié croisé avec la file de revue publiée — et n'en tirent que
 * des DÉNOMBREMENTS et des listes : aucun impact, aucune confiance, aucun
 * consensus, aucune surprise n'est fabriqué.
 */

export function AbsentCatalystsModule({ id }: { readonly id: string }) {
  const module = catalystsModule(id);
  if (module.status.kind !== 'absent') {
    throw new Error(`Module ${id} is served, not absent`);
  }
  return (
    <div data-module={id}>
      <AbsentModule title={module.title} question={module.question} reason={module.status.reason} note={module.status.note} />
    </div>
  );
}

/**
 * Ce qu'un module de sélection montre quand l'agenda n'est pas lisible.
 * L'état est DIT en clair, sans `data-state` : sur cette page, les deux
 * frontières `data-state` sont celles des deux sources (chronologie et
 * revue) — le témoin e2e « propre à CHAQUE source » compte exactement deux.
 */
export function SelectionAbsence({ state, withReason = false, reason = null }: { readonly state: ModuleState; readonly withReason?: boolean; readonly reason?: string | null }) {
  if (state === 'empty') {
    return (
      <p className="vx-module-sentence" role="status">
        {withReason
          ? `Aucun agenda publié${reason !== null ? ` — raison serveur : ${reason}` : ' par le worker : aucun catalyseur ne peut être relié'}.`
          : 'Aucun agenda publié : rien à relier (voir la chronologie).'}
      </p>
    );
  }
  if (state === 'ready' || state === 'refreshing') {
    return null;
  }
  return (
    <p className="vx-module-sentence" role="status">
      Agenda non lisible — {MODULE_STATE_LABELS[state].toLowerCase()} : rien à relier (voir la chronologie).
    </p>
  );
}

function censusOf(keys: readonly string[], labelOf: (key: string) => string = (key) => key): readonly CensusEntry[] {
  const counts = new Map<string, number>();
  for (const key of keys) {
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .map(([key, count]) => ({ key, label: labelOf(key), count }));
}

// ---------------------------------------------------------------------------

export function UpcomingCountModule({
  selection,
  state,
  reason,
}: {
  readonly selection: CatalystSelectionView | null;
  readonly state: ModuleState;
  readonly reason: string | null;
}) {
  const module = catalystsModule('upcoming-count');
  return (
    <Card rank="quiet" kicker="Agenda × file de revue" title={module.title} titleId="vx-cat-count-title" footer={<>reliés par le contexte croisé publié ; les non reliés restent sur Calendrier</>}>
      {selection === null ? (
        // La raison serveur n'est écrite qu'UNE fois sur la page : dans la
        // chronologie (dominante). Ici, seul l'état est nommé.
        <SelectionAbsence state={state} reason={reason} />
      ) : (
        <div className="vx-metrics-row" data-testid="cat-count">
          <Metric label="Reliés" value={String(selection.catalysts.length)} testId="cat-count-linked" />
          <Metric label="Non reliés" value={String(selection.unlinkedCount)} note="servis, non comptés comme catalyseurs" size="compact" />
          <Metric label="Thèses orphelines" value={String(selection.thesesWithoutCatalyst.length)} size="compact" />
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function RevisionsModule({ selection, state }: { readonly selection: CatalystSelectionView | null; readonly state: ModuleState }) {
  const module = catalystsModule('revisions');
  const revised = selection === null ? [] : selection.catalysts.filter((entry) => entry.event.revised);
  return (
    <Card rank="quiet" kicker="Publiées par la source" title={module.title} titleId="vx-cat-revisions-title" footer={<>drapeau et détail sont deux champs distincts du snapshot ; aucune direction de révision n’est déduite</>}>
      {selection === null ? (
        <SelectionAbsence state={state} />
      ) : (
        <>
          <Metric label="Événements reliés révisés" value={String(revised.length)} note={`sur ${selection.catalysts.length} relié(s)`} testId="cat-revisions-count" />
          {revised.length > 0 ? (
            <ul className="vx-inspector-list" data-testid="cat-revisions">
              {revised.map(({ event }) => (
                <li key={event.eventId}>
                  <code>{event.ticker ?? event.eventId}</code> {event.title ?? ''}
                  <span className="vx-inspector-unit"> — {event.revisions.length > 0 ? `${event.revisions.length} révision(s) publiée(s)` : 'détail non publié'}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export interface CatalystFilters {
  readonly hiddenCategories: ReadonlySet<string>;
  readonly hiddenLinks: ReadonlySet<CatalystLink>;
}

export function applyCatalystFilters(catalysts: readonly CatalystView[], filters: CatalystFilters): readonly CatalystView[] {
  return catalysts.filter(
    (entry) => !filters.hiddenCategories.has(entry.event.category) && entry.links.some((link) => !filters.hiddenLinks.has(link)),
  );
}

export function FiltersModule({
  selection,
  state,
  filters,
  onToggleCategory,
  onToggleLink,
  shown,
}: {
  readonly selection: CatalystSelectionView | null;
  readonly state: ModuleState;
  readonly filters: CatalystFilters;
  readonly onToggleCategory: (category: string) => void;
  readonly onToggleLink: (link: CatalystLink) => void;
  readonly shown: number;
}) {
  const module = catalystsModule('filters');
  const categories = selection === null ? [] : [...new Set(selection.catalysts.map((entry) => entry.event.category))].sort();
  return (
    <Card rank="quiet" kicker="Affichage local" title={module.title} titleId="vx-cat-filters-title" footer={<>un filtre masque, il ne reclasse pas ; le snapshot servi reste entier</>}>
      {selection === null ? (
        <SelectionAbsence state={state} />
      ) : (
        <>
          <div className="vx-matrix-filters vx-opp-filters" role="group" aria-label="Catégories affichées" data-testid="cat-filter-categories">
            {categories.map((category) => (
              <button
                key={category}
                type="button"
                className="vx-legend-chip"
                aria-pressed={!filters.hiddenCategories.has(category)}
                onClick={() => {
                  onToggleCategory(category);
                }}
              >
                {categoryLabelOf(category)}
              </button>
            ))}
          </div>
          <div className="vx-matrix-filters vx-opp-filters" role="group" aria-label="Liens affichés" data-testid="cat-filter-links">
            {(['thesis', 'position'] as const).map((link) => (
              <button
                key={link}
                type="button"
                className="vx-legend-chip"
                aria-pressed={!filters.hiddenLinks.has(link)}
                onClick={() => {
                  onToggleLink(link);
                }}
              >
                {LINK_LABELS[link]}
              </button>
            ))}
          </div>
          <p className="vx-matrix-count" role="status" data-testid="cat-filter-count">
            {shown} affiché(s) sur {selection.catalysts.length} relié(s)
          </p>
        </>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function CategorySplitModule({ selection, state }: { readonly selection: CatalystSelectionView | null; readonly state: ModuleState }) {
  const module = catalystsModule('category-split');
  return (
    <Card rank="quiet" kicker="Dénombrement" title={module.title} titleId="vx-cat-split-title" footer={<>comptes d’événements reliés par catégorie publiée ; aucune pondération</>}>
      {selection === null ? (
        <SelectionAbsence state={state} />
      ) : (
        <CensusBars
          entries={censusOf(
            selection.catalysts.map((entry) => entry.event.category),
            (key) => categoryLabelOf(key),
          )}
          ariaLabel="Événements reliés par catégorie"
          testIdPrefix="cat-split"
          emptyLabel="Aucun événement relié."
        />
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------

const EXPOSURE_LINES = 6;

export function PortfolioExposureModule({ selection, state }: { readonly selection: CatalystSelectionView | null; readonly state: ModuleState }) {
  const module = catalystsModule('portfolio-exposure');
  const exposed = selection === null ? [] : selection.catalysts.filter((entry) => entry.positions.length > 0);
  return (
    <Card
      rank="quiet"
      kicker="Registre manuel"
      title={module.title}
      titleId="vx-cat-exposure-title"
      footer={
        <>
          positions déclarées par vous, nommées par le contexte croisé du snapshot ; <Link to="/portfolio">voir Portefeuille</Link>
        </>
      }
    >
      {selection === null ? (
        <SelectionAbsence state={state} />
      ) : exposed.length === 0 ? (
        <p className="vx-module-sentence" role="status" data-testid="cat-exposure-empty">
          Aucun événement relié ne touche une position déclarée.
        </p>
      ) : (
        <ul className="vx-cat-exposure-list" aria-label="Événements touchant une position déclarée" data-testid="cat-exposure">
          {exposed.slice(0, EXPOSURE_LINES).map(({ event, positions }) => (
            <li key={event.eventId} className="vx-cat-exposure-line">
              {/* Une liste imbriquée : la ligne d'agenda reste un `li` dans un `ul`, jamais un `li` nu dans un `li`. */}
              <ul className="vx-agenda-mini">
                <AgendaLine event={event} />
              </ul>
              <span className="vx-inspector-unit">
                positions {positions.map((identifier) => `#${identifier}`).join(', ')}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function SourcesFreshnessModule({ selection, state }: { readonly selection: CatalystSelectionView | null; readonly state: ModuleState }) {
  const module = catalystsModule('sources-freshness');
  return (
    <Card rank="quiet" kicker="Dénombrement" title={module.title} titleId="vx-cat-sources-title" footer={<>sources et fraîcheur telles que publiées par événement ; aucun délai mesuré ici</>}>
      {selection === null ? (
        <SelectionAbsence state={state} />
      ) : (
        <>
          <CensusBars
            entries={censusOf(selection.catalysts.map((entry) => entry.event.source ?? 'source non publiée'))}
            ariaLabel="Événements reliés par source"
            testIdPrefix="cat-source"
            emptyLabel="Aucun événement relié."
          />
          <CensusBars
            entries={censusOf(
              selection.catalysts.map((entry) => (entry.event.fresh === true ? 'fresh' : entry.event.fresh === false ? 'stale' : 'unknown')),
              (key) => (key === 'fresh' ? 'fraîche' : key === 'stale' ? 'périmée' : 'fraîcheur non publiée'),
            )}
            ariaLabel="Événements reliés par fraîcheur publiée"
            testIdPrefix="cat-fresh"
            emptyLabel="Aucun événement relié."
          />
        </>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function WindowModule({
  data,
  populationTheses,
  state,
}: {
  readonly data: CalendarResponse | undefined;
  readonly populationTheses: string | null;
  readonly state: ModuleState;
}) {
  const module = catalystsModule('window');
  return (
    <Card rank="quiet" kicker="Deux snapshots" title={module.title} titleId="vx-cat-window-title" footer={<>populations séparées, jamais additionnées ; leur croisement ne crée aucune donnée nouvelle</>}>
      {data === undefined ? (
        <SelectionAbsence state={state} />
      ) : (
        <>
          <dl className="vx-inspector-facts" data-testid="cat-window">
            <div>
              <dt>Snapshot d’agenda</dt>
              <dd>
                v{data.snapshot_version ?? '—'} · {data.as_of !== null ? <time dateTime={data.as_of}>{data.as_of}</time> : 'as_of non publié'}
              </dd>
            </div>
            <div>
              <dt>Fenêtre</dt>
              <dd>
                {data.window.from_utc ?? '—'} → {data.window.to_utc ?? '—'} · {data.window.events_in_window} sur {data.window.events_total} événement(s)
              </dd>
            </div>
            <div>
              <dt>État servi</dt>
              <dd>
                <code>{data.state}</code>
                {data.reason !== null ? <span className="vx-inspector-unit"> — {data.reason}</span> : null}
              </dd>
            </div>
          </dl>
          <p className="vx-cat-populations" role="note" data-testid="cat-populations">
            Populations séparées, jamais additionnées — agenda : <code>{data.population ?? '—'}</code> · thèses :{' '}
            <code>{populationTheses ?? '—'}</code>. Les deux snapshots sont indépendants ; leur croisement ne crée aucune donnée
            nouvelle.
          </p>
        </>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function ConflictsModule({ selection, state }: { readonly selection: CatalystSelectionView | null; readonly state: ModuleState }) {
  const module = catalystsModule('conflicts');
  const conflicting = selection === null ? [] : selection.catalysts.filter((entry) => entry.event.versionState === VERSION_STATE_CONFLICTING);
  const rejected = selection === null ? [] : selection.catalysts.filter((entry) => entry.event.rejectedRevisions.length > 0);
  return (
    <Card rank="quiet" kicker="Publiés par le worker" title={module.title} titleId="vx-cat-conflicts-title" footer={<>un conflit n’est jamais résolu ici : la version affichée suit l’ordre stable publié</>}>
      {selection === null ? (
        <SelectionAbsence state={state} />
      ) : (
        <div className="vx-metrics-row" data-testid="cat-conflicts">
          <Metric label="Versions en conflit" value={String(conflicting.length)} size="compact" testId="cat-conflicts-versions" />
          <Metric label="Révisions rejetées" value={String(rejected.length)} size="compact" testId="cat-conflicts-rejected" />
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function OrphanThesesModule({ theses, state }: { readonly theses: readonly ThesisEntryView[] | null; readonly state: ModuleState }) {
  const module = catalystsModule('orphan-theses');
  return (
    <Card
      rank="quiet"
      kicker="Fait de couverture"
      title={module.title}
      titleId="vx-cat-orphans-title"
      className="vx-cat-orphans"
      {...(theses === null ? {} : { 'aside': <>{theses.length}</> })}
      footer={<>l’absence d’événement publié ne signifie pas qu’aucun événement n’existe — un fait de couverture, pas un verdict</>}
    >
      {theses === null ? (
        <SelectionAbsence state={state} />
      ) : theses.length === 0 ? (
        <p className="vx-module-sentence" role="status" data-testid="cat-orphans-empty">
          Chaque thèse déclarée est touchée par au moins un événement servi.
        </p>
      ) : (
        <ul data-testid="cat-orphans">
          {theses.map((thesis) => (
            <li key={thesis.id} data-testid={`cat-orphan-${thesis.id}`}>
              {thesis.title}
              {thesis.instrumentTicker !== null ? <code>{thesis.instrumentTicker}</code> : null}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
