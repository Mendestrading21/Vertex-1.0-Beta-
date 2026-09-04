import { useState } from 'react';

import { isApiError } from '../../../api/client.ts';
import { postThesis } from '../../../api/portfolioApi.ts';
import type { CreateThesisRequest } from '../../../api/client.ts';
import { localDateTimeToUtcIso, serverRejectionOf } from '../../portfolio/portfolioView.ts';
import type { ServerRejectionView } from '../../portfolio/portfolioView.ts';

/**
 * « Nouvelle thèse » — déclaration utilisateur : énoncé + hypothèses +
 * INVALIDATION OBLIGATOIRE (ce qui prouverait la thèse fausse fait partie de
 * l'énoncé, jamais optionnel).
 *
 * L'`idempotency_key` est générée côté client (crypto.randomUUID) au moment
 * de l'envoi initial et RÉUTILISÉE sur chaque nouvelle tentative : un rejeu
 * réseau est sûr (200 `created=false` = même thèse, succès silencieux).
 */

interface Draft {
  readonly title: string;
  readonly hypotheses: string;
  readonly invalidation: string;
  readonly ticker: string;
  readonly horizon: string;
  readonly reviewDueLocal: string;
  readonly note: string;
}

const EMPTY_DRAFT: Draft = {
  title: '',
  hypotheses: '',
  invalidation: '',
  ticker: '',
  horizon: '',
  reviewDueLocal: '',
  note: '',
};

type Outcome =
  | { readonly phase: 'idle' }
  | { readonly phase: 'invalid_input'; readonly issues: readonly string[] }
  | { readonly phase: 'pending' }
  | { readonly phase: 'created'; readonly thesisId: number; readonly replayed: boolean }
  | { readonly phase: 'rejected'; readonly status: number; readonly rejection: ServerRejectionView | null }
  | { readonly phase: 'offline' };

export function buildThesisRequest(
  draft: Draft,
  idempotencyKey: string,
): { readonly request: CreateThesisRequest | null; readonly issues: readonly string[] } {
  const issues: string[] = [];
  if (draft.title.trim() === '') {
    issues.push('titre obligatoire');
  }
  if (draft.hypotheses.trim() === '') {
    issues.push('hypothèses obligatoires');
  }
  if (draft.invalidation.trim() === '') {
    issues.push('invalidation obligatoire — dire ce qui prouverait la thèse fausse');
  }
  if (issues.length > 0) {
    return { request: null, issues };
  }
  const ticker = draft.ticker.trim();
  return {
    request: {
      title: draft.title.trim(),
      hypotheses: draft.hypotheses.trim(),
      invalidation: draft.invalidation.trim(),
      instrument: ticker === '' ? null : { ticker },
      horizon: draft.horizon.trim() === '' ? null : draft.horizon.trim(),
      review_due_at: localDateTimeToUtcIso(draft.reviewDueLocal),
      note: draft.note.trim() === '' ? null : draft.note.trim(),
      portfolio_id: null,
      idempotency_key: idempotencyKey,
    },
    issues: [],
  };
}

export function ThesisForm({ onCreated }: { readonly onCreated: () => void }) {
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [outcome, setOutcome] = useState<Outcome>({ phase: 'idle' });
  // Clé de rejeu de l'envoi EN COURS : posée au premier essai, réutilisée
  // sur retry, remise à zéro après succès ou modification du brouillon.
  const [inFlightKey, setInFlightKey] = useState<string | null>(null);

  function update<K extends keyof Draft>(key: K, value: Draft[K]): void {
    setDraft((previous) => ({ ...previous, [key]: value }));
    setInFlightKey(null); // brouillon modifié = nouvelle opération, nouvelle clé
  }

  async function submit(): Promise<void> {
    const key = inFlightKey ?? crypto.randomUUID();
    setInFlightKey(key);
    const built = buildThesisRequest(draft, key);
    if (built.request === null) {
      setOutcome({ phase: 'invalid_input', issues: built.issues });
      return;
    }
    setOutcome({ phase: 'pending' });
    try {
      const receipt = await postThesis(built.request);
      setOutcome({ phase: 'created', thesisId: receipt.thesis_id, replayed: !receipt.created });
      setDraft(EMPTY_DRAFT);
      setInFlightKey(null);
      onCreated();
    } catch (error) {
      if (isApiError(error)) {
        if (error.kind === 'NETWORK') {
          setOutcome({ phase: 'offline' }); // clé conservée pour le retry
          return;
        }
        if (error.status !== null && error.kind === 'HTTP') {
          setOutcome({
            phase: 'rejected',
            status: error.status,
            rejection: serverRejectionOf(error.detail),
          });
          return;
        }
      }
      setOutcome({ phase: 'rejected', status: 0, rejection: null });
    }
  }

  return (
    <section className="vx-thesis-form" aria-labelledby="vx-thesis-form-title">
      <h2 id="vx-thesis-form-title">Nouvelle thèse</h2>
      <form
        className="vx-thesis-form-grid"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <label htmlFor="thesis-title" className="vx-pf-form-wide">
          Titre
          <input
            id="thesis-title"
            type="text"
            value={draft.title}
            onChange={(event) => {
              update('title', event.target.value);
            }}
          />
        </label>
        <label htmlFor="thesis-hypotheses" className="vx-pf-form-wide">
          Hypothèses (ce que la thèse suppose vrai)
          <textarea
            id="thesis-hypotheses"
            rows={3}
            value={draft.hypotheses}
            onChange={(event) => {
              update('hypotheses', event.target.value);
            }}
          />
        </label>
        <label htmlFor="thesis-invalidation" className="vx-pf-form-wide">
          Invalidation (OBLIGATOIRE — ce qui prouverait la thèse fausse)
          <textarea
            id="thesis-invalidation"
            rows={2}
            value={draft.invalidation}
            onChange={(event) => {
              update('invalidation', event.target.value);
            }}
          />
        </label>
        <label htmlFor="thesis-ticker">
          Ticker (facultatif)
          <input
            id="thesis-ticker"
            type="text"
            value={draft.ticker}
            onChange={(event) => {
              update('ticker', event.target.value);
            }}
          />
        </label>
        <label htmlFor="thesis-horizon">
          Horizon (texte libre, facultatif)
          <input
            id="thesis-horizon"
            type="text"
            value={draft.horizon}
            onChange={(event) => {
              update('horizon', event.target.value);
            }}
          />
        </label>
        <label htmlFor="thesis-review-due">
          Revue prévue le (heure locale → UTC, facultatif)
          <input
            id="thesis-review-due"
            type="datetime-local"
            value={draft.reviewDueLocal}
            onChange={(event) => {
              update('reviewDueLocal', event.target.value);
            }}
          />
        </label>
        <label htmlFor="thesis-note">
          Note (facultative)
          <input
            id="thesis-note"
            type="text"
            value={draft.note}
            onChange={(event) => {
              update('note', event.target.value);
            }}
          />
        </label>
        <div className="vx-pf-form-actions">
          <button type="submit" className="vx-primary-action" disabled={outcome.phase === 'pending'}>
            {outcome.phase === 'offline' ? 'Réessayer (même clé de rejeu)' : 'Enregistrer la thèse'}
          </button>
        </div>
      </form>

      <div aria-live="polite" data-testid="thesis-form-outcome">
        {outcome.phase === 'invalid_input' ? (
          <div className="vx-pf-form-invalid" role="alert">
            <strong>Entrée incomplète — rien n'a été envoyé</strong>
            <ul>
              {outcome.issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          </div>
        ) : outcome.phase === 'created' ? (
          <p className="vx-pf-form-recorded" role="status" data-testid="thesis-form-created">
            Thèse enregistrée (n°{outcome.thesisId}) — rafraîchissement de la file mis en file côté
            serveur.
          </p>
        ) : outcome.phase === 'rejected' ? (
          <div className="vx-pf-form-rejected" role="alert" data-testid="thesis-form-rejected">
            <strong>
              Thèse refusée par le serveur ({outcome.status === 0 ? 'réponse inattendue' : outcome.status})
            </strong>
            {outcome.rejection !== null ? (
              outcome.rejection.wireIssues.length > 0 ? (
                <ul>
                  {outcome.rejection.wireIssues.map((issue) => (
                    <li key={issue}>
                      <code>{issue}</code>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>
                  Raison exacte :{' '}
                  {outcome.rejection.code === null ? (
                    <span className="vx-cell-absent">code de refus non publié</span>
                  ) : (
                    <code>{outcome.rejection.code}</code>
                  )}
                  {outcome.rejection.message !== null ? ` — ${outcome.rejection.message}` : null}
                </p>
              )
            ) : (
              <p>Refus sans corps lisible — aucune raison n'est inventée à la place.</p>
            )}
          </div>
        ) : outcome.phase === 'offline' ? (
          <p className="vx-pf-form-rejected" role="alert">
            Réseau indisponible — la thèse n'est peut-être pas enregistrée. « Réessayer » renvoie la
            MÊME clé de rejeu : jamais de doublon.
          </p>
        ) : null}
      </div>
    </section>
  );
}
