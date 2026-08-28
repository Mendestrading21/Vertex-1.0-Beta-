# Composition des douze pages — Black Glass

## Règle maîtresse

Une page répond à une question, possède une dominante et montre trois à cinq modules au premier niveau. Vertex ingère beaucoup d'information mais n'affiche pas tout en même temps. L'utilisateur découvre la preuve par progression : résumé → dominante → rail/détail → source.

Le mot « dashboard » décrit le shell commun, pas une mosaïque interchangeable de KPI.

Vertex 1.0 Beta est `DESKTOP ONLY`. Le téléphone sert uniquement au pilotage
Claude Code par Remote Control ; il n'expose aucune interface Vertex. Le mobile
est `LATER`, tandis que les contrats sémantiques restent réutilisables.

## Grille et surfaces

### Bureau large — 1600×1000

- rail : 232 px ouvert ou 68 px replié ;
- contenu : 12 colonnes, largeur utile maximale 1600 px, gaps 16–20 px ;
- dominante : 7–8 colonnes ;
- rail de preuve : 4–5 colonnes, maximum 360 px lorsque fixe ;
- bandeau de contexte : une ligne, pas une rangée de cartes ;
- seconde rangée : deux modules support maximum.

### Bureau de référence — 1440×900

- rail 232 px rétractable, contenu 12 colonnes ;
- dominante 7–8 colonnes et rail 4–5 colonnes ;
- aucune seconde mosaïque sous la dominante.

### Laptop compact — 1280×800

- rail réduit à 68 px si nécessaire ;
- dominante pleine largeur lorsque le rail de preuves ne conserve pas 320 px ;
- détail en `SideSheet` ou sous la dominante ;
- tables avec colonnes essentielles épinglées et détail à la demande.

À 1024×768, un smoke test vérifie seulement la dégradation laptop : aucun
chevauchement, crash ou contenu critique masqué. Les références de QA sont
1280×800, 1440×900 et 1600×1000. Aucun viewport mobile.

## Shell constant

1. rail de navigation ;
2. `ContextBar` : instrument/périmètre, snapshot, source, fraîcheur et santé ;
3. titre + question dominante ;
4. zone d'action principale unique ;
5. grille de modules ;
6. région live discrète pour refresh/incidents ;
7. `SideSheet` de provenance ou détail.

Le contexte ne saute pas lors d'une navigation entre Analyse, Options et Simulateur. Un changement de snapshot est une action explicite et visible.

## Composition page par page

| Page et question | Dominante | Modules visibles bureau (3–5) | Dégradation laptop 1024 px |
|---|---|---|---|
| Aujourd'hui — Qu'est-ce qui mérite mon attention maintenant ? | `AttentionQueue` | `SessionHealthStrip`, file, `Next24Hours`, `ExposureFocus` | dominante pleine largeur ; détail en `SideSheet` |
| Calendrier — Quels événements peuvent affecter mes instruments et mon portefeuille ? | `EventAgenda` | filtres compacts, agenda, `ExposureCrossing`, `EventDetail` | agenda par jour ; fiche en `SideSheet` |
| Marchés — Dans quel contexte vais-je analyser les instruments ? | `MarketMap` | `MarketContextStrip`, `MarketRegimeGauge`, carte, `BreadthPanel`, `BenchmarkStrip` | carte remplacée par table sectorielle si largeur insuffisante |
| Opportunités — Quels candidats admissibles méritent une analyse approfondie ? | `OpportunityTable` | barre recherche/filtres, table, `CandidateCompare`, `GateEvidenceRail` | colonnes essentielles ; comparaison limitée à deux |
| Analyse — Que disent les données certifiées et quelles limites restent ouvertes ? | `PriceVolumeChart` | `AdviceCard` + confiance calibrée conditionnelle, graphique, `EvidenceRail`, `ScenarioSet` | graphique pleine largeur ; preuves sous la dominante |
| Options — Quels contrats sont réellement exploitables et quels risques portent-ils ? | `OptionChain` | `UnderlyingStrip`, chaîne, `OptionSurface`, `OptionInspector` | strikes épinglés ; inspecteur en `SideSheet` |
| Simulateur — Comment une structure réagit-elle au prix, au temps et à la volatilité ? | `PayoffChart` | `LegComposer`, `AssumptionPanel`, payoff/surface, `SimulationSummary` | compositeur puis graphique pleine largeur |
| Portefeuille — Quelles expositions résultent de mon ledger manuel ? | `PortfolioTable` | `PortfolioSummary`, `RiskGauge`, table, `ConcentrationPanel`, `PortfolioRiskRail` | colonnes essentielles ; fiche position en `SideSheet` |
| Suivi — Quelles thèses, alertes et informations doivent être revues ? | `ReviewQueue` | file, `ThesisDetail`, `RevisionTimeline`, `WatchlistHygiene` | file puis fiche sous la dominante |
| Performance — Quelle performance ai-je réellement enregistrée ? | `PerformanceChart` | capital/drawdown, `PerformanceMetrics`, `MonthlyHeatmap`, `AttributionPanel` | graphiques empilés et métriques repliables |
| Vertex AI — Comment expliquer sans créer une seconde vérité ? | `AiAnswer` | question/périmètre, réponse, `CitationRail`, `ContradictionPanel` | réponse pleine largeur ; citations sous la réponse |
| Système — Puis-je faire confiance aux sources et sauvegardes maintenant ? | `SourceHealthMatrix` | `FreshnessCoverageGauge`, matrice, `JobQueuePanel`, `SecurityBackupPanel`, `AuditIncidentLog` | matrice avec colonnes épinglées ; diagnostics sous la dominante |

Cette matrice est normative. Une sixième section visible exige d'en remplacer une ou de la déplacer dans le détail ; elle ne s'ajoute pas sous le pli.

## Hiérarchie Black Glass

- niveau 0 : fond `--vx-app`, sans texture ;
- niveau 1 : dominante `--vx-surface-0` avec bordure douce ;
- niveau 2 : rail/fiche `--vx-surface-1` ;
- niveau 3 : popover/dialog `--vx-surface-2` et bordure forte ;
- sélection : mince gradient argent→violet uniquement sur contrôle sélectionné ou action primaire ;
- blur : réservé au rail/sheet superposé, jamais à toutes les cartes ;
- ombre : une ombre diffuse faible pour séparer une couche modale, aucune élévation 3D.

Les surfaces ne doivent pas devenir identiques. La hiérarchie vient d'abord de l'espace, de la typographie et des bordures, puis seulement d'une nuance de fond.

## Scannabilité

- ligne de titre : 24–32 px, question en texte secondaire ;
- nombres comparables en Geist Mono tabulaire ;
- métadonnées regroupées, jamais répétées dans chaque cellule si l'en-tête les porte ;
- une conclusion textuelle au-dessus ou sous chaque graphique ;
- fraîcheur visible sans ouvrir un tooltip ;
- les contradictions ont la même présence visuelle que les confirmations ;
- une page reste compréhensible en niveaux de gris.

## Flux d'information et autorité

```text
DTO serveur versionné → état/qualité → représentation → détail/provenance
```

Le navigateur choisit une représentation, filtre ou ordonne selon l'utilisateur. Il ne calcule jamais prix, P&L, rendement, Greeks, score, rang canonique, volatilité, scénario ou probabilité. Un état stale empêche tout recalcul exigeant du live ; la dernière vue reste consultable avec son heure.

## Graphiques

- Lightweight Charts seulement pour chandeliers/volume sur Analyse ; deux overlays maximum ; attribution TradingView/NOTICE et lien public obligatoires.
- ECharts pour carte, payoff, surface, drawdown, heatmap et attribution ; imports modulaires, ARIA activé, motifs et table alternative.
- TanStack Table + Virtual pour les grandes collections ; la virtualisation n'est pas une permission de charger des données illimitées.
- Jauges linéaires/segmentées pour confiance calibrée, régime, fraîcheur/couverture et risque nommé ; seuils/version/provenance obligatoires, zéro cadran décoratif.
- SVG/CSS interne seulement pour sparklines, micro-barres et jauges factuelles du catalogue ; aucune 3D, aucun WebGL décoratif, aucun globe, cadran ou particule.

## Validation de page

Avant merge, capturer 1280×800, 1440×900 et 1600×1000, puis exécuter le
smoke test 1024×768 et répondre oui à chaque question :

- la question dominante se lit-elle avant les modules ?
- une seule représentation attire-t-elle d'abord le regard ?
- y a-t-il entre trois et cinq modules visibles ?
- provenance, unité et fraîcheur sont-elles accessibles ?
- la dégradation laptop conserve-t-elle la décision et la provenance ?
- loading, partial, delayed, stale, offline et error restent-ils honnêtes ?
- la page est-elle opérable clavier, zoom 200 %, reduced motion et sans couleur ?
- le bundle route ne charge-t-il que son moteur graphique ?
- aucun calcul financier ou second verdict n'existe-t-il dans le client ?

Le laboratoire vectoriel `design-assets/preview/Vertex_BlackGlass_UILab.svg` matérialise la page Analyse, mais les règles de cette matrice prévalent sur le mockup.
