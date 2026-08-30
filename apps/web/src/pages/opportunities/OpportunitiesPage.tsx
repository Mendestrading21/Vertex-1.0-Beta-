import type { OpportunitiesResponse } from '../../api/client.ts';
import { useOpportunities } from '../../api/decisionApi.ts';
import { pageStateOf } from '../../api/hooks.ts';
import type { PageDataState } from '../../api/hooks.ts';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import type { DataState } from '../../components/DataStateBoundary.tsx';
import { FreshnessBadge } from '../../components/FreshnessBadge.tsx';
import { SyntheticBanner } from '../../components/SyntheticBanner.tsx';
import { OpportunityTable } from './OpportunityTable.tsx';
import {
  CALENDAR_REF_STATUS_LABELS,
  opportunitiesContentOf,
} from './opportunitiesView.ts';
import type { OpportunitiesContentView } from './opportunitiesView.ts';

/**
 * Page Opportunités — question : « Quels candidats admissibles méritent une
 * analyse approfondie ? »
 *
 * Tout vient du snapshot `opportunities/global` publié par le worker sous
 * l'unique `AdviceEngine`. L'interface ne classe ni ne note : elle sépare
 * strictement les deux groupes, affiche pour chaque exclu la raison publiée,
 * et rend visible la provenance (profil appliqué / non appliqué, snapshot
 * calendrier utilisé comme provenance des catalyseurs).
 *
 * Sur la population synthétique actuelle, la totalité des candidats est
 * exclue en `INSUFFICIENT_DATA` : c'est le comportement VOULU d'un moteur
 * fail-closed, affiché comme tel — pas un état d'erreur — et le groupe
 * qualifié porte son état vide honnête.
 *
 * États servis, jamais confondus : `ok`, `stale` (même contenu, mais hors
 * budget de fraîcheur : il s'affiche sous le bandeau « Données périmées » avec
 * son âge serveur et sa raison) et `empty`. L'âge affiché est le `age_seconds`
 * PUBLIÉ par le serveur — jamais mesuré par le navigateur.
 *
 * `clock_inconsistent` (dérive d'horloge entre le worker et l'API au-delà de
 * la tolérance) reste FERMÉ : aucun contenu n'est rendu. Mais la cause publiée
 * par le serveur est affichée, sinon la page dirait « erreur » là où le
 * serveur dit précisément que c'est l'horloge, et non le contenu. Tout autre
 * état hors contrat reste fermé sans cause inventée.
 */

export function opportunitiesFrameStateOf(
  queryState: PageDataState,
  data: OpportunitiesResponse | undefined,
): {
  readonly state: DataState | 'auth-required';
  readonly view: OpportunitiesContentView | null;
  readonly detail?: string;
} {
  if (queryState !== 'ready' && queryState !== 'refreshing') {
    return { state: queryState, view: null };
  }
  if (data === undefined) {
    return { state: 'error', view: null };
  }
  const served: string = data.state;
  if (served === 'empty') {
    return { state: 'empty', view: null };
  }
  if (served === 'clock_inconsistent') {
    // Fermé comme tout état sans contenu servable, mais la cause vient du
    // serveur : dire « erreur » seul laisserait croire à un contenu invalide.
    return {
      state: 'error',
      view: null,
      detail:
        data.reason ??
        'Horloge incohérente entre le worker et l’API : aucun verdict n’est affiché.',
    };
  }
  if (served !== 'ok' && served !== 'stale') {
    // Fail-closed : un état hors contrat n'est jamais rendu comme un succès,
    // et aucune cause n'est inventée pour lui.
    return { state: 'error', view: null };
  }
  const view = opportunitiesContentOf(data.content);
  if (view === null) {
    return { state: 'error', view: null };
  }
  // Un verdict périmé garde son contenu SOUS un bandeau explicite : il n'est
  // ni masqué, ni présenté comme courant.
  return { state: served === 'stale' ? 'stale' : queryState, view };
}

function ProfileRefPanel({ view }: { readonly view: OpportunitiesContentView }) {
  const profile = view.profileRef;
  return (
    <section className="vx-opp-profile" aria-labelledby="vx-opp-profile-title" data-testid="opp-profile">
      <h2 id="vx-opp-profile-title">Profil de stratégie référencé</h2>
      <p className="vx-opp-profile-id">
        Identifiant <code data-testid="opp-profile-id">{profile.id ?? '—'}</code> — version{' '}
        <code data-testid="opp-profile-version">{profile.version ?? '—'}</code> — source{' '}
        <code>{profile.source ?? '—'}</code>
      </p>
      <p className="vx-opp-profile-note">
        Le profil n’est appliqué qu’EN PARTIE, et le snapshot le publie : les deux listes
        ci-dessous sont distinctes et ne se remplacent jamais.
      </p>
      <div className="vx-opp-profile-lists">
        <div data-testid="opp-profile-applied">
          <h3>
            <span aria-hidden="true">✓</span> Appliqué
          </h3>
          {profile.applied.length === 0 ? (
            <p className="vx-cell-absent">Aucun champ déclaré appliqué.</p>
          ) : (
            <ul>
              {profile.applied.map((entry) => (
                <li key={entry}>{entry}</li>
              ))}
            </ul>
          )}
        </div>
        <div data-testid="opp-profile-not-applied">
          <h3>
            <span aria-hidden="true">⊘</span> Non appliqué
          </h3>
          {profile.notApplied.length === 0 ? (
            <p className="vx-cell-absent">Aucun champ déclaré non appliqué.</p>
          ) : (
            <ul>
              {profile.notApplied.map((entry) => (
                <li key={entry.field}>
                  <code>{entry.field}</code> — {entry.reason ?? 'raison non publiée'}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}

function CalendarRefPanel({ view }: { readonly view: OpportunitiesContentView }) {
  const reference = view.calendarRef;
  const status = reference.status ?? '';
  return (
    <section
      className="vx-opp-calref"
      aria-labelledby="vx-opp-calref-title"
      data-testid="opp-calendar-ref"
      data-status={status}
    >
      <h2 id="vx-opp-calref-title">Provenance des catalyseurs — snapshot calendrier</h2>
      <p className="vx-opp-calref-status">
        <span aria-hidden="true">{status === 'USED' ? '●' : '⊘'}</span> Statut{' '}
        <code data-testid="opp-calref-status">{status === '' ? '—' : status}</code> —{' '}
        {CALENDAR_REF_STATUS_LABELS[status] ?? 'statut relayé tel quel par le serveur'}
      </p>
      <dl className="vx-opp-calref-facts">
        <div>
          <dt>Ressource</dt>
          <dd>
            <code>
              {reference.kind ?? '—'}/{reference.key ?? '—'}
            </code>{' '}
            version <code data-testid="opp-calref-version">{reference.version ?? '—'}</code>
          </dd>
        </div>
        <div>
          <dt>as_of du snapshot</dt>
          <dd>
            {reference.snapshotAsOf !== null ? (
              <time dateTime={reference.snapshotAsOf}>{reference.snapshotAsOf}</time>
            ) : (
              <span className="vx-cell-absent">non publié</span>
            )}
          </dd>
        </div>
        <div>
          <dt>as_of du contenu</dt>
          <dd>
            {reference.contentAsOf !== null ? (
              <time dateTime={reference.contentAsOf}>{reference.contentAsOf}</time>
            ) : (
              <span className="vx-cell-absent">non publié</span>
            )}
          </dd>
        </div>
        <div>
          <dt>Schéma du contenu</dt>
          <dd>
            <code>{reference.contentSchemaVersion ?? '—'}</code>
          </dd>
        </div>
        <div>
          <dt>Âge maximal admis (s)</dt>
          <dd className="vx-num">{reference.maxAgeSeconds ?? '—'}</dd>
        </div>
        <div>
          <dt>Événements à venir comptés</dt>
          <dd className="vx-num">{reference.eventsUpcoming ?? '—'}</dd>
        </div>
        <div>
          <dt>Événements passés ignorés</dt>
          <dd className="vx-num">{reference.eventsIgnoredPast ?? '—'}</dd>
        </div>
        <div>
          <dt>Événements sans instrument</dt>
          <dd className="vx-num">{reference.eventsWithoutTicker ?? '—'}</dd>
        </div>
        <div>
          <dt>Événements refusés</dt>
          <dd className="vx-num">{reference.eventsRejected ?? '—'}</dd>
        </div>
      </dl>
    </section>
  );
}

function ExclusionReasonsPanel({ view }: { readonly view: OpportunitiesContentView }) {
  const entries = [...view.exclusionReasons.entries()].sort((left, right) =>
    left[0].localeCompare(right[0]),
  );
  return (
    <section
      className="vx-opp-reasons"
      aria-labelledby="vx-opp-reasons-title"
      data-testid="opp-exclusion-reasons"
    >
      <h2 id="vx-opp-reasons-title">Répartition des raisons d’exclusion</h2>
      {entries.length === 0 ? (
        <p className="vx-matrix-empty">Aucune raison d’exclusion publiée.</p>
      ) : (
        <div
          className="vx-cal-scroll"
          tabIndex={0}
          role="region"
          aria-label="Répartition publiée des raisons d’exclusion"
        >
        <table className="vx-matrix-table">
          <caption>
            Compteurs publiés par le worker. Chaque clé est la raison exacte
            (<code>gate:reason_code</code> ou <code>required_evidence:nom</code>).
          </caption>
          <thead>
            <tr>
              <th scope="col">Raison publiée</th>
              <th scope="col">Candidats</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([reason, count]) => (
              <tr key={reason} data-testid={`opp-reason-${reason}`}>
                <th scope="row">
                  <code>{reason}</code>
                </th>
                <td className="vx-num">{count}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
      <h3>Statuts publiés sur l’univers</h3>
      <div
        className="vx-cal-scroll"
        tabIndex={0}
        role="region"
        aria-label="Comptage des statuts publiés sur l’univers"
      >
      <table className="vx-matrix-table">
        <caption>Comptage des statuts du moteur unique sur l’univers déclaré.</caption>
        <thead>
          <tr>
            <th scope="col">Statut</th>
            <th scope="col">Candidats</th>
          </tr>
        </thead>
        <tbody>
          {[...view.coverage.statusCounts.entries()].sort().map(([status, count]) => (
            <tr key={status} data-testid={`opp-status-count-${status}`}>
              <th scope="row">
                <code>{status}</code>
              </th>
              <td className="vx-num">{count}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </section>
  );
}

function LimitationsPanel({ view }: { readonly view: OpportunitiesContentView }) {
  return (
    <section className="vx-opp-limitations" aria-labelledby="vx-opp-limitations-title">
      <h2 id="vx-opp-limitations-title">Limites publiées</h2>
      {view.limitations.length === 0 ? (
        <p className="vx-cell-absent">Aucune limite publiée.</p>
      ) : (
        <ul data-testid="opp-limitations">
          {view.limitations.map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      )}
      <p className="vx-opp-ordering">
        Classement : <code>{view.ordering.method ?? '—'}</code> —{' '}
        {view.ordering.keys.join(' → ') || 'aucune clé publiée'}.{' '}
        {view.ordering.note ?? ''}
      </p>
    </section>
  );
}

export function OpportunitiesPage() {
  const query = useOpportunities();
  const queryState = pageStateOf(query);
  const frame = opportunitiesFrameStateOf(queryState, query.data);
  const view = frame.view;

  return (
    <article className="vx-opportunities" aria-labelledby="vx-page-title-opportunities">
      <header className="vx-page-header">
        <h1 id="vx-page-title-opportunities">Opportunités</h1>
        <p className="vx-page-question">
          Quels candidats admissibles méritent une analyse approfondie ?
        </p>
      </header>

      {view !== null ? <SyntheticBanner population={view.population} /> : null}

      {frame.state === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : view === null ? (
        <DataStateBoundary
          state={frame.state as DataState}
          {...(frame.state === 'empty'
            ? {
                detail:
                  query.data?.reason ??
                  'Aucun snapshot d’opportunités publié : rien n’est affiché.',
              }
            : {})}
          {...(frame.detail !== undefined ? { detail: frame.detail } : {})}
        />
      ) : (
        <DataStateBoundary
          state={frame.state as DataState}
          {...(frame.state === 'stale'
            ? {
                detail:
                  query.data?.reason ??
                  'Verdict hors budget de fraîcheur (raison non publiée) : il n’est pas courant.',
              }
            : {})}
          {...(query.data?.as_of != null ? { asOfLabel: query.data.as_of } : {})}
        >
          <p className="vx-opp-provenance" data-testid="opp-provenance">
            <FreshnessBadge
              ageSeconds={query.data?.age_seconds ?? null}
              sourceLabel="âge publié par le serveur"
            />
            {' — '}
            Snapshot version <code>{query.data?.snapshot_version ?? '—'}</code> — publié{' '}
            {view.asOf !== null ? <time dateTime={view.asOf}>{view.asOf}</time> : '—'} — moteur{' '}
            <code>{view.engineVersion ?? '—'}</code> — schéma{' '}
            <code>{view.schemaVersion ?? '—'}</code> — univers déclaré{' '}
            <span className="vx-num">{view.coverage.universeSize ?? '—'}</span> — observations
            considérées{' '}
            <span className="vx-num">{view.coverage.observationsConsidered ?? '—'}</span>
          </p>

          <OpportunityTable
            group="qualified"
            candidates={view.candidates.qualified}
            emptyMessage={
              'Aucun candidat qualifié. Sur cette population, le moteur unique ferme les gates ' +
              'requises et publie un statut fermé pour chaque candidat : c’est le comportement ' +
              'attendu d’une décision fail-closed, pas une panne. Le détail par candidat est ' +
              'dans le groupe « Exclus » ci-dessous.'
            }
          />

          <OpportunityTable
            group="excluded"
            candidates={view.candidates.excluded}
            contradictory={view.candidates.contradictory}
            emptyMessage="Aucun candidat exclu publié."
          />

          <ExclusionReasonsPanel view={view} />
          <ProfileRefPanel view={view} />
          <CalendarRefPanel view={view} />
          <LimitationsPanel view={view} />
        </DataStateBoundary>
      )}
    </article>
  );
}
