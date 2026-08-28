# LOT-14 — Page Opportunités

## Références et dépendances

- Fiche produit obligatoire : `docs/01-product/pages/04-opportunities.md`.
- Références : `docs/03-domain/DECISION_ENGINE.md`, `docs/03-domain/PROBABILITY_CALIBRATION.md`, `docs/03-domain/DATA_QUALITY.md`, `docs/04-integrations/DATA_FUSION.md`, `docs/05-design/ACCESSIBILITY.md` et `docs/06-quality/TEST_STRATEGY.md`.
- Dépendances bloquantes : LOT-02 Contrats canoniques, LOT-03 Stockage et qualité, LOT-04 IBKR, LOT-05 TradingView, LOT-06 Data Fusion, LOT-07 Quant, LOT-08 Décision, LOT-09 API/jobs et LOT-10 Design shell.

## Objectif

Livrer `/opportunities`, une table virtualisée qui sépare sans ambiguïté les candidats qualifiés des candidats exclus et permet d'ouvrir une analyse approfondie avec les gates, preuves, informations et événements associés.

Vertex 1.0 Beta est **DESKTOP ONLY** : `1280×800`, `1440×900` et `1600×1000`.
`1024×768` est un contrôle de dégradation laptop optionnel. Les cartes, feuilles
et interactions téléphone sont `LATER` ; statut, raison, source et âge restent dans
les contrats sémantiques.

## Non-objectifs

- créer un score frontend, un classement IA ou une probabilité non calibrée ;
- laisser un candidat `BLOCKED` ou `INSUFFICIENT_DATA` dans la section qualifiée ;
- masquer une exclusion, un conflit d'identité ou un défaut de liquidité ;
- exécuter un ordre ou présenter un bouton d'achat/vente ;
- charger toutes les lignes IBKR en abonnement live simultané.

## Livrables attendus

1. Route `/opportunities`, barre unique recherche/univers/filtres et URL partageable sans donnée sensible.
2. Table TanStack Table/Virtual qualifiés/exclus avec raison principale et fraîcheur.
3. Comparaison limitée à deux ou trois candidats.
4. Rail de `GateResult`, événements, news et preuves avec provenance par colonne.
5. Mode de densité desktop compact à `1280×800` et détail dans un `SideSheet`.
6. Stories, fixtures massives synthétiques et suite de tests complète.

## Contrats et autorité

Entrées : `ScannerResult`, imports screener TradingView, `AdviceResult`, `GateResult`, mesures de liquidité, événements, `NewsCluster`, fondamentaux et état d'identité.

- Le serveur fournit qualification, ordre canonique, score éventuel, version et décomposition.
- Une porte est évaluée avant le rang ; le frontend n'a aucun fallback permissif.
- Une probabilité n'est rendue que si `probability_evidence` satisfait le contrat de calibration.
- Chaque cellule traçable conserve source, `as_of` et identifiant de calcul.

## Interface et états

- `loading` : lignes squelettes et en-têtes stables.
- `refreshing` : sélection et scroll conservés.
- `empty` : répartition des raisons d'exclusion, jamais faux « aucun marché ».
- `partial` : colonnes/couverture manquantes annoncées et gates respectées.
- `delayed` : délai par ligne/source.
- `stale` : ordre figé, aucun reranking, watermark.
- `offline` : snapshot en lecture seule.
- `error` : dernière liste valide et diagnostic de l'enrichissement fautif.

Desktop phase 1 : la table, ses filtres et le détail conservent instrument, statut,
raison, source et âge aux trois viewports. Bottom nav, cartes téléphone et feuille
basse ne sont pas implémentés ; `Mobile UI = LATER`.

## Tests obligatoires

- Unitaires : séparation qualifié/exclu, rendu gates, probabilité absente si preuve insuffisante.
- Contrats : statut inconnu rejeté, conflit `InstrumentId`, score/version et preuves.
- Storybook : huit états, 0/1/10 000 lignes et contenu long.
- E2E : import TradingView, scanner IBKR, conflit d'identité, gate bloquante, stale et comparaison.
- Virtualisation : focus, sélection et position conservés lors d'un refresh.
- Sécurité : paramètres URL allowlistés, texte externe échappé, aucun identifiant de compte.

## Performance, sécurité et accessibilité

- Fixture 10 000 lignes : scroll ordinaire à 60 FPS sur la machine de référence et filtre local p95 ≤ 100 ms.
- Snapshot préparé p95 API ≤ 250 ms ; pagination/virtualisation sans surabonnement de source.
- Aucun moteur graphique dans le chunk de route hors sparklines internes.
- Table opérable au clavier, en-têtes annoncés, focus visible et fallback non virtualisé de taille bornée pour audit lecteur d'écran.
- Zéro violation axe critique/sérieuse ; WCAG 2.2 AA et zoom 200 %.

## Critères de sortie mesurables

- Zéro candidat `BLOCKED` ou `INSUFFICIENT_DATA` dans « Qualifiés » sur tests de contrat et E2E.
- 100 % des lignes affichent statut, raison principale, fraîcheur et provenance accessible.
- Aucune probabilité sans `probability_evidence` valide.
- Virtualisation sans perte de focus sur 10 000 lignes et les trois viewports
  desktop passe ; `1024×768` est vérifié seulement si utile comme dégradation
  laptop.
- Les huit états UI et scénarios de la fiche sont couverts.
- Revue humaine confirmant l'absence d'ordre, de score client et de fallback fail-open.
