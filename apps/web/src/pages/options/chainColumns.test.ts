import { describe, expect, it } from 'vitest';

import {
  CHAIN_COLUMNS,
  CHAIN_COLUMNS_DEFAULT,
  CHAIN_COLUMNS_MAX,
  COLONNES_NON_SERVIES,
  columnByKey,
} from './chainColumns.ts';

/**
 * Ce que ces tests gèlent.
 *
 * Le vocabulaire de colonnes est l'endroit où la tentation d'inventer une
 * donnée est la plus forte : un spread « se calcule facilement », un mid
 * « n'est qu'une moyenne ». Les assertions ci-dessous rendent ces raccourcis
 * impossibles à prendre sans casser un test.
 */

describe('Vocabulaire de colonnes de la chaîne — servi, et rien que servi', () => {
  it('n’expose AUCUNE colonne calculée localement', () => {
    // Un spread, un mid, un dernier échangé ou une moneyness ne sont pas des
    // colonnes « manquantes » : ce sont des champs que le contrat ne publie
    // pas, et les fabriquer serait un calcul financier dans le navigateur.
    const interdites = ['spread', 'mid', 'last', 'moneyness', 'atm', 'intrinsic', 'extrinsic'];
    for (const cle of CHAIN_COLUMNS.map((c) => c.key)) {
      expect(interdites).not.toContain(cle);
    }
  });

  it('DÉCLARE ce que le contrat ne publie pas, avec le motif', () => {
    // Sans cette liste, chercher le spread laisse croire à un oubli
    // d'interface plutôt qu'à une absence de champ.
    expect(COLONNES_NON_SERVIES.length).toBeGreaterThanOrEqual(4);
    const noms = COLONNES_NON_SERVIES.map((e) => e.nom.toLowerCase());
    expect(noms.join(' ')).toContain('spread');
    expect(noms.join(' ')).toContain('mid');
    for (const entree of COLONNES_NON_SERVIES) {
      expect(entree.motif.length, `motif trop court : ${entree.nom}`).toBeGreaterThan(40);
    }
  });

  it('donne à CHAQUE colonne une unité et une définition', () => {
    for (const colonne of CHAIN_COLUMNS) {
      expect(colonne.unit.trim(), `unité manquante : ${colonne.key}`).not.toBe('');
      expect(colonne.definition.length, `définition trop courte : ${colonne.key}`).toBeGreaterThan(20);
    }
  });

  it('expose les champs SERVIS qui n’étaient jamais affichés', () => {
    // `volume`, `open_interest`, `bid_size` et `ask_size` voyageaient jusqu'au
    // navigateur et étaient jetés. C'est la liquidité : sans elle, la chaîne ne
    // dit pas si un strike est négociable.
    const cles = CHAIN_COLUMNS.map((c) => c.key);
    for (const attendue of ['volume', 'open_interest', 'bid_size', 'ask_size']) {
      expect(cles, `colonne servie absente du vocabulaire : ${attendue}`).toContain(attendue);
    }
  });

  it('expose les six sensibilités publiées par le worker', () => {
    const cles = CHAIN_COLUMNS.map((c) => c.key);
    for (const greek of ['delta', 'gamma', 'vega', 'theta_per_calendar_day', 'rho_per_bp']) {
      expect(cles, `sensibilité servie absente : ${greek}`).toContain(greek);
    }
  });

  it('a une sélection par défaut lisible, jamais « tout »', () => {
    // Douze colonnes par côté font vingt-quatre colonnes de nombres : comparer
    // deux strikes devient impossible, ce qui est pourtant l'objet de la chaîne.
    expect(CHAIN_COLUMNS_DEFAULT.length).toBeLessThan(CHAIN_COLUMNS.length);
    expect(CHAIN_COLUMNS_DEFAULT.length).toBeLessThanOrEqual(CHAIN_COLUMNS_MAX);
    for (const cle of CHAIN_COLUMNS_DEFAULT) {
      expect(columnByKey(cle), `défaut inconnu du vocabulaire : ${cle}`).toBeDefined();
    }
  });

  it('range chaque colonne dans un groupe nommé', () => {
    for (const colonne of CHAIN_COLUMNS) {
      expect(['cotation', 'liquidité', 'sensibilité']).toContain(colonne.group);
    }
  });

  it('n’a aucune clé en double', () => {
    const cles = CHAIN_COLUMNS.map((c) => c.key);
    expect(new Set(cles).size).toBe(cles.length);
  });

  it('traduit les raisons typées des colonnes calculées', () => {
    // Le code serveur fait foi et reste affiché ; la phrase française
    // l'accompagne pour qui ne connaît pas le vocabulaire du worker.
    const iv = columnByKey('iv');
    expect(iv?.explain?.('crossed_quote')).toContain('quote croisée');
    expect(iv?.explain?.('code_inconnu')).toBeUndefined();
    expect(iv?.explain?.(null)).toBeUndefined();
  });
});
