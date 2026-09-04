import { useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import type { OptionChainContract, OptionChainExpiration, OptionChainResponse } from '../../api/client.ts';
import { pageStateOf, useOptionChain } from '../../api/hooks.ts';
import { AbsentModule } from '../../components/AbsentModule.tsx';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import type { DataState } from '../../components/DataStateBoundary.tsx';
import { SyntheticBanner } from '../../components/SyntheticBanner.tsx';
import { useDeclaredInstruments } from '../devUniverse.ts';
import { ChainSnapshotInspector } from './ChainSnapshotInspector.tsx';
import { OptionChainTable } from './OptionChainTable.tsx';
import { OptionInspector } from './OptionInspector.tsx';
import {
  DividendModule,
  IdentityStripModule,
  IvSmileModule,
  RateModule,
  SpotModule,
  UnderlyingModule,
  UnderlyingSeriesModule,
  VolStructureModule,
} from './OptionsModules.tsx';
import { OPTIONS_MODULES, optionsModule } from './optionsModules.ts';
import {
  chainStateOf,
  chainTransferBlockReasonOf,
  groupCoverageOf,
  groupKeyOf,
  groupLabelOf,
  rowBudgetOf,
  spotViewOf,
} from './optionsView.ts';
import { pageAccentAttrs } from '../../components/widgets/pageAccent.ts';
import { Widget } from '../../components/widgets/Widget.tsx';

/**
 * Page Options (`TL / 05`) — question : « Quels contrats sont réellement
 * exploitables et quels risques portent-ils ? »
 *
 * LOT-A5 — LA PLANCHE §5 EN ENTIER. `pages-05-06-options-simulator.png`
 * (moitié gauche) compose quinze modules autour d'une dominante : la table
 * de chaîne Calls | Strike | Puts du groupe (expiration, trading_class)
 * sélectionné — les groupes ne sont JAMAIS fusionnés. Neuf modules sont
 * SERVIS : le sous-jacent (clôture et variation de Marchés, série du
 * dossier), le snapshot de chaîne (références, couverture, budget), le spot
 * observé, le taux et le dividende SUPPOSÉS par le calcul d'IV, le sourire
 * d'IV du groupe affiché et la structure par échéance (géométrie des IV
 * publiées, calls et puts, aucun point de référence choisi). Six n'ont ni
 * source ni contrat : mouvement attendu, IV de référence, rang d'IV,
 * métriques de stratégie ; le composeur et le profil de payoff vivent sur
 * Simulateur, joints par l'unique action de l'inspecteur.
 *
 * L'INSPECTEUR PORTE LE CONTRAT OUVERT (identité, quote, IV et Greeks
 * THÉORIQUES avec leur lignée — LOT-13), sinon la vérité du snapshot.
 * Aucun calcul financier ici : IV, Greeks et statuts arrivent calculés et
 * étiquetés par le worker.
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

function AbsentOptionsModule({ id }: { readonly id: string }) {
  const module = optionsModule(id);
  if (module.status.kind !== 'absent') {
    throw new Error(`Module ${id} is served, not absent`);
  }
  return (
    // LOT P3b — la taille vient du catalogue : sans elle, une absence prend la
    // taille par défaut et déplace ses voisines dans la planche.
    <div data-module={id} data-size={module.size}>
      <AbsentModule title={module.title} question={module.question} reason={module.status.reason} note={module.status.note} />
    </div>
  );
}

/**
 * LOT P3b — LA PLANCHE §5 SANS SOUS-JACENT CHOISI.
 *
 * CE QUE LA PAGE FAISAIT. Elle rendait le sélecteur, une seule carte
 * « Aucune donnée », et laissait les deux tiers de l'écran vides. Un lecteur
 * ne pouvait pas savoir ce que cette destination sait faire : la planche
 * n'existait qu'une fois un instrument ouvert.
 *
 * CE QU'ELLE FAIT MAINTENANT. La planche entière tient sa place. Les six
 * modules SANS SOURCE gardent le motif exact de leur absence — inchangé. Les
 * neuf modules SERVIS déclarent l'état `empty` avec sa cause : aucun
 * sous-jacent n'est sélectionné.
 *
 * CE QU'ELLE N'INVENTE PAS. Aucune valeur, aucun exemple, aucun instrument par
 * défaut. `empty` est un état DÉCLARÉ de `ModuleState`, et `Widget` ne rend
 * aucun enfant dans cet état : il n'y a rien à remplir, donc rien n'est
 * rempli.
 *
 * POURQUOI LA PHRASE VIT DANS LE PIED, ET NON DANS `stateDetail`. La capture
 * l'a montré : `stateDetail` est rendu en `<code>` par `ModuleStatus`, parce
 * que c'est le canal des CAUSES SERVEUR — un `reason_code`, un diagnostic
 * verbatim. Y écrire une phrase française la faisait passer en chasse fixe et
 * la faisait lire comme un code du serveur. La prose va au pied ; le canal du
 * serveur reste au serveur.
 */
const SANS_SELECTION = 'Aucun sous-jacent sélectionné — en choisir un ci-dessus.';

function NoUnderlyingBoard() {
  return (
    <div className="vx-options-grid vx-board" data-testid="options-grid">
      {OPTIONS_MODULES.map((module) =>
        module.status.kind === 'absent' ? (
          <AbsentOptionsModule key={module.id} id={module.id} />
        ) : (
          <Widget
            key={module.id}
            id={module.id}
            size={module.size}
            title={module.title}
            state="empty"
            footer={<>{SANS_SELECTION}</>}
          >
            {null}
          </Widget>
        ),
      )}
    </div>
  );
}

interface InspectedContractSelection {
  readonly contract: OptionChainContract;
  readonly groupKey: string;
  readonly snapshot: OptionChainResponse;
}

function ChainFrame({
  data,
  state,
  underlying,
  groups,
  selected,
  onSelectGroup,
  onInspect,
}: {
  readonly data: OptionChainResponse;
  readonly state: DataState;
  readonly underlying: string;
  readonly groups: readonly OptionChainExpiration[];
  readonly selected: OptionChainExpiration | null;
  readonly onSelectGroup: (key: string) => void;
  readonly onInspect: (contract: OptionChainContract, trigger: HTMLElement | null) => void;
}) {
  const budget = rowBudgetOf(data);
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
      : state === 'stale'
        ? (data.reason ?? 'Le relais a publié ce snapshot comme périmé.')
        : state === 'delayed'
          ? 'La population publiée est DELAYED : ces observations ne décrivent pas le marché à cet instant.'
          : undefined;
  const pendingTrigger = useRef<HTMLElement | null>(null);

  return (
    <section className="vx-chartframe" data-rank="dominant" data-module="chain" aria-labelledby="vx-chain-title">
      <header className="vx-chartframe-head">
        <p className="vx-chartframe-question">
          Quels contrats sont réellement exploitables et quels risques portent-ils ?
        </p>
        <h2 id="vx-chain-title">Chaîne d'options — {underlying}</h2>
      </header>

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
                    onSelectGroup(key);
                  }}
                >
                  <span className="vx-chain-group-name">{groupLabelOf(group)}</span>
                  <span className="vx-chain-group-meta">
                    qualité {group.quality} · {coverage.expected ?? 'nombre non publié de'}{' '}
                    contrats attendus · {coverage.quotesValid ?? 'nombre non publié de'} quotes
                    saines · {coverage.ivResolved ?? 'nombre non publié d’'} IV résolues ·{' '}
                    {coverage.discardedCount ?? 'nombre non publié d’'} écarté(s) du calcul
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
                  pendingTrigger.current = target;
                }
              }}
            >
              <OptionChainTable
                group={selected}
                onInspect={(contract) => {
                  onInspect(contract, pendingTrigger.current);
                }}
              />
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
        <p data-testid="chain-population-limit">
          Limites : population publiée <code>{data.population ?? 'NON_PUBLIÉE'}</code> ; une quote
          croisée, périmée ou absente n'a jamais d'IV ; le statut d'open interest est relayé
          contrat par contrat lorsqu'il est publié.
        </p>
      </footer>
    </section>
  );
}

function OptionsBoard({
  data,
  state,
  queryRefreshing,
  underlying,
}: {
  readonly data: OptionChainResponse;
  readonly state: DataState;
  readonly queryRefreshing: boolean;
  readonly underlying: string;
}) {
  const groups = data.expirations;
  const [selectedKey, setSelectedKey] = useState<string>(() =>
    groups.length > 0 && groups[0] !== undefined ? groupKeyOf(groups[0]) : '',
  );
  const [inspected, setInspected] = useState<InspectedContractSelection | null>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  const selected = groups.find((group) => groupKeyOf(group) === selectedKey) ?? groups[0] ?? null;
  // Un contrat inspecté n'est valable que dans le snapshot et le groupe qui
  // l'ont publié. Un refetch SSE peut remplacer sa quote ou retirer le groupe :
  // l'ancien objet ne doit alors jamais redevenir transférable avec le nouvel
  // état global. La comparaison de référence est immédiate au rendu.
  const currentInspected =
    inspected !== null && inspected.snapshot === data && selected !== null && inspected.groupKey === groupKeyOf(selected)
      ? inspected.contract
      : null;
  const spot = spotViewOf(data);
  const transferBlockReason = chainTransferBlockReasonOf(state, data, selected?.quality ?? null, queryRefreshing);

  function closeInspector(): void {
    setInspected(null);
    triggerRef.current?.focus();
    triggerRef.current = null;
  }

  return (
    <>
      <div className="vx-options-grid vx-board" data-testid="options-grid">
        <div data-module="underlying">
          <UnderlyingModule underlying={underlying} />
        </div>
        <div data-module="identity-strip">
          <IdentityStripModule data={data} />
        </div>

        <div data-module="spot">
          <SpotModule data={data} />
        </div>
        <AbsentOptionsModule id="expected-move" />
        <AbsentOptionsModule id="iv-reference" />
        <AbsentOptionsModule id="iv-rank" />

        <div data-module="dividend">
          <DividendModule data={data} />
        </div>
        <div data-module="rate">
          <RateModule data={data} />
        </div>
        <div data-module="vol-structure">
          <VolStructureModule groups={groups} />
        </div>

        <div data-module="underlying-series">
          <UnderlyingSeriesModule underlying={underlying} />
        </div>
        <div data-module="iv-smile">
          <IvSmileModule group={selected} />
        </div>

        <ChainFrame
          data={data}
          state={state}
          underlying={underlying}
          groups={groups}
          selected={selected}
          onSelectGroup={(key) => {
            // L'inspecteur porte un contrat du groupe courant. Le conserver
            // après une bascule ferait juger cet ancien contrat avec la qualité
            // du nouveau groupe. Fermer le panneau maintient cette identité.
            if (key !== selectedKey) {
              setInspected(null);
              triggerRef.current = null;
            }
            setSelectedKey(key);
          }}
          onInspect={(contract, trigger) => {
            triggerRef.current = trigger;
            if (selected !== null) {
              setInspected({ contract, groupKey: groupKeyOf(selected), snapshot: data });
            }
          }}
        />

        <AbsentOptionsModule id="strategy-builder" />
        <AbsentOptionsModule id="payoff-profile" />
        <AbsentOptionsModule id="strategy-metrics" />
      </div>

      {currentInspected !== null ? (
        <OptionInspector
          contract={currentInspected}
          underlying={underlying}
          spot={spot}
          population={data.population}
          transferBlockReason={transferBlockReason}
          onClose={closeInspector}
        />
      ) : (
        <ChainSnapshotInspector data={data} />
      )}
    </>
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
        <OptionsBoard
          key={underlying}
          data={data}
          state={state}
          queryRefreshing={queryState === 'refreshing'}
          underlying={underlying}
        />
      ) : null}
    </>
  );
}

export function OptionsPage() {
  const { underlying } = useParams<{ underlying?: string }>();

  return (
    <article className="vx-page" {...pageAccentAttrs('options')} aria-labelledby="vx-page-title-options">
      <div className="vx-page-header">
        <h1 id="vx-page-title-options">Options</h1>
        <p className="vx-page-question">
          Quels contrats sont réellement exploitables et quels risques portent-ils ?
        </p>
      </div>

      {underlying === undefined || underlying === '' ? (
        <>
          <UnderlyingPicker current={null} />
          <NoUnderlyingBoard />
        </>
      ) : (
        <ChainRoute underlying={underlying} />
      )}
    </article>
  );
}
