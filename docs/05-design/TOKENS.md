# Tokens Black Glass

`DESIGN_SYSTEM.md` définit la palette. Le LOT-10 la convertit en une source typée unique générant CSS et documentation ; aucune page ne déclare une couleur brute.

## Familles

- couleur : surface, texte, bordure, état, option et macro ;
- espace : grille de 4 px, valeurs 4/8/12/16/20/24/32/40/48 ;
- rayon : 6/10/14 px, pilule seulement pour badge ;
- ombre : deux niveaux sobres, jamais utilisée comme seule séparation ;
- typographie : `body`, `meta`, `label`, `title`, `display`, `mono-number` ;
- motion : 140/180/220 ms, courbes documentées et variante reduced-motion ;
- z-index : base, sticky, popover, sheet, dialog, toast ; aucune valeur locale arbitraire ;
- densité : confortable par défaut, compacte uniquement dans tables analytiques.

## États sémantiques

`positive`, `negative`, `warning`, `neutral`, `option`, `macro`, `live`, `delayed`, `stale`, `offline`, `estimated`, `simulated`. Chaque token de couleur a un libellé/icône associé et une paire texte/fond vérifiée AA.

## Validation

La CI refuse couleurs hex/rgb hors fichier source, espacements arbitraires et tokens non documentés. Storybook montre états, thèmes, focus, contrastes et reduced-motion. Les captures de référence utilisent les mêmes données synthétiques déterministes.

