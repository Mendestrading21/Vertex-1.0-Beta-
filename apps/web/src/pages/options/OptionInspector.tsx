import { useCallback, useEffect, useId, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import type { OptionChainContract } from '../../api/client.ts';
import { InspectorPanel } from '../../shell/inspector.tsx';
import { SIMULATOR_TRANSFER_VERSION } from '../simulator/transfer.ts';
import type { SimulatorTransfer } from '../simulator/transfer.ts';
import type { CalculationMetaView, SpotView } from './optionsView.ts';
import { greeksViewOf, ivAbsentLabel, ivViewOf, quoteViewOf } from './optionsView.ts';

/**
 * OptionInspector — panneau de l'INSPECTEUR du shell (LOT-13), montrant UN
 * contrat tel que publié :
 * identité complète, quote verbatim + qualité, IV/Greeks Vertex avec unités,
 * badge THÉORIQUE et lignée `CalculationRecord`, ou leur raison d'absence
 * typée (jamais un zéro).
 *
 * Unique action : « Envoyer au Simulateur » — un transfert d'ANALYSE typé
 * (voir ../simulator/transfer.ts). Aucun bouton, champ ou vocabulaire
 * d'exécution n'existe ici, par construction.
 */

function AbsentValue({ label }: { readonly label: string }) {
  return (
    // Voir AttentionQueue.tsx : `aria-label` est interdit sur le rôle
    // implicite `generic` d'un <span> ; `title` seul ne fournit pas un
    // nom accessible fiable.
    <span className="vx-cell-absent" role="img" aria-label={label} title={label}>
      —
    </span>
  );
}

function CalculationMeta({ meta }: { readonly meta: CalculationMetaView | null }) {
  if (meta === null) {
    return <AbsentValue label="lignée de calcul non publiée" />;
  }
  return (
    <dl className="vx-inspector-calc">
      <div>
        <dt>CalculationRecord</dt>
        <dd>
          <code>{meta.calculationId ?? '—'}</code>
        </dd>
      </div>
      <div>
        <dt>Moteur</dt>
        <dd>
          <code>{meta.engineVersion ?? '—'}</code>
        </dd>
      </div>
      <div>
        <dt>Méthode</dt>
        <dd>{meta.method ?? '—'}</dd>
      </div>
      <div>
        <dt>input_hash</dt>
        <dd>
          <code className="vx-inspector-hash">{meta.inputHash ?? '—'}</code>
        </dd>
      </div>
      <div>
        <dt>result_hash</dt>
        <dd>
          <code className="vx-inspector-hash">{meta.resultHash ?? '—'}</code>
        </dd>
      </div>
    </dl>
  );
}

export interface OptionInspectorProps {
  readonly contract: OptionChainContract;
  readonly underlying: string;
  readonly spot: SpotView | null;
  readonly population: string | null;
  readonly onClose: () => void;
}

export function OptionInspector({
  contract,
  underlying,
  spot,
  population,
  onClose,
}: OptionInspectorProps) {
  const titleId = useId();
  const navigate = useNavigate();
  const [sheetNode, setSheetNode] = useState<HTMLDivElement | null>(null);

  /**
   * Le focus entre dans le panneau dès que son nœud existe.
   *
   * Une ref de rappel, et non un `useEffect([])` : le panneau est monté par
   * PORTAIL, et au premier rendu le nœud d'accueil du shell n'est pas encore
   * résolu. Un effet de montage ne trouverait alors aucun bouton à focaliser —
   * c'est le défaut rencontré en convertissant Aujourd'hui.
   */
  const attacherPanneau = useCallback((node: HTMLDivElement | null) => {
    setSheetNode(node);
    node?.querySelector<HTMLElement>('button')?.focus();
  }, []);

  /**
   * `Échap` referme depuis n'importe quel élément du panneau.
   *
   * Écouteur NATIF sur le nœud plutôt que `onKeyDown` sur le conteneur :
   * sans `role="dialog"`, ce conteneur est un élément statique, et la règle
   * d'accessibilité du linter refuse — à juste titre — d'y accrocher un
   * gestionnaire clavier.
   */
  useEffect(() => {
    if (sheetNode === null) {
      return;
    }
    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === 'Escape') {
        event.stopPropagation();
        onClose();
      }
    }
    sheetNode.addEventListener('keydown', onKeyDown);
    return () => {
      sheetNode.removeEventListener('keydown', onKeyDown);
    };
  }, [sheetNode, onClose]);

  const quote = quoteViewOf(contract);
  const iv = ivViewOf(contract);
  const greeks = greeksViewOf(contract);
  const canTransfer = contract.right !== null && contract.strike !== null;

  function sendToSimulator(): void {
    if (contract.right === null || contract.strike === null) {
      return;
    }
    const transfer: SimulatorTransfer = {
      version: SIMULATOR_TRANSFER_VERSION,
      source: 'options',
      underlying,
      conId: contract.con_id,
      right: contract.right,
      strike: contract.strike,
      expiration: contract.expiration,
      tradingClass: contract.trading_class,
      multiplier: contract.multiplier,
      currency: contract.currency,
      premium: quote.ask,
      premiumSide: quote.ask !== null ? 'ASK' : null,
      spot: spot?.value ?? null,
      iv: iv.status === 'OK' ? iv.value : null,
      population,
    };
    void navigate('/simulator', { state: { simulatorTransfer: transfer } });
  }

  return (
    <InspectorPanel
      subject={`${contract.right ?? '?'} ${contract.strike ?? '—'} · ${contract.expiration} · ${contract.trading_class}`}
    >
      <div ref={attacherPanneau} className="vx-sheet" data-testid="option-inspector">
        <div className="vx-sheet-head">
          {/* Le sujet est déjà rendu par l'inspecteur : ce titre reste pour
              `aria-labelledby` sans doubler visuellement l'en-tête. */}
          <h3 id={titleId} className="vx-visually-hidden">
            {contract.right ?? '?'} {contract.strike ?? '—'} · {contract.expiration} ·{' '}
            {contract.trading_class}
          </h3>
          <button type="button" className="vx-sheet-close" onClick={onClose}>
            Fermer
          </button>
        </div>
      {contract.synthetic ? <p className="vx-badge vx-badge-synthetic">SYNTHÉTIQUE</p> : null}

      <h3>Identité du contrat</h3>
      <dl className="vx-sheet-facts">
        <div>
          <dt>con_id</dt>
          <dd>
            {contract.con_id === null ? (
              <AbsentValue label="con_id absent (identité incomplète)" />
            ) : (
              <code>{contract.con_id}</code>
            )}
          </dd>
        </div>
        <div>
          <dt>Sous-jacent</dt>
          <dd>
            <code>{underlying}</code>
          </dd>
        </div>
        <div>
          <dt>Right</dt>
          <dd>{contract.right ?? <AbsentValue label="right illisible" />}</dd>
        </div>
        <div>
          <dt>Strike</dt>
          <dd>
            {contract.strike === null ? (
              <AbsentValue label="strike illisible" />
            ) : (
              <code className="vx-num">
                {contract.strike} {contract.currency}
              </code>
            )}
          </dd>
        </div>
        <div>
          <dt>Expiration</dt>
          <dd>
            <time dateTime={contract.expiration}>{contract.expiration}</time>
          </dd>
        </div>
        <div>
          <dt>Trading class</dt>
          <dd>
            <code>{contract.trading_class}</code>
          </dd>
        </div>
        <div>
          <dt>Exchange</dt>
          <dd>
            <code>{contract.exchange}</code>
          </dd>
        </div>
        <div>
          <dt>Multiplicateur</dt>
          <dd>
            <code className="vx-num">{contract.multiplier}</code>
          </dd>
        </div>
        <div>
          <dt>Devise</dt>
          <dd>{contract.currency}</dd>
        </div>
        <div>
          <dt>Style / règlement</dt>
          <dd>
            {contract.style} / {contract.settlement}
          </dd>
        </div>
      </dl>

      <h3>Quote observée et qualité</h3>
      <dl className="vx-sheet-facts">
        <div>
          <dt>Statut</dt>
          <dd>
            <span className="vx-quote-status" data-status={quote.status ?? 'UNKNOWN'}>
              {quote.status ?? 'inconnu'}
            </span>
          </dd>
        </div>
        <div>
          <dt>Bid / taille</dt>
          <dd>
            {quote.bid === null ? (
              <AbsentValue label="bid absent" />
            ) : (
              <code className="vx-num">
                {quote.bid} {contract.currency} ({quote.bidSize ?? '—'})
              </code>
            )}
          </dd>
        </div>
        <div>
          <dt>Ask / taille</dt>
          <dd>
            {quote.ask === null ? (
              <AbsentValue label="ask absent" />
            ) : (
              <code className="vx-num">
                {quote.ask} {contract.currency} ({quote.askSize ?? '—'})
              </code>
            )}
          </dd>
        </div>
        <div>
          <dt>Observée (UTC)</dt>
          <dd>
            {quote.observedAt === null ? (
              <AbsentValue label="instant d'observation non publié" />
            ) : (
              <time dateTime={quote.observedAt}>{quote.observedAt}</time>
            )}
          </dd>
        </div>
        <div>
          <dt>Âge au snapshot</dt>
          <dd>
            {quote.ageSeconds === null ? (
              <AbsentValue label="âge non publié" />
            ) : (
              <code className="vx-num">{quote.ageSeconds} s</code>
            )}
          </dd>
        </div>
        <div>
          <dt>Volume</dt>
          <dd>
            {contract.volume === null ? (
              <AbsentValue label="volume non publié" />
            ) : (
              <code className="vx-num">{contract.volume}</code>
            )}
          </dd>
        </div>
        <div>
          <dt>Open interest</dt>
          <dd>
            {contract.open_interest === null ? (
              <AbsentValue label="open interest non publié" />
            ) : (
              <code className="vx-num">
                {contract.open_interest} ({contract.open_interest_status ?? 'statut non publié'})
              </code>
            )}
          </dd>
        </div>
      </dl>

      <h3>
        IV Vertex{' '}
        {iv.status === 'OK' ? <span className="vx-badge vx-badge-theoretical">THÉORIQUE</span> : null}
      </h3>
      {iv.status === 'OK' && iv.value !== null ? (
        <>
          <p className="vx-inspector-value">
            <code className="vx-num">{iv.value}</code>{' '}
            <span className="vx-inspector-unit">
              volatilité annualisée (décimal, 0.25 = 25 %/an), côté {iv.quoteSide ?? '?'}
            </span>
          </p>
          <CalculationMeta meta={iv.calculation} />
        </>
      ) : (
        <p className="vx-inspector-absent" role="status">
          {ivAbsentLabel(iv.reason)}
        </p>
      )}

      <h3>
        Greeks Vertex{' '}
        {greeks.status === 'OK' ? (
          <span className="vx-badge vx-badge-theoretical">THÉORIQUE</span>
        ) : null}
      </h3>
      {greeks.status === 'OK' ? (
        <>
          <dl className="vx-sheet-facts">
            {greeks.entries.map((entry) => (
              <div key={entry.key}>
                <dt>{entry.label}</dt>
                <dd>
                  <code className="vx-num">{entry.value}</code>{' '}
                  <span className="vx-inspector-unit">{entry.unit}</span>
                </dd>
              </div>
            ))}
          </dl>
          <CalculationMeta meta={greeks.calculation} />
        </>
      ) : (
        <p className="vx-inspector-absent" role="status">
          Greeks absents — {greeks.reason ?? 'raison non publiée'}
        </p>
      )}

      <div className="vx-inspector-actions">
        <button
          type="button"
          className="vx-primary-action"
          onClick={sendToSimulator}
          disabled={!canTransfer}
        >
          Envoyer au Simulateur
        </button>
        <p className="vx-inspector-note">
          Transfert d'analyse théorique uniquement : le Simulateur prépare une étude, jamais une
          transaction.
        </p>
      </div>
      </div>
    </InspectorPanel>
  );
}
