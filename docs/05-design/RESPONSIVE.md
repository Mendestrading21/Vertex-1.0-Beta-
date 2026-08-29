# Largeurs de bureau — Beta Desktop Only

## Portée de phase

Vertex 1.0 Beta est une application bureau/laptop. Le téléphone n'est pas un
client Vertex : il sert uniquement à piloter Claude Code par Remote Control.
Toute interface téléphone ou tablette tactile est classée `LATER`.

Les contrats restent sémantiques, accessibles et indépendants de la
présentation afin qu'une phase ultérieure puisse concevoir un vrai client
mobile sans dupliquer les calculs ni les décisions.

## Bureau large — 1600×1000

Rail ouvert, contenu 12 colonnes, dominante et rail de preuves côte à côte.
La largeur utile reste bornée à 1600 px afin d'éviter les lignes et tableaux
excessivement étirés.

## Bureau de référence — 1440×900

Composition canonique : rail 232 px rétractable, grille 12 colonnes, dominante
7–8 colonnes et rail de détail 4–5 colonnes.

## Laptop compact — 1280×800

Rail rétractable à 68 px, grille 10–12 colonnes selon la page. Un rail secondaire
peut devenir `SideSheet` ou passer sous la dominante. Les tables gardent leurs
colonnes essentielles et ouvrent le détail dans un panneau.

## Dégradation laptop — 1024×768

Test de robustesse utile mais non cible principale : rail compact, dominante
pleine largeur, panneaux secondaires sous la dominante ou en `SideSheet`.
Aucun crash, chevauchement ou donnée financière masquée n'est accepté ; cette
largeur ne doit toutefois pas provoquer la création d'une navigation mobile.

## QA

Captures et E2E obligatoires : 1280×800, 1440×900 et 1600×1000. Un smoke test
1024×768 vérifie la dégradation laptop. Aucun viewport 390/360, bottom nav,
`MobileActionBar`, geste tactile ou QA mobile dans la Beta.
