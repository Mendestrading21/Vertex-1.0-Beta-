# LOT-11 — Page Aujourd'hui

## Références et dépendances

- Fiche produit obligatoire : `docs/01-product/pages/01-today.md`.
- Standards transversaux : `docs/05-design/UI_STATES.md`, `docs/05-design/ACCESSIBILITY.md`, `docs/05-design/RESPONSIVE.md`, `docs/06-quality/PERFORMANCE_BUDGETS.md` et `docs/06-quality/TEST_STRATEGY.md`.
- Dépendances bloquantes : LOT-02 Contrats canoniques, LOT-03 Stockage et qualité, LOT-04 IBKR, LOT-05 TradingView, LOT-06 Data Fusion, LOT-08 Décision, LOT-09 API/jobs et LOT-10 Design shell.

Le lot ne peut être déclaré terminé tant que les DTO consommés sont générés depuis l'OpenAPI et que le shell de LOT-10 expose `DataStateBoundary`, la navigation et les tokens validés.

Périmètre Vertex 1.0 Beta : **DESKTOP ONLY** aux viewports `1280×800`,
`1440×900` et `1600×1000`. `1024×768` est une dégradation laptop optionnelle.
La UI mobile et sa QA sont `LATER`, avec contrats sémantiques conservés.

## Objectif

Livrer `/today`, un briefing lisible en moins de trente secondes, dominé par une file de 8 à 15 éléments réellement prioritaires. La page doit fusionner incidents de données, risques du portefeuille manuel, thèses, événements, informations et opportunités sans créer une nouvelle autorité métier.

## Non-objectifs

- créer un tableau de bord de KPI ou un score opaque ;
- recalculer le rang, la fraîcheur, le régime ou un verdict dans le navigateur ;
- déclencher un ordre, modifier une position IBKR ou transformer une alerte en décision ;
- ajouter une source ou une bibliothèque sans ADR et registre de dépendances ;
- afficher du contenu démo silencieux quand une source réelle échoue.

## Livrables attendus

1. Route `/today` et module de page conforme au shell LOT-10.
2. Bandeau séance/régime/santé, file d'attention dominante, fenêtre 24 heures et expositions concernées.
3. Détail d'un élément dans un `SideSheet` desktop accessible.
4. Provenance, âge, couverture et jusqu'à trois `relevance_reasons` visibles par ligne.
5. Stories et fixtures synthétiques couvrant tous les états et toutes les familles d'éléments.
6. Tests de composants, contrats, accessibilité, E2E et performance associés à la page.

## Contrats et autorité

Entrées minimales : `NewsCluster`, `CorporateEvent`, `MacroEvent`, `PortfolioRisk`, `Thesis`, `AdviceResult`, `SourceHealth` et une enveloppe de briefing contenant classement, couverture et `as_of`.

- L'API fournit l'ordre final et les raisons ; le client ne trie que sur demande explicite de l'utilisateur et ne réécrit jamais la priorité canonique.
- Une ligne conserve ses identifiants de preuve et son `trace_id`.
- Les nombres décimaux restent des chaînes typées jusqu'au composant de formatage.
- Toute action utilisateur est non financière : ouvrir, acquitter, reporter ou suivre.

## Interface et états

- `loading` : squelette de lignes stable, sans faux éléments.
- `refreshing` : briefing précédent visible avec activité discrète.
- `empty` : « rien ne demande votre attention » et périmètre observé.
- `partial` : couverture et familles manquantes explicites.
- `delayed` : âge exact et badge, jamais « live ».
- `stale` : file figée, watermark et calcul dépendant du live bloqué.
- `offline` : dernier briefing daté, lecture et brouillons seulement.
- `error` : modules sains conservés, diagnostic de la source fautive.

Desktop phase 1 : la file et le détail restent lisibles aux trois viewports de
référence ; à `1280×800`, les modules secondaires peuvent passer sous la file sans
perdre provenance, risque ou action. Aucun contenu critique ne dépend d'un hover.
Bottom nav, feuille basse et variante téléphone ne sont pas implémentés ;
`Mobile UI = LATER`.

## Tests obligatoires

- Unitaires : rendu des raisons, ordre reçu, formatage date/unité et absence de retri implicite.
- Contrats : compatibilité de l'enveloppe briefing et rejet d'un état inconnu ou incomplet.
- Storybook : huit états UI, chaque famille d'élément et textes longs.
- E2E Playwright sur Chromium, Firefox et WebKit : incident, news liée à une position, événement, opportunité bloquée et offline.
- Résilience : source news en erreur alors que portefeuille et calendrier restent disponibles.
- Sécurité : titres/URLs non fiables neutralisés, aucune donnée de compte ou secret dans le DOM, logs ou télémétrie.

## Performance, sécurité et accessibilité

- Lecture du snapshot préparé : p95 API ≤ 250 ms et p99 ≤ 750 ms.
- Interaction locale ordinaire ≤ 100 ms ; aucune tâche longue causée par le classement.
- Aucun moteur graphique chargé sur cette route ; bundle initial global ≤ 300 Ko gzip recommandé.
- WCAG 2.2 AA, focus visible/restauré, ordre clavier identique à l'ordre visuel,
  zoom 200 % et cibles interactives suffisantes.
- Les statuts vert/rouge/ambre ont aussi un libellé et un symbole.
- Zéro violation axe critique ou sérieuse ; revue NVDA ou VoiceOver du parcours principal.

## Critères de sortie mesurables

- 8 à 15 éléments affichés par défaut et aucun doublon visible dans un `NewsCluster`.
- 100 % des lignes affichent type, raison principale, source et `as_of`.
- Aucun élément `BLOCKED` n'est présenté comme opportunité qualifiée.
- Les huit états UI ont chacun une story et une assertion E2E ou composant.
- Les trois viewports desktop `1280×800`, `1440×900` et `1600×1000` passent sans
  débordement ni perte d'information ; `1024×768` est contrôlé seulement si utile
  comme dégradation laptop et aucune QA mobile ne bloque la Beta.
- Les budgets performance, tests CI, accessibilité et scans sécurité sont verts.
- Revue humaine confirmant qu'aucun calcul financier, ordre ou second verdict n'existe dans la page.
