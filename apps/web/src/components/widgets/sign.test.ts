/**
 * L'AUTORITÉ DU SIGNE, ET LES DEUX FAUTES QU'ELLE REMPLACE.
 *
 * Chaque cas ci-dessous a existé en production sous une des quatre règles
 * concurrentes. Ils sont figés ici pour qu'aucune cinquième ne renaisse.
 */
import { describe, expect, it } from 'vitest';

import { signGroupOfServed, signGroupOfText } from './sign.ts';

describe('signGroupOfText — le signe est LU, jamais décidé', () => {
  it.each([
    // Un zéro servi est un zéro, quel que soit le signe que le serveur y met.
    // `-0.00` était lu « perte » par les deux copies de `signOf`, qui
    // testaient le tiret AVANT le zéro.
    ['0', 'flat'],
    ['0.00', 'flat'],
    ['+0.00', 'flat'],
    ['-0.00', 'flat'],
    ['0,00 %', 'flat'],
    ['-0,000 %', 'flat'],
    ['+1.20', 'up'],
    ['+0.01', 'up'],
    ['-1.20', 'down'],
    ['-0.01', 'down'],
  ] as const)('« %s » vaut %s', (valeur, attendu) => {
    expect(signGroupOfText(valeur)).toBe(attendu);
  });

  it.each([
    // SIGNE NON PUBLIÉ. Une chaîne positive sans « + » ne prouve pas un gain :
    // elle prouve que le serveur n'a pas publié de signe. Les deux copies de
    // `signOf` rendaient `up` — un gain inventé.
    '1.20',
    '42',
    '12,5 %',
    '',
    '   ',
    'n/a',
  ])('« %s » ne permet aucune conclusion', (valeur) => {
    expect(signGroupOfText(valeur)).toBeNull();
  });
});

describe('signGroupOfServed — une absence ne prend aucune couleur', () => {
  it.each([null, undefined])('%s reste null', (valeur) => {
    expect(signGroupOfServed(valeur)).toBeNull();
  });

  it('applique la même règle qu\'une chaîne présente', () => {
    expect(signGroupOfServed('-0.00')).toBe('flat');
    expect(signGroupOfServed('-3.10')).toBe('down');
  });
});

describe('La règle binaire qui a été retirée', () => {
  /**
   * REPRODUCTEUR EXACT du défaut : `startsWith('-') ? 'negative' : 'positive'`
   * n'avait pas d'état neutre. Sur un P&L latent servi `0.00`, il rendait
   * « positive » — et la feuille de style le peignait en vert.
   */
  const binaireHistorique = (valeur: string) =>
    valeur.startsWith('-') ? 'negative' : 'positive';

  it('peignait un zéro servi comme un gain ; l\'autorité ne le fait pas', () => {
    expect(binaireHistorique('0.00')).toBe('positive');
    expect(signGroupOfText('0.00')).toBe('flat');
  });

  it('lisait un zéro signé comme une perte ; l\'autorité ne le fait pas', () => {
    expect(binaireHistorique('-0.00')).toBe('negative');
    expect(signGroupOfText('-0.00')).toBe('flat');
  });
});
