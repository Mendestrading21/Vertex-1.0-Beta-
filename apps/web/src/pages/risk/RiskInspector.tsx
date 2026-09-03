import { Link } from 'react-router-dom';

import type { RiskMatrixResponse } from '../../api/client.ts';
import { FreshnessBadge } from '../../components/FreshnessBadge.tsx';
import { SnapshotFacts, publishedOr } from '../../components/inspector/SnapshotFacts.tsx';
import { InspectorPanel } from '../../shell/inspector.tsx';
import { BAND_LABELS, correlationRowsOf } from './CorrelationMatrix.tsx';
import type { RiskView } from './riskView.ts';

/**
 * Inspecteur de la page Risques (planche §9 : « mécanisme, déclencheur,
 * mitigation, limites et état de mesure »).
 *
 * Deux contenus, un panneau à la fois : l'INSTRUMENT ouvert depuis la
 * matrice — ses coefficients avec chacun des autres, avec la bande publiée,
 * ses séances perdues à l'alignement, son motif d'écart s'il en a un — sinon
 * la vérité du snapshot de la matrice. Aucune nouvelle vérité : ce panneau
 * ne reclasse aucune case et ne résume aucune corrélation.
 */

export function InstrumentInspector({
  ticker,
  view,
  onClose,
}: {
  readonly ticker: string;
  readonly view: RiskView;
  readonly onClose: () => void;
}) {
  const rows = correlationRowsOf(view);
  const row = rows.find((candidate) => candidate.ticker === ticker) ?? null;
  const lost = view.coverage.alignmentLoss.find((entry) => entry.ticker === ticker)?.lost ?? null;
  const days = view.coverage.tradingDaysPerInstrument.find((entry) => entry.ticker === ticker)?.days ?? null;
  const discard = view.coverage.discarded.find((entry) => entry.instrument === ticker) ?? null;
  return (
    <InspectorPanel subject={ticker}>
      <div className="vx-sheet-head">
        <p className="vx-inspector-note">{row?.label ?? ticker}</p>
        <button type="button" className="vx-sheet-close" onClick={onClose}>
          Fermer
        </button>
      </div>

      <SnapshotFacts
        testId="risk-instrument-facts"
        facts={[
          { label: 'Dans la matrice', value: row === null ? 'non — écarté ou hors périmètre retenu' : 'oui' },
          { label: 'Séances publiées', value: days === null ? 'non publiées' : String(days) },
          { label: 'Perdues à l’alignement', value: lost === null ? 'aucune publiée' : String(lost) },
          { label: 'Motif d’écart', value: discard === null ? 'aucun' : discard.reason },
          { label: 'Unité', value: <code>{publishedOr(view.unit)}</code> },
        ]}
      />

      <h3 className="vx-snapshot-block-title">Coefficients avec chaque instrument</h3>
      {row === null ? (
        <p className="vx-inspector-note">Aucun coefficient publié pour cet instrument.</p>
      ) : (
        <ul className="vx-inspector-list" data-testid="risk-instrument-coefficients">
          {row.cells.map((cell, index) => {
            const other = view.instruments[index];
            if (other === undefined || other.ticker === ticker) {
              return null;
            }
            return (
              <li key={other.ticker} data-band={cell.band}>
                <code>{other.ticker}</code> <code className="vx-num">{cell.value}</code>
                <span className="vx-inspector-unit"> — {BAND_LABELS[cell.band] ?? cell.band}</span>
              </li>
            );
          })}
        </ul>
      )}

      <p className="vx-inspector-note">
        <Link to={`/analysis/${encodeURIComponent(ticker)}`}>Ouvrir le dossier d’analyse</Link>
      </p>
    </InspectorPanel>
  );
}

export function MatrixInspector({ data, view }: { readonly data: RiskMatrixResponse; readonly view: RiskView | null }) {
  return (
    <InspectorPanel subject="Matrice publiée">
      <SnapshotFacts
        testId="risk-matrix-facts"
        facts={[
          { label: 'État servi', value: <code>{data.state}</code> },
          {
            label: 'Snapshot',
            value: (
              <>
                v{publishedOr(data.snapshot_version)} · <code>{publishedOr(view?.engineVersion)}</code>
              </>
            ),
          },
          {
            label: 'as_of',
            value: data.as_of === null ? 'non publié' : <time dateTime={data.as_of}>{data.as_of}</time>,
          },
          { label: 'Âge publié', value: <FreshnessBadge ageSeconds={data.age_seconds} sourceLabel="âge publié par le serveur" /> },
          { label: 'Population', value: <code>{publishedOr(view?.population)}</code> },
          { label: 'État des données', value: <code>{publishedOr(view?.dataState)}</code> },
          { label: 'Schéma', value: <code>{publishedOr(view?.schemaVersion)}</code> },
          {
            label: 'Périmètre',
            value:
              view === null || view.coverage.perimeter.length === 0
                ? 'non publié'
                : `${view.coverage.perimeter.join(', ')} — ${view.coverage.retained} retenu(s)`,
          },
          {
            label: 'Fenêtre',
            value: view?.coverage.window ?? 'non publiée',
          },
          {
            label: 'Observations',
            value: publishedOr(view?.coverage.observationsConsidered),
          },
        ]}
      />
      <p className="vx-inspector-note">
        Sélectionner un instrument (en-tête de ligne de la matrice) pour lire ses coefficients avec chacun, ses
        séances perdues et son motif d’écart.
      </p>
    </InspectorPanel>
  );
}
