import { CensusBars } from '../../components/CensusBars.tsx';
import { Metric } from '../../components/Metric.tsx';
import { Widget } from '../../components/widgets/Widget.tsx';
import { CALENDAR_REF_STATUS_LABELS } from './opportunitiesView.ts';
import type { CandidateView, OpportunitiesContentView } from './opportunitiesView.ts';
import { opportunitiesModule } from './opportunitiesModules.ts';
import type { ModuleState } from '../../components/moduleState.ts';

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

export function ActiveIdeasModule({
  view,
  servedState,
}: {
  readonly view: OpportunitiesContentView;
  /**
   * L'ÉTAT SERVI DE L'INSTANTANÉ, propagé par la page.
   *
   * Ces modules annonçaient `state="ready"` en dur : un instantané périmé ou
   * différé s'y affichait comme frais, et seul le cadre de page disait la
   * vérité — or un lecteur qui regarde une carte ne regarde pas le cadre.
   */
  readonly servedState: ModuleState;
}) {
  const module = opportunitiesModule('active-ideas');
  const coverage = view.coverage;
  return (
    <Widget
      id={module.id}
      size={module.size}
      state={servedState}
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
    </Widget>
  );
}

// ---------------------------------------------------------------------------

export function BiasSplitModule({
  view,
  servedState,
}: {
  readonly view: OpportunitiesContentView;
  /**
   * L'ÉTAT SERVI DE L'INSTANTANÉ, propagé par la page.
   *
   * Ces modules annonçaient `state="ready"` en dur : un instantané périmé ou
   * différé s'y affichait comme frais, et seul le cadre de page disait la
   * vérité — or un lecteur qui regarde une carte ne regarde pas le cadre.
   */
  readonly servedState: ModuleState;
}) {
  const module = opportunitiesModule('bias-split');
  return (
    <Widget
      id={module.id}
      size={module.size}
      state={servedState}
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
    </Widget>
  );
}

// ---------------------------------------------------------------------------

export function OpportunityHealthModule({
  view,
  servedState,
}: {
  readonly view: OpportunitiesContentView;
  /**
   * L'ÉTAT SERVI DE L'INSTANTANÉ, propagé par la page.
   *
   * Ces modules annonçaient `state="ready"` en dur : un instantané périmé ou
   * différé s'y affichait comme frais, et seul le cadre de page disait la
   * vérité — or un lecteur qui regarde une carte ne regarde pas le cadre.
   */
  readonly servedState: ModuleState;
}) {
  const module = opportunitiesModule('opportunity-health');
  const entries = [...view.coverage.statusCounts.entries()]
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .map(([key, count]) => ({ key, count }));
  return (
    <Widget
      id={module.id}
      size={module.size}
      state={servedState}
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
    </Widget>
  );
}

// ---------------------------------------------------------------------------

export function ProfileModule({
  view,
  servedState,
}: {
  readonly view: OpportunitiesContentView;
  /**
   * L'ÉTAT SERVI DE L'INSTANTANÉ, propagé par la page.
   *
   * Ces modules annonçaient `state="ready"` en dur : un instantané périmé ou
   * différé s'y affichait comme frais, et seul le cadre de page disait la
   * vérité — or un lecteur qui regarde une carte ne regarde pas le cadre.
   */
  readonly servedState: ModuleState;
}) {
  const module = opportunitiesModule('profile');
  const profile = view.profileRef;
  return (
    <Widget
      id={module.id}
      size={module.size}
      state={servedState}
      rank="quiet"
      kicker="Profil appliqué en partie"
      title={module.title}
      titleId="vx-opp-profile-title"
      className="vx-opp-profile"
      footer={<>source <code>{profile.source ?? 'non publiée'}</code></>}
    >
      <div data-testid="opp-profile">
        <p className="vx-opp-profile-id">
          Identifiant{' '}
          <code data-testid="opp-profile-id">{profile.id ?? 'identifiant non publié'}</code> —
          version{' '}
          <code data-testid="opp-profile-version">{profile.version ?? 'version non publiée'}</code>
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
    </Widget>
  );
}

// ---------------------------------------------------------------------------

export function ExclusionsModule({
  view,
  servedState,
}: {
  readonly view: OpportunitiesContentView;
  /**
   * L'ÉTAT SERVI DE L'INSTANTANÉ, propagé par la page.
   *
   * Ces modules annonçaient `state="ready"` en dur : un instantané périmé ou
   * différé s'y affichait comme frais, et seul le cadre de page disait la
   * vérité — or un lecteur qui regarde une carte ne regarde pas le cadre.
   */
  readonly servedState: ModuleState;
}) {
  const module = opportunitiesModule('exclusions');
  // LOT P2c — MÊME ORDRE QUE LES STATUTS SUR L'UNIVERS : le compte le plus
  // gros d'abord, la clé servie pour départager. Une liste de raisons se lit
  // pour savoir CE QUI bloque le plus ; l'ordre alphabétique le cachait
  // derrière la première lettre.
  const entries = [...view.exclusionReasons.entries()].sort(
    (left, right) => right[1] - left[1] || left[0].localeCompare(right[0]),
  );
  return (
    <Widget
      id={module.id}
      size={module.size}
      state={servedState}
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
      {/* LOT P2c — UNE TABLE DE DEUX COLONNES DEVIENT DES BARRES. Deux colonnes
          dont l'une ne porte qu'un entier n'avaient pas besoin d'un en-tête,
          d'une région défilante et d'un `scope`. `CensusBars` dit la même
          chose en montrant les proportions, avec le compte SERVI écrit à côté
          de sa barre — jamais un pourcentage, qui serait un calcul. C'est la
          forme que portent déjà les statuts sur l'univers, dans la carte
          voisine : une répartition, une seule façon de la lire. */}
      <div data-testid="opp-exclusion-reasons">
        <CensusBars
          entries={entries.map(([reason, count]) => ({ key: reason, count }))}
          ariaLabel="Répartition publiée des raisons d’exclusion"
          testIdPrefix="opp-reason"
          emptyLabel="Aucune raison d’exclusion publiée."
        />
      </div>
    </Widget>
  );
}

// ---------------------------------------------------------------------------

/**
 * UN DÉNOMBREMENT SERVI, OU L'AVEU. Jamais un tiret : dans une liste où les
 * voisins portent de vrais comptes, « — » est indiscernable d'un zéro publié —
 * et le zéro, lui, est une DONNÉE. Le `<dt>` voisin nomme déjà la mesure, donc
 * « non publié » y suffit sans le répéter.
 *
 * La classe suit l'état : un texte d'absence n'est ni chassé ni aligné comme
 * un chiffre.
 */
function CountCell({ value }: { readonly value: number | null }) {
  return value === null ? (
    <dd className="vx-cell-absent">non publié</dd>
  ) : (
    <dd className="vx-num">{value}</dd>
  );
}

export function CalendarRefModule({
  view,
  servedState,
}: {
  readonly view: OpportunitiesContentView;
  /**
   * L'ÉTAT SERVI DE L'INSTANTANÉ, propagé par la page.
   *
   * Ces modules annonçaient `state="ready"` en dur : un instantané périmé ou
   * différé s'y affichait comme frais, et seul le cadre de page disait la
   * vérité — or un lecteur qui regarde une carte ne regarde pas le cadre.
   */
  readonly servedState: ModuleState;
}) {
  const module = opportunitiesModule('catalysts-provenance');
  const reference = view.calendarRef;
  const status = reference.status ?? '';
  return (
    <Widget
      id={module.id}
      size={module.size}
      state={servedState}
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
          <code data-testid="opp-calref-status">
            {status === '' ? 'statut non publié' : status}
          </code>{' '}
          —{' '}
          {CALENDAR_REF_STATUS_LABELS[status] ?? 'statut relayé tel quel par le serveur'}
        </p>
        <p className="vx-opp-calref-status">
          Ressource{' '}
          <code>
            {reference.kind ?? 'type non publié'}/{reference.key ?? 'clé non publiée'}
          </code>{' '}
          version{' '}
          <code data-testid="opp-calref-version">
            {reference.version ?? 'version non publiée'}
          </code>{' '}
          · schéma{' '}
          <code>{reference.contentSchemaVersion ?? 'schéma non publié'}</code>
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
            <CountCell value={reference.maxAgeSeconds} />
          </div>
          <div>
            <dt>Événements à venir comptés</dt>
            <CountCell value={reference.eventsUpcoming} />
          </div>
          <div>
            <dt>Événements passés ignorés</dt>
            <CountCell value={reference.eventsIgnoredPast} />
          </div>
          <div>
            <dt>Événements sans instrument</dt>
            <CountCell value={reference.eventsWithoutTicker} />
          </div>
          <div>
            <dt>Événements refusés</dt>
            <CountCell value={reference.eventsRejected} />
          </div>
        </dl>
      </div>
    </Widget>
  );
}

// ---------------------------------------------------------------------------

export function LimitationsModule({
  view,
  servedState,
}: {
  readonly view: OpportunitiesContentView;
  /**
   * L'ÉTAT SERVI DE L'INSTANTANÉ, propagé par la page.
   *
   * Ces modules annonçaient `state="ready"` en dur : un instantané périmé ou
   * différé s'y affichait comme frais, et seul le cadre de page disait la
   * vérité — or un lecteur qui regarde une carte ne regarde pas le cadre.
   */
  readonly servedState: ModuleState;
}) {
  const module = opportunitiesModule('quality');
  return (
    <Widget
      id={module.id}
      size={module.size}
      state={servedState}
      rank="quiet"
      kicker="Déclaré par le moteur"
      title={module.title}
      titleId="vx-opp-limitations-title"
      className="vx-opp-limitations"
      footer={
        <>
          schéma <code>{view.schemaVersion ?? 'non publié'}</code> · moteur{' '}
          <code>{view.engineVersion ?? 'non publié'}</code>
        </>
      }
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
    </Widget>
  );
}
