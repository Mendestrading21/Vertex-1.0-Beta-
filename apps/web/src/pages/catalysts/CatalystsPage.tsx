import { useCalendar } from '../../api/decisionApi.ts';
import { useFollowUpQueue } from '../../api/portfolioApi.ts';
import { pageStateOf } from '../../api/hooks.ts';
import type { PageDataState } from '../../api/hooks.ts';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import type { DataState } from '../../components/DataStateBoundary.tsx';
import { calendarEventsOf } from '../calendar/calendarView.ts';
import { CatalystTimeline } from './CatalystTimeline.tsx';
import { selectCatalysts } from './catalystsView.ts';
import type { CatalystSelectionView } from './catalystsView.ts';
import { ReviewQueueSection } from './review/ReviewQueueSection.tsx';
import { queueContentOf } from './review/followUpView.ts';

/**
 * Page Catalyseurs — question du contrat des douze pages (§10) :
 * « Quels événements vérifiés peuvent modifier la thèse et quand ? »
 *
 * Douzième destination du blueprint, créée au LOT-10. Elle n'invente aucune
 * donnée : elle CROISE deux snapshots déjà publiés et déjà servis —
 * `calendar/global` (agenda, avec son `event_context` qui nomme les thèses et
 * positions touchées) et `review_queue/global` (thèses, échéances,
 * information nouvelle). Aucun nouvel endpoint, aucun nouveau calcul.
 *
 * Elle absorbe l'ancienne destination `/follow-up`
 * (docs/05-design/PAGE_ARBITRATION.md) : une thèse est mise en revue PARCE
 * QU'un catalyseur l'a touchée. La file de revue devient donc le module qui
 * suit la timeline, et garde sa question (règle 4).
 *
 * Ne pas confondre avec Calendrier (§11) : Calendrier sert TOUT l'agenda dans
 * une fenêtre temporelle et son fuseau ; Catalyseurs n'en sert que la part
 * reliée à une thèse ou à une position. Un seul propriétaire de donnée, deux
 * questions — jamais deux vérités.
 *
 * Les deux requêtes sont INDÉPENDANTES et leurs états ne sont pas fondus :
 * si l'agenda répond et pas la file, la timeline s'affiche et le module de
 * revue affiche SON état dégradé. Fondre les deux masquerait laquelle des
 * deux sources manque.
 */

/** État du cadre de la timeline, dérivé du seul snapshot d'agenda. */
export function catalystFrameStateOf(
  queryState: PageDataState,
  agendaState: string | undefined,
): DataState | 'auth-required' {
  if (queryState !== 'ready' && queryState !== 'refreshing') {
    return queryState;
  }
  if (agendaState === undefined) {
    return 'error';
  }
  if (agendaState === 'empty' || agendaState === 'empty_window') {
    return 'empty';
  }
  if (agendaState === 'stale') {
    return 'stale';
  }
  // Dégradation signalée PAR LE SERVEUR. `not_entitled` et `rejected` ne sont
  // pas des états « partiels » : rien n'est servi, donc rien n'est affiché.
  if (agendaState === 'not_entitled' || agendaState === 'rejected') {
    return 'error';
  }
  if (agendaState === 'degraded') {
    return 'partial';
  }
  return queryState;
}

export function CatalystsPage() {
  const calendarQuery = useCalendar(null);
  const queueQuery = useFollowUpQueue();

  const calendarState = pageStateOf(calendarQuery);
  const frameState = catalystFrameStateOf(calendarState, calendarQuery.data?.state);

  // La file de revue est LUE ici pour l'appariement, mais son état reste
  // celui du module : une file absente ne fait pas disparaître la timeline.
  const queueView =
    queueQuery.data !== undefined && queueQuery.data.state !== 'empty'
      ? queueContentOf(queueQuery.data.content)
      : null;

  const selection: CatalystSelectionView | null =
    calendarQuery.data !== undefined && frameState !== 'empty' && frameState !== 'error'
      ? selectCatalysts(calendarEventsOf(calendarQuery.data.agenda), queueView?.theses ?? [])
      : null;

  return (
    <article className="vx-page" aria-labelledby="vx-page-title-catalysts">
      <div className="vx-page-header">
        <h1 id="vx-page-title-catalysts">Catalyseurs</h1>
        <p className="vx-page-question">
          Quels événements vérifiés peuvent modifier la thèse et quand ?
        </p>
      </div>

      {calendarState === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : (
        <>
          {frameState === 'empty' ? (
            <DataStateBoundary
              state="empty"
              detail={
                calendarQuery.data?.reason !== null && calendarQuery.data?.reason !== undefined
                  ? `Aucun agenda publié — raison serveur : ${calendarQuery.data.reason}`
                  : "Aucun agenda publié par le worker : aucun catalyseur ne peut être relié."
              }
            />
          ) : selection === null ? (
            <DataStateBoundary
              state={frameState === 'auth-required' ? 'error' : frameState}
              {...(frameState === 'offline'
                ? { detail: "L'API locale est injoignable — aucun catalyseur affiché." }
                : frameState === 'error'
                  ? {
                      detail:
                        "Agenda absent, refusé ou sans droit — rien n'est reconstruit à la place.",
                    }
                  : {})}
            />
          ) : (
            <DataStateBoundary
              state={frameState === 'auth-required' ? 'error' : frameState}
              {...(frameState === 'partial'
                ? {
                    detail:
                      'Couverture incomplète signalée par le serveur : la timeline ne montre que les événements réellement servis.',
                  }
                : {})}
              {...(calendarQuery.data?.as_of !== null && calendarQuery.data?.as_of !== undefined
                ? { asOfLabel: calendarQuery.data.as_of }
                : {})}
            >
              <p className="vx-cat-populations" role="note" data-testid="cat-populations">
                Populations séparées, jamais additionnées — agenda :{' '}
                <code>{calendarQuery.data?.population ?? '—'}</code> · thèses :{' '}
                <code>{queueView?.populationTheses ?? '—'}</code>. Les deux snapshots sont
                indépendants ; leur croisement ne crée aucune donnée nouvelle.
              </p>

              <CatalystTimeline
                catalysts={selection.catalysts}
                unlinkedCount={selection.unlinkedCount}
              />

              {selection.thesesWithoutCatalyst.length > 0 ? (
                <section
                  className="vx-cat-orphans"
                  aria-labelledby="vx-cat-orphans-title"
                  data-testid="cat-orphans"
                >
                  <h2 id="vx-cat-orphans-title">
                    Thèses sans catalyseur servi ({selection.thesesWithoutCatalyst.length})
                  </h2>
                  <p className="vx-cat-orphans-note">
                    Aucun événement de l'agenda servi ne touche ces thèses. C'est un fait de
                    couverture, pas un verdict : l'absence d'événement publié ne signifie pas
                    qu'aucun événement n'existe.
                  </p>
                  <ul>
                    {selection.thesesWithoutCatalyst.map((thesis) => (
                      <li key={thesis.id} data-testid={`cat-orphan-${thesis.id}`}>
                        {thesis.title}
                        {thesis.instrumentTicker !== null ? (
                          <code>{thesis.instrumentTicker}</code>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
            </DataStateBoundary>
          )}

          <ReviewQueueSection />
        </>
      )}
    </article>
  );
}
