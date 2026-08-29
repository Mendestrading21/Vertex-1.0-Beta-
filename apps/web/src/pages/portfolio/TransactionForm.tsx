import { useState } from 'react';

import { isApiError } from '../../api/client.ts';
import { postTransaction } from '../../api/portfolioApi.ts';
import type { LedgerEventKind, RecordTransactionRequest } from '../../api/client.ts';
import {
  LEDGER_KINDS,
  LEDGER_KIND_LABELS,
  POSITION_KINDS,
  localDateTimeToUtcIso,
  serverRejectionOf,
} from './portfolioView.ts';
import type { ServerRejectionView } from './portfolioView.ts';

/**
 * « Enregistrer une transaction (déjà exécutée hors Vertex) » — journal
 * comptable de FAITS PASSÉS uniquement.
 *
 * - Champs décimaux en TEXTE, transmis tels quels (chaînes exactes, jamais
 *   de conversion flottante) ; la validation de fond est SERVEUR (422
 *   affiché verbatim : code + message ou défauts Pydantic) ;
 * - `effective_at` saisi en heure locale (datetime-local) et converti en
 *   instant UTC ISO à l'envoi ;
 * - rien ici n'est une instruction ni un ticket : le serveur n'a aucune
 *   capacité de transmission et cette page n'en invente pas.
 */

interface FormDraft {
  readonly kind: LedgerEventKind;
  readonly ticker: string;
  readonly quantity: string;
  readonly price: string;
  readonly amount: string;
  readonly currency: string;
  readonly fees: string;
  readonly effectiveAtLocal: string;
  readonly note: string;
}

const EMPTY_DRAFT: FormDraft = {
  kind: 'DEPOSIT',
  ticker: '',
  quantity: '',
  price: '',
  amount: '',
  currency: '',
  fees: '0',
  effectiveAtLocal: '',
  note: '',
};

type Outcome =
  | { readonly phase: 'idle' }
  | { readonly phase: 'invalid_input'; readonly issues: readonly string[] }
  | { readonly phase: 'pending' }
  | { readonly phase: 'recorded'; readonly transactionId: number }
  | { readonly phase: 'rejected'; readonly status: number; readonly rejection: ServerRejectionView | null }
  | { readonly phase: 'offline' }
  | { readonly phase: 'error' };

export function buildTransactionRequest(
  draft: FormDraft,
): { readonly request: RecordTransactionRequest | null; readonly issues: readonly string[] } {
  const issues: string[] = [];
  const effectiveAt = localDateTimeToUtcIso(draft.effectiveAtLocal);
  if (effectiveAt === null) {
    issues.push("date/heure d'effet obligatoire (heure locale, convertie en UTC à l'envoi)");
  }
  if (draft.amount.trim() === '') {
    issues.push('impact de trésorerie signé obligatoire (chaîne décimale)');
  }
  if (draft.currency.trim() === '') {
    issues.push('devise obligatoire');
  }
  if (POSITION_KINDS.has(draft.kind) && draft.ticker.trim() === '') {
    issues.push('ticker obligatoire pour un fait de position (achat/vente enregistré)');
  }
  if (issues.length > 0 || effectiveAt === null) {
    return { request: null, issues };
  }
  const ticker = draft.ticker.trim();
  return {
    request: {
      kind: draft.kind,
      amount: draft.amount.trim(),
      currency: draft.currency.trim(),
      fees: draft.fees.trim() === '' ? '0' : draft.fees.trim(),
      effective_at: effectiveAt,
      instrument: ticker === '' ? null : { ticker },
      quantity: draft.quantity.trim() === '' ? null : draft.quantity.trim(),
      price: draft.price.trim() === '' ? null : draft.price.trim(),
      note: draft.note.trim() === '' ? null : draft.note.trim(),
    },
    issues: [],
  };
}

export function TransactionForm({ onRecorded }: { readonly onRecorded: () => void }) {
  const [draft, setDraft] = useState<FormDraft>(EMPTY_DRAFT);
  const [outcome, setOutcome] = useState<Outcome>({ phase: 'idle' });

  function update<K extends keyof FormDraft>(key: K, value: FormDraft[K]): void {
    setDraft((previous) => ({ ...previous, [key]: value }));
  }

  async function submit(): Promise<void> {
    const built = buildTransactionRequest(draft);
    if (built.request === null) {
      setOutcome({ phase: 'invalid_input', issues: built.issues });
      return;
    }
    setOutcome({ phase: 'pending' });
    try {
      const receipt = await postTransaction(built.request);
      setOutcome({ phase: 'recorded', transactionId: receipt.transaction_id });
      setDraft(EMPTY_DRAFT);
      onRecorded();
    } catch (error) {
      if (isApiError(error)) {
        if (error.kind === 'NETWORK') {
          setOutcome({ phase: 'offline' });
          return;
        }
        if (error.status !== null && error.status >= 400 && error.status < 500 && error.kind === 'HTTP') {
          setOutcome({
            phase: 'rejected',
            status: error.status,
            rejection: serverRejectionOf(error.detail),
          });
          return;
        }
      }
      setOutcome({ phase: 'error' });
    }
  }

  const needsInstrument = POSITION_KINDS.has(draft.kind);

  return (
    <section className="vx-pf-form" aria-labelledby="vx-pf-form-title">
      <h2 id="vx-pf-form-title">Enregistrer une transaction (déjà exécutée hors Vertex)</h2>
      <p className="vx-pf-form-note" role="note">
        Journal comptable de faits passés : la saisie décrit ce qui a DÉJÀ eu lieu hors Vertex.
        Rien n'est transmis à un courtier — cette capacité n'existe pas.
      </p>
      <form
        className="vx-pf-form-grid"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <label htmlFor="pf-kind">
          Nature du fait
          <select
            id="pf-kind"
            value={draft.kind}
            onChange={(event) => {
              update('kind', event.target.value as LedgerEventKind);
            }}
          >
            {LEDGER_KINDS.map((kind) => (
              <option key={kind} value={kind}>
                {LEDGER_KIND_LABELS[kind]} — {kind}
              </option>
            ))}
          </select>
        </label>
        <label htmlFor="pf-effective-at">
          Effet le (heure locale → UTC)
          <input
            id="pf-effective-at"
            type="datetime-local"
            value={draft.effectiveAtLocal}
            onChange={(event) => {
              update('effectiveAtLocal', event.target.value);
            }}
          />
        </label>
        <label htmlFor="pf-amount">
          Impact de trésorerie signé (décimal)
          <input
            id="pf-amount"
            type="text"
            inputMode="decimal"
            value={draft.amount}
            onChange={(event) => {
              update('amount', event.target.value);
            }}
          />
        </label>
        <label htmlFor="pf-currency">
          Devise
          <input
            id="pf-currency"
            type="text"
            value={draft.currency}
            onChange={(event) => {
              update('currency', event.target.value);
            }}
          />
        </label>
        <label htmlFor="pf-fees">
          Frais (décimal)
          <input
            id="pf-fees"
            type="text"
            inputMode="decimal"
            value={draft.fees}
            onChange={(event) => {
              update('fees', event.target.value);
            }}
          />
        </label>
        <label htmlFor="pf-ticker">
          Ticker {needsInstrument ? '(obligatoire pour ce fait)' : '(facultatif)'}
          <input
            id="pf-ticker"
            type="text"
            value={draft.ticker}
            onChange={(event) => {
              update('ticker', event.target.value);
            }}
          />
        </label>
        <label htmlFor="pf-quantity">
          Quantité (décimal)
          <input
            id="pf-quantity"
            type="text"
            inputMode="decimal"
            value={draft.quantity}
            onChange={(event) => {
              update('quantity', event.target.value);
            }}
          />
        </label>
        <label htmlFor="pf-price">
          Prix unitaire (décimal)
          <input
            id="pf-price"
            type="text"
            inputMode="decimal"
            value={draft.price}
            onChange={(event) => {
              update('price', event.target.value);
            }}
          />
        </label>
        <label htmlFor="pf-note" className="vx-pf-form-wide">
          Note (facultative)
          <input
            id="pf-note"
            type="text"
            value={draft.note}
            onChange={(event) => {
              update('note', event.target.value);
            }}
          />
        </label>
        <div className="vx-pf-form-actions">
          <button type="submit" className="vx-primary-action" disabled={outcome.phase === 'pending'}>
            Enregistrer la transaction
          </button>
        </div>
      </form>

      <div aria-live="polite" data-testid="pf-form-outcome">
        {outcome.phase === 'invalid_input' ? (
          <div className="vx-pf-form-invalid" role="alert">
            <strong>Entrée incomplète — rien n'a été envoyé</strong>
            <ul>
              {outcome.issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          </div>
        ) : outcome.phase === 'recorded' ? (
          <p className="vx-pf-form-recorded" role="status">
            Fait enregistré au journal (ligne n°{outcome.transactionId}) — revalorisation mise en
            file côté serveur.
          </p>
        ) : outcome.phase === 'rejected' ? (
          <div className="vx-pf-form-rejected" role="alert" data-testid="pf-form-rejected">
            <strong>Enregistrement refusé par le serveur ({outcome.status})</strong>
            {outcome.rejection === null ? (
              <p>Refus sans corps lisible — aucune raison n'est inventée à la place.</p>
            ) : outcome.rejection.wireIssues.length > 0 ? (
              <ul>
                {outcome.rejection.wireIssues.map((issue) => (
                  <li key={issue}>
                    <code>{issue}</code>
                  </li>
                ))}
              </ul>
            ) : (
              <p>
                Raison exacte : <code>{outcome.rejection.code ?? '—'}</code>
                {outcome.rejection.message !== null ? ` — ${outcome.rejection.message}` : null}
              </p>
            )}
          </div>
        ) : outcome.phase === 'offline' ? (
          <p className="vx-pf-form-rejected" role="alert">
            API locale injoignable — le fait N'A PAS été enregistré.
          </p>
        ) : outcome.phase === 'error' ? (
          <p className="vx-pf-form-rejected" role="alert">
            Réponse inattendue de l'API — état de l'enregistrement inconnu, vérifier le journal.
          </p>
        ) : null}
      </div>
    </section>
  );
}
