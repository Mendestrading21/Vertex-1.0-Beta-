# LOT-12 — Page Calendrier

## Références et dépendances

- Fiche produit obligatoire : `docs/01-product/pages/02-calendar.md`.
- Références : `docs/03-domain/CANONICAL_CONTRACTS.md`, `docs/03-domain/DATA_QUALITY.md`, `docs/04-integrations/SOURCE_CAPABILITY_MATRIX.md`, `docs/05-design/UI_STATES.md`, `docs/05-design/RESPONSIVE.md` et `docs/06-quality/TEST_STRATEGY.md`.
- Dépendances bloquantes : LOT-02 Contrats canoniques, LOT-03 Stockage et qualité, LOT-04 IBKR, LOT-05 TradingView, LOT-06 Data Fusion, LOT-09 API/jobs et LOT-10 Design shell.

## Objectif

Livrer `/calendar`, un agenda chronologique jour/semaine qui distingue clairement les événements macro, résultats, dividendes, expirations, splits, IPO, conférences et filings, puis montre leur relation avec positions manuelles, watchlists et thèses.

Vertex 1.0 Beta est **DESKTOP ONLY** aux viewports `1280×800`, `1440×900` et
`1600×1000`. `1024×768` peut servir de dégradation laptop. La UI mobile est
`LATER` ; les contrats d'événement, l'ordre temporel, les filtres et la provenance
restent sémantiquement prêts pour une adaptation future.

## Non-objectifs

- masquer les limites d'abonnement WSH ou inventer l'importance d'un événement ;
- fusionner une date estimée et une date confirmée ;
- construire une variante téléphone, feuille basse ou navigation mobile pendant
  la phase 1 ;
- effectuer un calcul financier ou une recommandation dans le client ;
- envoyer une notification externe sans consentement et contrat dédiés.

## Livrables attendus

1. Route `/calendar` avec agenda dominant et navigation jour/semaine.
2. Barre de filtres compacte, persistante et accessible.
3. Croisement visuel position/watchlist/thèse sans exposer de compte courtier.
4. Fiche événement avec sources, statut estimé/confirmé, fuseaux et historique de révision.
5. Création d'une note ou alerte locale idempotente.
6. Stories, fixtures synthétiques et tests complets de la page.

## Contrats et autorité

Entrées : `CorporateEvent`, `MacroEvent`, `Filing`, événements WSH normalisés, signaux Pine ciblés, liens `InstrumentId`, `Thesis` et expositions manuelles.

- Le backend résout le fuseau source, exchange et utilisateur et fournit les timestamps UTC plus métadonnées d'affichage.
- L'importance provient de la source ou d'une règle nommée/versionnée.
- Les révisions sont append-only ; l'UI ne remplace jamais silencieusement une ancienne date.
- Les conflits restent visibles et ne sont pas résolus par vote ou IA.

## Interface et états

- `loading` : squelette d'agenda gardant les repères temporels.
- `refreshing` : événements présents conservés.
- `empty` : absence réelle pour la période et les filtres, jamais agenda vide si un droit manque.
- `partial` : fournisseurs, catégories et couverture manquants listés.
- `delayed` : délai annoncé sur les événements concernés.
- `stale` : dernière synchronisation et révisions potentiellement manquantes visibles.
- `offline` : événements déjà chargés consultables ; note en brouillon.
- `error` : panne isolée par source avec les autres événements maintenus.

Desktop phase 1 : agenda chronologique, filtres visibles et fiche événement dans
un panneau accessible. À `1280×800`, la densité peut être réduite sans masquer
date, statut, source ou fuseau. Aucune interaction essentielle n'est drag-only ou
hover-only. La variante téléphone et les feuilles basses sont `LATER`.

## Tests obligatoires

- Unitaires : regroupement, ordre, fuseaux, dates estimées/confirmées et révisions.
- Contrats : événements versionnés, conflit de date et droit absent.
- Storybook : huit états, événements très longs, simultanés et révisés.
- E2E : earnings, macro, expiration, WSH absent, changement DST et création de note.
- Résilience : une source échoue sans vider les autres.
- Sécurité : contenu fournisseur neutralisé, URL sûre, aucune donnée sensible dans une alerte locale.

## Performance, sécurité et accessibilité

- Snapshot préparé p95 API ≤ 250 ms ; changement local de filtre ≤ 100 ms.
- ECharts n'est chargé que si une heatmap secondaire est réellement activée ; l'agenda principal reste HTML sémantique.
- Liste virtualisée seulement au-delà du seuil mesuré, sans casser focus ni lecteur d'écran.
- WCAG 2.2 AA : structure temporelle annoncée, raccourcis non obligatoires, focus restauré et zoom 200 %.
- Zéro violation axe critique/sérieuse et parcours NVDA ou VoiceOver validé.

## Critères de sortie mesurables

- 100 % des événements montrent catégorie, statut, source, heure et fuseau utilisateur.
- Les dates estimées et confirmées ne partagent jamais le même libellé.
- Un droit WSH absent produit `NOT_ENTITLED`, jamais un écran vide.
- Les filtres persistent après navigation et restent opérables au clavier.
- Les huit états UI, les trois viewports desktop et les scénarios E2E de la fiche
  sont verts ; `1024×768` n'est qu'un contrôle laptop optionnel.
- Aucun secret, compte courtier, calcul financier ou verdict n'est présent dans le module.
