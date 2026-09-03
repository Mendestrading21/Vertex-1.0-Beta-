import type { MarketsOverview } from '../../api/client.ts';
import type { FlatTicker } from '../../components/markets/marketsView.ts';
import { GROUP_LABELS_FR, frDecimal, signSymbolOf } from '../../components/markets/marketsView.ts';
import { InspectorPanel } from '../../shell/inspector.tsx';

/**
 * Inspecteur de la page Marchés (planche §2 : « instrument/secteur
 * sélectionné, contexte et sources »).
 *
 * Deux contenus, un seul panneau à la fois :
 * - un INSTRUMENT sélectionné (tuile, puce sectorielle ou ligne de table) :
 *   ses chaînes serveur verbatim — clôtures, jours de bourse, rendement,
 *   poids, qualité — et la LIGNÉE du calcul (moteur, méthode, hashes) ;
 * - sinon, la vérité du snapshot qui alimente la carte.
 *
 * Aucune nouvelle vérité : ce panneau ne calcule rien, ne compare rien et ne
 * propose rien. Une valeur absente est dite « non publié ».
 */

function publie(value: string | number | null | undefined): string {
  return value === null || value === undefined || value === '' ? 'non publié' : String(value);
}

function lineageString(calculation: Record<string, unknown>, key: string): string {
  const value = calculation[key];
  return typeof value === 'string' && value !== '' ? value : 'non publié';
}

export function InstrumentInspector({
  entry,
  data,
  onClose,
}: {
  readonly entry: FlatTicker;
  readonly data: MarketsOverview;
  readonly onClose: () => void;
}) {
  const ticker = entry.ticker;
  return (
    <InspectorPanel subject={ticker.ticker}>
      <div className="vx-sheet-head">
        <p className="vx-inspector-note">
          {entry.sectorLabel}
          {ticker.synthetic ? <span className="vx-badge vx-badge-synthetic">SYNTHÉTIQUE</span> : null}
        </p>
        <button type="button" className="vx-sheet-close" onClick={onClose}>
          Fermer
        </button>
      </div>
      <dl className="vx-inspector-facts" data-testid="markets-instrument-facts">
        <div>
          <dt>Dernière clôture</dt>
          <dd>
            <span className="vx-inspector-value">{frDecimal(ticker.last_close)}</span>{' '}
            <span className="vx-inspector-unit">{publie(ticker.currency)}</span> · {ticker.trading_day}
          </dd>
        </div>
        <div>
          <dt>Clôture précédente</dt>
          <dd>
            <span className="vx-inspector-value">{frDecimal(ticker.previous_close)}</span>{' '}
            <span className="vx-inspector-unit">{publie(ticker.currency)}</span> ·{' '}
            {ticker.previous_trading_day}
          </dd>
        </div>
        <div>
          <dt>Rendement 1 j</dt>
          <dd data-sign={entry.group}>
            <span aria-hidden="true">{signSymbolOf(entry.group)}</span>{' '}
            <span className="vx-inspector-value">{frDecimal(ticker.return_1d_pct)} %</span>{' '}
            <span className="vx-visually-hidden">({GROUP_LABELS_FR[entry.group]})</span>
            <span className="vx-inspector-unit"> (ratio {ticker.return_1d})</span>
          </dd>
        </div>
        <div>
          <dt>Poids</dt>
          <dd>
            secteur {frDecimal(ticker.weight_in_sector_pct)} % · global {frDecimal(ticker.weight_global_pct)} %
          </dd>
        </div>
        <div>
          <dt>Qualité</dt>
          <dd>
            <code>{ticker.quality}</code>
          </dd>
        </div>
        <div>
          <dt>Snapshot</dt>
          <dd>
            v{publie(data.snapshot_version)} · as_of {publie(data.as_of)}
          </dd>
        </div>
      </dl>
      <p className="vx-inspector-lineage" data-testid="markets-instrument-lineage">
        calcul <code>{lineageString(ticker.calculation, 'calculation_id')}</code> ·{' '}
        {lineageString(ticker.calculation, 'engine_version')} · statut{' '}
        {lineageString(ticker.calculation, 'status')}
        <br />
        méthode : {lineageString(ticker.calculation, 'method')}
        <br />
        entrées {lineageString(ticker.calculation, 'input_hash')}
        <br />
        résultat {lineageString(ticker.calculation, 'result_hash')}
      </p>
    </InspectorPanel>
  );
}

export function SnapshotInspector({ data }: { readonly data: MarketsOverview }) {
  const coverage = data.coverage;
  return (
    <InspectorPanel subject="Carte des marchés">
      <dl className="vx-inspector-facts" data-testid="markets-snapshot-facts">
        <div>
          <dt>Snapshot</dt>
          <dd>
            v{publie(data.snapshot_version)} · <code>{publie(data.engine_version)}</code>
          </dd>
        </div>
        <div>
          <dt>as_of</dt>
          <dd>{data.as_of === null ? 'non publié' : <time dateTime={data.as_of}>{data.as_of}</time>}</dd>
        </div>
        <div>
          <dt>Âge publié</dt>
          <dd>{data.age_seconds === null ? 'non publié' : `${data.age_seconds} s`}</dd>
        </div>
        <div>
          <dt>Population</dt>
          <dd>
            <code>{publie(data.population)}</code>
          </dd>
        </div>
        <div>
          <dt>État worker</dt>
          <dd>
            <code>{publie(data.data_state)}</code>
          </dd>
        </div>
        <div>
          <dt>Unité</dt>
          <dd>
            <code>{publie(data.unit)}</code> affichée en {publie(data.display_unit)}
          </dd>
        </div>
        <div>
          <dt>Couverture</dt>
          <dd>
            {coverage === null
              ? 'non publiée'
              : `${coverage.covered}/${coverage.expected} couverts · ${coverage.discarded} écartés · ${coverage.received} reçus · ${coverage.observations_considered} observations`}
          </dd>
        </div>
        <div>
          <dt>Fenêtre</dt>
          <dd>{coverage === null ? 'non publiée' : `${coverage.lookback_seconds} s de recul`}</dd>
        </div>
      </dl>
      <p className="vx-inspector-note">
        Sélectionner un instrument (tuile, puce sectorielle ou ligne de table) pour lire ses
        chaînes publiées et la lignée de son calcul.
      </p>
    </InspectorPanel>
  );
}
