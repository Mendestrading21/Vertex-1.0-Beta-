/**
 * Sourire d'IV : géométrie seule sur les IV PUBLIÉES ; un contrat sans IV n'a
 * pas de point (jamais un zéro) et son absence est comptée ; calls et puts
 * restent deux séries ; aucun point de référence n'est choisi.
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { makeAbsentIvContract, makeChainContract, makeChainGroup } from '../../test/fixtures.ts';
import { IvSmile, ivSmileSeriesOf } from './IvSmile.tsx';

describe('ivSmileSeriesOf', () => {
  it('sépare calls et puts, trie par strike, compte les IV absentes', () => {
    const group = makeChainGroup({
      contracts: [
        makeChainContract({ strike: '110.00', iv: { status: 'OK', value: '0.30', quote_side: 'MID', value_nature: 'THEORETICAL' } }),
        makeChainContract({ con_id: 2, strike: '100.00' }),
        makeChainContract({ con_id: 3, right: 'PUT', strike: '100.00', iv: { status: 'OK', value: '0.26', quote_side: 'MID', value_nature: 'THEORETICAL' } }),
        makeAbsentIvContract({ con_id: 4, strike: '105.00' }),
      ],
    });
    const series = ivSmileSeriesOf(group);
    expect(series.calls.map((point) => point.strike)).toEqual(['100.00', '110.00']);
    expect(series.puts.map((point) => point.strike)).toEqual(['100.00']);
    expect(series.absentCount).toBe(1);
    expect(series.strikeMin).toBe('100.00');
    expect(series.strikeMax).toBe('110.00');
    expect(series.ivMin).toBe('0.24500000000000001');
    expect(series.ivMax).toBe('0.30');
  });

  it('un groupe sans IV résolue ne trace rien et le dit', () => {
    const group = makeChainGroup({ contracts: [makeAbsentIvContract(), makeAbsentIvContract({ con_id: 5, right: 'PUT' })] });
    expect(ivSmileSeriesOf(group).calls).toEqual([]);
    render(<IvSmile group={group} label="test" />);
    const absent = screen.getByTestId('iv-smile-absent');
    expect(absent.textContent).toContain('sans IV');
    expect(screen.queryByTestId('iv-smile')).toBeNull();
  });
});

describe('IvSmile', () => {
  it('rend un point par IV publiée, deux séries, et écrit les bornes PUBLIÉES', () => {
    const { container } = render(<IvSmile group={makeChainGroup()} label="Sourire" />);
    expect(container.querySelectorAll('.vx-smile-dot')).toHaveLength(2);
    expect(container.querySelectorAll('.vx-smile-dot[data-right="CALL"]')).toHaveLength(1);
    expect(container.querySelectorAll('.vx-smile-dot[data-right="PUT"]')).toHaveLength(1);
    const caption = screen.getByTestId('iv-smile').textContent ?? '';
    expect(caption).toContain('0.24500000000000001');
    expect(caption).toContain('1 sans IV');
    expect(caption).not.toMatch(/ATM|référence/);
  });
});
