import { pageStateOf, useAttention, useCapabilities } from '../api/hooks.ts';
import { AuthRequiredNotice } from '../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../components/DataStateBoundary.tsx';
import { FreshnessBadge } from '../components/FreshnessBadge.tsx';
import { SyntheticBanner } from '../components/SyntheticBanner.tsx';
import { AttentionQueue } from './AttentionQueue.tsx';

/**
 * Page Aujourd'hui — question : « Qu'est-ce qui mérite réellement mon
 * attention maintenant ? »
 *
 * Visuel dominant unique : la file d'attention (aucun moteur graphique sur
 * cette route). Bandeau de santé haut réutilisant la requête capacités
 * (minimal : base + fraîcheur worker), bandeau population SYNTHETIC et état
 * vide honnête « aucun snapshot publié ».
 */

function HealthStrip() {
  const capabilities = useCapabilities();
  if (capabilities.data === undefined) {
    return (
      <p className="vx-health-strip" role="status">
        Santé système non disponible pour l'instant (réponse capacités absente).
      </p>
    );
  }
  const health = capabilities.data.health;
  return (
    <p className="vx-health-strip" role="status">
      <span data-health={health.db.status}>
        Base : {health.db.status === 'ok' ? 'ok' : 'erreur'}
      </span>
      <span>
        Worker ({health.worker.method}) :{' '}
        {health.worker.last_snapshot_as_of === null ? (
          'aucun snapshot observé'
        ) : (
          <FreshnessBadge ageSeconds={health.worker.age_seconds} sourceLabel="dernier snapshot" />
        )}
      </span>
    </p>
  );
}

export function TodayPage() {
  const attention = useAttention();
  const state = pageStateOf(attention);
  const data = attention.data;

  return (
    <article className="vx-page" aria-labelledby="vx-page-title-today">
      <div className="vx-page-header">
        <h1 id="vx-page-title-today">Aujourd'hui</h1>
        <p className="vx-page-question">
          Qu'est-ce qui mérite réellement mon attention maintenant ?
        </p>
      </div>

      {state === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : state === 'ready' || state === 'refreshing' ? (
        data !== undefined && data.state === 'empty' ? (
          <DataStateBoundary
            state="empty"
            detail={`Aucun snapshot publié — le worker n'a encore rien produit (raison serveur : ${
              data.reason ?? 'non fournie'
            }). Rien n'est inventé à la place.`}
          />
        ) : (
          <DataStateBoundary
            state={state}
            {...(data !== undefined && data.as_of !== null ? { asOfLabel: `as_of ${data.as_of}` } : {})}
          >
            {data !== undefined ? (
              <>
                <HealthStrip />
                <SyntheticBanner population={data.population} />
                <p className="vx-queue-summary" role="status">
                  {data.items.length} item{data.items.length > 1 ? 's' : ''} publié
                  {data.items.length > 1 ? 's' : ''} (snapshot version {data.snapshot_version ?? '—'}
                  , population {data.population ?? '—'})
                </p>
                <AttentionQueue items={data.items} asOf={data.as_of} />
              </>
            ) : null}
          </DataStateBoundary>
        )
      ) : (
        <DataStateBoundary
          state={state}
          {...(state === 'offline'
            ? {
                detail:
                  "L'API locale est injoignable — la file d'attention ne peut pas être affichée.",
              }
            : state === 'error'
              ? { detail: "Réponse invalide ou inattendue de l'API — aucune file affichée." }
              : {})}
        />
      )}
    </article>
  );
}
