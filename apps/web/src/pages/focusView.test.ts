import { describe, expect, it } from 'vitest';

import { makeExcludedCandidate, makeMarketsSectors, makeOpportunities, makeOpportunitiesContent } from '../test/fixtures.ts';
import { FOCUS_LIMIT, focusInstrumentsOf } from './focusView.ts';
import { opportunitiesContentOf } from './opportunities/opportunitiesView.ts';

describe('focusInstrumentsOf — les dossiers publiés, dans l’ordre publié, bornés', () => {
  it('retient un candidat dont les barres sont OK et dont Marchés publie la cotation', () => {
    const view = opportunitiesContentOf(makeOpportunities().content);
    // Le fixture exclut SYN-ENER-01 (barres OK) ; Marchés le cote.
    const entries = focusInstrumentsOf(view, makeMarketsSectors());
    expect(entries.map((entry) => entry.ticker.ticker)).toEqual(['SYN-ENER-01']);
  });

  it('ignore un candidat sans barres, un doublon, un instrument sans cotation, et respecte la borne', () => {
    const content = makeOpportunitiesContent({
      excluded: [
        makeExcludedCandidate({ ticker: 'SYN-ENER-01' }),
        makeExcludedCandidate({ ticker: 'SYN-ENER-01' }),
        makeExcludedCandidate({ ticker: 'SYN-TECH-01', bars_status: 'ABSENT' }),
        makeExcludedCandidate({ ticker: 'SYN-INCONNU-99' }),
        makeExcludedCandidate({ ticker: 'SYN-FINL-01' }),
        makeExcludedCandidate({ ticker: 'SYN-HLTH-01' }),
        makeExcludedCandidate({ ticker: 'SYN-TECH-01' }),
      ],
    });
    const view = opportunitiesContentOf(content);
    const sectors = makeMarketsSectors();
    const tickers = focusInstrumentsOf(view, sectors).map((entry) => entry.ticker.ticker);
    expect(tickers).not.toContain('SYN-INCONNU-99');
    expect(new Set(tickers).size).toBe(tickers.length);
    expect(tickers.length).toBeLessThanOrEqual(FOCUS_LIMIT);
    expect(focusInstrumentsOf(view, sectors, 1)).toHaveLength(1);
  });

  it('sans contenu publié : rangée vide, jamais un instrument deviné', () => {
    expect(focusInstrumentsOf(null, makeMarketsSectors())).toHaveLength(0);
  });
});
