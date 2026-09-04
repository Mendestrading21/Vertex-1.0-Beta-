# Dossiers de refonte — audit-conception du 2026-09-04

Ces quinze documents sont la matière de la **phase IV** du
`docs/99-status/PLAN_MAITRE.md` : un dossier par espace, plus trois coupes
transversales.

## Comment ils ont été produits

Cinquante et un agents, en trois passes :

1. **Audit** — douze auditeurs, un par espace, qui lisent le code, les contrats
   Python et les jobs du worker. Leur consigne centrale n'était pas de décrire
   l'existant mais de trouver **les champs réellement publiés par le contrat et
   jamais lus par l'interface** — la matière déjà calculée que la page jette.
2. **Conception** — douze concepteurs, qui dessinent la page cible à partir de
   cet audit : chaque module avec son titre exact, sa question, sa taille sur la
   grille, sa primitive, sa forme graphique, **le champ précis qui l'alimente**
   et son texte d'absence.
3. **Réfutation** — vingt-quatre lentilles adversariales, deux par espace. La
   première va vérifier dans le dépôt que chaque champ déclaré « servi » existe
   vraiment, et doute par défaut. La seconde chasse les violations des lois :
   vocabulaire d'ordre, lecture de compte IBKR, probabilité sans calibration,
   texte d'absence contenant un chiffre, seconde dominante, jauge circulaire,
   grille régulière là où il faut de l'asymétrie.

## Ce que la troisième passe a trouvé

**Les vingt-quatre lentilles ont rendu `CORRECTIONS_REQUISES`. Aucune
conception n'a survécu intacte.** 338 réfutations au total.

C'est la raison d'être du §4 de chaque dossier, et c'est pourquoi **aucun de ces
documents n'est une spécification approuvée**. Le lot qui implémente un espace
applique d'abord les corrections de son §4, puis dessine.

## Chiffres mesurés

| | |
|---|---:|
| Espaces couverts | 12 |
| **Champs servis et jamais affichés** | **306** |
| Réfutations à traiter | 338 |
| Primitives neuves exigées | 26 |

Les 306 champs sont le vrai gisement : ils ne demandent aucun calcul nouveau,
aucune source nouvelle, aucun droit nouveau. Python les produit déjà, le contrat
les publie déjà, et l'interface les jette.

## Les fichiers

| Fichier | Contenu |
|---|---|
| `00-intelligence-faisable.md` | Ce que Vertex peut calculer et ne calcule pas : verdict `FAISABLE` / `BLOQUÉ-PAR-SOURCE` / `INTERDIT` par intelligence, avec la preuve par fichier et le calcul à écrire. Nourrit les lots 7 à 13. |
| `00-systeme-visuel.md` | État exact des jetons, des neuf portes, des primitives et des familles de classes de table. Contrastes calculés. Nourrit les lots 4 à 6. |
| `00-rangement-documentaire.md` | Le désordre documentaire mesuré et l'arborescence cible, fichier par fichier. Nourrit le lot 1. |
| `aujourd.md` · `calendrier.md` · `marche.md` · `opportunite.md` · `analyse.md` · `option.md` · `simulateur.md` · `portefeuille.md` · `suivi.md` · `performance.md` · `vertex-ia.md` · `systeme.md` | Un dossier par espace : audit mesuré, conception, réfutations, primitives exigées. Nourrissent les lots 14 à 20. |

## Limite déclarée

Ces dossiers sont produits par lecture du dépôt, pas par exécution du produit.
Ils nomment des défauts visibles dans le code ; ils ne remplacent ni une
relecture de captures aux trois largeurs, ni les tests. Cette session a mesuré
que la relecture de captures trouve ce qu'aucun test ne voit — une règle CSS
morte, un débordement de 118 px, un thème natif clair. Elle reste obligatoire
avant chaque commit de lot de page.
