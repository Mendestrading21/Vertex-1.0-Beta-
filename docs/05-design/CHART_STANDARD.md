# Standard des graphiques

## Bibliothèques

- TradingView Lightweight Charts : chandeliers, volume, lignes de prix et annotations.
- Apache ECharts : heatmaps, treemaps, surfaces, payoff, drawdown, attribution, calendrier et distributions.
- SVG/CSS interne : sparklines et micro-barres simples seulement.
- Aucun Chart.js, Plotly ou D3 ajouté par défaut.

Lightweight Charts exige la NOTICE et une attribution/lien TradingView visible. ECharts exige conservation des notices Apache et sous-composants.

## Contrat `ChartFrame`

Chaque graphique déclare :

- question métier ;
- titre et conclusion textuelle ;
- unité, devise, timezone et période ;
- source, `as_of`, fraîcheur et couverture ;
- légende interactive ;
- états loading/refreshing/empty/partial/delayed/stale/offline/error ;
- résumé textuel ;
- table accessible et export ;
- méthode/calcul et version ;
- limites et hypothèses.

## Carte page → visualisation

| Page | Dominante | Moteur |
|---|---|---|
| Aujourd'hui | file de priorité | HTML/table |
| Calendrier | agenda | HTML + ECharts si heatmap |
| Marchés | heatmap/treemap | ECharts |
| Opportunités | table virtualisée | TanStack Table/Virtual |
| Analyse | chandeliers/volume | Lightweight Charts |
| Options | chaîne | TanStack Table/Virtual |
| Simulateur | payoff/surface | ECharts |
| Portefeuille | table | TanStack Table |
| Suivi | file de revues | HTML/table |
| Performance | capital/drawdown | ECharts |
| Vertex AI | réponse/citations | HTML |
| Système | matrice de santé | HTML/table |

## Performance

Importer chaque moteur par route. Aucun moteur de graphique dans le bundle initial. Décimer les séries côté worker avec méthode déclarée, jamais masquer des points côté client sans trace. Les interactions ordinaires visent 60 FPS.

## Couverture visuelle et jauges

La bibliothèque doit couvrir explicitement : prix/volume, chaîne d'options,
smile/skew et surface IV, payoff/sensibilités, scénarios
baissier-neutre-haussier, performance/drawdown, états et contradictions.

Les jauges ne remplacent pas ces graphiques. Elles sont limitées à quatre
familles factuelles : confiance calibrée, régime de marché, fraîcheur/couverture
et mesure de risque nommée. Formes autorisées : barre linéaire, bullet chart et
bande segmentée. Valeur, unité, bornes, seuils, méthode/version, qualité,
provenance et `as_of` viennent du serveur. Fraîcheur et couverture restent deux
barres indépendantes. Aucun speedometer, score opaque, aiguille animée ou 3D.
