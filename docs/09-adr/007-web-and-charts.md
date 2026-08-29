# ADR-007 — Web React strict et moteurs graphiques spécialisés

- Statut : Accepté
- Date : 2026-08-28
- Portée : PWA desktop Beta, design system, graphiques, tables

## Contexte

Les douze pages doivent partager une identité Black Glass cohérente sur desktop et représenter cours, options, distributions et états système. Une bibliothèque unique ne couvre pas correctement toutes ces formes. L’interface ne doit pas devenir un moteur financier parallèle.

## Décision

- Le web est une PWA React desktop avec TypeScript strict, Vite et pnpm.
- La Beta qualifie 1280×800, 1440×900 et 1600×1000 ; 1024×768 est un mode laptop dégradé qui conserve vérité financière, provenance, alertes et actions essentielles.
- L'interface téléphone est `LATER`. Les contrats OpenAPI, états et identités restent indépendants du viewport pour éviter tout fork métier futur.
- TanStack Query gère l’état serveur ; TanStack Table et Virtual gèrent les tables longues.
- Radix fournit les primitives de comportement, tandis que Vertex possède tous les styles.
- Lightweight Charts rend prix, chandeliers, volumes et annotations, avec attribution obligatoire.
- ECharts rend heatmaps, surfaces, payoff, drawdown, calendrier et distributions.
- SVG ou CSS interne est réservé aux micro-visualisations simples.
- Chaque moteur est encapsulé dans le package charts et chargé par route.
- ChartFrame impose source, unité, période, as_of, fraîcheur, couverture, état dégradé, résumé textuel et table accessible.
- Toute décimation ou agrégation est effectuée et tracée côté Python.
- TypeScript ne calcule aucune valeur financière autoritaire.

## Conséquences

### Positives

- Chaque représentation utilise le moteur adapté.
- Performances contrôlables par chargement différé.
- Accessibilité, provenance et états dégradés deviennent uniformes.
- L’identité visuelle ne dépend pas d’un thème générique.

### Coûts et contraintes

- Deux moteurs graphiques doivent être maintenus et testés.
- Les adapters internes doivent stabiliser leurs APIs.
- Les notices et l’attribution TradingView doivent être conservées.

## Options rejetées

| Option | Motif du rejet |
|---|---|
| Un seul moteur pour tout | Compromis de qualité et d’accessibilité |
| D3 libre partout | Surface de code et maintenance trop grandes |
| Chart.js ou Plotly en plus | Duplication sans besoin démontré |
| Dashboard de cartes génériques | Hiérarchie faible et densité excessive |
| Calculs dans les composants | Contredit l’autorité Python |

## Critères de réexamen

Une nouvelle bibliothèque n’entre qu’après un cas impossible à couvrir, un prototype mesuré, une revue de licence, un wrapper interne et le retrait éventuel d’une dépendance existante.
