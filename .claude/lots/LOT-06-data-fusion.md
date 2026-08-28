# LOT-06 — Data Fusion Hub

## Références et dépendances

- Références obligatoires : `docs/04-integrations/DATA_FUSION.md`, `docs/04-integrations/SOURCE_CAPABILITY_MATRIX.md`, `docs/03-domain/CANONICAL_CONTRACTS.md`, `docs/03-domain/DATA_QUALITY.md`, `docs/03-domain/UNITS_TIME_AND_PRECISION.md` et `docs/04-integrations/AI_GATEWAY.md`.
- Dépendances bloquantes : LOT-02 Contrats/identités, LOT-03 Stockage/qualité, LOT-04 Edge IBKR et LOT-05 Ingress/imports TradingView.
- Les sources primaires complémentaires nécessitent une API, un flux ou un téléchargement officiellement autorisé, un ADR et une entrée au registre des dépendances avant implémentation.

## Objectif

Construire une couche de fusion déterministe qui exploite le maximum d'informations légalement accessibles depuis les abonnements IBKR et TradingView, puis les sources primaires approuvées, tout en réduisant le bruit. Elle normalise, relie, versionne, déduplique, mesure la couverture, conserve les conflits et classe la pertinence sans cacher la provenance ni inventer une disponibilité.

Les familles couvertes sont : marché, options, scanners, actualités, calendrier macro/société, fondamentaux, ETF, signaux techniques, watchlists, portefeuille manuel et thèses utilisateur.

## Non-objectifs et interdictions

- scraper une interface, automatiser un navigateur ou contourner paywall, entitlement, quota ou condition de redistribution ;
- lire compte, positions, P&L, marge, ordres ou exécutions IBKR ;
- transformer une alerte TradingView, un titre de presse ou un score de pertinence en verdict ;
- résoudre une contradiction par vote majoritaire, dernier arrivé, moyenne ou IA ;
- supprimer irréversiblement un item considéré comme doublon ;
- remplacer silencieusement une source absente/retardée par une autre ou mélanger live et delayed ;
- présenter une couverture partielle comme exhaustive ;
- laisser l'IA décider de l'identité, de la déduplication canonique, de la vérité d'un fait ou du classement final ;
- copier ou afficher un corps d'article au-delà de ses droits.

## Livrables attendus

1. Catalogue versionné `SourceCapability`/`SourceEntitlement`/`SourceCoverage`, sondé par environnement et cas d'usage.
2. Registre de politique par champ : source prioritaire, compléments autorisés, conditions de fraîcheur, droits de restitution, résolution des conflits et fallback explicite.
3. Normaliseurs canoniques pour `NewsItem`, `CorporateEvent`, `MacroEvent`, `FundamentalFact`, `Filing`, `EtfProfile`, `EtfExposure`, `TechnicalSignal`, `ScannerResult` et `WatchlistSnapshot`.
4. Graphe d'identité `EntityLink` reliant instrument, émetteur, CIK, ISIN/CUSIP lorsque licenciés, `conId`, ticker TradingView, provider news et ETF, avec période de validité et statut de résolution.
5. Pipeline de news : ingestion selon droits, URL canonique, empreinte déterministe, `NewsCluster`, `ArticleAccess`, langues et versions.
6. Pipeline d'événements : rapprochement et révisions WSH/Pine/sources primaires, statut estimé/confirmé/annulé, timezone et `ConflictRecord`.
7. Pipeline fondamentaux : concept, taxonomie, unité, devise, période, dimensions, filing et date de disponibilité, sans look-ahead.
8. Pipeline ETF : profil, benchmark, émetteur, structure, documents, actifs/expositions datés et couverture explicite ; aucune estimation silencieuse des holdings absents.
9. Fusion scanner/signaux : résultats IBKR, snapshots CSV/Pine Screener et alertes Pine conservés séparément, liés à l'instrument et à l'heure.
10. Moteur de déduplication explicable et réversible, avec `FusionDecision`, règles/version, candidats, similarités auxiliaires et raisons.
11. Moteur de pertinence déterministe et décomposable : lien position manuelle/thèse/watchlist/instrument ouvert, portée, proximité, nouveauté, fiabilité, qualité et fraîcheur.
12. API de lecture « timeline canonique », recherche et détail de provenance ; maximum trois raisons de pertinence résumées, détail complet accessible.
13. Jobs de réconciliation/rejeu, quarantaine, revue manuelle et audit complet des changements de politique.
14. Tableaux de santé par famille/source : fraîcheur, couverture, conflits, retard, entitlement, backlog, erreurs et droits de contenu.
15. Jeu de données synthétique multi-source, golden clusters, événements révisés, identités ambiguës et ETF partiels.

## Politique de priorité et vérité

| Domaine | Autorité initiale | Complément permis | Comportement en défaut |
|---|---|---|---|
| Prix/options live | IBKR API | alerte TradingView comme déclencheur seulement | bloque le live |
| Contrats | IBKR `conId` + identité complète | symbologie TradingView | quarantaine si ambigu |
| Scanner | IBKR scanner | export/Pine Screener daté | deux snapshots, pas de faux temps réel |
| News | providers IBKR selon droits | émetteur/autorité/source primaire | headline/lien/corps selon `ArticleAccess` |
| Événement société | WSH si disponible | Pine ciblé + source primaire | conserve révisions/conflit |
| Fondamentaux US | filing SEC point-in-time | Pine `request.financial` daté | champ manquant explicite |
| Macro | organisme officiel/FRED-ALFRED | Pine `request.economic` | vintage conservé |
| Technique | calcul Python sur données IBKR | signal Pine versionné | observations comparées, non fusionnées |
| Watchlist/screener TV | liste Vertex + export officiel | scanner IBKR | snapshot manuel horodaté |
| News/calendrier UI TV | aucun accès automatique supposé | lien profond utilisateur | jamais aspiré |

La politique est versionnée, testée et renvoie toujours la liste des observations candidates, la décision de fusion et les limites. Changer une priorité de source exige ADR, migration/rejeu contrôlé et rapport de différence.

## Déduplication, conflits et droits

La déduplication suit cet ordre : identifiant fournisseur, identifiant/document officiel, URL canonique, empreinte normalisée titre+entités, puis similarité et fenêtre temporelle comme aide. Un cluster conserve tous les items, fournisseurs, timestamps, versions et droits. La similarité ne supprime jamais seule une observation.

- Deux prix de sources différentes restent deux observations.
- Une date d'événement crée des révisions ; l'historique n'est pas écrasé.
- Un fait fondamental se distingue par taxonomie/concept/période/unité/dimensions/filing.
- Les conflits non résolus sont visibles et peuvent bloquer les usages dépendants.
- `ArticleAccess` gouverne stockage, aperçu, résumé, lien et restitution indépendamment.
- L'expiration ou la révocation d'un droit empêche une nouvelle restitution et déclenche le traitement de conservation prévu, sans falsifier l'historique d'audit.

## Fraîcheur, couverture et classement

- Chaque champ sélectionné conserve `source_event_ids`, politique appliquée, `as_of`, fraîcheur, qualité, entitlement et éventuel conflit.
- Les TTL sont nommés et dépendants du cas d'usage, de la session et de la famille ; aucune constante globale « fresh ».
- Les collections publient attendu/reçu/valide/retardé/périmé/manquant, ratio de couverture et âge maximal.
- Le rang de pertinence expose ses composantes et raisons. Une source payante ou populaire n'obtient pas un bonus opaque.
- La personnalisation utilise seulement portefeuille manuel, thèses, watchlists et historique Vertex autorisé ; aucune donnée de compte broker.
- L'IA peut résumer après le cluster déterministe via `AI_GATEWAY.md`, jamais modifier appartenance, vérité, rang, couverture ou droit.

## Tests obligatoires

- Contrats : chaque famille valide ses unités, identités, timestamps, droits, version et `DataEnvelope`.
- Identité : changement de ticker, même symbole sur deux exchanges, ADR/action, ETF/action homonymes, option multi-`tradingClass` et identifiant expiré.
- Déduplication : identifiant exact, URL paramétrée, titres similaires non identiques, traduction, correction tardive, syndication, collision de hash et événement hors fenêtre.
- Conflits : prix divergents, date révisée, unité/devise incompatible, filing amendé, vintage macro et holding ETF absent.
- Droits : headline-only, lien-only, article autorisé puis révoqué, provider indisponible, export manuel et absence d'entitlement.
- Fraîcheur/couverture : ouvert/fermé/DST, live/delayed/frozen/stale/partial, univers incomplet et fallback refusé.
- Classement : raisons décomposables, stabilité à entrées égales, lien direct position/thèse/watchlist, nouveauté et aucun passage d'un item bloqué en qualifié.
- Propriétés : permutation de l'ordre d'arrivée sans changement du résultat déterministe hors politique « latest », idempotence du rejeu et conservation de masse des observations.
- Intégration : ingestion IBKR/TV simulée, PostgreSQL réel, outbox, crash/reprise, mise à jour de politique et reconstruction d'un agrégat.
- Sécurité : HTML/URL/formule CSV hostiles, prompt injection dans headline/article, corps interdit et fuite de données manuelles.
- Charge : rafale news/alerts/scanner, backpressure, cluster populaire massif et requêtes timeline bornées.

## Critères de sortie mesurables

- 100 % des valeurs fusionnées sont retraçables à au moins un `source_event_id`, une politique versionnée, un droit, une qualité et un `as_of`.
- 100 % des capacités configurées affichent un des six statuts canoniques avec `tested_at`, délai et raison ; aucun fallback silencieux dans les tests mutants.
- Le rejeu de 100 000 observations synthétiques produit les mêmes IDs, clusters, révisions, rangs et hashes qu'une ingestion à froid.
- Permuter l'ordre de livraison du corpus golden ne change aucun résultat déterministe, sauf champs explicitement définis par temps d'observation et testés comme tels.
- Zéro suppression physique lors de la déduplication ; chaque cluster restitue l'intégralité des items, sources, versions et droits autorisés.
- Les golden cases de faux amis restent dans des clusters distincts et les duplicatas exacts aboutissent à un cluster unique.
- Tous les conflits critiques restent visibles et bloquent les usages configurés ; aucun vote, moyenne ou IA ne les résout.
- 100 % des listes publient couverture et âge ; aucune liste partielle n'emploie « complet », « tout le marché » ou « live » hors preuve.
- Chaque résultat classé expose au moins une et au plus trois raisons résumées, plus toutes ses composantes dans le détail ; score stable à entrées égales.
- Aucun corps headline-only/link-only n'apparaît dans API, index de recherche, cache IA, logs ou exports.
- p95 lecture d'un snapshot préparé ≤ 250 ms et p99 ≤ 750 ms sur le jeu de référence ; réconciliation et recherche respectent les budgets documentés.
- Couverture de branches 100 % sur priorités, droits, fraîcheur, conflits et déduplication ; mutation score conforme aux modules critiques.
- Revue humaine de dix clusters, dix événements et cinq ETF confirme provenance, limites, pertinence et absence de scraping/donnée de compte.

