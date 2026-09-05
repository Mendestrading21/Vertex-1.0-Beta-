import type { MarketsSector } from '../../api/client.ts';
import { GROUP_LABELS_FR, flattenTickers, frDecimal, signSymbolOf } from './marketsView.ts';

/**
 * Carte sectorielle — la planche la montre sur Aujourd'hui ET sur Marchés :
 * une tuile par secteur, les instruments couverts et leur rendement signé.
 *
 * TOUT vient du snapshot `markets_overview` : le rendement de chaque
 * instrument est la chaîne serveur `return_1d_pct`, telle quelle, virgule
 * française. AUCUN rendement de SECTEUR n'est affiché : le contrat n'en
 * publie pas, et le calculer ici (moyenne, pondération) créerait une seconde
 * autorité. La tuile dit donc ce qu'elle sait — combien d'instruments sont
 * couverts sur combien déclarés — et montre les instruments un à un.
 *
 * La couleur suit le signe mais ne le porte jamais seule : chaque puce écrit
 * le glyphe et la valeur signée, et un texte masqué nomme le groupe.
 */
export interface SectorGridProps {
  readonly sectors: readonly MarketsSector[];
  /** Instrument sélectionné (inspecteur). `null` sans sélection. */
  readonly selected?: string | null;
  /** Sans `onSelect`, les puces sont de simples libellés — jamais un bouton mort. */
  readonly onSelect?: (ticker: string) => void;
}

export function SectorGrid({ sectors, selected = null, onSelect }: SectorGridProps) {
  if (sectors.length === 0) {
    return (
      <p className="vx-sector-empty" role="status">
        Aucun secteur publié par le worker — rien n&apos;est dessiné à la place.
      </p>
    );
  }
  return (
    <div className="vx-sector-grid" data-testid="sector-grid">
      {sectors.map((sector) => {
        const entries = flattenTickers([sector]);
        return (
          <section key={sector.sector} className="vx-sector" aria-label={sector.label}>
            <header className="vx-sector-head">
              <h3>{sector.label}</h3>
              <span className="vx-sector-count">
                {sector.covered_count}/{sector.declared_count} couverts
              </span>
            </header>
            {entries.length === 0 ? (
              <p className="vx-sector-none">Aucun instrument couvert.</p>
            ) : (
              <ul className="vx-sector-chips">
                {entries.map((entry) => {
                  const texte = (
                    <>
                      <code>{entry.ticker.ticker}</code>
                      <span className="vx-sector-return">
                        <span aria-hidden="true">{signSymbolOf(entry.group)}</span>{' '}
                        {frDecimal(entry.ticker.return_1d_pct)} %
                      </span>
                      <span className="vx-visually-hidden">({GROUP_LABELS_FR[entry.group]})</span>
                    </>
                  );
                  return (
                    <li key={entry.ticker.ticker} data-sign={entry.group}>
                      {onSelect === undefined ? (
                        <span className="vx-sector-chip">{texte}</span>
                      ) : (
                        <button
                          type="button"
                          className="vx-sector-chip"
                          aria-pressed={selected === entry.ticker.ticker}
                          onClick={() => {
                            onSelect(entry.ticker.ticker);
                          }}
                        >
                          {texte}
                        </button>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        );
      })}
    </div>
  );
}
