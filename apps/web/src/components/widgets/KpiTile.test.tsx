import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { KPI_TILE_TONES, KpiTile } from './KpiTile.tsx';

const SERIE = ['10', '11', '12', '13'];

describe('KpiTile — la tuile de mesure', () => {
  it('valeur servie : chiffre verbatim, unité, libellé, pastille d’icône', () => {
    render(
      <KpiTile
        glyph="manual-ledger"
        label="Valorisation"
        value="12184.20"
        unit="CHF"
        absentNote="valorisation non publiée"
        tone="macro"
      />,
    );
    const tile = screen.getByTestId('kpi-tile');
    expect(tile.getAttribute('data-tone')).toBe('macro');
    expect(screen.getByTestId('kpi-tile-value').textContent).toBe('12184.20');
    expect(screen.getByTestId('kpi-tile-unit').textContent).toBe('CHF');
    expect(tile.textContent).toContain('Valorisation');
    expect(screen.getByTestId('glyph')).toBeTruthy();
  });

  it('REFUS — sans valeur servie, la tuile DIT l’absence : ni teinte, ni pastille, ni série', () => {
    render(
      <KpiTile
        glyph="manual-ledger"
        label="Valorisation"
        value={null}
        unit="CHF"
        absentNote="le snapshot ne publie aucune valorisation"
        tone="macro"
        delta={{ value: '+1.20', sign: 'up', period: '1 j' }}
        series={{ closes: SERIE, caption: 'série', unit: 'CHF', windowLabel: '4 barres servies' }}
      />,
    );
    const tile = screen.getByTestId('kpi-tile');
    // Une absence ne prend AUCUNE teinte : teinter, c'est qualifier un vide.
    expect(tile.getAttribute('data-tone')).toBe('neutral');
    expect(tile.textContent).toContain('le snapshot ne publie aucune valorisation');
    // Une variation ou une série sans la mesure qu'elles qualifient n'ont rien
    // à qualifier : la tuile ne les rend pas.
    expect(screen.queryByTestId('kpi-delta')).toBeNull();
    expect(screen.queryByTestId('spark-figure-line')).toBeNull();
    // L'unité seule n'est pas une donnée : elle ne s'affiche pas sans valeur.
    expect(screen.queryByTestId('kpi-tile-unit')).toBeNull();
  });

  it('REFUS — signe non publié : la variation est rendue, la tuile ne se colore pas', () => {
    render(
      <KpiTile
        glyph="market-regime"
        label="Écart"
        value="3.40"
        unit="%"
        absentNote="écart non publié"
        tone="macro"
        delta={{ value: '1.20', sign: null, period: '1 j' }}
      />,
    );
    const delta = screen.getByTestId('kpi-delta');
    expect(delta.getAttribute('data-sign')).toBe('unknown');
    expect(delta.textContent).toContain('signe non publié');
    // La teinte de la tuile reste celle DÉCLARÉE, jamais dérivée d'un signe
    // absent : ni positive, ni negative.
    expect(screen.getByTestId('kpi-tile').getAttribute('data-tone')).toBe('macro');
  });

  it('le vocabulaire de teintes EXCLUT les familles de signe financier', () => {
    // Le vert et le rouge appartiennent au SIGNE servi, porté par `KpiDelta`.
    // Une pastille d'icône ne peut pas les prendre : elle affirmerait un sens
    // sur une mesure qui n'en a pas.
    expect([...KPI_TILE_TONES].sort()).toEqual(['macro', 'neutral', 'option', 'silver'].sort());
  });

  it('série servie : la figure est rendue sous la mesure', () => {
    render(
      <KpiTile
        glyph="evidence-rail"
        label="Clôtures"
        value="13"
        unit="CHF"
        absentNote="clôture non publiée"
        series={{
          closes: SERIE,
          caption: 'Clôtures servies',
          unit: 'CHF',
          windowLabel: '4 barres servies sur 4',
        }}
      />,
    );
    expect(screen.getByTestId('spark-figure-line')).toBeTruthy();
  });

  it('le SIGNE de la mesure servie colore la figure, jamais la pastille', () => {
    // Le P&L latent EST une mesure signée : son signe est publié dans la
    // chaîne servie, et il colore le chiffre. La pastille d'icône, elle, ne
    // prend jamais le vert ni le rouge — sa teinte reste déclarée.
    render(
      <KpiTile
        glyph="manual-ledger"
        label="P&L latent"
        value="-55.00"
        valueSign="down"
        unit="CHF"
        absentNote="P&L latent non publié"
        tone="macro"
        testId="pf-value-unrealized"
      />,
    );
    const tile = screen.getByTestId('pf-value-unrealized');
    expect(tile.getAttribute('data-sign')).toBe('down');
    expect(tile.getAttribute('data-tone')).toBe('macro');
  });

  it('REFUS — signe de mesure non publié : aucun attribut de signe', () => {
    // « 55 » sans « + » ne porte AUCUN signe publié. Le classer positif
    // inventerait une direction que le serveur n'a pas publiée.
    render(
      <KpiTile
        glyph="manual-ledger"
        label="P&L latent"
        value="55"
        valueSign={null}
        unit="CHF"
        absentNote="P&L latent non publié"
        testId="pf-value-unrealized"
      />,
    );
    expect(screen.getByTestId('pf-value-unrealized').getAttribute('data-sign')).toBeNull();
  });
});
