import { AbsentCell } from '../../components/absence.tsx';
import { exclusionReasonLabel } from './portfolioView.ts';
import type { ExcludedLotRow, ValuedLotRow } from './portfolioView.ts';

/**
 * Lots ouverts VALORISÉS (chaînes serveur verbatim) puis, dans une section
 * SÉPARÉE, les lots EXCLUS avec leur raison.
 *
 * Un lot exclu n'apparaît JAMAIS à zéro dans la table des valorisés : les
 * deux populations de lignes restent disjointes et ne sont jamais sommées.
 *
 * LOT-A6 : ce composant est le CORPS du module « Lots ouverts valorisés » de
 * la planche §7 (la carte est portée par la page) ; chaque ligne valorisée
 * ouvre l'inspecteur du lot (« Inspecter {ticker} »), qui montre sa
 * provenance manuelle, son poids publié et son journal.
 */

export function PortfolioTable({
  lots,
  excluded,
  selected = null,
  onInspect,
}: {
  readonly lots: readonly ValuedLotRow[];
  readonly excluded: readonly ExcludedLotRow[];
  readonly selected?: string | null;
  readonly onInspect?: (lotId: string) => void;
}) {
  return (
    <div className="vx-pf-table-body">
      {lots.length === 0 ? (
        <p className="vx-cell-absent" data-testid="pf-lots-empty">
          Aucun lot ouvert valorisé — l'absence reste une absence, aucun zéro n'est fabriqué.
        </p>
      ) : (
        <div className="vx-pf-table-scroll" tabIndex={0} role="region" aria-label="Lots ouverts défilants">
          <table className="vx-pf-lots" aria-label="Lots ouverts valorisés (valeurs serveur exactes)">
            <thead>
              <tr>
                <th scope="col">Ticker</th>
                <th scope="col">Lot</th>
                <th scope="col">Quantité restante</th>
                <th scope="col">Coût unitaire</th>
                <th scope="col">Mark (clôture synthétique)</th>
                <th scope="col">Valeur marquée</th>
                <th scope="col">P&amp;L latent</th>
                <th scope="col">Devise</th>
                <th scope="col">Qualité de la marque</th>
                {onInspect !== undefined ? <th scope="col">Inspecteur</th> : null}
              </tr>
            </thead>
            <tbody>
              {lots.map((lot) => (
                <tr key={lot.lotId} {...(selected === lot.lotId ? { 'data-selected': 'true' } : {})}>
                  <th scope="row">
                    <code>{lot.ticker}</code>
                  </th>
                  <td>
                    <code>{lot.lotId}</code>
                  </td>
                  <td className="vx-num">{lot.quantity}</td>
                  <td className="vx-num">{lot.unitCost}</td>
                  <td className="vx-num">{lot.mark}</td>
                  <td className="vx-num">{lot.marketValue}</td>
                  <td className="vx-num" data-sign={lot.unrealizedPnl.startsWith('-') ? 'negative' : 'positive'}>
                    {lot.unrealizedPnl}
                  </td>
                  <td>
                    <code>{lot.currency}</code>
                  </td>
                  <td>
                    <span className="vx-badge vx-badge-synthetic">SYNTHÉTIQUE</span>
                  </td>
                  {onInspect !== undefined ? (
                    <td>
                      <button
                        type="button"
                        className="vx-opp-inspect"
                        aria-pressed={selected === lot.lotId}
                        aria-label={`Inspecter ${lot.ticker} (lot ${lot.lotId})`}
                        onClick={() => {
                          onInspect(lot.lotId);
                        }}
                      >
                        Détail
                      </button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <section className="vx-pf-excluded" aria-labelledby="vx-pf-excluded-title" data-testid="pf-excluded">
        <h3 id="vx-pf-excluded-title">Lots exclus de la valorisation ({excluded.length})</h3>
        {excluded.length === 0 ? (
          <p className="vx-cell-absent">Aucun lot exclu.</p>
        ) : (
          <>
            <p className="vx-pf-excluded-note">
              Ces lots ne sont PAS valorisés et n'entrent dans aucun total : un lot sans marque
              utilisable est écarté avec sa raison, jamais compté à zéro.
            </p>
            <div className="vx-pf-table-scroll" tabIndex={0} role="region" aria-label="Lots exclus défilants">
              <table className="vx-pf-excluded-table" aria-label="Lots exclus et raison d'exclusion">
                <thead>
                  <tr>
                    <th scope="col">Lot</th>
                    <th scope="col">Ticker</th>
                    <th scope="col">Devise</th>
                    <th scope="col">Raison (code serveur)</th>
                    <th scope="col">Explication</th>
                  </tr>
                </thead>
                <tbody>
                  {excluded.map((lot, index) => (
                    /* LOT T4-2 — LA CLÉ NE SE FABRIQUE PLUS. `lotId` valait
                       « — » par repli, et les positions invalides le
                       recevaient EN DUR : deux d'entre elles de même ticker et
                       même raison donnaient deux fois la même clé, cassant la
                       réconciliation React. Une ligne SANS identifiant servi
                       prend son rang de rendu — un index n'est pas une donnée,
                       c'est une position, et c'est exactement ce qu'il est. */
                    <tr
                      key={
                        lot.lotId === null
                          ? `sans-lot-${index}-${lot.reason}`
                          : `${lot.lotId}-${lot.reason}`
                      }
                    >
                      <th scope="row">
                        {lot.lotId === null ? (
                          /* Une position invalide n'a pas de lot : elle a été
                             rejetée avant d'en devenir un. Le serveur n'a rien
                             omis — « sans objet », jamais « non publié ». */
                          <AbsentCell quoi="lot" nature="not_applicable" reason={lot.reason} />
                        ) : (
                          <code>{lot.lotId}</code>
                        )}
                      </th>
                      <td>
                        {lot.ticker === null ? (
                          <AbsentCell quoi="instrument" nature="not_published" reason={null} />
                        ) : (
                          <code>{lot.ticker}</code>
                        )}
                      </td>
                      <td>
                        {lot.currency === null ? (
                          <AbsentCell quoi="devise" nature="not_published" reason={null} accord="f" />
                        ) : (
                          <code>{lot.currency}</code>
                        )}
                      </td>
                      <td>
                        <code>{lot.reason}</code>
                      </td>
                      <td>{exclusionReasonLabel(lot.reason)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
