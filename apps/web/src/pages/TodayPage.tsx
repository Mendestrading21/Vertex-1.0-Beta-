import type { AttentionSnapshot } from '../api/client.ts';
import { pageStateOf, useAttention, useCapabilities } from '../api/hooks.ts';
import type { PageDataState } from '../api/hooks.ts';
import { AuthRequiredNotice } from '../components/AuthRequiredNotice.tsx';
import { Card } from '../components/Card.tsx';
import { DataStateBoundary } from '../components/DataStateBoundary.tsx';
import type { DataState } from '../components/DataStateBoundary.tsx';
import { FreshnessBadge } from '../components/FreshnessBadge.tsx';
import { SyntheticBanner } from '../components/SyntheticBanner.tsx';
import { AttentionQueue } from './AttentionQueue.tsx';
import { SnapshotRail } from './SnapshotRail.tsx';

/**
 * Page Aujourd'hui — question : « Qu'est-ce qui mérite réellement mon
 * attention maintenant ? »
 *
 * Visuel dominant unique : la file d'attention (aucun moteur graphique sur
 * cette route). Bandeau de santé haut réutilisant la requête capacités
 * (minimal : base + fraîcheur worker), bandeau population SYNTHETIC et état
 * vide honnête « aucun snapshot publié ».
 *
 * REFONTE V3 — PREMIÈRE PAGE SUR LA PRIMITIVE. La file portait
 * `.vx-today-primary`, le rail portait `.vx-snapshot-rail` : deux surfaces
 * inscrites à la main dans les 15 listes de sélecteurs de la couche
 * thématique, et TOUTES LES DEUX porteuses de la tranche métallique réservée à
 * la dominante. Deux dominantes sur un écran, c'est zéro dominante : le regard
 * n'a plus de point d'entrée.
 *
 * Désormais : la file est la seule carte `dominant` — c'est elle qui répond à
 * la question de la page — et les blocs de vérité du snapshot sont `quiet`.
 * La porte `one-dominant-per-page.test.ts` refuse la seconde.
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
      <span className="vx-health-strip-item" data-health={health.db.status}>
        <span className="vx-health-strip-label">Base locale</span>
        <strong>{health.db.status === 'ok' ? 'Disponible' : 'Erreur'}</strong>
      </span>
      <span className="vx-health-strip-item">
        <span className="vx-health-strip-label">Worker · {health.worker.method}</span>
        {health.worker.last_snapshot_as_of === null ? (
          <strong>Aucun snapshot observé</strong>
        ) : (
          <FreshnessBadge ageSeconds={health.worker.age_seconds} sourceLabel="dernier snapshot" />
        )}
      </span>
    </p>
  );
}

/**
 * État du cadre d'attention, dérivé des faits servis et jamais du seul succès
 * HTTP. L'absence explicite de snapshot prime sur les états qui supposent un
 * contenu ; un snapshot périmé prime ensuite sur sa population, puis une
 * population retardée sur un rafraîchissement de transport.
 */
export function attentionFrameStateOf(
  queryState: PageDataState,
  data: AttentionSnapshot | undefined,
): DataState | 'auth-required' {
  if (queryState !== 'ready' && queryState !== 'refreshing') {
    return queryState;
  }
  if (data === undefined) {
    return 'error';
  }
  if (data.state === 'empty') {
    return 'empty';
  }
  if (data.state === 'stale') {
    return 'stale';
  }
  if (data.population === 'DELAYED') {
    return 'delayed';
  }
  return queryState;
}

function degradedDetailOf(state: DataState | 'auth-required', data: AttentionSnapshot | undefined) {
  if (data === undefined) {
    return undefined;
  }
  const age = data.age_seconds === null ? 'âge non publié' : `âge publié ${data.age_seconds} s`;
  if (state === 'stale') {
    return `Snapshot publié périmé par le relais : ${
      data.reason ?? 'raison non publiée'
    } ; ${age}.`;
  }
  if (state === 'delayed') {
    return `Population DELAYED publiée par le worker : ces observations ne décrivent pas le marché à cet instant ; ${age}.`;
  }
  return undefined;
}

export function TodayPage() {
  const attention = useAttention();
  const queryState = pageStateOf(attention);
  const data = attention.data;
  const state = attentionFrameStateOf(queryState, data);
  const degradedDetail = degradedDetailOf(state, data);

  return (
    <article className="vx-page" aria-labelledby="vx-page-title-today">
      <div className="vx-page-header">
        <p className="vx-page-eyebrow">Cockpit décisionnel</p>
        <h1 id="vx-page-title-today">Aujourd'hui</h1>
        <p className="vx-page-question">
          Qu'est-ce qui mérite réellement mon attention maintenant ?
        </p>
      </div>

      {state === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : state === 'empty' ? (
        <DataStateBoundary
          state="empty"
          detail={`Aucun snapshot publié — le worker n'a encore rien produit (raison serveur : ${
            data?.reason ?? 'non fournie'
          }). Rien n'est inventé à la place.`}
        />
      ) : state === 'loading' || state === 'offline' || state === 'error' ? (
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
      ) : data !== undefined ? (
        <DataStateBoundary
          state={state}
          {...(degradedDetail !== undefined ? { detail: degradedDetail } : {})}
          {...(data.as_of !== null ? { asOfLabel: `as_of ${data.as_of}` } : {})}
        >
          <HealthStrip />
          <SyntheticBanner population={data.population} />
          <div className="vx-today-layout">
            <Card
              className="vx-today-primary"
              rank="dominant"
              kicker="Priorité publiée"
              title="File d'attention"
              titleId="vx-attention-title"
              aside={<>{data.items.length} éléments</>}
              footer={
                <>
                  Ordre publié par le worker — aucun reclassement local. Population{' '}
                  {data.population ?? 'non publiée'}
                  {data.as_of === null ? '' : ` · as_of ${data.as_of}`}
                </>
              }
            >
              <AttentionQueue items={data.items} asOf={data.as_of} />
            </Card>
            <SnapshotRail
              snapshotVersion={data.snapshot_version}
              asOf={data.as_of}
              population={data.population}
              itemCount={data.items.length}
              rejectedCount={data.rejected_count}
              coverage={data.coverage}
            />
          </div>
        </DataStateBoundary>
      ) : (
        <DataStateBoundary
          state="error"
          detail="Réponse absente — aucune file affichée à la place."
        />
      )}
    </article>
  );
}
