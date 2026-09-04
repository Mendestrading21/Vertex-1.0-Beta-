import { useCallback, useEffect, useId, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import type { OptionChainContract } from '../../api/client.ts';
import { InspectorPanel } from '../../shell/inspector.tsx';
import { SIMULATOR_TRANSFER_VERSION } from '../simulator/transfer.ts';
import type { SimulatorTransfer } from '../simulator/transfer.ts';
import type { CalculationMetaView, SpotView } from './optionsView.ts';
import { AbsentCell } from '../../components/absence.tsx';
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

function CalculationMeta({ meta }: { readonly meta: CalculationMetaView | null }) {
  if (meta === null) {
    return <AbsentCell quoi="lignée de calcul" nature="not_published" reason={null} accord="f" />;
  }
  return (
    <dl className="vx-inspector-calc">
      <div>
        <dt>CalculationRecord</dt>
        <dd>
          <code>{meta.calculationId ?? 'calcul non publié'}</code>
        </dd>
      </div>
      <div>
        <dt>Moteur</dt>
        <dd>
          <code>{meta.engineVersion ?? 'non publié'}</code>
        </dd>
      </div>
      <div>
        <dt>Méthode</dt>
        <dd>{meta.method ?? <span className="vx-cell-absent">méthode non publiée</span>}</dd>
      </div>
      <div>
        <dt>input_hash</dt>
        <dd>
          <code className="vx-inspector-hash">{meta.inputHash ?? 'non publié'}</code>
        </dd>
      </div>
      <div>
        <dt>result_hash</dt>
        <dd>
          <code className="vx-inspector-hash">{meta.resultHash ?? 'non publié'}</code>
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
  readonly transferBlockReason: string | null;
  readonly onClose: () => void;
}

export function OptionInspector({
  contract,
  underlying,
  spot,
  population,
  transferBlockReason,
  onClose,
}: OptionInspectorProps) {
  const titleId = useId();
  const transferNoteId = useId();
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
  const quoteTransferBlockReason =
    quote.status !== 'OK'
      ? `Transfert bloqué : statut de quote ${quote.status ?? 'NON_PUBLIÉ'}. Seule une quote OK peut fournir une prime au Simulateur.`
      : quote.ask === null
        ? 'Transfert bloqué : ask non publié. Aucune prime ne sera suggérée au Simulateur.'
        : null;
  const effectiveTransferBlockReason = transferBlockReason ?? quoteTransferBlockReason;
  const canTransfer =
    contract.right !== null && contract.strike !== null && effectiveTransferBlockReason === null;

  function sendToSimulator(): void {
    if (
      contract.right === null ||
      contract.strike === null ||
      effectiveTransferBlockReason !== null ||
      quote.status !== 'OK' ||
      quote.ask === null
    ) {
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
      premiumSide: 'ASK',
      spot: spot?.value ?? null,
      iv: iv.status === 'OK' ? iv.value : null,
      population,
    };
    void navigate('/simulator', { state: { simulatorTransfer: transfer } });
  }

  return (
    <InspectorPanel
      subject={`${contract.right ?? 'sens non publié'} ${
        contract.strike ?? 'strike non publié'
      } · ${contract.expiration} · ${contract.trading_class}`}
    >
      <div ref={attacherPanneau} className="vx-sheet" data-testid="option-inspector">
        <div className="vx-sheet-head">
          {/* Le sujet est déjà rendu par l'inspecteur : ce titre reste pour
              `aria-labelledby` sans doubler visuellement l'en-tête. */}
          <h3 id={titleId} className="vx-visually-hidden">
            {contract.right ?? 'sens non publié'} {contract.strike ?? 'strike non publié'} ·{' '}
            {contract.expiration} ·{' '}
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
              <AbsentCell quoi="con_id" nature="not_published" reason="identité incomplète" />
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
          <dd>{contract.right ?? <AbsentCell quoi="sens" nature="not_recognised" reason={null} />}</dd>
        </div>
        <div>
          <dt>Strike</dt>
          <dd>
            {contract.strike === null ? (
              <AbsentCell quoi="strike" nature="not_recognised" reason={null} />
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
              <AbsentCell quoi="bid" nature="not_published" reason={null} />
            ) : (
              <code className="vx-num">
                {quote.bid} {contract.currency} ({quote.bidSize ?? 'taille non publiée'})
              </code>
            )}
          </dd>
        </div>
        <div>
          <dt>Ask / taille</dt>
          <dd>
            {quote.ask === null ? (
              <AbsentCell quoi="ask" nature="not_published" reason={null} />
            ) : (
              <code className="vx-num">
                {quote.ask} {contract.currency} ({quote.askSize ?? 'taille non publiée'})
              </code>
            )}
          </dd>
        </div>
        <div>
          <dt>Observée (UTC)</dt>
          <dd>
            {quote.observedAt === null ? (
              <AbsentCell quoi="instant d’observation" nature="not_published" reason={null} />
            ) : (
              <time dateTime={quote.observedAt}>{quote.observedAt}</time>
            )}
          </dd>
        </div>
        <div>
          <dt>Âge au snapshot</dt>
          <dd>
            {quote.ageSeconds === null ? (
              <AbsentCell quoi="âge" nature="not_published" reason={null} />
            ) : (
              <code className="vx-num">{quote.ageSeconds} s</code>
            )}
          </dd>
        </div>
        <div>
          <dt>Volume</dt>
          <dd>
            {contract.volume === null ? (
              <AbsentCell quoi="volume" nature="not_published" reason={null} />
            ) : (
              <code className="vx-num">{contract.volume}</code>
            )}
          </dd>
        </div>
        <div>
          <dt>Open interest</dt>
          <dd>
            {contract.open_interest === null ? (
              <AbsentCell quoi="open interest" nature="not_published" reason={null} />
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
              volatilité annualisée (décimal, 0.25 = 25 %/an), côté{' '}
              {iv.quoteSide ?? 'non publié'}
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
          aria-describedby={transferNoteId}
        >
          Envoyer au Simulateur
        </button>
        <p id={transferNoteId} className="vx-inspector-note" role="status">
          {effectiveTransferBlockReason ??
            "Transfert d'analyse théorique uniquement : le Simulateur prépare une étude, jamais une transaction."}
        </p>
      </div>
      </div>
    </InspectorPanel>
  );
}
