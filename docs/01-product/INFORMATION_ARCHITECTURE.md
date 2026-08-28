# Architecture de l'information

## Navigation

- **Décider** : Aujourd'hui, Opportunités, Analyse, Options, Simulateur.
- **Observer** : Calendrier, Marchés.
- **Piloter** : Portefeuille, Suivi, Performance.
- **Assistance** : Vertex AI, Système.

Vertex 1.0 Beta : rail latéral rétractable sur bureau/laptop. Les largeurs de référence sont 1280, 1440 et 1600 px ; à 1024 px, le rail peut rester replié et les modules secondaires passer sous la dominante. Le contexte courant — instrument, snapshot, source et fraîcheur — reste stable pendant la navigation.

Mobile : **LATER**. Aucune arborescence de rendu ou navigation Vertex pour téléphone n'est définie dans la Beta. Les mêmes identifiants de route et contrats sémantiques sont néanmoins conservés pour la phase ultérieure. Sur téléphone, Claude Remote Control peut piloter la session desktop ; il ne rend pas l'interface Vertex.

## Contrat de page

Chaque page définit : objectif/non-objectifs, question principale, visuel dominant, trois à cinq modules, unique action principale, contrats API, unités, source, fraîcheur, états, adaptation desktop, accessibilité, télémétrie, budget et tests. Les contrats de données, d'états et d'actions sont sémantiques et indépendants du rendu afin de rester réutilisables lorsque Mobile passera de **LATER** à une phase planifiée.

## Densité

La collecte n'impose pas la densité visuelle. Le Data Fusion Hub peut traiter de nombreux éléments ; la page expose d'abord la file filtrée, puis le détail à la demande dans un panneau ou une route dédiée.

## États communs

`loading`, `refreshing`, `empty`, `partial`, `delayed`, `stale`, `offline`, `error`. Un rafraîchissement conserve la dernière donnée visible et sa date. `empty` n'est jamais transformé en zéro. `stale` bloque les recalculs exigeant du live.
