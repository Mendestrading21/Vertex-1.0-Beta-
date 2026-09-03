import { Link } from 'react-router-dom';

import { pageStateOf } from '../../api/hooks.ts';
import { usePerformance, usePortfolio } from '../../api/portfolioApi.ts';
import { AbsentModule } from '../../components/AbsentModule.tsx';
import { Metric } from '../../components/Metric.tsx';
import { moduleStateOf } from '../../components/moduleState.ts';
import type { ModuleState } from '../../components/moduleState.ts';
import { DayBars } from '../../components/widgets/DayBars.tsx';
import type { DayBarEntry } from '../../components/widgets/DayBars.tsx';
import { SparkFigure } from '../../components/widgets/SparkFigure.tsx';
import { StatusChip } from '../../components/widgets/StatusChip.tsx';
import { Widget } from '../../components/widgets/Widget.tsx';
import type { WidgetServed } from '../../components/widgets/Widget.tsx';
import { ConcentrationBars } from '../portfolio/ConcentrationPanel.tsx';
import { METRIC_LABELS, performanceContentOf } from '../portfolio/performance/performanceView.ts';
import { valuationContentOf } from '../portfolio/portfolioView.ts';
import type { ValuationContentView } from '../portfolio/portfolioView.ts';
import { riskModule } from './riskModules.ts';
import type { RiskView } from './riskView.ts';

/**
 * Les modules SERVIS de la planche §9, hors la dominante (la matrice, portée
 * par la page). Quatre lisent le snapshot de la matrice déjà validé par la
 * page ; deux lisent le registre manuel et sa performance par les hooks des
 * pages propriétaires (vues pures importées, jamais les pages — porte
 * `INEFFECTIVE_DYNAMIC_IMPORT`), chacun avec son état.
 *
 * LOT P4 — FORMES V2 ET CINQ ABSENCES QUI MENTAIENT. Chaque module passe par
 * `Widget` (ADR-017) : un seul porteur de `data-rank`, `data-module` et
 * `data-size` déclarés par le catalogue, onze états, méta servie. Les formes
 * suivent la DONNÉE : barres sur rail pour des dénombrements de séances, bande
 * de parts sur des RATIOS servis (jamais convertis en pourcentages), aire sous
 * une série de drawdown servie, pastilles pour des statuts.
 *
 * Cinq absences se lisaient comme des faits avant ce lot, et sont corrigées
 * ici et dans `riskView.ts` :
 *
 * 1. une séance non publiée par instrument devenait `0` — « aucune séance » et
 *    « pas publié » se lisaient pareil ;
 * 2. une perte d'alignement NULLE et servie était filtrée, donc indistincte
 *    d'un instrument absent de la matrice ;
 * 3. un seuil de bande non publié s'affichait « — », un tiret qui se lit comme
 *    une valeur ;
 * 4. une paire extrême servie SEULE était effacée parce que l'autre manquait ;
 * 5. l'état servi de la valorisation était écrasé par un `'ok'` codé en dur :
 *    une valorisation périmée se lisait « prête ».
 */

/** État de module dérivé d'un état de page, sans jamais l'inventer. */
export function riskModuleState(pageState: ModuleState, dataState: string | null): ModuleState {
  // `data_state` est SERVI par le contenu de la matrice ; quand il annonce une
  // couverture partielle, le module le dit au lieu de rester « prêt ».
  if (dataState === 'partial' && (pageState === 'ready' || pageState === 'refreshing')) {
    return 'partial';
  }
  return pageState;
}

export function AbsentRiskModule({ id }: { readonly id: string }) {
  const module = riskModule(id);
  if (module.status.kind !== 'absent') {
    throw new Error(`Module ${id} is served, not absent`);
  }
  // `data-size` vient du catalogue comme pour un module servi : la planche
  // compose de la même façon un module absent et un module servi.
  return (
    <div data-module={id} data-size={module.size}>
      <AbsentModule title={module.title} question={module.question} reason={module.status.reason} note={module.status.note} />
    </div>
  );
}

// ---------------------------------------------------------------------------

export function ExtremesModule({
  view,
  state,
  served,
}: {
  readonly view: RiskView | null;
  readonly state: ModuleState;
  /** Absent pour les modules qui partagent le snapshot de la dominante : sa
   *  provenance est déjà datée sur le même écran, la répéter est du bruit. */
  readonly served?: WidgetServed;
}) {
  const module = riskModule('extremes');
  const extremes = view === null ? null : view.extremes;
  return (
    <Widget
      id="extremes"
      size={module.size}
      kicker="Publiées avec la matrice"
      title={module.title}
      titleId="vx-risk-extremes-title"
      state={state}
      {...(served === undefined ? {} : { served })}
      footer={<>coefficients exacts du serveur ; l’avertissement de synchronicité reste visible</>}
    >
      {extremes === null ? (
        <p className="vx-module-sentence" role="status" data-testid="risk-extremes-empty">
          {view === null
            ? 'Matrice non publiée : aucune paire à nommer.'
            : 'Aucune paire extrême publiée : la matrice n’a pas été construite.'}
        </p>
      ) : (
        <dl className="vx-risk-extremes" data-testid="risk-extremes">
          <div>
            <dt>Paire la plus liée</dt>
            <dd>
              {/* Chaque paire est indépendante : l'absence de l'autre ne
                  l'efface plus (`_checked_pair` accepte une paire nulle). */}
              {extremes.mostCorrelated === null ? (
                <span data-absent="true">non publiée</span>
              ) : (
                <>
                  {extremes.mostCorrelated.pair} <strong>{extremes.mostCorrelated.value}</strong>
                </>
              )}
            </dd>
          </div>
          <div>
            <dt>Paire la plus opposée</dt>
            <dd>
              {extremes.mostOpposed === null ? (
                <span data-absent="true">non publiée</span>
              ) : (
                <>
                  {extremes.mostOpposed.pair} <strong>{extremes.mostOpposed.value}</strong>
                </>
              )}
            </dd>
          </div>
        </dl>
      )}
      {view !== null && view.synchronicityWarning !== null ? (
        <p className="vx-risk-caveat" role="note">
          {view.synchronicityWarning}
        </p>
      ) : null}
    </Widget>
  );
}

// ---------------------------------------------------------------------------

function lookbackLabel(seconds: number | null): string {
  if (seconds === null) {
    return 'non publiée';
  }
  return `${seconds} s`;
}

export function CoverageModule({
  view,
  state,
  served,
}: {
  readonly view: RiskView | null;
  readonly state: ModuleState;
  /** Absent pour les modules qui partagent le snapshot de la dominante : sa
   *  provenance est déjà datée sur le même écran, la répéter est du bruit. */
  readonly served?: WidgetServed;
}) {
  const module = riskModule('coverage');
  if (view === null) {
    return (
      <Widget id="coverage" size={module.size} kicker="Périmètre déclaré" title={module.title} titleId="vx-risk-coverage-title" state={state} {...(served === undefined ? {} : { served })}>
        <p className="vx-module-sentence" role="status">
          Matrice non publiée : aucune couverture à décrire.
        </p>
      </Widget>
    );
  }
  const coverage = view.coverage;
  return (
    <Widget
      id="coverage"
      size={module.size}
      kicker="Périmètre déclaré"
      title={module.title}
      titleId="vx-risk-coverage-title"
      state={state}
      {...(served === undefined ? {} : { served })}
      footer={<>le périmètre est DÉCLARÉ, jamais deviné : comparer qui à qui est une décision, pas une déduction du code</>}
    >
      <dl className="vx-risk-coverage" data-testid="risk-coverage">
        <div>
          <dt>Instruments retenus</dt>
          <dd>
            {coverage.retained} sur {coverage.perimeterSize} déclarés
            {coverage.retainedTickers.length > 0 ? (
              <>
                {' '}
                (<code>{coverage.retainedTickers.join(', ')}</code>)
              </>
            ) : null}
          </dd>
        </div>
        <div>
          <dt>Séances communes</dt>
          <dd>
            {coverage.commonDays} (minimum déclaré&nbsp;: {coverage.minimumDays})
          </dd>
        </div>
        <div>
          <dt>Fenêtre</dt>
          <dd>{coverage.window ?? 'non publiée'}</dd>
        </div>
        <div>
          <dt>Unité</dt>
          <dd>
            <code>{view.unit ?? 'non publiée'}</code>
          </dd>
        </div>
        <div>
          <dt>Enregistrements lus dans la fenêtre</dt>
          {/* Le serveur compte des ENVELOPPES d'observation, pas des séances
              ni des rendements : le libellé dit ce que le nombre est. */}
          <dd>{coverage.observationsConsidered === null ? 'non publié' : coverage.observationsConsidered}</dd>
        </div>
        <div>
          <dt>Retour en arrière</dt>
          <dd>{lookbackLabel(coverage.lookbackSeconds)}</dd>
        </div>
      </dl>
    </Widget>
  );
}

// ---------------------------------------------------------------------------

/** Séances perdues et séances servies, en barres de DÉNOMBREMENT. */
function countBars(entries: ReadonlyArray<{ readonly ticker: string; readonly value: number | null }>): readonly DayBarEntry[] {
  return entries.map((entry) => ({
    key: entry.ticker,
    label: entry.ticker,
    // `null` reste `null` : la barre n'est pas dessinée et l'entrée dit
    // « non publié », au lieu d'une barre de hauteur zéro qui serait un fait.
    value: entry.value === null ? null : String(entry.value),
  }));
}

export function AlignmentModule({
  view,
  state,
  served,
}: {
  readonly view: RiskView | null;
  readonly state: ModuleState;
  /** Absent pour les modules qui partagent le snapshot de la dominante : sa
   *  provenance est déjà datée sur le même écran, la répéter est du bruit. */
  readonly served?: WidgetServed;
}) {
  const module = riskModule('alignment');
  if (view === null) {
    return (
      <Widget id="alignment" size={module.size} kicker="Séances perdues" title={module.title} titleId="vx-risk-alignment-title" state={state} {...(served === undefined ? {} : { served })}>
        <p className="vx-module-sentence" role="status">
          Matrice non publiée.
        </p>
      </Widget>
    );
  }
  const coverage = view.coverage;
  const pertes = countBars(coverage.alignmentLoss.map((entry) => ({ ticker: entry.ticker, value: entry.lost })));
  const seances = countBars(coverage.tradingDaysPerInstrument.map((entry) => ({ ticker: entry.ticker, value: entry.days })));
  return (
    <Widget
      id="alignment"
      size={module.size}
      kicker="Séances perdues"
      title={module.title}
      titleId="vx-risk-alignment-title"
      state={state}
      {...(served === undefined ? {} : { served })}
      footer={<>une séance manquante chez un seul instrument la retire à TOUS : le calcul exige une matrice complète et refuse un trou plutôt que de le combler</>}
    >
      <div data-testid="risk-alignment">
        <DayBars
          entries={pertes}
          unit="séance(s)"
          ariaLabel="Séances perdues à l’alignement, par instrument"
          emptyLabel="Aucune perte d’alignement publiée."
        />
      </div>
      {seances.length > 0 ? (
        <div data-testid="risk-sessions">
          <p className="vx-module-sentence">Séances servies par instrument :</p>
          <DayBars entries={seances} unit="séance(s)" ariaLabel="Séances servies par instrument" />
        </div>
      ) : null}
    </Widget>
  );
}

// ---------------------------------------------------------------------------

export function DiscardsModule({
  view,
  state,
  served,
}: {
  readonly view: RiskView | null;
  readonly state: ModuleState;
  /** Absent pour les modules qui partagent le snapshot de la dominante : sa
   *  provenance est déjà datée sur le même écran, la répéter est du bruit. */
  readonly served?: WidgetServed;
}) {
  const module = riskModule('discards');
  if (view === null) {
    return (
      <Widget id="discards" size={module.size} kicker="Écartés avec leur raison" title={module.title} titleId="vx-risk-discards-title" state={state} {...(served === undefined ? {} : { served })}>
        <p className="vx-module-sentence" role="status">
          Matrice non publiée.
        </p>
      </Widget>
    );
  }
  const coverage = view.coverage;
  return (
    <Widget
      id="discards"
      size={module.size}
      kicker="Écartés avec leur raison"
      title={module.title}
      titleId="vx-risk-discards-title"
      state={state}
      {...(served === undefined ? {} : { served })}
      footer={<>un instrument écarté ne devient jamais une colonne vide : il sort avec son motif</>}
    >
      {coverage.discarded.length === 0 ? (
        <p className="vx-module-sentence" role="status" data-testid="risk-discards-empty">
          Aucun instrument écarté du périmètre déclaré.
        </p>
      ) : (
        <ul className="vx-risk-discards-list" data-testid="risk-discards">
          {coverage.discarded.map((entry) => (
            <li key={entry.instrument}>
              <span>{entry.instrument}</span> {entry.reason}
            </li>
          ))}
        </ul>
      )}
      {coverage.rejectedServedCount > 0 ? (
        <p className="vx-module-sentence" data-testid="risk-rejected-records">
          {/* Le compte est celui des enregistrements SERVIS ; en rendre moins
              sous-déclarerait les refus du serveur. */}
          {coverage.rejectedServedCount} enregistrement(s) rejeté(s)
          {coverage.rejectedRecords.length > 0 ? <> : {coverage.rejectedRecords.join(' ; ')}</> : null}
          {coverage.rejectedRecords.length < coverage.rejectedServedCount ? (
            <> · {coverage.rejectedServedCount - coverage.rejectedRecords.length} dans une forme que l’interface ne sait pas rendre</>
          ) : null}
        </p>
      ) : null}
    </Widget>
  );
}

// ---------------------------------------------------------------------------

/** Lecture DÉFENSIVE du portefeuille : un corps étranger reste une absence. */
function valuationOf(data: unknown): ValuationContentView | null {
  if (typeof data !== 'object' || data === null) {
    return null;
  }
  const valuation = (data as Record<string, unknown>)['valuation'];
  if (typeof valuation !== 'object' || valuation === null || typeof (valuation as Record<string, unknown>)['state'] !== 'string') {
    return null;
  }
  return valuationContentOf(valuation as Parameters<typeof valuationContentOf>[0]);
}

/** État SERVI de la valorisation, relayé tel quel. */
function valuationServedState(data: unknown): { readonly state: string } | undefined {
  if (typeof data !== 'object' || data === null) {
    return undefined;
  }
  const valuation = (data as Record<string, unknown>)['valuation'];
  if (typeof valuation !== 'object' || valuation === null) {
    return undefined;
  }
  const state = (valuation as Record<string, unknown>)['state'];
  return typeof state === 'string' ? { state } : undefined;
}

function portfolioIdOf(data: unknown): number | null {
  if (typeof data !== 'object' || data === null) {
    return null;
  }
  const portfolio = (data as Record<string, unknown>)['portfolio'];
  if (typeof portfolio !== 'object' || portfolio === null) {
    return null;
  }
  const id = (portfolio as Record<string, unknown>)['id'];
  return typeof id === 'number' ? id : null;
}

export function RegisterConcentrationModule() {
  const module = riskModule('concentration');
  const query = usePortfolio();
  const view = valuationOf(query.data);
  // L'état SERVI par la valorisation est conservé : un `'ok'` codé en dur
  // faisait lire « prête » une valorisation périmée ou vide.
  const state = moduleStateOf(pageStateOf(query), valuationServedState(query.data));
  return (
    <Widget
      id="concentration"
      size={module.size}
      kicker="Registre manuel"
      title={module.title}
      titleId="vx-risk-concentration-title"
      state={state}
      stateDetail={view === null && query.data !== undefined ? 'valorisation illisible ou absente' : null}
      footer={
        <>
          poids normalisés et Herfindahl publiés par la valorisation ; <Link to="/portfolio">voir Portefeuille</Link>
        </>
      }
    >
      {view === null ? (
        <p className="vx-module-sentence" role="status">
          Aucune valorisation lisible : aucune concentration à montrer.
        </p>
      ) : view.blocks.length === 0 ? (
        <p className="vx-module-sentence" role="status" data-testid="risk-concentration-empty">
          Aucune position dérivée du journal : aucune concentration à mesurer.
        </p>
      ) : (
        <div data-testid="risk-concentration">
          {view.blocks.map((block) => (
            <div key={block.currency} className="vx-risk-concentration-block">
              <Metric
                label={`Herfindahl (${block.currency})`}
                value={block.concentrationStatus === 'OK' ? block.herfindahl : null}
                absentLabel={block.concentrationStatus === 'OK' ? 'non publié' : (block.concentrationStatus ?? 'ABSENT')}
                note={`${block.weights.length} ticker(s) pondéré(s)`}
                testId={`risk-herfindahl-${block.currency}`}
                size="compact"
              />
              {block.concentrationStatus === 'OK' ? <ConcentrationBars block={block} testIdPrefix="risk-bars" /> : null}
            </div>
          ))}
        </div>
      )}
    </Widget>
  );
}

// ---------------------------------------------------------------------------

export function DrawdownModule() {
  const module = riskModule('max-drawdown');
  const portfolioQuery = usePortfolio();
  const portfolioId = portfolioIdOf(portfolioQuery.data);
  const query = usePerformance(portfolioId);
  const portfolioState = pageStateOf(portfolioQuery);
  const queryState =
    portfolioId === null ? (portfolioState === 'ready' || portfolioState === 'refreshing' ? 'error' : portfolioState) : pageStateOf(query);
  const view = query.data === undefined || query.data.state === 'empty' ? null : performanceContentOf(query.data.content);
  const state = moduleStateOf(queryState, query.data);
  // Les points vivent DANS le bloc de métrique, pas à la racine : la courbe
  // affichée est celle du drawdown BRUT, nommée comme telle dans la légende.
  const brut = view === null ? null : view.metrics.drawdown_gross;
  const points = brut !== null && brut.status === 'OK' ? brut.drawdownPoints : [];
  return (
    <Widget
      id="max-drawdown"
      size={module.size}
      kicker="Snapshot de performance"
      title={module.title}
      titleId="vx-risk-drawdown-title"
      state={state}
      stateDetail={portfolioId === null ? 'portefeuille non lu' : (query.data?.reason ?? null)}
      footer={
        view === null ? (
          <>baisse maximale depuis un sommet, publiée par le serveur, brut et net des frais</>
        ) : (
          <>
            population <code>{view.population ?? 'non publiée'}</code> · <Link to="/portfolio">voir Performance</Link>
          </>
        )
      }
    >
      {view === null ? (
        <p className="vx-module-sentence" role="status">
          Aucun snapshot de performance publié pour ce portefeuille.
        </p>
      ) : (
        <>
          <div className="vx-metrics-row" data-testid="risk-drawdown">
            {(['drawdown_gross', 'drawdown_net'] as const).map((key) => {
              const block = view.metrics[key];
              return (
                <Metric
                  key={key}
                  label={METRIC_LABELS[key]}
                  value={block.status === 'OK' ? block.maxDrawdownPct : null}
                  unit="%"
                  sign={block.status === 'OK' && block.maxDrawdownPct !== null ? (block.maxDrawdownPct.startsWith('-') ? 'down' : 'flat') : null}
                  absentLabel={block.status === 'OK' ? 'non publié' : `${block.status}${block.reason !== null ? ` — ${block.reason}` : ''}`}
                  {...(block.status === 'OK' && block.peakAt !== null && block.troughAt !== null ? { note: `sommet ${block.peakAt} → creux ${block.troughAt}` } : {})}
                  testId={`risk-${key}`}
                />
              );
            })}
          </div>
          {points.length >= 2 ? (
            <div data-testid="risk-drawdown-series">
              <SparkFigure
                closes={points.map((point) => point.drawdown)}
                labels={points.map((point) => point.tradingDay)}
                sign="down"
                caption={`${METRIC_LABELS.drawdown_gross} — courbe servie`}
                unit="%"
                windowLabel={`${points.length} séance(s) servie(s), du ${points[0]?.tradingDay ?? ''} au ${points[points.length - 1]?.tradingDay ?? ''}`}
                variant="area"
                tone="negative"
              />
            </div>
          ) : (
            <p className="vx-module-sentence" role="status" data-testid="risk-drawdown-series-absent">
              Série de drawdown insuffisante : {points.length} point(s) servi(s), deux au minimum pour tracer une aire.
            </p>
          )}
        </>
      )}
    </Widget>
  );
}

// ---------------------------------------------------------------------------

/** Pastille d'état de la matrice, servie — jamais déduite d'une couleur. */
export function MatrixStateChip({ view }: { readonly view: RiskView }) {
  if (view.dataState === null) {
    return <StatusChip label="ÉTAT DES DONNÉES NON DÉCLARÉ" tone="warning" />;
  }
  // Le code SERVI est le libellé lui-même : le répéter en chasse fixe donnait
  // « ok ok » sur la capture. Un code n'est montré que s'il DIT autre chose.
  return <StatusChip label={`état des données : ${view.dataState}`} tone={view.dataState === 'complete' ? 'neutral' : 'warning'} />;
}
