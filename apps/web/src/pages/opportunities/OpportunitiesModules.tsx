import { Card } from '../../components/Card.tsx';
import { CensusBars } from '../../components/CensusBars.tsx';
import { Metric } from '../../components/Metric.tsx';
import { CALENDAR_REF_STATUS_LABELS } from './opportunitiesView.ts';
import type { CandidateView, OpportunitiesContentView } from './opportunitiesView.ts';
import { opportunitiesModule } from './opportunitiesModules.ts';

/**
 * Les modules SERVIS de la planche §3, hors la dominante. Tous lisent le MÊME
 * snapshot `opportunities/global` déjà validé par la page (`view`) : aucun
 * n'ouvre une seconde requête, aucun ne calcule — comptes publiés, chaînes
 * verbatim, ordre publié.
 */

const DIRECTION_LABELS: Readonly<Record<string, string>> = {
  BULLISH: 'Haussière',
  BEARISH: 'Baissière',
  NEUTRAL: 'Neutre',
  MIXED: 'Contrastée',
  UNKNOWN: 'Inconnue',
};

/** Compte des directions PUBLIÉES par candidat, tous groupes confondus. */
export function directionCensusOf(
  view: OpportunitiesContentView,
): readonly { readonly key: string; readonly label: string; readonly count: number }[] {
  const counts = new Map<string, number>();
  const all: readonly CandidateView[] = [
    ...view.candidates.qualified,
    ...view.candidates.contradictory,
    ...view.candidates.excluded,
  ];
  for (const candidate of all) {
    const key = candidate.advice.direction ?? 'NON_PUBLIÉE';
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .map(([key, count]) => ({ key, label: DIRECTION_LABELS[key] ?? key, count }));
}

// ---------------------------------------------------------------------------

export function ActiveIdeasModule({ view }: { readonly view: OpportunitiesContentView }) {
  const module = opportunitiesModule('active-ideas');
  const coverage = view.coverage;
  return (
    <Card
      rank="quiet"
      kicker="Couverture publiée"
      title={module.title}
      titleId="vx-opp-ideas-title"
      footer={<>univers déclaré par le worker · aucun candidat reclassé ici</>}
    >
      <div className="vx-metrics-row">
        <Metric
          label="Qualifiés"
          value={coverage.qualifiedCount === null ? null : String(coverage.qualifiedCount)}
          testId="opp-ideas-qualified"
        />
        <Metric
          label="Exclus"
          value={coverage.excludedCount === null ? null : String(coverage.excludedCount)}
          testId="opp-ideas-excluded"
        />
        <Metric
          label="Univers"
          value={coverage.universeSize === null ? null : String(coverage.universeSize)}
          {...(coverage.observationsConsidered === null
            ? {}
            : { note: `${coverage.observationsConsidered} observations considérées` })}
          testId="opp-ideas-universe"
        />
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function BiasSplitModule({ view }: { readonly view: OpportunitiesContentView }) {
  const module = opportunitiesModule('bias-split');
  return (
    <Card
      rank="quiet"
      kicker="Directions publiées"
      title={module.title}
      titleId="vx-opp-bias-title"
      footer={<>une direction UNKNOWN reste UNKNOWN — jamais convertie en neutre</>}
    >
      <CensusBars
        entries={directionCensusOf(view)}
        ariaLabel="Candidats par direction publiée"
        testIdPrefix="opp-direction"
        emptyLabel="Aucun candidat publié : aucune direction à compter."
      />
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function OpportunityHealthModule({ view }: { readonly view: OpportunitiesContentView }) {
  const module = opportunitiesModule('opportunity-health');
  const entries = [...view.coverage.statusCounts.entries()]
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .map(([key, count]) => ({ key, count }));
  return (
    <Card
      rank="quiet"
      kicker="Moteur fail-closed"
      title={module.title}
      titleId="vx-opp-health-title"
      footer={<>comptage du moteur unique sur l’univers déclaré</>}
    >
      <CensusBars
        entries={entries}
        ariaLabel="Candidats par statut publié"
        testIdPrefix="opp-status-count"
        emptyLabel="Aucun statut compté sur l’univers."
      />
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function ProfileModule({ view }: { readonly view: OpportunitiesContentView }) {
  const module = opportunitiesModule('profile');
  const profile = view.profileRef;
  return (
    <Card
      rank="quiet"
      kicker="Profil appliqué en partie"
      title={module.title}
      titleId="vx-opp-profile-title"
      className="vx-opp-profile"
      footer={<>source <code>{profile.source ?? 'non publiée'}</code></>}
    >
      <div data-testid="opp-profile">
        <p className="vx-opp-profile-id">
          Identifiant <code data-testid="opp-profile-id">{profile.id ?? '—'}</code> — version{' '}
          <code data-testid="opp-profile-version">{profile.version ?? '—'}</code>
        </p>
        <p className="vx-opp-profile-note">
          Le profil n’est appliqué qu’EN PARTIE, et le snapshot le publie : les deux listes sont
          distinctes et ne se remplacent jamais.
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
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function ExclusionsModule({ view }: { readonly view: OpportunitiesContentView }) {
  const module = opportunitiesModule('exclusions');
  const entries = [...view.exclusionReasons.entries()].sort((left, right) =>
    left[0].localeCompare(right[0]),
  );
  return (
    <Card
      rank="quiet"
      kicker="Compteurs publiés"
      title={module.title}
      titleId="vx-opp-reasons-title"
      className="vx-opp-reasons"
      footer={
        <>
          chaque clé est la raison exacte (<code>gate:reason_code</code> ou{' '}
          <code>required_evidence:nom</code>)
        </>
      }
    >
      <div data-testid="opp-exclusion-reasons">
        {entries.length === 0 ? (
          <p className="vx-module-sentence" role="status">
            Aucune raison d’exclusion publiée.
          </p>
        ) : (
          <div
            className="vx-cal-scroll"
            tabIndex={0}
            role="region"
            aria-label="Répartition publiée des raisons d’exclusion"
          >
            <table className="vx-matrix-table">
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
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function CalendarRefModule({ view }: { readonly view: OpportunitiesContentView }) {
  const module = opportunitiesModule('catalysts-provenance');
  const reference = view.calendarRef;
  const status = reference.status ?? '';
  return (
    <Card
      rank="quiet"
      kicker="Snapshot calendrier"
      title={module.title}
      titleId="vx-opp-calref-title"
      className="vx-opp-calref"
      footer={<>un catalyseur n’est compté que sur un snapshot calendrier USED — jamais deviné</>}
    >
      <div data-testid="opp-calendar-ref" data-status={status}>
        <p className="vx-opp-calref-status">
          <span aria-hidden="true">{status === 'USED' ? '●' : '⊘'}</span> Statut{' '}
          <code data-testid="opp-calref-status">{status === '' ? '—' : status}</code> —{' '}
          {CALENDAR_REF_STATUS_LABELS[status] ?? 'statut relayé tel quel par le serveur'}
        </p>
        <p className="vx-opp-calref-status">
          Ressource{' '}
          <code>
            {reference.kind ?? '—'}/{reference.key ?? '—'}
          </code>{' '}
          version <code data-testid="opp-calref-version">{reference.version ?? '—'}</code> · schéma{' '}
          <code>{reference.contentSchemaVersion ?? '—'}</code>
        </p>
        <dl className="vx-opp-calref-facts">
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
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------

export function LimitationsModule({ view }: { readonly view: OpportunitiesContentView }) {
  const module = opportunitiesModule('quality');
  return (
    <Card
      rank="quiet"
      kicker="Déclaré par le moteur"
      title={module.title}
      titleId="vx-opp-limitations-title"
      className="vx-opp-limitations"
      footer={<>schéma <code>{view.schemaVersion ?? '—'}</code> · moteur <code>{view.engineVersion ?? '—'}</code></>}
    >
      {view.limitations.length === 0 ? (
        <p className="vx-module-sentence" role="status">
          Aucune limite publiée.
        </p>
      ) : (
        <ul data-testid="opp-limitations" className="vx-opp-limits">
          {view.limitations.map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      )}
    </Card>
  );
}
