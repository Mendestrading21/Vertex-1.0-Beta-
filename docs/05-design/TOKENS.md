# Tokens Black Glass

`DESIGN_SYSTEM.md` définit la palette Titanium Ledger. Le LOT-10 la convertit
en une source typée unique générant CSS et documentation ; aucune page ne
déclare une couleur brute.

## Familles

- couleur : surface, texte, bordure, état, option, macro et, depuis ADR-017, un couple de dégradé `<famille>-gradient-start/-end` par famille de série (`silver`, `positive`, `negative`, `warning`, `option`, `macro`) ;
- espace : grille de 4 px, valeurs 4/8/12/16/20/24/32/40/48 ;
- rayon : clés 6/10/14/18/22, valeurs resserrées pour le registre métallique ;
- ombre : panneau, flottant et reflet interne sobres, jamais utilisés comme
  seule séparation ni comme halo lumineux ;
- typographie : `body`, `meta`, `label`, `title`, `display`, `mono-number` ;
- motion : 90/140/180/220 ms et 600 ms (`--vx-motion-600`, surbrillance unique d'une valeur mise à jour ; nom documentaire `--vx-motion-data`, ADR-017), courbes documentées et variante reduced-motion ;
- z-index : base, sticky, popover, sheet, dialog, toast ; aucune valeur locale arbitraire ;
- densité : confortable par défaut, compacte uniquement dans tables analytiques.

## États sémantiques

`positive`, `negative`, `warning`, `neutral`, `option`, `macro`, `live`, `delayed`, `stale`, `offline`, `estimated`, `simulated`. Chaque token de couleur a un libellé/icône associé et une paire texte/fond vérifiée AA.

## Teinte secondaire par page et dégradés (ADR-017)

`pageAccent` (`apps/web/src/design/tokens.ts`) est le vocabulaire fermé des
familles éligibles comme teinte sémantique secondaire d'une page : `macro`,
`option`, `positive`, `warning`. Chaque clé renvoie à une famille existante —
aucune couleur nouvelle, « une couleur = une signification » est préservé, et
`signal` (ambre) n'est pas éligible. Le CSS généré expose, par famille,
`[data-page-accent="<famille>"]` → `--vx-page-accent`, `--vx-page-accent-soft`,
`--vx-page-accent-gradient-start`, `--vx-page-accent-gradient-end`, sans valeur
par défaut dans `:root`. La page déclare sa famille dans son catalogue ; les
widgets consomment `--vx-page-accent*` sans jamais nommer la famille.

Les tokens `<famille>-gradient-start` (teinte à faible alpha) et
`<famille>-gradient-end` (même teinte à alpha 0) ne servent qu'à l'aire sous une
série servie ; jamais un fond de carte, jamais un dégradé entre deux teintes.

## Validation

La CI refuse couleurs hex/rgb hors fichier source, espacements arbitraires et tokens non documentés. Storybook montre états, thèmes, focus, contrastes et reduced-motion. Les captures de référence utilisent les mêmes données synthétiques déterministes.
