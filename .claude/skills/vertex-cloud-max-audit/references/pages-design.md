# Douze pages et contrat visuel

## Contrat approuvé

Vertex reste bureau uniquement. L'iPhone pilote Claude dans le cloud mais ne
change pas le produit. Contrôler `1280x800`, `1440x900` et `1600x1000` ;
`1024x768` est une dégradation facultative.

Conserver : fond bleu-noir orbital, petite sidebar intégrée, actif ambre, ticker
supérieur, cartes Black Glass translucides, bordures titane fines, cadran de
régime circulaire, espace central dominant, inspecteur droit, couleurs
financières strictes, typographie dense et badge `VERTEX 1.0 BETA`.

Refuser sans nouvelle décision : grande sidebar flottante, chaque bouton dans
sa boîte, fond noir neutre, nouvelle navigation, compositions de widgets
alternatives, autre logo, effets Apple supplémentaires ou chiffres décoratifs.

## Navigation canonique

1. Aujourd'hui
2. Calendrier
3. Marchés
4. Opportunités
5. Analyse
6. Options
7. Simulateur
8. Portefeuille
9. Suivi
10. Performance
11. Vertex IA
12. Système

Documenter tout écart entre routes produit, routes React, liens du rail, titres
et redirections ; ne pas le normaliser silencieusement.

## Matrice par page

Pour chacune des douze pages, vérifier et citer :

| Axe | Question |
|---|---|
| Intention | Quelle question métier unique et quelle action humaine ? |
| Route | Route, paramètres, deep link, état sans sélection et 404. |
| Données | Hook, schéma, API, snapshot, worker, source et état réel/synthétique. |
| Fraîcheur | Timestamp, source, timezone, seuil, stale/partial/missing visible. |
| Composition | Objet dominant, preuves secondaires, inspecteur et action primaire. |
| Widgets | Utilité, unité, période, provenance ; aucun doublon décoratif. |
| Graphes | Question, axes, échelle, timezone, tooltip, trous, zoom et tableau accessible. |
| États | Loading, empty, error, stale, degraded, not-entitled, unsupported, unknown. |
| Interaction | Clavier, focus, hover, sélection, filtres, URL et persistance. |
| Accessibilité | Noms, contraste, forme en plus de la couleur, motion réduite. |
| Performance | Chargement par route, taille, rendu, virtualisation et budget. |
| Preuve | Tests unitaires, intégration, E2E et captures aux trois viewports. |

## Vérité visuelle

- L'ambre désigne marque/sélection/action, jamais gain.
- Vert et rouge restent financiers et doublés par texte, signe, forme ou icône.
- Une donnée absente ne devient ni zéro ni tiret ambigu.
- Chaque valeur importante expose provenance, temps et statut.
- Un graphique sans données garde son cadre explicatif et son état, pas une
  courbe synthétique non étiquetée.
- La vue ne recalcule jamais verdict, Greek, IV, prix, probabilité, score,
  breakeven, risque/rendement, P&L ou classement canonique.

Si la capture maîtresse n'est pas versionnée et accessible au SHA audité,
classer la fidélité pixel comme `BLOQUÉ` et auditer seulement le contrat codifié,
les tokens, composants et captures CI disponibles.
