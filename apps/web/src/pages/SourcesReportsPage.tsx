import { useSyncExternalStore } from 'react';

import type { SystemCapabilities, SystemHealth } from '../api/client.ts';
import { pageStateOf, useAttention, useCapabilities } from '../api/hooks.ts';
import { sseStateStore } from '../api/events.ts';
import type { SseConnectionState } from '../api/events.ts';
import { AuthRequiredNotice } from '../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../components/DataStateBoundary.tsx';
import { FreshnessBadge } from '../components/FreshnessBadge.tsx';
import { SyntheticBanner } from '../components/SyntheticBanner.tsx';
import { SourceHealthMatrix } from './SourceHealthMatrix.tsx';

/**
 * Page Sources & Rapports — question : « Puis-je faire confiance aux sources,
 * traitements et sauvegardes maintenant ? »
 *
 * Destination du blueprint qui ABSORBE l'ancienne page Système
 * (docs/05-design/PAGE_ARBITRATION.md) : la question et les capacités livrées
 * sont inchangées, seule l'identité de destination l'est. Le lignage, les
 * incidents et les rapports que la cible doit encore recevoir ne sont PAS
 * simulés ici — ils resteront absents tant qu'ils ne seront pas réels.
 *
 * Visuel dominant unique : la matrice de santé des sources. Modules
 * secondaires : santé des composants (db, snapshots, worker en
 * heartbeat_proxy assumé comme limitation), état du flux SSE et bandeau de
 * population SYNTHETIC lorsqu'une population synthétique est publiée.
 *
 * La route API `/v1/system/capabilities` ne bouge PAS : la règle 2 de
 * l'arbitrage et `.claude/rules/architecture.md` interdisent de déplacer une
 * responsabilité serveur sans ADR.
 */

const SSE_LABELS: Readonly<Record<SseConnectionState, string>> = {
  connecting: 'connexion en cours',
  open: 'connecté',
  retrying: 'reconnexion (backoff)',
  stopped: 'arrêté (aucune session active)',
};

function HealthPanel({ health }: { readonly health: SystemHealth }) {
  const sseState = useSyncExternalStore(sseStateStore.subscribe, sseStateStore.getState);
  return (
    <section className="vx-health" aria-label="Santé des composants">
      <h2>Santé des composants</h2>
      <dl className="vx-health-grid">
        <div className="vx-health-item">
          <dt>Base de données</dt>
          <dd data-health={health.db.status}>
            {health.db.status === 'ok' ? 'ok (SELECT 1)' : 'erreur (SELECT 1 en échec)'}
          </dd>
        </div>
        <div className="vx-health-item">
          <dt>Snapshot attention</dt>
          <dd>
            {health.attention_snapshot.present ? (
              <>
                version {health.attention_snapshot.version}{' '}
                <FreshnessBadge ageSeconds={health.attention_snapshot.age_seconds} />
              </>
            ) : (
              'jamais publié'
            )}
          </dd>
        </div>
        <div className="vx-health-item">
          <dt>Snapshot capacités</dt>
          <dd>
            {health.capabilities_snapshot.present ? (
              <>
                version {health.capabilities_snapshot.version}{' '}
                <FreshnessBadge ageSeconds={health.capabilities_snapshot.age_seconds} />
              </>
            ) : (
              'jamais publié'
            )}
          </dd>
        </div>
        <div className="vx-health-item">
          <dt>
            Worker <span className="vx-health-method">({health.worker.method})</span>
          </dt>
          <dd>
            {health.worker.last_snapshot_as_of === null ? (
              'aucun snapshot observé'
            ) : (
              <FreshnessBadge
                ageSeconds={health.worker.age_seconds}
                sourceLabel="dernier snapshot publié"
              />
            )}
            <p className="vx-health-limitation">
              Limitation assumée : « heartbeat_proxy » mesure l'âge du snapshot le plus récent,
              pas une observation directe du processus worker.
            </p>
          </dd>
        </div>
        <div className="vx-health-item">
          <dt>Flux SSE (client)</dt>
          <dd data-sse={sseState}>{SSE_LABELS[sseState]}</dd>
        </div>
      </dl>
    </section>
  );
}

function SourcesReportsReady({ data }: { readonly data: SystemCapabilities }) {
  const attention = useAttention();
  // La nature vient d'une SECONDE requête. Tant qu'elle n'a pas répondu, on ne
  // sait pas encore — ce n'est pas la même chose qu'une nature non déclarée.
  // Rendre le bandeau tout de suite afficherait « NATURE NON DÉCLARÉE » en
  // rouge à chaque chargement de la page : une fausse alerte, et la confusion
  // exacte entre « absent » et « pas encore connu » que le programme interdit.
  // Une requête en ERREUR, en revanche, laisse bien la nature indéterminée et
  // doit avertir.
  const attentionSettled = !attention.isPending;
  const population = attention.data?.population ?? null;
  return (
    <>
      {attentionSettled ? <SyntheticBanner population={population} /> : null}
      <SourceHealthMatrix entries={data.capabilities} total={data.total} />
      <HealthPanel health={data.health} />
      {data.unknown_probed_capability_ids.length > 0 ? (
        <section className="vx-unknown-probes" aria-label="Sondes hors manifeste">
          <h2>Sondes hors manifeste</h2>
          <p>
            Identifiants sondés absents du manifeste déclaré — relayés tels quels, jamais fusionnés
            ni ignorés :
          </p>
          <ul>
            {data.unknown_probed_capability_ids.map((id) => (
              <li key={id}>
                <code>{id}</code>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </>
  );
}

export function SourcesReportsPage() {
  const capabilities = useCapabilities();
  const state = pageStateOf(capabilities);

  return (
    <article className="vx-page" aria-labelledby="vx-page-title-sources-reports">
      <div className="vx-page-header">
        <h1 id="vx-page-title-sources-reports">Sources &amp; Rapports</h1>
        <p className="vx-page-question">
          Puis-je faire confiance aux sources, traitements et sauvegardes maintenant ?
        </p>
      </div>

      {state === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : state === 'ready' || state === 'refreshing' ? (
        <DataStateBoundary
          state={state}
          {...(capabilities.data !== undefined
            ? { asOfLabel: `vérifié à ${capabilities.data.checked_at}` }
            : {})}
        >
          {capabilities.data !== undefined ? <SourcesReportsReady data={capabilities.data} /> : null}
        </DataStateBoundary>
      ) : (
        <DataStateBoundary
          state={state}
          {...(state === 'offline'
            ? {
                detail:
                  "L'API locale est injoignable — aucun état de capacité ne peut être affiché.",
              }
            : state === 'error'
              ? {
                  detail:
                    "Réponse invalide ou inattendue de l'API — aucun état de capacité affiché.",
                }
              : {})}
        />
      )}
    </article>
  );
}
