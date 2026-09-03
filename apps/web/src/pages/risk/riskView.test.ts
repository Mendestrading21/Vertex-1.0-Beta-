/**
 * Lecture du contrat Risques — ce que la vue a le DROIT de faire d'une donnée
 * manquante, cassée ou nulle.
 *
 * POURQUOI CE FICHIER EXISTE (lot P4). La vue relayait six absences comme si
 * elles étaient des faits : un compte non publié devenait `0`, une perte
 * d'alignement nulle SERVIE disparaissait comme si rien n'était publié, un
 * seuil absent devenait un tiret ambigu, une paire extrême servie seule était
 * effacée parce que l'autre manquait, une cellule cassée devenait une chaîne
 * vide qui se lit comme une absence, et le nombre d'enregistrements rejetés
 * comptait ce que l'interface savait rendre au lieu de ce que le serveur avait
 * servi. `.claude/rules/frontend.md` l'interdit : « ne jamais remplacer une
 * donnée absente par 0, un tiret ambigu, une fixture ou une ancienne valeur ».
 *
 * Chaque cas ci-dessous a été écrit ROUGE contre la version précédente de
 * `riskViewOf`, puis rendu vert par la correction — jamais l'inverse.
 */
import { describe, expect, it } from 'vitest';

import type { RiskMatrixResponse } from '../../api/client.ts';
import { riskViewOf } from './riskView.ts';

/** Réponse minimale : seul le contenu passé en paramètre varie. */
function reponse(content: Record<string, unknown>): RiskMatrixResponse {
  return {
    resource: 'risk_matrix',
    scope: 'global',
    state: 'ok',
    as_of: '2026-09-03T10:00:00Z',
    age_seconds: 42,
    snapshot_version: 7,
    content,
  } as unknown as RiskMatrixResponse;
}

describe('riskViewOf — une absence n’est jamais un zéro', () => {
  it('un compte de séances NON PUBLIÉ reste absent, il ne devient pas zéro', () => {
    const vue = riskViewOf(
      reponse({
        coverage: {
          trading_days_per_instrument: { AAA: 120, BBB: null, CCC: 'douze' },
        },
      }),
    );
    const parTicker = new Map(vue.coverage.tradingDaysPerInstrument.map((e) => [e.ticker, e.days]));
    expect(parTicker.get('AAA')).toBe(120);
    // Servi à `null` ou dans une forme illisible : ABSENT, jamais 0 — sinon
    // « aucune séance » et « pas publié » deviennent la même phrase.
    expect(parTicker.get('BBB')).toBeNull();
    expect(parTicker.get('CCC')).toBeNull();
  });

  it('une perte d’alignement NULLE et SERVIE est conservée, pas filtrée', () => {
    const vue = riskViewOf(
      reponse({ coverage: { trading_days_lost_to_alignment: { AAA: 3, BBB: 0 } } }),
    );
    const parTicker = new Map(vue.coverage.alignmentLoss.map((e) => [e.ticker, e.lost]));
    expect(parTicker.get('AAA')).toBe(3);
    // « BBB n'a rien perdu » est un FAIT publié. Le filtrer le rendait
    // indistinct de « BBB n'est pas dans la matrice ».
    expect(parTicker.has('BBB')).toBe(true);
    expect(parTicker.get('BBB')).toBe(0);
  });

  it('un seuil NON PUBLIÉ est nul, jamais un tiret ambigu', () => {
    const vue = riskViewOf(reponse({ coverage: { strong_threshold: '0.70' } }));
    expect(vue.coverage.strongThreshold).toBe('0.70');
    // Le tiret se lit comme une valeur affichée ; l'absence doit rester une
    // absence que la page nomme elle-même.
    expect(vue.coverage.moderateThreshold).toBeNull();
  });
});

describe('riskViewOf — une donnée servie n’est jamais effacée par une autre', () => {
  it('une seule paire extrême servie est conservée', () => {
    const vue = riskViewOf(
      reponse({ extremes: { most_correlated: { a: 'AAA', b: 'BBB', value: '0.91' } } }),
    );
    expect(vue.extremes).not.toBeNull();
    expect(vue.extremes?.mostCorrelated).toEqual({ pair: 'AAA et BBB', value: '0.91' });
    // L'autre paire n'est pas publiée : elle est nulle, et la première reste.
    expect(vue.extremes?.mostOpposed).toBeNull();
  });

  it('aucun bloc extremes publié : la vue le dit, sans forger de paire', () => {
    expect(riskViewOf(reponse({})).extremes).toBeNull();
  });
});

describe('riskViewOf — une cellule cassée se distingue d’une cellule absente', () => {
  it('une cellule non textuelle devient nulle, jamais une chaîne vide', () => {
    const vue = riskViewOf(
      reponse({
        matrix: [['1.00', 0.42], ['1.00']],
        matrix_bands: [['self', null], ['self']],
      }),
    );
    // `0.42` est un NOMBRE là où le contrat publie des chaînes rendues : la
    // valeur est illisible pour l'interface, qui ne la reformate pas.
    expect(vue.matrix[0]?.[1]).toBeNull();
    expect(vue.matrix[0]?.[0]).toBe('1.00');
    // Une bande absente reste absente : elle ne devient jamais « weak », ce
    // qui affirmerait « peu liés » sur une case dont personne ne sait rien.
    expect(vue.bands[0]?.[1]).toBeNull();
  });
});

describe('riskViewOf — les rejets sont comptés tels que servis', () => {
  it('le compte servi survit même quand une entrée est illisible', () => {
    const vue = riskViewOf(
      reponse({
        coverage: {
          rejected_records: [
            { instrument: 'AAA', reason: 'source_not_allowed' },
            null,
            'texte-libre',
          ],
        },
      }),
    );
    // Trois enregistrements SERVIS, deux seulement rendables : afficher « 2 »
    // sous-déclarerait ce que le serveur a rejeté.
    expect(vue.coverage.rejectedServedCount).toBe(3);
    expect(vue.coverage.rejectedRecords).toHaveLength(2);
  });
});
