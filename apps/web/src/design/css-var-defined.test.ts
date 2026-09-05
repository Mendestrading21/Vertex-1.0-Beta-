// @vitest-environment node
/**
 * PORTE — AUCUNE VARIABLE CSS N'EST RÉFÉRENCÉE SANS ÊTRE DÉFINIE.
 *
 * POURQUOI ELLE EXISTE. Une faute de frappe dans `var(--vx-focus)` — un jeton
 * qui n'existe pas — ne produit AUCUNE erreur : la déclaration est simplement
 * ignorée, et la propriété garde sa valeur héritée. Un contour de focus
 * disparaît, une couleur de statut se confond avec le texte courant, et rien
 * ne le signale. C'est arrivé pendant la refonte : `--vx-focus` a été écrit à
 * la place de `--vx-signal`, et seul un examen à la main l'a vu.
 *
 * Aucune autre porte ne pouvait l'attraper : `tokens-css.test.ts` vérifie que
 * la source typée engendre bien le fichier généré, `no-dead-token` vérifie
 * qu'un jeton défini est consommé. Le cas inverse — un jeton consommé mais
 * jamais défini — n'était couvert nulle part.
 *
 * CE QU'ELLE ACCEPTE. Une variable définie ailleurs dans les mêmes feuilles,
 * y compris posée en ligne par un composant, à condition que la définition
 * existe dans le CSS. Une valeur de repli explicite (`var(--x, 1px)`) reste
 * examinée : le repli masque le défaut, il ne le corrige pas.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const FEUILLES = ['tokens.css', '../styles/global.css', '../styles/widgets.css', '../styles/fonts.css'];

function lire(nom: string): string {
  return readFileSync(fileURLToPath(new URL(nom, import.meta.url)), 'utf8');
}

/**
 * Variables posées en ligne par un composant TypeScript (`style={{ '--x': … }}`).
 * Elles sont DÉFINIES au rendu, pas dans la feuille : les chercher dans le CSS
 * les déclarerait fautives à tort.
 */
const POSEES_EN_LIGNE = new Set<string>([]);

describe('Variables CSS — référencées, donc définies', () => {
  const css = FEUILLES.map(lire).join('\n');

  const definies = new Set<string>();
  for (const trouve of css.matchAll(/(--vx-[a-z0-9-]+)\s*:/g)) {
    definies.add(trouve[1]!);
  }

  const referencees = new Map<string, number>();
  for (const trouve of css.matchAll(/var\(\s*(--vx-[a-z0-9-]+)/g)) {
    const nom = trouve[1]!;
    referencees.set(nom, (referencees.get(nom) ?? 0) + 1);
  }

  it('trouve un corpus non vide — sinon la porte serait vide de sens', () => {
    // Sans ce garde-fou, une expression rationnelle cassée rendrait la porte
    // verte par construction : zéro référence, zéro faute.
    expect(definies.size).toBeGreaterThan(50);
    expect(referencees.size).toBeGreaterThan(50);
  });

  it('n’en référence AUCUNE qui ne soit définie', () => {
    const inconnues = [...referencees.keys()]
      .filter((nom) => !definies.has(nom) && !POSEES_EN_LIGNE.has(nom))
      .sort();
    expect(
      inconnues,
      `Variables utilisées mais jamais définies : la déclaration est ignorée en silence.\n${inconnues.join('\n')}`,
    ).toEqual([]);
  });
});
