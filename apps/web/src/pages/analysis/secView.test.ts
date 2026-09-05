// @vitest-environment node
/**
 * Lecture défensive des faits SEC : entrées illisibles ignorées, valeurs
 * verbatim, seul le domaine officiel devient un lien.
 */
import { describe, expect, it } from 'vitest';

import { makeEmptySecFundamentals, makeSecFundamentals } from '../../test/fixtures.ts';
import { officialSecUrl, secFundamentalsViewOf } from './secView.ts';

describe('secFundamentalsViewOf', () => {
  it('relaie dépôts, faits et couverture tels que publiés', () => {
    const view = secFundamentalsViewOf(makeSecFundamentals());
    expect(view.filings).toHaveLength(1);
    expect(view.filings[0]?.form).toBe('10-Q');
    expect(view.filings[0]?.primaryDocumentUrl).toMatch(/^https:\/\/www\.sec\.gov\//);
    expect(view.facts.map((fact) => fact.concept)).toEqual(['Assets', 'Revenues']);
    expect(view.facts[0]?.value).toBe('110');
    expect(view.coverage.publishedFacts).toBe(2);
    expect(view.conflictCount).toBe(0);
  });

  it('ignore une entrée illisible au lieu de la compléter', () => {
    const view = secFundamentalsViewOf(
      makeSecFundamentals({
        filings: [{ form: '10-K' }, 'texte' as unknown as Record<string, unknown>],
        facts: [{ value: '1' }],
      }),
    );
    expect(view.filings).toEqual([]);
    expect(view.facts).toEqual([]);
  });

  it('un snapshot vide donne des listes vides et une couverture non publiée', () => {
    const view = secFundamentalsViewOf(makeEmptySecFundamentals());
    expect(view.filings).toEqual([]);
    expect(view.facts).toEqual([]);
    expect(view.coverage.observationsConsidered).toBeNull();
  });
});

describe('officialSecUrl', () => {
  it('ne relaie qu’une URL du domaine officiel', () => {
    expect(officialSecUrl('https://www.sec.gov/Archives/edgar/data/1/x.htm')).not.toBeNull();
    expect(officialSecUrl('https://example.com/sec.gov/x.htm')).toBeNull();
    expect(officialSecUrl(null)).toBeNull();
  });
});
