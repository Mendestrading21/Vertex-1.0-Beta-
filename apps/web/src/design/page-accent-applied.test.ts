// @vitest-environment node
/**
 * LA TEINTE DE PAGE EST APPLIQUÉE, PAS SEULEMENT DÉCLARÉE.
 *
 * POURQUOI CETTE PORTE EXISTE. `PAGE_ACCENTS` (ADR-017) déclarait cinq
 * teintes de page. Mesuré avant le lot P3a : UNE seule page posait
 * l'attribut, et elle l'écrivait EN DUR — donc sans lien avec la table — et
 * AUCUNE règle CSS ne lisait `--vx-page-accent`. Le mécanisme entier était
 * inerte : une décision de conception qui ne produisait rien à l'écran.
 *
 * `catalog.test.ts` vérifiait déjà la COHÉRENCE INTERNE de la table (famille
 * connue, pas de couleur de signe, douze destinations décidées). Il ne
 * pouvait pas voir qu'elle ne servait à rien. Cette porte ferme ce trou :
 * elle vérifie le chaînon manquant, de la table jusqu'au pixel.
 *
 * CE QU'ELLE NE PROUVE PAS :
 *  · elle ne juge pas si la teinte est BELLE, ni si son contraste est
 *    suffisant — ce dernier point est mesuré à la main et écrit dans
 *    `widgets.css`, pas automatisé ici ;
 *  · elle ne vérifie pas que l'attribut est posé sur le BON élément, seulement
 *    que la page appelle le helper du catalogue ;
 *  · une page qui déclare `null` n'est pas contrôlée : ne rien poser est
 *    précisément ce qu'on attend d'elle.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

import { PAGE_ACCENTS } from '../components/widgets/pageAccent.ts';

const PAGES_DIR = join(process.cwd(), 'src', 'pages');
const STYLES_DIR = join(process.cwd(), 'src', 'styles');

function filesUnder(dir: string, ext: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      out.push(...filesUnder(full, ext));
    } else if (entry.endsWith(ext)) {
      out.push(full);
    }
  }
  return out;
}

const SOURCES = filesUnder(PAGES_DIR, '.tsx')
  .filter((path) => !path.includes('.test.'))
  .map((path) => readFileSync(path, 'utf8'))
  .join('\n');

describe('teinte de page appliquée (ADR-017)', () => {
  it('toute page qui DÉCLARE une teinte appelle le helper du catalogue', () => {
    for (const [page, famille] of Object.entries(PAGE_ACCENTS)) {
      if (famille === null) {
        continue;
      }
      expect(
        SOURCES.includes(`pageAccentAttrs('${page}')`),
        `${page} déclare la teinte « ${famille} » et ne la pose nulle part`,
      ).toBe(true);
    }
  });

  it('aucune page n’écrit `data-page-accent` en dur — le catalogue est le seul propriétaire', () => {
    expect(
      /data-page-accent\s*=\s*["'{]/.test(SOURCES),
      'un attribut écrit à la main court-circuite PAGE_ACCENTS',
    ).toBe(false);
  });

  it('au moins une règle CSS LIT `--vx-page-accent` — un jeton que personne ne lit n’existe pas', () => {
    const feuilles = filesUnder(STYLES_DIR, '.css')
      .map((path) => readFileSync(path, 'utf8'))
      .join('\n');
    expect(feuilles).toMatch(/var\(--vx-page-accent[),]/);
  });
});
