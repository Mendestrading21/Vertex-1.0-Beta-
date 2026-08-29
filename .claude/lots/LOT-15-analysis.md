# LOT-15 — Page Analyse

## Références et dépendances

- Fiche produit obligatoire : `docs/01-product/pages/05-analysis.md`.
- Références : `docs/03-domain/CANONICAL_CONTRACTS.md`, `docs/03-domain/DECISION_ENGINE.md`, `docs/03-domain/DATA_QUALITY.md`, `docs/05-design/CHART_STANDARD.md`, `docs/05-design/UI_STATES.md`, `docs/05-design/ACCESSIBILITY.md`, `docs/05-design/RESPONSIVE.md` et `docs/06-quality/PERFORMANCE_BUDGETS.md`.
- Dépendances bloquantes : LOT-02 Contrats canoniques, LOT-03 Stockage et qualité, LOT-04 IBKR, LOT-05 TradingView, LOT-06 Data Fusion, LOT-07 Quant, LOT-08 Décision, LOT-09 API/jobs et LOT-10 Design shell.
- Réutiliser les liens instrument/opportunité de LOT-13 et LOT-14 sans rendre ces pages indispensables au chargement direct de la route.

Le lot ne démarre pas tant qu'un `InstrumentId` ambigu reste résolu silencieusement par symbole. Un conflit d'identité doit être exposé et bloquant.

## Question à laquelle la page répond

Que disent les données certifiées sur cet instrument, et quelles limites restent ouvertes ?

La route `/analysis/:instrument` doit fournir une analyse traçable, centrée sur le prix et ses preuves, sans produire un second avis dans le navigateur.

## Non-objectifs

- ajouter un indicateur parce qu'il est visuellement séduisant ou empiler plus de deux overlays ;
- recalculer niveau, tendance, volatilité, scénario, gate, probabilité ou verdict en TypeScript ;
- traiter une alerte TradingView comme prix de référence ou décision ;
- générer une recommandation avec une IA, inventer une explication ou masquer une contradiction ;
- déclencher un ordre, lire un compte IBKR ou exposer des contrôles achat/vente ;
- recomputer sur un snapshot périmé ou hors ligne.

## Contrats, autorité et règles financières

Entrées minimales : `InstrumentId`, `Bar[]`, `QuoteSnapshot`, `TechnicalSignal`, `NewsCluster`, `CorporateEvent`, `FundamentalFact`, contexte d'exposition manuelle, `AdviceResult`, `GateResult`, scénarios versionnés et enveloppes `DataEnvelope`.

- Le backend livre les séries prêtes à tracer, niveaux, mesures, scénarios, hypothèses, conclusion factuelle et identifiants de `CalculationRecord`.
- Le frontend généré depuis OpenAPI ne fait que sélectionner, afficher et formater. Aucun calcul financier n'est autorisé en TypeScript, y compris rendement, variation, agrégation OHLCV, conversion de devise, volatilité ou interpolation.
- Un `AdviceResult` conserve `as_of`, `valid_until`, version moteur, limites, preuves et résultat de chaque gate. Expiré, il reste historique et n'est jamais présenté comme actuel.
- Une alerte Pine expose script, version, timeframe, heure de barre et état de repaint ; elle reste une preuve secondaire distincte de la quote IBKR.
- Chaque scénario baissier, neutre ou haussier est livré par l'API avec hypothèses, horizon, déclencheurs, invalidation, unité et provenance. L'UI ne lui attribue aucune probabilité implicite.
- Toute écriture de thèse est idempotente, révisionnée et séparée du résultat canonique.

## Livrables desktop

1. Route `/analysis/:instrument` avec en-tête instrument, marché, devise, session, qualité et fraîcheur.
2. Carte compacte `AdviceResult` montrant statut, direction, horizon, validité, gates, limites et lien vers preuves.
3. `ChartFrame` Lightweight Charts dominant : chandeliers, volume, deux overlays maximum, annotations et sélecteurs bornés.
4. Rail de preuves structuré en actualités, événements, fondamentaux, signaux techniques et contradictions ; aucune timeline décorative sans données.
5. Comparaison des trois scénarios, avec hypothèses et invalidations lisibles sans le graphique.
6. Création/mise à jour d'une thèse, avec aperçu de la révision avant enregistrement.
7. Alternative tabulaire OHLCV, résumé textuel, export autorisé et attribution TradingView visible conformément à la licence Lightweight Charts.

## Périmètre Vertex 1.0 Beta

- Phase 1 **DESKTOP ONLY** : `1280×800`, `1440×900` et `1600×1000`.
- `1024×768` peut servir de dégradation laptop contrôlée si utile ; il ne crée ni
  navigation ni interaction mobile.
- Les variantes téléphone, plein écran tactile, accordéons mobiles, feuilles basses,
  bottom nav, `MobileActionBar` et QA `390`/`360` sont `LATER` et non bloquantes.
- Les contrats sémantiques conservent instrument, état, source, `as_of`, avis,
  preuves, scénarios, brouillon et alternative OHLCV pour permettre l'adaptation
  future sans divergence de vérité.

## États UI obligatoires

- `loading` : squelette stable du cadre, sans chandeliers fictifs.
- `refreshing` : snapshot précédent conservé avec son heure.
- `empty` : cause précise — aucun historique, instrument non résolu ou période sans séance.
- `partial` : couverture, preuves ou séries manquantes listées ; gates reçues respectées.
- `delayed` : délai exact, badge source et absence du mot « live ».
- `stale` : watermark sur graphique et avis, `valid_until` visible, tout recompute bloqué.
- `offline` : dernier snapshot consultable et brouillon de thèse local ; aucun nouveau calcul.
- `error` : module fautif isolé, autres preuves et dernier snapshot valides préservés.

## Accessibilité, performance et sécurité

- WCAG 2.2 AA, focus visible/restauré, zoom 200 %, réduction des animations et aucun contenu essentiel au hover ou à la couleur.
- `ChartFrame` fournit titre, conclusion, unité, devise, timezone, période, source, couverture, méthode, limites et table équivalente.
- Navigation clavier du graphique vers la table et les preuves ; annonces non bavardes lors d'un refresh.
- Lightweight Charts est chargé uniquement sur cette route et absent du bundle initial.
- Snapshot préparé : API p95 ≤ 250 ms et p99 ≤ 750 ms ; interaction locale p95 ≤ 100 ms ; pan/zoom ordinaires à 60 FPS sur la fixture de référence.
- La décimation éventuelle est serveur/worker, enregistrée et déclarée ; jamais de suppression silencieuse de points côté client.
- Les titres, URLs et contenus externes sont neutralisés ; aucun secret, payload brut, compte ou donnée sensible dans DOM, logs et télémétrie.

## Tests obligatoires

- Unitaires : mapping DTO→séries, attribution, unités, formatage des timestamps, limite de deux overlays et absence de dérivation financière.
- Contrats : identité ambiguë, `AdviceResult` expiré, gate bloquante, Pine versionné, scénarios sans probabilité implicite et décimaux sous forme de chaînes.
- Propriétés/backend : niveaux et scénarios référencent un `CalculationRecord` reproductible ; invariants OHLC et tri temporel.
- Storybook/visuels : huit états, données denses/rares, textes longs, trois
  viewports desktop et thèmes Black Glass ; `1024×768` seulement si utile comme
  dégradation laptop.
- E2E Playwright Chromium/Firefox/WebKit : contradiction, alerte Pine, cluster de news, gate bloquante, sauvegarde de thèse, stale et offline.
- Accessibilité : table OHLCV équivalente, navigation clavier, lecteur d'écran et absence de dépendance à la couleur.
- Sécurité : URL externe hostile, texte fournisseur, paramètres de route invalides et vérification qu'aucune capacité d'ordre/compte n'entre dans le bundle.

## Critères de sortie mesurables

- 100 % des valeurs financières visibles exposent unité, source ou calcul, et `as_of` accessible.
- Zéro calcul financier, conversion ou second verdict en TypeScript, confirmé par revue et tests architecturaux.
- Un avis expiré/delayed/stale ne peut déclencher aucun recalcul qualifié côté client.
- Les trois scénarios conservent hypothèses et invalidations ; toute contradiction reste visible.
- La table accessible contient exactement les OHLCV rendus par le graphique après sélection serveur.
- Les huit états UI, les trois viewports desktop, budgets, tests E2E,
  accessibilité et sécurité sont verts ; aucune QA mobile ne bloque la Beta.
- Attribution Lightweight Charts et notices tierces validées avant merge.
