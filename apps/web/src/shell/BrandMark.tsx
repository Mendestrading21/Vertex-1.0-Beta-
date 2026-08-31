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
  return (
    <span
      className="vx-brand-facet"
      style={{ maskImage: `url(${brandMarkUrl})`, WebkitMaskImage: `url(${brandMarkUrl})` }}
    />
  );
}
