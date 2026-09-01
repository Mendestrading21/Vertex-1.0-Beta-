import { useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import type { OptionChainContract, OptionChainResponse } from '../../api/client.ts';
import { pageStateOf, useOptionChain } from '../../api/hooks.ts';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import type { DataState } from '../../components/DataStateBoundary.tsx';
import { SyntheticBanner } from '../../components/SyntheticBanner.tsx';
import { useDeclaredInstruments } from '../devUniverse.ts';
import { OptionChainTable } from './OptionChainTable.tsx';
import { OptionInspector } from './OptionInspector.tsx';
import {
  chainStateOf,
  groupCoverageOf,
  groupKeyOf,
  groupLabelOf,
  rowBudgetOf,
  spotViewOf,
} from './optionsView.ts';

/**
 * Page Options — question : « Quels contrats sont réellement exploitables et
 * quels risques portent-ils ? »
 *
 * Dominante unique : la table de chaîne Calls | Strike | Puts du groupe
 * (expiration, trading_class) sélectionné. Le sélecteur liste les groupes
 * EXACTEMENT comme publiés — deux trading classes d'une même date restent
 * deux entrées distinctes, jamais fusionnées — avec la couverture de chaque
 * groupe et le budget de lignes publié. Le détail d'un contrat s'ouvre dans
 * l'inspecteur (panneau latéral) ; son unique action est « Envoyer au
 * Simulateur » (transfert d'analyse typé). Aucun calcul financier ici : IV,
 * Greeks et statuts arrivent calculés et étiquetés par le worker.
 */

function UnderlyingPicker({ current }: { readonly current: string | null }) {
  const instruments = useDeclaredInstruments();
  if (instruments.length === 0) {
    return (
      <nav className="vx-underlying-picker" aria-label="Sous-jacents disponibles">
        <span className="vx-underlying-picker-label">Sous-jacent :</span>
        <span className="vx-underlying-empty">
          Aucun sous-jacent publié — la page Marchés n&apos;en couvre encore aucun.
        </span>
      </nav>
    );
  }
  return (
    <nav className="vx-underlying-picker" aria-label="Sous-jacents disponibles">
      <span className="vx-underlying-picker-label">Sous-jacent :</span>
      {instruments.map((candidate) => (
        <Link
          key={candidate}
          to={`/options/${candidate}`}
          className="vx-underlying-link"
          aria-current={candidate === current ? 'page' : undefined}
        >
          {candidate}
        </Link>
      ))}
    </nav>
  );
}

function ChainFrame({
  data,
  state,
  underlying,
}: {
  readonly data: OptionChainResponse;
  readonly state: DataState;
  readonly underlying: string;
}) {
  const groups = data.expirations;
  const [selectedKey, setSelectedKey] = useState<string>(() =>
    groups.length > 0 && groups[0] !== undefined ? groupKeyOf(groups[0]) : '',
  );
  const [inspected, setInspected] = useState<OptionChainContract | null>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  const selected = groups.find((group) => groupKeyOf(group) === selectedKey) ?? groups[0] ?? null;
  const budget = rowBudgetOf(data);
  const spot = spotViewOf(data);
  const asOf = data.as_of;

  const degradedGroups = groups.filter((group) => group.quality !== 'VALID');
  const detail =
    state === 'partial'
      ? [
          degradedGroups.length > 0
            ? `${degradedGroups.length} groupe(s) publié(s) avec qualité dégradée (${degradedGroups
                .map((group) => `${groupLabelOf(group)} : ${group.quality}`)
                .join(' ; ')}).`
            : null,
          budget !== null && budget.truncatedRows !== null && budget.truncatedRows > 0
            ? `${budget.truncatedRows} ligne(s) tronquée(s) par le budget publié.`
            : null,
        ]
          .filter((part): part is string => part !== null)
          .join(' ')
      : undefined;

  function closeInspector(): void {
    setInspected(null);
    triggerRef.current?.focus();
    triggerRef.current = null;
  }

  return (
    <section className="vx-chartframe" aria-labelledby="vx-chain-title">
      <header className="vx-chartframe-head">
        <p className="vx-chartframe-question">
          Quels contrats sont réellement exploitables et quels risques portent-ils ?
        </p>
        <h2 id="vx-chain-title">Chaîne d'options — {underlying}</h2>
      </header>

      <dl className="vx-chartframe-meta">
        <div>
          <dt>Source</dt>
          <dd>
            <code>synthetic-dev</code> via snapshot worker v{data.snapshot_version ?? '—'} (moteur{' '}
            <code>{data.engine_version ?? '—'}</code>)
          </dd>
        </div>
        <div>
          <dt>as_of</dt>
          <dd>{asOf === null ? '—' : <time dateTime={asOf}>{asOf}</time>}</dd>
        </div>
        <div>
          <dt>Spot publié</dt>
          <dd>
            {spot === null || spot.value === null ? (
              '—'
            ) : (
              <>
                <code className="vx-num">{spot.value}</code> {spot.currency ?? ''} (observé{' '}
                {spot.observedAt ?? 'à un instant non publié'})
              </>
            )}
          </dd>
        </div>
        <div>
          <dt>Couverture</dt>
          <dd>
            {data.coverage === null
              ? '—'
              : `${String(data.coverage['groups_published'] ?? '—')} groupe(s) publié(s) sur ${String(
                  data.coverage['observations_considered'] ?? '—',
                )} observation(s) considérée(s)`}
          </dd>
        </div>
        <div>
          <dt>Budget de lignes</dt>
          <dd data-testid="chain-row-budget">
            {budget === null
              ? '—'
              : `${budget.publishedRows ?? '—'} publiée(s) / ${budget.totalRows ?? '—'} construite(s), plafond ${budget.maxRows ?? '—'}, ${budget.truncatedRows ?? '—'} tronquée(s)`}
          </dd>
        </div>
        <div>
          <dt>Nature des valeurs</dt>
          <dd>
            quotes verbatim ; IV/Greeks{' '}
            <span className="vx-badge vx-badge-theoretical">THÉORIQUE</span> (
            {data.value_nature ?? '—'})
          </dd>
        </div>
      </dl>

      <SyntheticBanner population={data.population} />

      <DataStateBoundary
        state={state}
        {...(detail !== undefined ? { detail } : {})}
        {...(asOf !== null ? { asOfLabel: `as_of ${asOf}` } : {})}
      >
        <fieldset className="vx-chain-groups">
          <legend>
            Expiration et trading class — jamais fusionnées : deux classes d'une même date sont deux
            entrées distinctes
          </legend>
          <div className="vx-chain-group-list" role="group" aria-label="Groupes publiés">
            {groups.map((group) => {
              const key = groupKeyOf(group);
              const coverage = groupCoverageOf(group);
              const active = selected !== null && groupKeyOf(selected) === key;
              return (
                <button
                  key={key}
                  type="button"
                  aria-pressed={active}
                  className="vx-chain-group"
                  data-testid="chain-group"
                  onClick={() => {
                    setSelectedKey(key);
                  }}
                >
                  <span className="vx-chain-group-name">{groupLabelOf(group)}</span>
                  <span className="vx-chain-group-meta">
                    qualité {group.quality} · {coverage.expected ?? '—'} contrats attendus ·{' '}
                    {coverage.quotesValid ?? '—'} quotes saines · {coverage.ivResolved ?? '—'} IV
                    résolues · {coverage.discardedCount ?? '—'} écarté(s) du calcul
                  </span>
                </button>
              );
            })}
          </div>
        </fieldset>

        {selected !== null ? (
          <>
            <p className="vx-chain-selected-meta">
              Groupe affiché : <strong>{groupLabelOf(selected)}</strong> — style {selected.style},
              règlement {selected.settlement}, multiplicateur{' '}
              <code className="vx-num">{selected.multiplier}</code>, maturité{' '}
              <code className="vx-num">{selected.maturity_years}</code> an(s), qualité{' '}
              {selected.quality}. Une IV absente est affichée « — » avec sa raison (au survol et
              dans l'inspecteur), jamais 0.
            </p>
            <div
              onClickCapture={(event) => {
                // Mémorise le déclencheur pour restituer le focus à la fermeture.
                const target = event.target;
                if (target instanceof HTMLElement && target.closest('.vx-chain-inspect') !== null) {
                  triggerRef.current = target;
                }
              }}
            >
              <OptionChainTable group={selected} onInspect={setInspected} />
            </div>
          </>
        ) : (
          <p role="status">Aucun groupe publié dans ce snapshot.</p>
        )}
      </DataStateBoundary>

      <footer className="vx-chartframe-foot">
        <p>
          Méthode : quotes relayées verbatim avec leur statut (<code>OK</code>,{' '}
          <code>CROSSED</code>, <code>STALE</code>, <code>MISSING</code>) ; IV Vertex{' '}
          <code>options.implied_volatility</code> et Greeks <code>options.greeks</code> calculés par
          le worker sur le MID d'une quote saine uniquement (lignée <code>CalculationRecord</code>{' '}
          conservée, nature THÉORIQUE). Rendu direct de la table (~24 contrats par groupe, budget
          serveur 240 lignes) — décision documentée, aucune virtualisation externe.
        </p>
        <p>
          Limites : données SYNTHÉTIQUES de développement ; une quote croisée, périmée ou absente
          n'a jamais d'IV ; l'open interest est publié différé (<code>OI_DELAYED</code>).
        </p>
      </footer>

      {inspected !== null ? (
        <OptionInspector
          contract={inspected}
          underlying={underlying}
          spot={spot}
          population={data.population}
          onClose={closeInspector}
        />
      ) : null}
    </section>
  );
}

function ChainRoute({ underlying }: { readonly underlying: string }) {
  const chain = useOptionChain(underlying);
  const queryState = pageStateOf(chain);
  const data = chain.data;
  const state = chainStateOf(queryState, data);

  return (
    <>
      <UnderlyingPicker current={underlying} />
      {state === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : state === 'empty' ? (
        <DataStateBoundary
          state="empty"
          detail={`Aucun snapshot de chaîne publié pour « ${underlying} » — raison serveur : ${
            data?.reason ?? 'non fournie'
          }. Rien n'est inventé à la place.`}
        />
      ) : state === 'loading' || state === 'offline' || state === 'error' ? (
        <DataStateBoundary
          state={state}
          {...(state === 'offline'
            ? { detail: "L'API locale est injoignable — la chaîne ne peut pas être affichée." }
            : state === 'error'
              ? { detail: "Réponse invalide ou inattendue de l'API — aucune chaîne affichée." }
              : {})}
        />
      ) : data !== undefined ? (
        <ChainFrame key={underlying} data={data} state={state} underlying={underlying} />
      ) : null}
    </>
  );
}

export function OptionsPage() {
  const { underlying } = useParams<{ underlying?: string }>();

  return (
    <article className="vx-page" aria-labelledby="vx-page-title-options">
      <div className="vx-page-header">
        <h1 id="vx-page-title-options">Options</h1>
        <p className="vx-page-question">
          Quels contrats sont réellement exploitables et quels risques portent-ils ?
        </p>
      </div>

      {underlying === undefined || underlying === '' ? (
        <>
          <UnderlyingPicker current={null} />
          <DataStateBoundary
            state="empty"
            detail="Aucun sous-jacent sélectionné — en choisir un ci-dessus. Aucun instrument n'est ouvert par défaut."
          />
        </>
      ) : (
        <ChainRoute underlying={underlying} />
      )}
    </article>
  );
}
