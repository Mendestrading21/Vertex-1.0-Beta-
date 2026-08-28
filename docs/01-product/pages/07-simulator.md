# Page 07 — Simulateur `/simulator/:id?`

## Question

Comment une structure réagit-elle au prix, au temps et à la volatilité ?

## Dominante et modules

Dominante : payoff ; bascule explicite vers surface spot/temps.

1. Compositeur de jambes.
2. Hypothèses et snapshot.
3. Graphique dominant.
4. Gain/perte max, breakevens, Greeks et sensibilités.

Action principale : sauvegarder une simulation.

## Données et logique

Contrats exacts, snapshot options, spot, courbes, dividendes et surface IV. Tous les calculs sont backend. Monte-Carlo avancé seulement avec seed, chemins, modèle et intervalle d'incertitude.

## États et adaptation desktop

Stale demande conserver ou rebaser le snapshot. Offline : aucun nouveau calcul. Cible Vertex 1.0 Beta : 1280, 1440 et 1600 px. À 1024 px, Compositeur, Hypothèses et Résultat s'empilent dans cet ordre sur la page desktop, avec le payoff immédiatement avant les métriques.

Mobile : **LATER**. Les contrats sémantiques des jambes, hypothèses, snapshots, états, résultats et sauvegarde sont conservés, sans parcours Vertex pour téléphone.

## Acceptation

- payoff égal à la somme des jambes et coûts ;
- résultats déterministes à seed fixe ;
- cas expiration, zéro vol et strikes extrêmes ;
- E2E invalid input, stale rebase et structure multi-jambes.
