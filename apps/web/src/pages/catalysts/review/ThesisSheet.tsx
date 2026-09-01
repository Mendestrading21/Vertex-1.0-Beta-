import { useEffect, useId, useRef, useState } from 'react';
import type { KeyboardEvent as ReactKeyboardEvent } from 'react';

import { isApiError } from '../../../api/client.ts';
import { postThesisRevision } from '../../../api/portfolioApi.ts';
import type { ThesisRevisionRequest } from '../../../api/client.ts';
import { serverRejectionOf } from '../../portfolio/portfolioView.ts';
import type { ServerRejectionView } from '../../portfolio/portfolioView.ts';
import { thesisStatusLabel } from './followUpView.ts';
import type { ThesisEntryView } from './followUpView.ts';

/**
 * Fiche thèse — panneau latéral accessible (focus piégé, Échap, restitution
 * du focus par le parent au démontage).
 *
 * Contenu : hypothèses, invalidation (le falsifiable), état PROJETÉ par le
 * serveur et repères d'historique append-only (création, dernière action,
 * nombre de révisions). L'historique intégral des révisions n'est pas servi
 * par l'API (aucune route de lecture) : il est affiché comme NON DISPONIBLE,
 * jamais reconstruit.
 *
 * Actions de revue → POST /theses/{id}/revisions avec une idempotency_key
 * générée CÔTÉ CLIENT (crypto.randomUUID) au moment où l'action est engagée
 * et RÉUTILISÉE à chaque nouvelle tentative : un rejeu réseau est sûr, la
 * réponse 200 `created=false` (déjà enregistré) est traitée comme un succès
 * silencieux.
 */

type ActionKind = 'REVIEWED' | 'SNOOZED' | 'NOTE_UPDATED' | 'ARCHIVED' | 'REACTIVATED';

const ACTION_LABELS: Readonly<Record<ActionKind, string>> = {
  REVIEWED: 'Revue faite',
  SNOOZED: 'Reporter',
  NOTE_UPDATED: 'Ajouter une note',
  ARCHIVED: 'Archiver',
  REACTIVATED: 'Réactiver',
};

interface PendingAction {
  readonly kind: ActionKind;
  /** Clé de rejeu générée UNE fois, réutilisée sur chaque tentative. */
  readonly idempotencyKey: string;
  readonly note: string;
  readonly snoozeUntilLocal: string;
}

type ActionOutcome =
  | { readonly phase: 'idle' }
  | { readonly phase: 'pending' }
  | { readonly phase: 'done'; readonly kind: ActionKind; readonly replayed: boolean }
  | {
      readonly phase: 'rejected';
      readonly status: number;
      readonly rejection: ServerRejectionView | null;
    }
  | { readonly phase: 'offline' };

export function buildRevisionRequest(action: PendingAction): ThesisRevisionRequest | null {
  if (action.kind === 'SNOOZED') {
    if (action.snoozeUntilLocal === '') {
      return null;
    }
    const parsed = new Date(action.snoozeUntilLocal);
    if (Number.isNaN(parsed.getTime())) {
      return null;
    }
    return {
      action: 'SNOOZED',
      idempotency_key: action.idempotencyKey,
      note: action.note.trim() === '' ? null : action.note.trim(),
      snapshot_ref: null,
      snooze_until: parsed.toISOString(),
    };
  }
  if (action.kind === 'NOTE_UPDATED' && action.note.trim() === '') {
    return null;
  }
  return {
    action: action.kind,
    idempotency_key: action.idempotencyKey,
    note: action.note.trim() === '' ? null : action.note.trim(),
    snapshot_ref: null,
    snooze_until: null,
  };
}

export function ThesisSheet({
  thesis,
  onClose,
  onRevised,
}: {
  readonly thesis: ThesisEntryView;
  readonly onClose: () => void;
  readonly onRevised: () => void;
}) {
  const sheetRef = useRef<HTMLDivElement | null>(null);
  const titleId = useId();
  const [pending, setPending] = useState<PendingAction | null>(null);
  const [outcome, setOutcome] = useState<ActionOutcome>({ phase: 'idle' });

  useEffect(() => {
    const sheet = sheetRef.current;
    if (sheet !== null) {
      sheet.querySelector<HTMLElement>('button')?.focus();
    }
  }, []);

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      event.stopPropagation();
      onClose();
      return;
    }
    if (event.key !== 'Tab') {
      return;
    }
    const sheet = sheetRef.current;
    if (sheet === null) {
      return;
    }
    const focusables = Array.from(
      sheet.querySelectorAll<HTMLElement>(
        'button, a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      ),
    ).filter((element) => !element.hasAttribute('disabled'));
    if (focusables.length === 0) {
      return;
    }
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first?.focus();
    }
  };

  function startAction(kind: ActionKind): void {
    setOutcome({ phase: 'idle' });
    setPending({
      kind,
      idempotencyKey: crypto.randomUUID(),
      note: '',
      snoozeUntilLocal: '',
    });
  }

  async function send(action: PendingAction): Promise<void> {
    const request = buildRevisionRequest(action);
    if (request === null) {
      return;
    }
    setOutcome({ phase: 'pending' });
    try {
      const receipt = await postThesisRevision(thesis.id, request);
      // `created=false` = rejeu idempotent : même révision, rien de réécrit —
      // traité comme le même succès, sans avertissement parasite.
      setOutcome({ phase: 'done', kind: action.kind, replayed: !receipt.created });
      setPending(null);
      onRevised();
    } catch (error) {
      if (isApiError(error)) {
        if (error.kind === 'NETWORK') {
          // La clé de rejeu est CONSERVÉE : « Réessayer » renverra la même.
          setOutcome({ phase: 'offline' });
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

  const needsDate = pending?.kind === 'SNOOZED';
  const needsNote = pending?.kind === 'NOTE_UPDATED';
  const sendDisabled =
    pending === null ||
    outcome.phase === 'pending' ||
    (needsDate && pending.snoozeUntilLocal === '') ||
    (needsNote && pending.note.trim() === '');

  return (
    <div
      className="vx-sheet"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      ref={sheetRef}
      onKeyDown={handleKeyDown}
      data-testid="thesis-sheet"
    >
      <div className="vx-sheet-head">
        <h2 id={titleId}>{thesis.title}</h2>
        <button type="button" className="vx-sheet-close" onClick={onClose}>
          Fermer
        </button>
      </div>

      <dl className="vx-sheet-facts">
        <div>
          <dt>État projeté (serveur)</dt>
          <dd>
            <code>{thesis.status ?? '—'}</code> ({thesisStatusLabel(thesis.status)})
            {thesis.isDue ? <span className="vx-badge vx-badge-warning"> à revoir</span> : null}
          </dd>
        </div>
        <div>
          <dt>Instrument</dt>
          <dd>{thesis.instrumentTicker !== null ? <code>{thesis.instrumentTicker}</code> : 'aucun'}</dd>
        </div>
        <div>
          <dt>Hypothèses</dt>
          <dd className="vx-thesis-text">{thesis.hypotheses ?? '—'}</dd>
        </div>
        <div>
          <dt>Invalidation (ce qui prouverait la thèse fausse)</dt>
          <dd className="vx-thesis-text" data-testid="thesis-invalidation">
            {thesis.invalidation ?? '—'}
          </dd>
        </div>
        <div>
          <dt>Horizon</dt>
          <dd>{thesis.horizon ?? '—'}</dd>
        </div>
        <div>
          <dt>Échéance de revue effective</dt>
          <dd>
            {thesis.effectiveReviewDueAt !== null ? (
              <time dateTime={thesis.effectiveReviewDueAt}>{thesis.effectiveReviewDueAt}</time>
            ) : (
              'aucune'
            )}
            {thesis.snoozeUntil !== null ? (
              <>
                {' '}
                (reportée jusqu'au <time dateTime={thesis.snoozeUntil}>{thesis.snoozeUntil}</time>)
              </>
            ) : null}
          </dd>
        </div>
      </dl>

      <section aria-label="Historique des révisions (append-only)" className="vx-thesis-history">
        <h3>Historique append-only</h3>
        <ul className="vx-sheet-list">
          <li>
            Créée le{' '}
            {thesis.createdAt !== null ? (
              <time dateTime={thesis.createdAt}>{thesis.createdAt}</time>
            ) : (
              '—'
            )}{' '}
            (révision CREATED)
          </li>
          <li>
            {thesis.revisionCount ?? '—'} révision(s) au total — dernière action :{' '}
            <code>{thesis.lastAction ?? '—'}</code>
            {thesis.lastRecordedAt !== null ? (
              <>
                {' '}
                le <time dateTime={thesis.lastRecordedAt}>{thesis.lastRecordedAt}</time>
              </>
            ) : null}
          </li>
          <li>
            Dernière revue :{' '}
            {thesis.lastReviewedAt !== null ? (
              <time dateTime={thesis.lastReviewedAt}>{thesis.lastReviewedAt}</time>
            ) : (
              'jamais'
            )}
          </li>
          <li className="vx-cell-absent">
            Détail ligne à ligne des révisions : NON DISPONIBLE — l'API ne publie pas de route de
            lecture de l'historique ; rien n'est reconstruit côté client.
          </li>
        </ul>
      </section>

      {thesis.hasNewInformation ? (
        <section aria-label="Nouvelle information" className="vx-thesis-new-info">
          <h3>
            <span className="vx-badge vx-badge-warning">nouvelle information</span>
          </h3>
          <ul className="vx-sheet-list">
            {thesis.urgencyReasons.map((reason) => (
              <li key={`${reason.code}-${reason.clusterId ?? ''}`}>
                <code>{reason.code}</code> — cluster <code>{reason.clusterId ?? '—'}</code>, reçu{' '}
                {reason.lastReceivedAt !== null ? (
                  <time dateTime={reason.lastReceivedAt}>{reason.lastReceivedAt}</time>
                ) : (
                  '—'
                )}{' '}
                (référence :{' '}
                {reason.referenceInstant !== null ? (
                  <time dateTime={reason.referenceInstant}>{reason.referenceInstant}</time>
                ) : (
                  '—'
                )}
                )
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {thesis.clusters.length > 0 ? (
        <section aria-label="Contexte d'information" className="vx-thesis-clusters">
          <h3>
            Contexte d'information — population{' '}
            <code>{thesis.informationPopulation ?? '—'}</code> (séparée des thèses, jamais
            fusionnée)
          </h3>
          <ul className="vx-sheet-list">
            {thesis.clusters.map((cluster) => (
              <li key={cluster.clusterId}>
                {cluster.synthetic ? (
                  <span className="vx-badge vx-badge-synthetic">SYNTHÉTIQUE</span>
                ) : null}{' '}
                {cluster.title ?? cluster.clusterId} — sources : {cluster.sources.join(', ') || '—'}
                {' · '}droits : {cluster.rights.join(', ') || '—'}
                {' · '}reçu :{' '}
                {cluster.lastReceivedAt !== null ? (
                  <time dateTime={cluster.lastReceivedAt}>{cluster.lastReceivedAt}</time>
                ) : (
                  '—'
                )}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-label="Actions de revue" className="vx-thesis-actions">
        <h3>Actions de revue (révisions append-only)</h3>
        <div className="vx-thesis-action-buttons">
          {(Object.keys(ACTION_LABELS) as ActionKind[]).map((kind) => (
            <button
              key={kind}
              type="button"
              onClick={() => {
                startAction(kind);
              }}
              disabled={outcome.phase === 'pending'}
            >
              {ACTION_LABELS[kind]}
            </button>
          ))}
        </div>

        {pending !== null ? (
          <div className="vx-thesis-action-form" data-testid="thesis-action-form">
            <p>
              Action engagée : <strong>{ACTION_LABELS[pending.kind]}</strong> — clé de rejeu client{' '}
              <code className="vx-pf-hash">{pending.idempotencyKey}</code> (réutilisée telle quelle
              en cas de nouvelle tentative).
            </p>
            {pending.kind === 'SNOOZED' ? (
              <label htmlFor="thesis-snooze-until">
                Reporter jusqu'au (heure locale → UTC)
                <input
                  id="thesis-snooze-until"
                  type="datetime-local"
                  value={pending.snoozeUntilLocal}
                  onChange={(event) => {
                    setPending({ ...pending, snoozeUntilLocal: event.target.value });
                  }}
                />
              </label>
            ) : null}
            <label htmlFor="thesis-action-note">
              Note {pending.kind === 'NOTE_UPDATED' ? '(obligatoire)' : '(facultative)'}
              <input
                id="thesis-action-note"
                type="text"
                value={pending.note}
                onChange={(event) => {
                  setPending({ ...pending, note: event.target.value });
                }}
              />
            </label>
            <div className="vx-thesis-action-send">
              <button
                type="button"
                className="vx-primary-action"
                disabled={sendDisabled}
                onClick={() => {
                  void send(pending);
                }}
              >
                {outcome.phase === 'offline' || outcome.phase === 'rejected'
                  ? 'Réessayer (même clé de rejeu)'
                  : 'Enregistrer la révision'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setPending(null);
                  setOutcome({ phase: 'idle' });
                }}
              >
                Annuler
              </button>
            </div>
          </div>
        ) : null}

        <div aria-live="polite" data-testid="thesis-action-outcome">
          {outcome.phase === 'done' ? (
            <p role="status" className="vx-pf-form-recorded">
              Révision « {ACTION_LABELS[outcome.kind]} » enregistrée — la file sera rafraîchie par
              le serveur.
            </p>
          ) : outcome.phase === 'offline' ? (
            <p role="alert" className="vx-pf-form-rejected">
              Réseau indisponible — la révision n'est peut-être pas enregistrée. « Réessayer »
              renvoie la MÊME clé de rejeu : jamais de doublon.
            </p>
          ) : outcome.phase === 'rejected' ? (
            <div role="alert" className="vx-pf-form-rejected">
              <strong>
                Révision refusée ({outcome.status === 0 ? 'réponse inattendue' : outcome.status})
              </strong>
              {outcome.rejection !== null ? (
                <p>
                  Raison exacte : <code>{outcome.rejection.code ?? '—'}</code>
                  {outcome.rejection.message !== null ? ` — ${outcome.rejection.message}` : null}
                  {outcome.rejection.wireIssues.length > 0
                    ? ` — ${outcome.rejection.wireIssues.join(' ; ')}`
                    : null}
                </p>
              ) : (
                <p>Refus sans corps lisible — aucune raison n'est inventée à la place.</p>
              )}
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}
