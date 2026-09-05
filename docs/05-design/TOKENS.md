# Tokens Black Glass

`DESIGN_SYSTEM.md` définit la palette Titanium Ledger. Le LOT-10 la convertit
en une source typée unique générant CSS et documentation ; aucune page ne
déclare une couleur brute.

## Familles

- couleur : surface, texte, bordure, état, option, macro et, depuis ADR-017, un couple de dégradé `<famille>-gradient-start/-end` par famille de série (`silver`, `positive`, `negative`, `warning`, `option`, `macro`) ;
- échelle divergente à bornes déclarées : `positive-band-1/2/3` et
  `negative-band-1/2/3`, trois crans par signe, employés uniquement par les
  surfaces qui peignent une valeur signée servie (carte des marchés, matrices).
  Les bornes en pourcent vivent dans `src/design/signedScale.ts` et sont
  publiées dans la légende de chaque figure qui les emploie ; elles ne
  dépendent JAMAIS des données affichées — une normalisation locale ferait
  changer de couleur la même valeur selon ses voisines. Les opacités des deux
  familles diffèrent parce que le vert est plus clair que le rouge : elles sont
  réglées pour une LISIBILITÉ égale du texte posé dessus, pas pour une
  transparence égale (`contrast.test.ts` le mesure cran par cran) ;
- espace : grille de 4 px, valeurs 4/8/12/16/20/24/32 ;
- rayon : clés 6/10/14/16/20, chacune valant ses pixels, plus `pill` réservé aux
  badges ;
- ombre : `panel`, `glass` et `inset` sobres, jamais utilisés comme
  seule séparation ni comme halo lumineux ;
- typographie : `micro`, `meta`, `body`, `title`, `display`, `headline`, `metric` ;
- motion : 90/140/180/220 ms et 600 ms (`--vx-motion-600`, surbrillance unique d'une valeur mise à jour ; nom documentaire `--vx-motion-data`, ADR-017), courbes documentées et variante reduced-motion ;
- z-index : base, sticky, popover, sheet, dialog, toast ; aucune valeur locale arbitraire ;
- densité : confortable par défaut, compacte uniquement dans tables analytiques.

## États sémantiques

`positive`, `negative`, `warning`, `neutral`, `option`, `macro`, `live`, `delayed`, `stale`, `offline`, `estimated`, `simulated`. Chaque token de couleur a un libellé/icône associé et une paire texte/fond vérifiée AA.

## Teinte secondaire par page et dégradés (ADR-017)

`pageAccent` (`apps/web/src/design/tokens.ts`) est le vocabulaire fermé des
familles éligibles comme teinte sémantique secondaire d'une page : `macro`,
`option`, `warning`. Chaque clé renvoie à une famille existante — aucune
couleur nouvelle, « une couleur = une signification » est préservé ; `signal`
(ambre) n'est pas éligible, ni `positive` ni `negative` (signe financier servi :
une teinte de page ne bascule pas selon le signe). Le CSS généré expose, par famille,
`[data-page-accent="<famille>"]` → `--vx-page-accent`, `--vx-page-accent-soft`,
`--vx-page-accent-gradient-start`, `--vx-page-accent-gradient-end`, sans valeur
par défaut dans `:root`. La page déclare sa famille dans son catalogue ; les
widgets consomment `--vx-page-accent*` sans jamais nommer la famille. Sans
déclaration, `var(--vx-page-accent)` est invalide à la valeur calculée et un
`fill` SVG retomberait sans erreur sur sa valeur initiale, le noir (interdit
par ADR-017) : la porte `catalog.test.ts` du lot L0 (chaque page qui consomme
`--vx-page-accent*` déclare sa famille) précède tout consommateur.

Les tokens `<famille>-gradient-start` (teinte à faible alpha) et
`<famille>-gradient-end` (même teinte à alpha 0) ne servent qu'à l'aire sous une
série servie ; jamais un fond de carte, jamais un dégradé entre deux teintes.

## Validation

La CI refuse couleurs hex/rgb hors fichier source, espacements arbitraires et tokens non documentés. Storybook montre états, thèmes, focus, contrastes et reduced-motion. Les captures de référence utilisent les mêmes données synthétiques déterministes.

### Plancher typographique

La plus petite taille de l'échelle vaut 11 px. Elle est réservée aux étiquettes
qui ACCOMPAGNENT une valeur — unité, coiffe, libellé de groupe de navigation —
et qui ne portent jamais seules une information ; une valeur, un statut ou un
motif d'absence prennent la taille de méta au minimum.

Le CSS n'écrit plus aucune taille littérale. Une porte les refuse toutes, y
compris celles qui égalent un jeton : c'est le nombre recopié qui fait dériver
une échelle, pas sa valeur du jour. Trente tailles littérales vivaient sous le
plancher affiché du système — dix-huit à 10 px, cinq à 10,5 px, six à 11 px,
une à 12 px — et l'échelle typographique cessait donc d'exister là où le texte
est le plus dense, c'est-à-dire là où elle compte le plus.
