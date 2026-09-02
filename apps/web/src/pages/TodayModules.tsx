import { Link } from 'react-router-dom';

import { useCalendar, useOpportunities } from '../api/decisionApi.ts';
import { pageStateOf, useCapabilities, useMarketsOverview } from '../api/hooks.ts';
import { usePortfolio } from '../api/portfolioApi.ts';
import { Card } from '../components/Card.tsx';
import { FreshnessBadge } from '../components/FreshnessBadge.tsx';
import { Metric } from '../components/Metric.tsx';
import { SectorGrid } from '../components/markets/SectorGrid.tsx';
import { frDecimal } from '../components/markets/marketsView.ts';
import { StatusBadge } from '../components/StatusBadge.tsx';
import { AgendaLine, readableEventTime } from '../components/calendar/AgendaLine.tsx';
import { ModuleStatus } from '../components/ModuleStatus.tsx';
import { moduleShowsContent, moduleStateOf } from '../components/moduleState.ts';
import type { ModuleState } from '../components/moduleState.ts';
import { statusLabelOf } from './calendar/calendarView.ts';
import { opportunitiesFrameStateOf } from './opportunities/opportunitiesView.ts';
import { valuationContentOf } from './portfolio/portfolioView.ts';
import {
  capabilityStatusCensus,
  leadingAgenda,
  opportunitiesSummaryOf,
  portfolioSummaryOf,
  todayModule,
} from './todayView.ts';

/**
 * Les modules SERVIS de la planche §1, hors la dominante. Chacun lit son
 * propre snapshot par le hook existant de la page propriétaire, dit son état
 * à sa place et ne montre AUCUNE valeur hors des états qui en portent une.
 * Aucun calcul : chaînes serveur, comptes publiés, ordre publié.
 */

function publie(value: string | number | null | undefined): string {
  return value === null || value === undefined || value === '' ? 'non publié' : String(value);
}

function signOf(value: string | null): 'up' | 'down' | 'flat' | null {
  if (value === null) {
    return null;
  }
  if (value.startsWith('-')) {
    return 'down';
  }
  if (value.startsWith('+') || /^[1-9]/.test(value)) {
    return 'up';
  }
  return 'flat';
}

// ---------------------------------------------------------------------------

export function GlobalMarketModule() {
  const query = useMarketsOverview();
  const state = moduleStateOf(pageStateOf(query), query.data);
  const data = query.data;
  const module = todayModule('global-market');
  const breadth = data?.breadth ?? null;
  const coverage = data?.coverage ?? null;
  return (
    <Card
      rank="quiet"
      kicker="Snapshot Marchés"
      title={module.title}
      titleId="vx-today-global-market-title"
      className="vx-today-module"
      {...(data?.as_of !== null && data?.as_of !== undefined && moduleShowsContent(state)
        ? { footer: <>as_of {data.as_of} · population {publie(data.population)}</> }
        : {})}
    >
      <ModuleStatus state={state} raw={state === 'closed' ? data?.state : data?.reason} />
      {moduleShowsContent(state) && data !== undefined ? (
        <>
          <div className="vx-metrics-row">
            <Metric
              label="Breadth"
              value={breadth !== null && breadth.status === 'OK' ? frDecimal(breadth.value_pct ?? '') : null}
              unit="%"
              absentLabel={
                breadth === null
                  ? 'Breadth non publiée'
                  : `Breadth non calculable : ${breadth.reason ?? 'raison non publiée'}`
              }
              {...(breadth !== null
                ? { note: `${breadth.above_count} en hausse sur ${breadth.covered_count} couverts` }
                : {})}
            />
            <Metric
              label="Couverture"
              value={coverage === null ? null : `${coverage.covered}/${coverage.expected}`}
              {...(coverage !== null ? { note: `${coverage.discarded} écartés` } : {})}
            />
          </div>
          <p className="vx-module-sentence" data-testid="today-market-conclusion">
            {data.conclusion ?? 'Aucune conclusion publiée.'}
          </p>
        </>
      ) : null}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function NextCatalystModule() {
  const query = useCalendar(null);
  const state = moduleStateOf(pageStateOf(query), query.data);
  const data = query.data;
  const module = todayModule('next-catalyst');
  const first = data === undefined ? null : (leadingAgenda(data.agenda, 1)[0] ?? null);
  return (
    <Card
      rank="quiet"
      kicker="Agenda publié"
      title={module.title}
      titleId="vx-today-next-catalyst-title"
      className="vx-today-module"
      {...(moduleShowsContent(state) && data !== undefined
        ? { footer: <>snapshot v{publie(data.snapshot_version)} · as_of {publie(data.as_of)}</> }
        : {})}
    >
      <ModuleStatus state={state} raw={state === 'closed' ? data?.state : data?.reason} />
      {moduleShowsContent(state) && data !== undefined ? (
        first === null ? (
          <p className="vx-module-sentence" role="status">
            Agenda publié sans aucun événement — rien n&apos;est inventé à la place.
          </p>
        ) : (
          <>
            <Metric
              label="Premier de l’agenda publié"
              value={readableEventTime(first)}
              size="compact"
              {...(first.exchangeTimezone !== null ? { unit: first.exchangeTimezone } : {})}
              note={
                <>
                  {first.ticker === null ? 'sans instrument' : <code>{first.ticker}</code>} ·{' '}
                  {statusLabelOf(first.status)} · importance{' '}
                  <code>{first.importance.code ?? 'non publiée'}</code>
                </>
              }
            />
            <p className="vx-module-sentence">{first.title ?? 'titre non publié'}</p>
          </>
        )
      ) : null}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function SourceHealthModule() {
  const query = useCapabilities();
  const queryState = pageStateOf(query);
  const data = query.data;
  const state: ModuleState =
    queryState !== 'ready' && queryState !== 'refreshing' ? queryState : data === undefined ? 'error' : queryState;
  const module = todayModule('source-health');
  const census = data === undefined ? null : capabilityStatusCensus(data.capabilities);
  return (
    <Card
      rank="quiet"
      kicker="Capacités testées"
      title={module.title}
      titleId="vx-today-source-health-title"
      className="vx-today-module"
      {...(data !== undefined ? { footer: <>snapshot v{publie(data.snapshot_version)} · as_of {publie(data.as_of)}</> } : {})}
    >
      <ModuleStatus state={state} />
      {data !== undefined ? (
        <>
          <p className="vx-health-strip" role="status">
            <span className="vx-health-strip-item" data-health={data.health.db.status}>
              <span className="vx-health-strip-label">Base locale</span>
              <strong>{data.health.db.status === 'ok' ? 'Disponible' : 'Erreur'}</strong>
            </span>
            <span className="vx-health-strip-item">
              <span className="vx-health-strip-label">Worker · {data.health.worker.method}</span>
              {data.health.worker.last_snapshot_as_of === null ? (
                <strong>Aucun snapshot observé</strong>
              ) : (
                <FreshnessBadge ageSeconds={data.health.worker.age_seconds} sourceLabel="dernier snapshot" />
              )}
            </span>
          </p>
          <ul className="vx-status-census" aria-label="Capacités par statut testé">
            {census === null
              ? null
              : [...census.entries()].map(([status, count]) => (
                  <li key={status}>
                    <StatusBadge status={status} />
                    <span className="vx-status-census-count">{count}</span>
                  </li>
                ))}
          </ul>
          <p className="vx-module-sentence">
            {data.total} capacités déclarées ·{' '}
            <Link to="/sources-reports">voir Sources &amp; Rapports</Link>
          </p>
        </>
      ) : null}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function OpportunitiesModule() {
  const query = useOpportunities();
  const frame = opportunitiesFrameStateOf(pageStateOf(query), query.data);
  const module = todayModule('opportunities');
  const summary = frame.view === null ? null : opportunitiesSummaryOf(frame.view);
  const state: ModuleState = frame.state;
  return (
    <Card
      rank="quiet"
      kicker="Moteur fail-closed"
      title={module.title}
      titleId="vx-today-opportunities-title"
      className="vx-today-module"
      {...(summary !== null
        ? {
            footer: (
              <>
                ordre publié : {publie(summary.orderingMethod)} ·{' '}
                <Link to="/opportunities">voir toutes les opportunités</Link>
              </>
            ),
          }
        : {})}
    >
      <ModuleStatus state={state} raw={frame.detail ?? query.data?.reason} />
      {summary !== null ? (
        <>
          <div className="vx-metrics-row">
            <Metric label="Qualifiés" value={summary.qualifiedCount === null ? null : String(summary.qualifiedCount)} />
            <Metric label="Exclus" value={summary.excludedCount === null ? null : String(summary.excludedCount)} />
            <Metric label="Univers" value={summary.universeSize === null ? null : String(summary.universeSize)} />
          </div>
          {summary.qualified.length === 0 ? (
            <p className="vx-module-sentence" role="status">
              Aucun candidat qualifié : chaque candidat est fermé par une gate, avec sa raison publiée
              {summary.statusCounts.size > 0 ? (
                <>
                  {' '}
                  (
                  {[...summary.statusCounts.entries()]
                    .map(([status, count]) => `${status} × ${count}`)
                    .join(', ')}
                  )
                </>
              ) : null}
              .
            </p>
          ) : (
            <ol className="vx-mini-list" aria-label="Candidats qualifiés, ordre publié">
              {summary.qualified.map((candidate) => (
                <li key={candidate.ticker}>
                  <Link to={`/analysis/${candidate.ticker}`}>
                    <code>{candidate.ticker}</code>
                  </Link>{' '}
                  <span className="vx-mini-list-meta">
                    {candidate.advice.status} · {candidate.advice.direction ?? 'direction non publiée'} ·{' '}
                    {candidate.advice.horizon ?? 'horizon non publié'}
                  </span>
                  {candidate.synthetic ? <span className="vx-badge vx-badge-synthetic">SYNTHÉTIQUE</span> : null}
                </li>
              ))}
            </ol>
          )}
        </>
      ) : null}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function SectorsModule() {
  const query = useMarketsOverview();
  const state = moduleStateOf(pageStateOf(query), query.data);
  const data = query.data;
  const module = todayModule('sectors');
  return (
    <Card
      rank="quiet"
      kicker="Snapshot Marchés"
      title={module.title}
      titleId="vx-today-sectors-title"
      className="vx-today-module"
      {...(moduleShowsContent(state) && data !== undefined
        ? { footer: <>rendement 1 j par instrument, chaîne serveur · <Link to="/markets">voir Marchés</Link></> }
        : {})}
    >
      <ModuleStatus state={state} raw={state === 'closed' ? data?.state : data?.reason} />
      {moduleShowsContent(state) && data !== undefined ? <SectorGrid sectors={data.sectors} /> : null}
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function ManualPortfolioModule() {
  const query = usePortfolio();
  const queryState = pageStateOf(query);
  const data = query.data;
  const state = moduleStateOf(queryState, data?.valuation);
  const module = todayModule('manual-portfolio');
  const content = data === undefined ? null : valuationContentOf(data.valuation);
  const summary = content === null ? null : portfolioSummaryOf(content);
  return (
    <Card
      rank="quiet"
      kicker="Déclaré par l’utilisateur"
      title={module.title}
      titleId="vx-today-portfolio-title"
      className="vx-today-module"
      {...(summary !== null
        ? {
            footer: (
              <>
                marques {publie(summary.markPopulation)} · as_of {publie(summary.asOf)} ·{' '}
                <Link to="/portfolio">voir Portefeuille</Link>
              </>
            ),
          }
        : {})}
    >
      <ModuleStatus state={state} raw={state === 'closed' ? data?.valuation.state : data?.valuation.reason} />
      {moduleShowsContent(state) && summary !== null ? (
        <>
          {summary.markPopulation === 'SYNTHETIC' ? (
            <p className="vx-badge vx-badge-synthetic">MARQUES SYNTHÉTIQUES</p>
          ) : null}
          {summary.blocks.length === 0 ? (
            <p className="vx-module-sentence" role="status">
              Aucune position déclarée : rien n&apos;est valorisé.
            </p>
          ) : (
            summary.blocks.map((block) => (
              <div key={block.currency} className="vx-metrics-row">
                <Metric
                  label={`Valeur (${block.currency})`}
                  value={block.concentrationStatus === 'OK' ? block.totalValue : null}
                  unit={block.currency}
                  absentLabel={`Valeur non publiée : ${block.concentrationReason ?? block.concentrationStatus ?? 'statut absent'}`}
                />
                <Metric
                  label="Latent"
                  value={block.unrealizedStatus === 'OK' ? block.totalUnrealized : null}
                  unit={block.currency}
                  sign={block.unrealizedStatus === 'OK' ? signOf(block.totalUnrealized) : null}
                  absentLabel={`Latent non publié : ${block.unrealizedReason ?? block.unrealizedStatus ?? 'statut absent'}`}
                />
              </div>
            ))
          )}
          <p className="vx-module-sentence">
            lots valorisés {publie(summary.lotsValued)} · exclus {publie(summary.lotsExcluded)}
          </p>
        </>
      ) : moduleShowsContent(state) && summary === null && data !== undefined ? (
        <p className="vx-module-sentence" role="status">
          Valorisation publiée dans un schéma inconnu : rien n&apos;est affiché à moitié.
        </p>
      ) : null}
    </Card>
  );
}

// ---------------------------------------------------------------------------

const AGENDA_LINES = 5;

export function CalendarModule() {
  const query = useCalendar(null);
  const state = moduleStateOf(pageStateOf(query), query.data);
  const data = query.data;
  const module = todayModule('calendar');
  const lines = data === undefined ? [] : leadingAgenda(data.agenda, AGENDA_LINES);
  return (
    <Card
      rank="quiet"
      kicker="Agenda publié"
      title={module.title}
      titleId="vx-today-calendar-title"
      className="vx-today-module"
      {...(moduleShowsContent(state) && data !== undefined
        ? {
            footer: (
              <>
                {lines.length} premiers sur {data.agenda.length} publiés, ordre du worker ·{' '}
                <Link to="/calendar">voir le calendrier complet</Link>
              </>
            ),
          }
        : {})}
    >
      <ModuleStatus state={state} raw={state === 'closed' ? data?.state : data?.reason} />
      {moduleShowsContent(state) && data !== undefined ? (
        lines.length === 0 ? (
          <p className="vx-module-sentence" role="status">
            Agenda publié sans aucun événement.
          </p>
        ) : (
          <ul className="vx-agenda-mini" aria-label="Premiers événements de l’agenda publié">
            {lines.map((event) => (
              <AgendaLine key={event.eventId} event={event} />
            ))}
          </ul>
        )
      ) : null}
    </Card>
  );
}
