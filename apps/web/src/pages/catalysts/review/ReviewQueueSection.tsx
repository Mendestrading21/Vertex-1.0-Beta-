import { useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { pageStateOf, queryKeyForResource } from '../../../api/hooks.ts';
import { useFollowUpQueue } from '../../../api/portfolioApi.ts';
import type { PageDataState } from '../../../api/hooks.ts';
import type { FollowUpQueueResponse } from '../../../api/client.ts';
import { AuthRequiredNotice } from '../../../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../../../components/DataStateBoundary.tsx';
import type { DataState } from '../../../components/DataStateBoundary.tsx';
import { ThesisForm } from './ThesisForm.tsx';
import { ThesisSheet } from './ThesisSheet.tsx';
import { queueContentOf, thesisStatusLabel } from './followUpView.ts';
import type { QueueContentView } from './followUpView.ts';

/**
 * Module de revue de la page Catalyseurs — question conservée :
 * « Quelles thèses, alertes et informations doivent être revues ? »
 *
 * Était la destination `/follow-up`. Absorbée d'après
 * `docs/05-design/PAGE_ARBITRATION.md` : le contrat des douze pages (§10)
 * donne à Catalyseurs la question « quels événements vérifiés peuvent
 * modifier LA THÈSE et quand ? ». Une thèse est mise en revue PARCE QU'un
 * catalyseur l'a touchée — la file de revue est la conséquence de la
 * timeline, pas une destination concurrente.
 *
 * Règle 4 de l'arbitrage : une page absorbée garde sa question. Elle est
 * affichée telle quelle ci-dessous.
 *
 * Les routes API `/v1/follow-up/queue`, `/v1/theses` et leurs révisions ne
 * bougent pas (règle 2).
 *
 * Dominante : la file de revues DUE, dans l'ordre lexicographique documenté
 * du serveur (jamais retriée localement). Une « nouvelle information » élève
 * l'urgence visible (badge + raisons) mais ne modifie jamais la thèse : seul
 * l'utilisateur révise, via des révisions append-only.
 */

export function queueFrameStateOf(
  queryState: PageDataState,
  data: FollowUpQueueResponse | undefined,
): { readonly state: DataState | 'auth-required'; readonly view: QueueContentView | null } {
  if (queryState !== 'ready' && queryState !== 'refreshing') {
    return { state: queryState, view: null };
  }
  if (data === undefined) {
    return { state: 'error', view: null };
  }
  if (data.state === 'empty') {
    return { state: 'empty', view: null };
  }
  const view = queueContentOf(data.content);
  if (view === null) {
    return { state: 'error', view: null };
  }
  // Le relais publie l'âge de l'instantané et bascule en `stale` au-delà
  // du budget de fraîcheur du registre. Le contenu reste VISIBLE sous un
  // bandeau « Données périmées » : ce qui était interdit, c'est de le
  // servir sans dire son âge, pas de le servir. Testé AVANT `partial` :
  // un instantané périmé l'est en entier, la partialité de son contenu
  // est la moins forte des deux affirmations.
  if (data.state === 'stale') {
    return { state: 'stale', view };
  }
  return { state: queryState, view };
}

export function ReviewQueueSection() {
  const query = useFollowUpQueue();
  const queryClient = useQueryClient();
  const queryState = pageStateOf(query);
  const frame = queueFrameStateOf(queryState, query.data);
  const [openThesisId, setOpenThesisId] = useState<number | null>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  function refetchQueue(): void {
    void queryClient.invalidateQueries({ queryKey: queryKeyForResource('review_queue/global') });
  }

  function closeSheet(): void {
    setOpenThesisId(null);
    triggerRef.current?.focus();
    triggerRef.current = null;
  }

  const openThesis =
    frame.view !== null && openThesisId !== null
      ? (frame.view.theses.find((entry) => entry.id === openThesisId) ?? null)
      : null;

  return (
    <section className="vx-fu-module" aria-labelledby="vx-fu-module-title">
      <div className="vx-page-header">
        <h2 id="vx-fu-module-title">Revue des thèses</h2>
        <p className="vx-page-question">
          Quelles thèses, alertes et informations doivent être revues ?
        </p>
      </div>

      {queryState === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : frame.state === 'loading' || frame.state === 'offline' || (frame.state === 'error' && frame.view === null) ? (
        <DataStateBoundary
          state={frame.state}
          {...(frame.state === 'offline'
            ? { detail: "L'API locale est injoignable — aucune file affichée." }
            : frame.state === 'error'
              ? { detail: "Snapshot absent ou illisible — rien n'est reconstruit à la place." }
              : {})}
        />
      ) : frame.state === 'empty' || frame.view === null ? (
        <>
          <DataStateBoundary
            state="empty"
            detail={
              query.data?.reason !== null && query.data?.reason !== undefined
                ? `Aucune file publiée — raison serveur : ${query.data.reason}`
                : 'Aucune file de revues publiée par le worker.'
            }
          />
          <ThesisForm onCreated={refetchQueue} />
        </>
      ) : (
        <DataStateBoundary
          state={frame.state === 'auth-required' ? 'error' : frame.state}
          {...(frame.view.asOf !== null ? { asOfLabel: frame.view.asOf } : {})}
        >
          <p className="vx-fu-populations" role="note" data-testid="fu-populations">
            Populations séparées, jamais additionnées — thèses :{' '}
            <code>{frame.view.populationTheses ?? '—'}</code> · contexte d'information :{' '}
            <code>{frame.view.populationInformation ?? '—'}</code>. Snapshot du{' '}
            {frame.view.asOf !== null ? <time dateTime={frame.view.asOf}>{frame.view.asOf}</time> : '—'}.
          </p>

          <section className="vx-fu-queue" aria-labelledby="vx-fu-queue-title">
            <h3 id="vx-fu-queue-title">
              File de revues — {frame.view.due.length} thèse(s) à revoir
            </h3>
            <p className="vx-fu-ordering">
              Ordre du serveur (lexicographique) : {frame.view.orderingKeys.join(' ; ') || '—'}.
            </p>
            {frame.view.due.length === 0 ? (
              <p className="vx-cell-absent" data-testid="fu-due-empty">
                Aucune revue due — la file vide est un état réel, pas un défaut d'affichage.
              </p>
            ) : (
              <ol className="vx-fu-due-list" data-testid="fu-due-list">
                {frame.view.due.map((entry) => (
                  <li key={entry.thesisId} className="vx-fu-due-item" data-testid={`fu-due-${entry.thesisId}`}>
                    <button
                      type="button"
                      className="vx-fu-due-open"
                      onClick={(event) => {
                        triggerRef.current = event.currentTarget;
                        setOpenThesisId(entry.thesisId);
                      }}
                    >
                      <span className="vx-fu-due-rank">n°{entry.rank}</span>{' '}
                      <span className="vx-fu-due-title">{entry.title}</span>
                    </button>
                    <span className="vx-fu-due-meta">
                      échéance :{' '}
                      {entry.reviewDueAt !== null ? (
                        <time dateTime={entry.reviewDueAt}>{entry.reviewDueAt}</time>
                      ) : (
                        '—'
                      )}
                      {entry.overdueSeconds !== null && entry.overdueSeconds > 0 ? (
                        <span className="vx-badge vx-badge-warning">
                          en retard de {entry.overdueSeconds} s (au snapshot)
                        </span>
                      ) : null}
                      {entry.hasNewInformation ? (
                        <span className="vx-badge vx-badge-warning" data-testid={`fu-new-info-${entry.thesisId}`}>
                          nouvelle information
                        </span>
                      ) : null}
                    </span>
                    {entry.hasNewInformation && entry.urgencyReasons.length > 0 ? (
                      <span className="vx-fu-due-reasons">
                        {entry.urgencyReasons.map((reason) => (
                          <code key={`${reason.code}-${reason.clusterId ?? ''}`}>{reason.code}</code>
                        ))}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ol>
            )}
          </section>

          <section className="vx-fu-theses" aria-labelledby="vx-fu-theses-title">
            <h3 id="vx-fu-theses-title">Toutes les thèses ({frame.view.theses.length})</h3>
            {frame.view.theses.length === 0 ? (
              <p className="vx-cell-absent">Aucune thèse déclarée.</p>
            ) : (
              <div
                className="vx-pf-table-scroll"
                tabIndex={0}
                role="region"
                aria-label="Thèses défilantes"
              >
              <table className="vx-fu-theses-table" aria-label="Thèses déclarées et état projeté">
                <thead>
                  <tr>
                    <th scope="col">Thèse</th>
                    <th scope="col">Instrument</th>
                    <th scope="col">État projeté</th>
                    <th scope="col">Échéance effective</th>
                    <th scope="col">Révisions</th>
                    <th scope="col">Information</th>
                  </tr>
                </thead>
                <tbody>
                  {frame.view.theses.map((entry) => (
                    <tr key={entry.id} data-testid={`fu-thesis-${entry.id}`}>
                      <th scope="row">
                        <button
                          type="button"
                          className="vx-fu-thesis-open"
                          onClick={(event) => {
                            triggerRef.current = event.currentTarget;
                            setOpenThesisId(entry.id);
                          }}
                        >
                          {entry.title}
                        </button>
                      </th>
                      <td>
                        {entry.instrumentTicker !== null ? <code>{entry.instrumentTicker}</code> : '—'}
                      </td>
                      <td>
                        <code>{entry.status ?? '—'}</code> ({thesisStatusLabel(entry.status)})
                        {entry.isDue ? <span className="vx-badge vx-badge-warning"> à revoir</span> : null}
                      </td>
                      <td>
                        {entry.effectiveReviewDueAt !== null ? (
                          <time dateTime={entry.effectiveReviewDueAt}>{entry.effectiveReviewDueAt}</time>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="vx-num">{entry.revisionCount ?? '—'}</td>
                      <td>
                        {entry.hasNewInformation ? (
                          <span className="vx-badge vx-badge-warning">nouvelle information</span>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            )}
          </section>

          <ThesisForm onCreated={refetchQueue} />

          {openThesis !== null ? (
            <ThesisSheet thesis={openThesis} onClose={closeSheet} onRevised={refetchQueue} />
          ) : null}
        </DataStateBoundary>
      )}
    </section>
  );
}
