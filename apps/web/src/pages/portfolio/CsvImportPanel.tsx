import { useState } from 'react';

import { isApiError } from '../../api/client.ts';
import { postImportConfirm, postImportPreview } from '../../api/portfolioApi.ts';
import type { ImportConfirmResponse, ImportPreviewResponse } from '../../api/client.ts';
import { serverRejectionOf } from './portfolioView.ts';
import type { ServerRejectionView } from './portfolioView.ts';

/**
 * Import CSV en 3 temps : fichier → aperçu serveur (erreurs par ligne,
 * doublons potentiels — AUCUNE écriture) → confirmation.
 *
 * La confirmation renvoie l'ÉCHO INTACT des lignes valides de l'aperçu
 * (hash d'intégrité inclus, jamais reconstruit côté client) : le serveur
 * rejoue la validation et rejette toute divergence fail-closed.
 */

type Phase =
  | { readonly step: 'file' }
  | { readonly step: 'previewing' }
  | { readonly step: 'preview'; readonly preview: ImportPreviewResponse; readonly fileName: string }
  | { readonly step: 'confirming'; readonly preview: ImportPreviewResponse; readonly fileName: string }
  | { readonly step: 'recorded'; readonly receipt: ImportConfirmResponse }
  | {
      readonly step: 'rejected';
      readonly status: number;
      readonly rejection: ServerRejectionView | null;
      readonly preview: ImportPreviewResponse | null;
      readonly fileName: string | null;
    }
  | { readonly step: 'offline' };

export function CsvImportPanel({ onImported }: { readonly onImported: () => void }) {
  const [phase, setPhase] = useState<Phase>({ step: 'file' });

  async function preview(file: File): Promise<void> {
    setPhase({ step: 'previewing' });
    let csv: string;
    try {
      csv = await file.text();
    } catch {
      setPhase({
        step: 'rejected',
        status: 0,
        rejection: { code: 'FILE_UNREADABLE', message: 'fichier illisible côté navigateur', wireIssues: [] },
        preview: null,
        fileName: file.name,
      });
      return;
    }
    try {
      const result = await postImportPreview({ csv });
      setPhase({ step: 'preview', preview: result, fileName: file.name });
    } catch (error) {
      if (isApiError(error)) {
        if (error.kind === 'NETWORK') {
          setPhase({ step: 'offline' });
          return;
        }
        if (error.status !== null && error.kind === 'HTTP') {
          setPhase({
            step: 'rejected',
            status: error.status,
            rejection: serverRejectionOf(error.detail),
            preview: null,
            fileName: file.name,
          });
          return;
        }
      }
      setPhase({ step: 'rejected', status: 0, rejection: null, preview: null, fileName: file.name });
    }
  }

  async function confirm(previewResult: ImportPreviewResponse, fileName: string): Promise<void> {
    setPhase({ step: 'confirming', preview: previewResult, fileName });
    try {
      // Écho INTACT : les objets de l'aperçu partent tels quels, hash compris.
      const receipt = await postImportConfirm({ rows: previewResult.rows_valid });
      setPhase({ step: 'recorded', receipt });
      onImported();
    } catch (error) {
      if (isApiError(error)) {
        if (error.kind === 'NETWORK') {
          setPhase({ step: 'offline' });
          return;
        }
        if (error.status !== null && error.kind === 'HTTP') {
          setPhase({
            step: 'rejected',
            status: error.status,
            rejection: serverRejectionOf(error.detail),
            preview: previewResult,
            fileName,
          });
          return;
        }
      }
      setPhase({ step: 'rejected', status: 0, rejection: null, preview: previewResult, fileName });
    }
  }

  return (
    <section className="vx-pf-import" aria-labelledby="vx-pf-import-title">
      <h2 id="vx-pf-import-title">Import CSV (aperçu puis confirmation)</h2>
      <p className="vx-pf-form-note" role="note">
        Temps 1 : choisir le fichier. Temps 2 : le serveur valide chaque ligne SANS rien écrire
        (erreurs et doublons potentiels affichés). Temps 3 : confirmer — seules les lignes valides,
        renvoyées telles quelles avec leur hash d'intégrité, sont enregistrées (source
        IMPORT_CONFIRMED).
      </p>

      <label htmlFor="pf-import-file" className="vx-pf-import-file">
        Fichier CSV du journal
        <input
          id="pf-import-file"
          type="file"
          accept=".csv,text/csv"
          disabled={phase.step === 'previewing' || phase.step === 'confirming'}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file !== undefined) {
              void preview(file);
            }
            event.target.value = '';
          }}
        />
      </label>

      <div aria-live="polite" data-testid="pf-import-outcome">
        {phase.step === 'previewing' || phase.step === 'confirming' ? (
          <p role="status">Validation serveur en cours…</p>
        ) : null}

        {phase.step === 'preview' || phase.step === 'confirming' ? (
          <div className="vx-pf-import-preview" data-testid="pf-import-preview">
            <h3>
              Aperçu de « {phase.fileName} » — {phase.preview.rows_total} ligne(s) lue(s),{' '}
              {phase.preview.rows_valid.length} valide(s), {phase.preview.rows_invalid.length} en
              erreur, {phase.preview.potential_duplicates.length} doublon(s) potentiel(s)
            </h3>
            <p className="vx-pf-import-limits">
              Limites serveur : {phase.preview.max_bytes} octets, {phase.preview.max_rows} lignes de
              données. Aucune écriture n'a eu lieu à ce stade.
            </p>

            {phase.preview.rows_invalid.length > 0 ? (
              <table className="vx-pf-import-errors" aria-label="Lignes rejetées par la validation serveur">
                <thead>
                  <tr>
                    <th scope="col">Ligne</th>
                    <th scope="col">Codes d'erreur serveur</th>
                  </tr>
                </thead>
                <tbody>
                  {phase.preview.rows_invalid.map((row) => (
                    <tr key={row.row_number} data-testid={`pf-import-error-${row.row_number}`}>
                      <th scope="row" className="vx-num">
                        {row.row_number}
                      </th>
                      <td>
                        {row.errors.map((code) => (
                          <code key={code} className="vx-pf-import-error-code">
                            {code}
                          </code>
                        ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : null}

            {phase.preview.potential_duplicates.length > 0 ? (
              <ul className="vx-pf-import-duplicates">
                {phase.preview.potential_duplicates.map((dup) => (
                  <li key={dup.row_number}>
                    Ligne {dup.row_number} : correspond aux lignes de journal n°
                    {dup.matching_transaction_ids.join(', n°')} — information, jamais un rejet
                    silencieux.
                  </li>
                ))}
              </ul>
            ) : null}

            {phase.preview.rows_valid.length > 0 ? (
              <div className="vx-pf-table-scroll" tabIndex={0} role="region" aria-label="Lignes valides défilantes">
                <table className="vx-pf-import-valid" aria-label="Lignes valides prêtes à confirmer (écho serveur)">
                  <thead>
                    <tr>
                      <th scope="col">Ligne</th>
                      <th scope="col">Nature</th>
                      <th scope="col">Ticker</th>
                      <th scope="col">Quantité</th>
                      <th scope="col">Prix</th>
                      <th scope="col">Impact</th>
                      <th scope="col">Frais</th>
                      <th scope="col">Devise</th>
                      <th scope="col">Effet le</th>
                    </tr>
                  </thead>
                  <tbody>
                    {phase.preview.rows_valid.map((row) => (
                      <tr key={row.row_number}>
                        <th scope="row" className="vx-num">
                          {row.row_number}
                        </th>
                        <td>
                          <code>{row.kind}</code>
                        </td>
                        <td>{row.ticker !== '' ? <code>{row.ticker}</code> : '—'}</td>
                        <td className="vx-num">{row.quantity !== '' ? row.quantity : '—'}</td>
                        <td className="vx-num">{row.price !== '' ? row.price : '—'}</td>
                        <td className="vx-num">{row.amount}</td>
                        <td className="vx-num">{row.fees !== '' ? row.fees : '—'}</td>
                        <td>
                          <code>{row.currency}</code>
                        </td>
                        <td>
                          <time dateTime={row.effective_at}>{row.effective_at}</time>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="vx-cell-absent">Aucune ligne valide — rien à confirmer.</p>
            )}

            <div className="vx-pf-import-actions">
              <button
                type="button"
                className="vx-primary-action"
                disabled={phase.step === 'confirming' || phase.preview.rows_valid.length === 0}
                onClick={() => {
                  void confirm(phase.preview, phase.fileName);
                }}
              >
                Confirmer l'enregistrement des {phase.preview.rows_valid.length} ligne(s) valide(s)
              </button>
              <button
                type="button"
                disabled={phase.step === 'confirming'}
                onClick={() => {
                  setPhase({ step: 'file' });
                }}
              >
                Abandonner l'import
              </button>
            </div>
          </div>
        ) : null}

        {phase.step === 'recorded' ? (
          <p className="vx-pf-form-recorded" role="status" data-testid="pf-import-recorded">
            Import confirmé : {phase.receipt.recorded_transaction_ids.length} ligne(s) enregistrée(s)
            au journal (n°{phase.receipt.recorded_transaction_ids.join(', n°')}), source{' '}
            <code>{phase.receipt.source}</code>.
          </p>
        ) : null}

        {phase.step === 'rejected' ? (
          <div className="vx-pf-form-rejected" role="alert" data-testid="pf-import-rejected">
            <strong>
              Import refusé par le serveur ({phase.status === 0 ? 'réponse inattendue' : phase.status})
            </strong>
            {phase.rejection !== null ? (
              <p>
                Raison exacte : <code>{phase.rejection.code ?? '—'}</code>
                {phase.rejection.message !== null ? ` — ${phase.rejection.message}` : null}
                {phase.rejection.wireIssues.length > 0
                  ? ` — ${phase.rejection.wireIssues.join(' ; ')}`
                  : null}
              </p>
            ) : (
              <p>Refus sans corps lisible — aucune raison n'est inventée à la place.</p>
            )}
            <p>Rien n'a été écrit : le refus de confirmation est global (fail-closed).</p>
            <button
              type="button"
              onClick={() => {
                setPhase({ step: 'file' });
              }}
            >
              Recommencer
            </button>
          </div>
        ) : null}

        {phase.step === 'offline' ? (
          <p className="vx-pf-form-rejected" role="alert">
            API locale injoignable — aucun aperçu ni enregistrement n'a eu lieu.
          </p>
        ) : null}
      </div>
    </section>
  );
}
