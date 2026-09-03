# Bibliothèque de widgets — Vertex Black Glass

## Principe

Un widget n'est pas une tuile décorative. C'est un contrat visuel fermé qui répond à une sous-question, consomme un DTO versionné et sait dire honnêtement quand ses données sont partielles, retardées, périmées, hors ligne ou indisponibles.

La bibliothèque est volontairement limitée. Une page peut composer trois à cinq
modules visibles, dont une dominante. Les détails supplémentaires vivent dans
une fiche, un `SideSheet` ou une route dédiée. La Beta est bureau/laptop
uniquement ; les composants mobile sont `LATER`.

## Socle officiel vérifié

- [Radix Primitives — introduction](https://www.radix-ui.com/primitives/docs/overview/introduction) : primitives non stylées et accessibles ; Vertex garde la pleine autorité visuelle.
- [Radix — styling](https://www.radix-ui.com/primitives/docs/guides/styling) : les états sont exposés par `data-state`, utilisables sans recréer la logique du composant.
- [Radix — composition](https://www.radix-ui.com/primitives/docs/guides/composition) : `asChild` permet d'appliquer le comportement à nos boutons, à condition de propager props et ref.
- [TanStack Table](https://tanstack.com/table/latest) : moteur headless pour lignes, colonnes, tri, filtre, sélection et état de table.
- [Guide de virtualisation TanStack Table](https://tanstack.com/table/v8/docs/guide/virtualization) : Table ne virtualise pas elle-même ; TanStack Virtual décide quels index rendre.
- [TanStack Virtual](https://tanstack.com/virtual/latest) : virtualisation headless, le produit conserve le DOM et le contrat de scroll.
- [Lightweight Charts v5](https://tradingview.github.io/lightweight-charts/docs) : graphiques financiers Canvas, mises à jour incrémentales et obligation d'attribution TradingView/NOTICE.
- [Tutoriel accessibilité Lightweight Charts](https://tradingview.github.io/lightweight-charts/tutorials/a11y/intro) : le Canvas exige une couche explicite de description et de navigation clavier.
- [Apache ECharts — accessibilité](https://echarts.apache.org/handbook/en/best-practices/aria/) : importer `AriaComponent`, activer/décrire ARIA et utiliser des motifs en complément des couleurs.
- [Apache ECharts — imports modulaires](https://echarts.apache.org/handbook/en/basics/import/) : importer depuis `echarts/core` uniquement les séries, composants et renderer requis.
- [Apache ECharts — capacités](https://echarts.apache.org/en/feature.html) : Canvas pour les volumes denses et SVG pour certains rendus plus légers ; le choix Vertex reste mesuré sur ses laptops cible.

## Anatomie obligatoire

Chaque widget possède, dans cet ordre logique :

1. `WidgetHeader` : question courte, titre, périmètre et action secondaire éventuelle ;
2. `DataMeta` : source, `as_of`, fraîcheur, couverture, unité/devise/timezone ;
3. `DataStateBoundary` : état global reçu du backend ;
4. `WidgetBody` : une seule représentation dominante ;
5. `WidgetConclusion` : phrase factuelle fournie ou autorisée par le contrat, jamais un verdict inventé ;
6. `WidgetFooter` : méthode/version, limites, table/export/provenance ;
7. `WidgetDetails` à la demande, dans une primitive Radix adaptée.

Le header et les métadonnées restent visibles lorsqu'un widget passe `stale` ou `error`. Le squelette ne remplace jamais l'état précédent pendant `refreshing`.

## Familles

### Files et agendas

HTML sémantique d'abord : `AttentionQueue`, `EventAgenda`, `ReviewQueue`, `EvidenceRail`, `CitationRail`. Les listes sont virtualisées uniquement au-delà d'un seuil mesuré et conservent focus/position lors des refreshs.

### Tables de décision

`OpportunityTable`, `OptionChain`, `PortfolioTable` et `SourceHealthMatrix` utilisent TanStack Table. TanStack Table gère l'état d'interface ; le serveur fournit rangs, gates, P&L, Greeks, agrégats et toute autre valeur financière. Aucune fonction `aggregationFn` financière n'est autorisée dans le client.

TanStack Virtual n'est activé que pour un volume qui dépasse le budget DOM défini dans le catalogue. Une vue bornée non virtualisée sert aux tests lecteur d'écran et à l'export.

### Graphiques financiers

`PriceVolumeChart` utilise exclusivement Lightweight Charts, avec deux overlays maximum, `autoSize`/`ResizeObserver`, mise à jour incrémentale et attribution TradingView visible. Le Canvas seul n'est pas déclaré accessible : Vertex ajoute navigation clavier, focus visible, description courte et table OHLCV équivalente.

### Visualisations analytiques

`MarketMap`, `PayoffChart`, `PerformanceChart`, `ConcentrationPanel` et les vues de surface utilisent `echarts/core` par imports modulaires. `AriaComponent` et le renderer retenu sont explicitement enregistrés, `aria.show` est actif, une description courte remplace la liste automatique lorsqu'elle deviendrait bavarde, et des decals/signes complètent les couleurs. Le conteneur possède une taille avant `init`, réagit par `ResizeObserver` et l'instance est `dispose()` à la destruction. ECharts GL et toute visualisation 3D sont interdits.

Canvas est la valeur par défaut pour les données denses ; SVG est testé pour les
graphiques simples ou l'export. Le renderer n'est jamais changé sans test
mémoire/FPS et comparaison visuelle sur les profils laptop cible.

### Jauges factuelles

Les jauges sont autorisées lorsqu'elles répondent à une question bornée et que
le serveur fournit valeur, unité, échelle, seuils, méthode, qualité et `as_of`.
Elles utilisent une barre linéaire, un bullet chart, une bande segmentée ou,
depuis ADR-017, un arc gradué (`ArcGauge`) dont la position du marqueur est une
coordonnée servie ; aucun compteur automobile décoratif, aiguille animée,
volume 3D ou score composite opaque.

- `CalibratedConfidenceGauge` : visible uniquement avec
  `probability_evidence` valide, population/holdout, taille d'échantillon,
  intervalle et méthode de calibration. Sinon : « Données insuffisantes », sans
  pourcentage de remplacement.
- `MarketRegimeGauge` : régime discret versionné plus confiance descriptive ;
  il ne devient jamais une probabilité de trade.
- `FreshnessCoverageGauge` : deux barres indépendantes — âge contre TTL puis
  reçu contre attendu — sans moyenne entre fraîcheur et couverture.
- `RiskGauge` : une mesure nommée à la fois, avec unité et seuils. Un score
  générique « risque 72/100 » sans formule/version est interdit.

Chaque jauge expose la valeur en texte, le seuil actuel, les extrêmes, les
limites et une alternative tabulaire. Couleur, longueur et animation ne portent
jamais seules le sens. Le navigateur ne calcule ni pourcentage, ni seuil, ni
position du marqueur : les coordonnées de rendu proviennent du DTO serveur.

### Formes v2 (ADR-017)

Depuis `docs/09-adr/017-titanium-ledger-v2-formes-widgets.md`, les formes
suivantes sont admises, chacune sur une donnée servie et par une primitive du
socle (`apps/web/src/components/widgets/`) :

| Forme | Primitive | Donnée servie exigée |
|---|---|---|
| anneau / donut à chiffre central, quatuor d'anneaux | `RingShares` | parts `*_pct` servies ; chiffre central servi verbatim |
| jauge en arc graduée | `ArcGauge` | valeur bornée, bornes, seuils, position servie |
| aire à dégradé sous une série, sparkline en aire | `SparkFigure`, `MultiSeriesArea` | série servie ≥ 2 points, période nommée |
| barres sur rail | `CensusBars`, `DayBars` | comptes entiers ou parts servis |
| matrice de bandes | `CellGrid` | nom de bande servi + texte servi |
| liste groupée par jour | `ActivityFeed` | horodatages ISO servis, montants en chaînes signées |

Chaque widget porte la valeur en texte ; une absence est un état nommé, jamais
une barre de hauteur zéro ni un secteur vide. La teinte sémantique secondaire de
la page (`macro`, `option` ou `warning`, déclarée dans le catalogue ; jamais
`positive` ni `negative`, réservés au signe financier servi) est la seule teinte
ajoutée à l'argent, au titane et à l'ambre de la dominante.
Restent interdits : halo permanent, noir pur, carte floue, couleur seule,
compte à rebours ou horloge client, radar sans dimension servie, dégradé de
fond plein, pulsation, valeur abrégée côté client, toute forme sur une valeur
non servie.

### Fiches et formulaires

`AdviceCard`, `OptionInspector`, `LegComposer`, `ThesisDetail`, `AiAnswer` et les diagnostics système s'appuient sur les primitives Radix. Dialog, AlertDialog, Accordion, Tooltip, Popover, Tabs et Select sont enveloppés une seule fois dans le package UI Vertex.

## Contrat de données commun

```ts
type WidgetEnvelope<T> = {
  schemaVersion: string;
  state: 'loading' | 'refreshing' | 'empty' | 'partial' |
    'delayed' | 'stale' | 'offline' | 'error';
  asOf: string | null;
  staleAfter: string | null;
  sourceIds: string[];
  coverage: Coverage | null;
  rights: RightsSummary;
  payload: T | null;
  limitations: Limitation[];
  traceId: string;
};
```

Ce type illustre la frontière ; le client réel est généré depuis OpenAPI. Tous les prix, montants, ratios et quantités sensibles restent des chaînes décimales jusqu'au formateur. Le navigateur peut formater un nombre reçu, filtrer ou réordonner une vue selon un choix explicite ; il ne recalcule pas de donnée financière.

## Variantes visuelles fermées

| Variante | Usage | Interdit |
|---|---|---|
| `dominant` | question principale, 6–8 colonnes | deux dominantes sur une page |
| `support` | contexte directement utile | KPI isolé sans provenance |
| `rail` | preuves, détails, diagnostics | rail de plus de 360 px ou second dashboard |
| `inline` | état dans table/liste | carte imbriquée |
| `sheet` | détail à la demande | action critique sans titre/retour focus |
| `workflow-step` | formulaire ou simulation séquencée sur bureau compact | masquer les hypothèses au résultat |

Pas de variante `glass-card` libre : le verre est une propriété de surface contrôlée par tokens, pas une justification de carte.

## États

Les huit états définis dans `UI_STATES.md` sont obligatoires pour chaque widget de données. En complément :

- `NOT_ENTITLED` est une cause documentée de `partial` ou d'indisponibilité, jamais `empty` ;
- `invalid_input` est un état de formulaire, pas une erreur serveur ;
- `blocked` est un résultat métier reçu, pas une teinte du conteneur ;
- une panne d'une source n'efface pas les modules sains ;
- aucun widget ne fabrique un fallback financier côté client.

## Densité, actions et textes

- une dominante, une action principale remplie par page ;
- deux actions secondaires maximum dans un header ; le reste va dans un menu nommé ;
- 8–15 éléments par défaut dans une file ;
- 5–9 colonnes visibles par défaut ; à 1280 px, les colonnes secondaires passent dans le détail sans masquer provenance ni état ;
- titre descriptif, question en langage simple, conclusion d'une ligne ;
- unités et fraîcheur à proximité immédiate de la valeur ;
- aucun carrousel automatique, aucun badge sans texte et aucune jauge hors contrat factuel.

## Sécurité et contenu non fiable

Headlines, noms de fournisseurs, URLs, notes, réponses IA et fichiers importés sont non fiables. Les widgets n'interprètent aucun HTML externe, bornent les longueurs, sécurisent les liens et n'envoient pas les payloads complets en télémétrie. Les tooltips ne contiennent ni secret ni information indispensable.

## Definition of Done d'un widget

- entrée OpenAPI typée et aucune finance TypeScript ;
- story pour huit états et contenus longs aux trois viewports bureau ; smoke test de dégradation à 1024 px ;
- parcours clavier, lecteur d'écran, zoom 200 % et axe sans violation critique/sérieuse ;
- budget DOM, chunk et interaction mesuré ;
- table/résumé équivalent pour tout graphique ;
- erreurs isolées, dernière donnée valide conservée et datée ;
- provenance, couverture, méthode et limites accessibles ;
- aucune dépendance, icône ou variante hors catalogue.
