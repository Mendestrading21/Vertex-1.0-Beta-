import { useState } from 'react';

import { isApiError } from '../../api/client.ts';
import { getPortfolioExportCsv, postCompensation } from '../../api/portfolioApi.ts';
import type { LedgerTransactionEntry } from '../../api/client.ts';
import { serverRejectionOf } from './portfolioView.ts';
import type { ServerRejectionView } from './portfolioView.ts';

/**
 * Journal (ledger) — lignes VERBATIM de l'API, append-only.
 *
 * - une ligne compensée et sa ligne compensatoire restent visibles et LIÉES
 *   (`compensates` / `compensated_by`) : l'historique n'est jamais édité ;
 * - « Correction compensatoire » ajoute la ligne inverse d'un fait (note
 *   obligatoire, confirmation explicite) ; un second essai sur la même ligne
 *   est un 409 serveur, affiché verbatim ;
 * - l'export télécharge le CSV SERVI PAR L'API (aucune re-sérialisation).
 */

type CompensationPhase =
  | { readonly phase: 'confirming'; readonly transactionId: number; readonly note: string }
  | { readonly phase: 'pending'; readonly transactionId: number }
  | {
      readonly phase: 'rejected';
      readonly transactionId: number;
      readonly status: number;
      readonly rejection: ServerRejectionView | null;
    }
  | { readonly phase: 'offline'; readonly transactionId: number }
  | null;

function instrumentTicker(entry: LedgerTransactionEntry): string | null {
  const instrument = entry.instrument;
  if (typeof instrument !== 'object' || instrument === null) {
    return null;
  }
  const ticker = (instrument as Record<string, unknown>)['ticker'];
  return typeof ticker === 'string' && ticker !== '' ? ticker : null;
}

/** Déclenche le téléchargement navigateur d'un texte servi par l'API. */
function saveTextAsFile(text: string, filename: string, mediaType: string): void {
  const blob = new Blob([text], { type: mediaType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function LedgerPanel({
  transactions,
  onCompensated,
}: {
  readonly transactions: readonly LedgerTransactionEntry[];
  readonly onCompensated: () => void;
}) {
  const [compensation, setCompensation] = useState<CompensationPhase>(null);
  const [exportState, setExportState] = useState<'idle' | 'pending' | 'failed'>('idle');

  async function confirmCompensation(transactionId: number, note: string): Promise<void> {
    setCompensation({ phase: 'pending', transactionId });
    try {
      await postCompensation(transactionId, { note });
      setCompensation(null);
      onCompensated();
    } catch (error) {
      if (isApiError(error)) {
        if (error.kind === 'NETWORK') {
          setCompensation({ phase: 'offline', transactionId });
          return;
        }
        if (error.status !== null && error.kind === 'HTTP') {
          setCompensation({
            phase: 'rejected',
            transactionId,
            status: error.status,
            rejection: serverRejectionOf(error.detail),
          });
          return;
        }
      }
      setCompensation({ phase: 'rejected', transactionId, status: 0, rejection: null });
    }
  }

  async function exportCsv(): Promise<void> {
    setExportState('pending');
    try {
      const csv = await getPortfolioExportCsv();
      saveTextAsFile(csv, 'vertex-ledger.csv', 'text/csv');
      setExportState('idle');
    } catch {
      setExportState('failed');
    }
  }

  return (
    <section className="vx-pf-ledger" aria-labelledby="vx-pf-ledger-title">
      <div className="vx-pf-ledger-head">
        <h2 id="vx-pf-ledger-title">Journal ({transactions.length} ligne(s))</h2>
        <button
          type="button"
          className="vx-markets-export"
          disabled={exportState === 'pending'}
          onClick={() => {
            void exportCsv();
          }}
        >
          Exporter le journal (CSV servi par l'API)
        </button>
      </div>
      {exportState === 'failed' ? (
        <p role="alert" className="vx-pf-form-rejected">
          Export impossible — le serveur n'a pas fourni le CSV ; rien n'a été généré localement.
        </p>
      ) : null}

      {transactions.length === 0 ? (
        <p className="vx-cell-absent" data-testid="pf-ledger-empty">
          Journal vide — aucun fait déclaré pour l'instant.
        </p>
      ) : (
        <div className="vx-pf-table-scroll" tabIndex={0} role="region" aria-label="Journal défilant">
          <table className="vx-pf-ledger-table" aria-label="Journal des faits déclarés (append-only)">
            <thead>
              <tr>
                <th scope="col">N°</th>
                <th scope="col">Effet le (UTC)</th>
                <th scope="col">Nature</th>
                <th scope="col">Ticker</th>
                <th scope="col">Quantité</th>
                <th scope="col">Prix</th>
                <th scope="col">Impact</th>
                <th scope="col">Frais</th>
                <th scope="col">Devise</th>
                <th scope="col">Source</th>
                <th scope="col">Compensation</th>
                <th scope="col">Note</th>
                <th scope="col">Corriger</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((entry) => {
                const ticker = instrumentTicker(entry);
                const isCompensatingRow = entry.compensates !== null;
                const alreadyCompensated = entry.compensated_by !== null;
                return (
                  <tr key={entry.id} data-testid={`pf-ledger-row-${entry.id}`}>
                    <th scope="row" className="vx-num">
                      {entry.id}
                    </th>
                    <td>
                      <time dateTime={entry.effective_at}>{entry.effective_at}</time>
                    </td>
                    <td>
                      <code>{entry.kind}</code>
                    </td>
                    <td>{ticker !== null ? <code>{ticker}</code> : '—'}</td>
                    <td className="vx-num">{entry.quantity ?? '—'}</td>
                    <td className="vx-num">{entry.price ?? '—'}</td>
                    <td className="vx-num">{entry.amount}</td>
                    <td className="vx-num">{entry.fees}</td>
                    <td>
                      <code>{entry.currency}</code>
                    </td>
                    <td>
                      <code>{entry.source}</code>
                    </td>
                    <td>
                      {isCompensatingRow ? (
                        <span className="vx-badge vx-badge-warning">compense n°{entry.compensates}</span>
                      ) : alreadyCompensated ? (
                        <span className="vx-badge vx-badge-warning">
                          compensée par n°{entry.compensated_by}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td>{entry.note ?? '—'}</td>
                    <td>
                      {!isCompensatingRow && !alreadyCompensated ? (
                        <button
                          type="button"
                          className="vx-pf-compensate"
                          onClick={() => {
                            setCompensation({ phase: 'confirming', transactionId: entry.id, note: '' });
                          }}
                        >
                          Correction compensatoire
                        </button>
                      ) : (
                        <span className="vx-cell-absent">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {compensation !== null && compensation.phase === 'confirming' ? (
        <div className="vx-pf-compensate-confirm" role="group" aria-label="Confirmation de correction compensatoire" data-testid="pf-compensate-confirm">
          <p>
            Ajouter la ligne compensatoire de la ligne n°{compensation.transactionId} ? La ligne
            d'origine reste au journal ; la correction inverse impact, frais et quantité. La note
            de raison est obligatoire.
          </p>
          <label htmlFor="pf-compensate-note">
            Raison de la correction
            <input
              id="pf-compensate-note"
              type="text"
              value={compensation.note}
              onChange={(event) => {
                setCompensation({ ...compensation, note: event.target.value });
              }}
            />
          </label>
          <div className="vx-pf-compensate-actions">
            <button
              type="button"
              className="vx-primary-action"
              disabled={compensation.note.trim() === ''}
              onClick={() => {
                void confirmCompensation(compensation.transactionId, compensation.note.trim());
              }}
            >
              Confirmer la correction compensatoire
            </button>
            <button
              type="button"
              onClick={() => {
                setCompensation(null);
              }}
            >
              Annuler
            </button>
          </div>
        </div>
      ) : null}
      {compensation !== null && compensation.phase === 'rejected' ? (
        <div className="vx-pf-form-rejected" role="alert" data-testid="pf-compensate-rejected">
          <strong>
            Correction de la ligne n°{compensation.transactionId} refusée (
            {compensation.status === 0 ? 'réponse inattendue' : compensation.status})
          </strong>
          {compensation.rejection !== null ? (
            <p>
              Raison exacte : <code>{compensation.rejection.code ?? '—'}</code>
              {compensation.rejection.message !== null ? ` — ${compensation.rejection.message}` : null}
              {compensation.rejection.wireIssues.length > 0
                ? ` — ${compensation.rejection.wireIssues.join(' ; ')}`
                : null}
            </p>
          ) : (
            <p>Refus sans corps lisible — aucune raison n'est inventée à la place.</p>
          )}
          <button
            type="button"
            onClick={() => {
              setCompensation(null);
            }}
          >
            Fermer
          </button>
        </div>
      ) : null}
      {compensation !== null && compensation.phase === 'offline' ? (
        <p className="vx-pf-form-rejected" role="alert">
          API locale injoignable — la correction de la ligne n°{compensation.transactionId} n'a pas
          été enregistrée.
        </p>
      ) : null}
    </section>
  );
}
