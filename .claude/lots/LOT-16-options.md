# LOT-16 — Page Options

## Références et dépendances

- Fiche produit obligatoire : `docs/01-product/pages/06-options.md`.
- Références : `docs/03-domain/CANONICAL_CONTRACTS.md`, `docs/03-domain/UNITS_TIME_AND_PRECISION.md`, `docs/03-domain/DATA_QUALITY.md`, `docs/03-domain/CALCULATION_CATALOG.md`, `docs/04-integrations/IBKR.md`, `docs/05-design/CHART_STANDARD.md`, `docs/05-design/UI_STATES.md` et `docs/06-quality/PERFORMANCE_BUDGETS.md`.
- Dépendances bloquantes : LOT-02 Contrats canoniques, LOT-03 Stockage et qualité, LOT-04 IBKR, LOT-06 Data Fusion, LOT-07 Quant, LOT-09 API/jobs et LOT-10 Design shell.
- LOT-15 Analyse peut fournir le sous-jacent d'entrée ; la route doit aussi fonctionner directement avec un `InstrumentId` valide.

Le lot reste bloqué si l'identité d'un contrat repose sur expiration/strike/right sans `ibkr_con_id`, `trading_class`, multiplicateur, devise et règlement.

## Question à laquelle la page répond

Quels contrats sont réellement exploitables et quels risques portent-ils ?

La route `/options/:underlying` doit rendre la couverture et la liquidité aussi visibles que les prix, sans jamais suggérer ou préparer un ordre.

## Non-objectifs

- afficher une chaîne supposée « complète » sans preuve de couverture ni budget de lignes ;
- fusionner des expirations portant des `trading_class` différentes ;
- recalculer IV, Greeks, parité, spread, smile, skew, structure à terme ou GEX en TypeScript ;
- continuer une valorisation quand une quote nécessaire est stale, crossed, sans droit ou issue d'un ancien `connection_epoch` ;
- télécharger ou abonner toute la chaîne par défaut ;
- fournir bouton d'ordre, preview courtier, compte, position ou capacité d'exécution.

## Contrats, autorité et règles financières

Entrées : `InstrumentId`, `OptionContractId`, `OptionChainSnapshot`, `OptionQuote`, quote du sous-jacent, courbe de taux datée, dividendes, événements, résultats IV/Greeks/surface, couverture, entitlements et `CalculationRecord`.

- Le backend qualifie chaque contrat exact et fournit bid/mid/ask IV, Greeks, spreads, parité, anomalies, liquidité, unités et hypothèses.
- Le frontend ne calcule aucune moyenne bid/ask, IV, Greek, P&L, moneyness, rendement, GEX ou conversion. Tous les résultats financiers arrivent comme DTO générés depuis OpenAPI.
- La date d'expiration n'est jamais une identité. Le groupement sépare au minimum `trading_class`, multiplicateur, règlement, exercice, ajustement et devise.
- GEX est explicitement étiqueté `ESTIMATION`, avec méthode, hypothèses, couverture et limites ; il n'est jamais assimilé à une exposition observée.
- La politique serveur décide quelles lignes demander à IBKR selon fenêtre visible, sélection, cache, priorité et budget. Le navigateur n'appelle jamais IBKR et ne pilote pas directement le pacing.
- Un contrat sans droit produit `NOT_ENTITLED`; delayed, frozen et live restent distincts.
- L'unique action financière apparente est « envoyer au Simulateur », qui transmet une identité exacte et un snapshot, jamais une intention d'ordre.

## Livrables desktop

1. Route `/options/:underlying` avec identité du sous-jacent, marché, quote, session, droits et fraîcheur.
2. Sélecteur expiration + `trading_class`, avec couverture, liquidité et budget de lignes visibles.
3. Chaîne dominante virtualisée Calls / Strikes / Puts, colonnes configurables mais provenance accessible par cellule.
4. `ChartFrame` secondaire smile/skew et structure à terme, uniquement si couverture suffisante.
5. Inspecteur contrat : identité complète, quote, IV, Greeks, hypothèses, anomalies, événement proche et détails de calcul.
6. Sélection bornée d'une ou plusieurs jambes et transfert typé vers le Simulateur, sans ticket d'ordre.
7. Diagnostic pacing/entitlement compréhensible, sans exposer secrets ou configuration sensible.

## Périmètre Vertex 1.0 Beta

- Phase 1 **DESKTOP ONLY** : `1280×800`, `1440×900` et `1600×1000`.
- `1024×768` est une dégradation laptop optionnelle avec table desktop resserrée,
  jamais une variante téléphone.
- Segments mobiles, fiche pleine hauteur, feuilles basses, bottom nav,
  `MobileActionBar`, gestes tactiles et QA `390`/`360` sont `LATER`.
- Les contrats conservent l'identité exacte, `trading_class`, strike, colonnes
  essentielles, hypothèses, anomalies, sélection de jambes et action « Simuler »
  afin que la future UI mobile n'altère aucune sémantique.

## États UI obligatoires

- `loading` : structure de chaîne stable, sans prix factice et sans rafale d'abonnements.
- `refreshing` : lignes précédentes et scroll conservés, âge visible.
- `empty` : aucune expiration/contrat réel avec cause d'identité, marché ou filtre.
- `partial` : couverture reçue/attendue, lignes manquantes et usages encore permis.
- `delayed` : nature exacte delayed/frozen et interdiction d'étiquette live.
- `stale` : snapshot consultable, IV/Greeks non recalculés, envoi au Simulateur exige confirmation ou nouveau snapshot.
- `offline` : chaîne cache en lecture seule ; aucune nouvelle sélection exigeant calcul.
- `error` : expiration ou source fautive isolée ; autres expirations valides préservées.
- `NOT_ENTITLED` : permission manquante et capacité concernée expliquées, jamais assimilées à `empty`.

## Accessibilité, performance et sécurité

- Table virtualisée opérable au clavier, en-têtes Calls/Strikes/Puts correctement associés et fallback borné non virtualisé pour audit lecteur d'écran.
- Signes, libellés et motifs complètent vert/rouge ; focus visible, zoom 200 %,
  cibles interactives suffisantes et aucun hover indispensable.
- Une table accessible accompagne chaque smile/surface ; unités des Greeks, IV et prix sont annoncées.
- Abonnements bornés par fenêtre visible + marge serveur, backpressure avant la limite IBKR et annulation lors d'un changement d'expiration.
- Scroll à 60 FPS sur la fixture de référence ; interaction locale p95 ≤ 100 ms ; snapshot cached API p95 ≤ 250 ms et p99 ≤ 750 ms.
- ECharts est lazy-loadé seulement si la visualisation secondaire est ouverte ; aucun calcul numérique lourd sur le thread UI.
- Aucun module ordre, compte, position ou exécution dans bundle, API cliente, logs ou télémétrie. Les contenus externes sont neutralisés.

## Tests obligatoires

- Unitaires : groupement par identité exacte, rendu des unités, états live/delayed/frozen, couverture et colonnes configurables.
- Contrats : dates dupliquées par `trading_class`, multiplicateurs différents, adjusted options, quote croisée, droit absent et epoch de connexion ancien.
- Backend/propriétés : bornes et conventions Greeks, parité avec tolérance documentée, IV bid≤mid≤ask seulement quand les quotes le permettent, reproductibilité des `CalculationRecord`.
- Virtualisation/pacing : seules les fenêtres autorisées sont demandées, annulation vérifiée, backpressure et saturation simulées sans perte d'état.
- Storybook/visuel : huit états plus `NOT_ENTITLED`, chaîne partielle, contenu
  dense et trois viewports desktop ; `1024×768` en dégradation laptop si utile.
- E2E : changement de `trading_class`, quote crossed, delayed, reconnexion 1100/1101/1102, saturation, sélection multi-jambes et transfert vers Simulateur.
- Architecture/sécurité : recherche statique et test de bundle prouvant l'absence d'endpoint ou type ordre/compte/position/exécution.

## Critères de sortie mesurables

- Deux expirations de même date mais de `trading_class` différente ne partagent jamais lignes, calculs ni cache.
- 100 % des valeurs IV/Greeks affichent méthode, unité, `as_of` et état de qualité accessibles.
- Une donnée stale, crossed, `NOT_ENTITLED` ou d'ancien epoch ne produit aucun nouveau résultat exploitable.
- Le nombre de lignes actives respecte le budget configuré pendant scroll rapide et changement d'expiration.
- Zéro calcul financier en TypeScript et zéro capacité d'ordre/compte/position dans bundle, API et logs.
- Les états UI, les trois viewports desktop, tests de pacing/reconnexion,
  accessibilité, budgets et scans sécurité sont verts ; aucune QA mobile ne bloque
  la Beta.
