import { RingShares } from '../../components/widgets/RingShares.tsx';
import type { RingPart } from '../../components/widgets/RingShares.tsx';
import { SharesBand } from '../../components/widgets/SharesBand.tsx';
import type { SharePart } from '../../components/widgets/SharesBand.tsx';
import type { CurrencyBlockView } from './portfolioView.ts';

/**
 * Concentration par ticker — barres CSS (tokens) + table équivalente.
 *
 * Les poids affichés sont les chaînes serveur VERBATIM
 * (`portfolio.concentration`, poids normalisés + Herfindahl). Le nombre n'est
 * parsé que pour la GÉOMÉTRIE de la barre (largeur), jamais pour recalculer
 * ou reformater une valeur.
 *
 * REFONTE V3 — OÙ VIT LA CHAÎNE EXACTE. Le poids serveur fait jusqu'à
 * 28 décimales (`0.4295692665890570437233410943`, mesuré à l'écran). Affiché
 * tel quel à côté de sa barre, il ne se lit pas : il occupe la moitié de la
 * ligne et aucun œil n'en tire de comparaison. Il n'est pas question de
 * l'arrondir ici — arrondir, c'est produire une valeur que le serveur n'a pas
 * servie, ce que `.claude/rules/frontend.md` interdit.
 *
 * La résolution ne retire donc RIEN. La chaîne exacte reste :
 *   1. dans la table équivalente juste dessous, dont l'en-tête dit lui-même
 *      « Poids normalisé (chaîne serveur) » ;
 *   2. dans le nom accessible de chaque ligne de barre — un lecteur d'écran
 *      entend la valeur complète, chiffre par chiffre.
 * Seul l'œil est soulagé, au profit de la barre, qui est la comparaison qu'il
 * cherchait.
 *
 * LOT-A6 : ce composant est le CORPS de la dominante de la planche §7 ; la
 * carte (titre, kicker, pied) est portée par la page. Il sert aussi la page
 * Risques (module « Concentration du registre »), en barres seules.
 */

/**
 * Poids servis en bande de parts (LOT P4).
 *
 * Les poids publiés sont des RATIOS rendus, pas des pourcentages : la
 * primitive les reçoit sous l'identifiant `ratio`, qui dit leur échelle, et
 * la géométrie vit dans `geometry.ts`. La chaîne exacte — jusqu'à 28
 * décimales — reste écrite dans la légende de la bande ET dans la table
 * équivalente ci-dessous : rien n'est arrondi, rien n'est tronqué.
 */
export function ConcentrationBars({
  block,
  testIdPrefix = 'pf-bars',
}: {
  readonly block: CurrencyBlockView;
  readonly testIdPrefix?: string;
}) {
  return (
    <div data-testid={`${testIdPrefix}-${block.currency}`}>
      <SharesBand
        parts={block.weights.map((entry): SharePart => ({ key: entry.ticker, label: entry.ticker, ratio: entry.weight }))}
        unit={`du registre ${block.currency}`}
        ariaLabel={`Poids normalisés servis en ${block.currency}`}
        emptyLabel="Aucun poids publié : aucune bande tracée."
      />
    </div>
  );
}

export function ConcentrationPanel({ blocks }: { readonly blocks: readonly CurrencyBlockView[] }) {
  return (
    <div className="vx-pf-concentration-body">
      {blocks.length === 0 ? (
        <p className="vx-cell-absent" role="status">
          Aucune position dérivée du journal : aucune concentration à mesurer.
        </p>
      ) : null}
      {blocks.map((block) => (
        <div key={block.currency} className="vx-pf-concentration-block">
          <h3>
            Devise <code>{block.currency}</code>
          </h3>
          {block.concentrationStatus !== 'OK' ? (
            <p className="vx-cell-absent" data-testid={`pf-concentration-absent-${block.currency}`}>
              {block.concentrationStatus ?? 'ABSENT'}
              {block.concentrationReason !== null ? ` — ${block.concentrationReason}` : null} : aucune
              concentration n'est affichée sans calcul serveur publié.
            </p>
          ) : (
            <>
              <div className="vx-pf-concentration-figures">
                <RingShares
                  parts={block.weights.map((entry): RingPart => ({ key: entry.ticker, label: entry.ticker, ratio: entry.weight }))}
                  centerValue={block.herfindahl}
                  centerLabel="Herfindahl servi"
                  ariaLabel={`Poids normalisés servis en ${block.currency}, en anneau`}
                />
                <div className="vx-pf-concentration-band">
                  <ConcentrationBars block={block} />
                </div>
              </div>
              <table className="vx-pf-concentration-table" aria-label={`Poids de concentration (${block.currency})`}>
                <thead>
                  <tr>
                    <th scope="col">Ticker</th>
                    <th scope="col">Poids normalisé (chaîne serveur)</th>
                  </tr>
                </thead>
                <tbody>
                  {block.weights.map((entry) => (
                    <tr key={entry.ticker}>
                      <th scope="row">
                        <code>{entry.ticker}</code>
                      </th>
                      <td className="vx-num">{entry.weight}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="vx-pf-concentration-meta">
                Indice de Herfindahl :{' '}
                {block.herfindahl === null ? (
                  <span data-absent="true">non publié</span>
                ) : (
                  <code className="vx-num">{block.herfindahl}</code>
                )}
                {' · '}valeur totale marquée :{' '}
                {block.totalValue === null ? (
                  <span data-absent="true">non publiée</span>
                ) : (
                  <>
                    <code className="vx-num">{block.totalValue}</code> {block.currency}
                  </>
                )}
                {block.concentrationCalculation !== null ? (
                  <>
                    {' · '}calcul{' '}
                    <code>{block.concentrationCalculation.calculationId ?? 'non publié'}</code> (
                    {block.concentrationCalculation.engineVersion ?? 'version non publiée'})
                  </>
                ) : null}
              </p>
            </>
          )}
        </div>
      ))}
    </div>
  );
}
