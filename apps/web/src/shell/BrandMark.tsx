import brandMarkUrl from '../../../../design-assets/icons/custom/brand-mark.svg?url';

/**
 * Marque Vertex : polyèdre facetté, argent/titane, sans lettre.
 *
 * `references/canonical-visual.md` fixe deux contraintes que le rail violait :
 * « Ne pas réintroduire le monogramme `VX` » et, dans l'anatomie immuable du
 * shell, « monogramme facetté argent/titane en haut à gauche, SANS TEXTE
 * ADJACENT ». Le rail portait les deux — les lettres `VX` et le mot-symbole
 * « Vertex / Titanium Ledger » à côté.
 *
 * Le masque hérite de `currentColor` comme tout le catalogue d'icônes : la
 * marque reste lisible en monochrome et à petite taille, et aucune couleur
 * n'est encodée dans le SVG.
 */
export function BrandMark() {
  // L'URL est ENTRE GUILLEMETS, comme dans NavGlyph. `?url` renvoie une data
  // URI qui contient des apostrophes et des virgules ; sans guillemets, la
  // déclaration `mask-image` est invalide, le navigateur la calcule à `none`,
  // et `background-color: currentcolor` remplit alors tout le carré. La marque
  // s'affichait ainsi en pavé plein au lieu du polyèdre facetté — sans aucune
  // erreur, un masque invalide étant silencieux.
  const mask = `url("${brandMarkUrl}")`;

  return <span className="vx-brand-facet" style={{ maskImage: mask, WebkitMaskImage: mask }} />;
}
