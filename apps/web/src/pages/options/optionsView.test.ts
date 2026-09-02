/**
 * Vue Options — invariants de présentation : groupes (expiration,
 * trading_class) JAMAIS fusionnés, IV absente ≠ 0, dérivation d'état depuis
 * les statuts publiés uniquement.
 */
import { describe, expect, it } from 'vitest';

import {
  makeAbsentIvContract,
  makeChainContract,
  makeChainGroup,
  makeEmptyOptionChain,
  makeOptionChain,
} from '../../test/fixtures.ts';
import {
  buildStrikeRows,
  chainStateOf,
  chainTransferBlockReasonOf,
  groupKeyOf,
  groupLabelOf,
  ivAbsentLabel,
  ivViewOf,
  quoteViewOf,
  rowBudgetOf,
} from './optionsView.ts';

describe('groupes (expiration, trading_class) — jamais fusionnés', () => {
  it('deux trading classes de la MÊME date produisent deux clés distinctes', () => {
    const standard = makeChainGroup();
    const weekly = makeChainGroup({ trading_class: 'SYN-TECH-01W' });
    expect(standard.expiration).toBe(weekly.expiration);
    expect(groupKeyOf(standard)).not.toBe(groupKeyOf(weekly));
  });

  it('le libellé du sélecteur montre toujours la date ET la trading class', () => {
    const weekly = makeChainGroup({ trading_class: 'SYN-TECH-01W' });
    expect(groupLabelOf(weekly)).toBe('2026-09-26 · SYN-TECH-01W (SYNTH)');
  });

  it('le snapshot fixture porte bien 2 groupes distincts à la même date', () => {
    const chain = makeOptionChain();
    const sameDate = chain.expirations.filter((group) => group.expiration === '2026-09-26');
    expect(sameDate).toHaveLength(2);
    expect(new Set(sameDate.map((group) => groupKeyOf(group))).size).toBe(2);
  });
});

describe('buildStrikeRows — appariement au sein d’UN groupe', () => {
  it('apparie CALL/PUT par strike et trie par valeur croissante', () => {
    const group = makeChainGroup({
      contracts: [
        makeChainContract({ strike: '110.00', right: 'CALL', con_id: 1 }),
        makeChainContract({ strike: '100.00', right: 'PUT', con_id: 2 }),
        makeChainContract({ strike: '100.00', right: 'CALL', con_id: 3 }),
      ],
    });
    const { rows, unpairable } = buildStrikeRows(group);
    expect(unpairable).toHaveLength(0);
    expect(rows.map((row) => row.strike)).toEqual(['100.00', '110.00']);
    expect(rows[0]?.call?.con_id).toBe(3);
    expect(rows[0]?.put?.con_id).toBe(2);
    expect(rows[1]?.call?.con_id).toBe(1);
    expect(rows[1]?.put).toBeNull();
  });

  it('un contrat sans strike ou right lisible sort en « unpairable », jamais masqué', () => {
    const group = makeChainGroup({
      contracts: [makeChainContract({ strike: null, con_id: null })],
    });
    const { rows, unpairable } = buildStrikeRows(group);
    expect(rows).toHaveLength(0);
    expect(unpairable).toHaveLength(1);
  });
});

describe('IV absente ≠ 0', () => {
  it('une quote croisée donne une IV ABSENT avec sa raison typée', () => {
    const contract = makeAbsentIvContract();
    const iv = ivViewOf(contract);
    expect(iv.status).toBe('ABSENT');
    expect(iv.value).toBeNull(); // jamais « 0 »
    expect(iv.reason).toBe('crossed_quote');
    expect(ivAbsentLabel(iv.reason)).toContain('crossed_quote');
    expect(ivAbsentLabel(iv.reason)).toContain('quote croisée');
  });

  it('une raison inconnue reste relayée verbatim', () => {
    expect(ivAbsentLabel('mystery_reason')).toBe('IV absente — mystery_reason');
    expect(ivAbsentLabel(null)).toBe('IV absente — raison non publiée');
  });

  it('la quote verbatim conserve bid/ask/statut sans les convertir', () => {
    const quote = quoteViewOf(makeAbsentIvContract());
    expect(quote.bid).toBe('4.40');
    expect(quote.ask).toBe('4.20');
    expect(quote.status).toBe('CROSSED');
  });
});

describe('chainStateOf — dérivation depuis les statuts publiés', () => {
  it('relais des états requête hors succès', () => {
    expect(chainStateOf('loading', undefined)).toBe('loading');
    expect(chainStateOf('offline', undefined)).toBe('offline');
    expect(chainStateOf('auth-required', undefined)).toBe('auth-required');
    expect(chainStateOf('ready', undefined)).toBe('error');
  });

  it('state=empty serveur → empty ; snapshot sain → ready/refreshing', () => {
    expect(chainStateOf('ready', makeEmptyOptionChain())).toBe('empty');
    expect(chainStateOf('ready', makeOptionChain())).toBe('ready');
    expect(chainStateOf('refreshing', makeOptionChain())).toBe('refreshing');
  });

  it('state=stale serveur reste stale, même pendant un refresh ou avec un contenu partiel', () => {
    const stale = makeOptionChain({ state: 'stale' });
    expect(chainStateOf('ready', stale)).toBe('stale');
    expect(chainStateOf('refreshing', stale)).toBe('stale');

    const staleAndDegraded = makeOptionChain({
      state: 'stale',
      expirations: [makeChainGroup({ quality: 'PARTIAL' })],
    });
    expect(chainStateOf('ready', staleAndDegraded)).toBe('stale');
  });

  it('population=DELAYED publiée reste delayed et prime sur refresh/partial', () => {
    const delayed = makeOptionChain({ population: 'DELAYED' });
    expect(chainStateOf('ready', delayed)).toBe('delayed');
    expect(chainStateOf('refreshing', delayed)).toBe('delayed');

    const delayedAndDegraded = makeOptionChain({
      population: 'DELAYED',
      expirations: [makeChainGroup({ quality: 'PARTIAL' })],
    });
    expect(chainStateOf('ready', delayedAndDegraded)).toBe('delayed');
  });

  it('qualité de groupe dégradée OU troncature publiée → partial', () => {
    const degraded = makeOptionChain({
      expirations: [makeChainGroup({ quality: 'PARTIAL' })],
    });
    expect(chainStateOf('ready', degraded)).toBe('partial');
    const truncated = makeOptionChain({
      row_budget: { max_rows: 240, total_rows: 250, published_rows: 240, truncated_rows: 10 },
    });
    expect(chainStateOf('ready', truncated)).toBe('partial');
  });
});

describe('chainTransferBlockReasonOf — transfert fail-closed', () => {
  it('autorise uniquement ready avec population REAL ou SYNTHETIC', () => {
    expect(chainTransferBlockReasonOf('ready', makeOptionChain())).toBeNull();
    expect(
      chainTransferBlockReasonOf('ready', makeOptionChain({ population: 'REAL' })),
    ).toBeNull();
    expect(
      chainTransferBlockReasonOf('ready', makeOptionChain({ population: 'UNKNOWN_SOURCE' })),
    ).toContain("n'est ni REAL ni SYNTHETIC");
  });

  it('bloque refreshing et partial même avec une population autorisée', () => {
    expect(chainTransferBlockReasonOf('refreshing', makeOptionChain())).toContain(
      'actualisation est en cours',
    );
    expect(chainTransferBlockReasonOf('partial', makeOptionChain({ population: 'REAL' }))).toContain(
      'chaîne est partielle',
    );
  });
});

describe('rowBudgetOf — budget publié relayé verbatim', () => {
  it('relaie les quatre compteurs du bloc row_budget', () => {
    const budget = rowBudgetOf(makeOptionChain());
    expect(budget).toEqual({ maxRows: 240, totalRows: 5, publishedRows: 5, truncatedRows: 0 });
    expect(rowBudgetOf(makeEmptyOptionChain())).toBeNull();
  });
});
