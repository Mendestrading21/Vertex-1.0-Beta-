# LOT-17 — Page Simulateur

## Références et dépendances

- Fiche produit obligatoire : `docs/01-product/pages/07-simulator.md`.
- Références : `docs/03-domain/CANONICAL_CONTRACTS.md`, `docs/03-domain/UNITS_TIME_AND_PRECISION.md`, `docs/03-domain/DATA_QUALITY.md`, `docs/03-domain/CALCULATION_CATALOG.md`, `docs/05-design/CHART_STANDARD.md`, `docs/05-design/UI_STATES.md`, `docs/05-design/ACCESSIBILITY.md` et `docs/06-quality/TEST_STRATEGY.md`.
- Dépendances bloquantes : LOT-02 Contrats canoniques, LOT-03 Stockage et qualité, LOT-04 IBKR, LOT-07 Quant, LOT-09 API/jobs, LOT-10 Design shell et LOT-16 Options pour le sélecteur de contrat exact.

Aucune simulation n'est lancée tant que chaque jambe n'est pas reliée à un `OptionContractId` exact et à un snapshot immuable.

## Question à laquelle la page répond

Comment une structure réagit-elle au prix, au temps et à la volatilité ?

La route `/simulator/:id?` doit permettre d'explorer des hypothèses reproductibles sans transformer une simulation en promesse, recommandation ou ticket d'ordre.

## Non-objectifs

- exécuter, prévisualiser ou transmettre un ordre ;
- utiliser un symbole/strike/date incomplet pour identifier une jambe ;
- calculer payoff, breakeven, P&L, coûts, Greeks, surface ou Monte-Carlo en TypeScript ;
- présenter une trajectoire Monte-Carlo comme prévision ou masquer son intervalle d'incertitude ;
- rebaser silencieusement un snapshot stale ;
- afficher des résultats quand les entrées sont invalides, sans unité ou non reproductibles.

## Contrats, autorité et règles financières

Entrées : identités exactes des jambes, sens économique non exécutable, quantité, prix/coût explicite, snapshot options/sous-jacent, taux, dividendes, surface IV, événements, hypothèses, `CalculationRecord` et résultat de simulation versionné.

- Le backend valide la structure, fige `input_snapshot_id`, calcule payoff, coûts, gain/perte max, breakevens, Greeks et sensibilités, puis renvoie les séries prêtes à tracer.
- Le frontend ne somme pas les jambes, ne convertit pas devise/multiplicateur et n'interpole aucune surface. Aucun calcul financier en TypeScript, même comme fallback ou aperçu optimiste.
- Chaque résultat expose méthode, moteur, code SHA, input hash, hypothèses, paramètres, avertissements, unités et date.
- Un calcul Monte-Carlo exige modèle, seed, nombre de chemins, discrétisation, hypothèses, intervalle d'incertitude et diagnostics. À seed et entrées fixes, le résultat sérialisé est déterministe dans la tolérance enregistrée.
- `save` est idempotent et conserve chaque révision ; `rebase` crée un nouveau snapshot et ne remplace jamais l'ancien.
- Les structures « illimitées » restent ainsi nommées ; aucune valeur sentinelle ou plafond graphique n'est affiché comme gain/perte maximum réel.

## Livrables desktop

1. Route `/simulator/:id?` et création depuis zéro ou depuis la sélection exacte de LOT-16.
2. Compositeur de jambes borné, réordonnable au clavier, avec identité, quantité, prix de référence et validation serveur.
3. Panneau d'hypothèses : date d'évaluation, spot, volatilité, taux, dividendes, coûts et conventions, tous attribués.
4. `ChartFrame` ECharts dominant pour payoff ; bascule explicite vers surface spot/temps et sensibilités.
5. Résumé gain/perte max, breakevens, Greeks et avertissements, lié au `CalculationRecord`.
6. Comparaison « snapshot conservé » / « snapshot rebasé » sans mélanger les séries.
7. Sauvegarde, duplication et historique de révisions ; aucune action d'ordre.

## Périmètre Vertex 1.0 Beta

- Phase 1 **DESKTOP ONLY** : `1280×800`, `1440×900` et `1600×1000`.
- `1024×768` est une dégradation laptop optionnelle, sans transformer le
  compositeur en parcours téléphone.
- Plein écran tactile, étapes mobiles, feuilles basses, bottom nav,
  `MobileActionBar` et QA `390`/`360` sont `LATER`.
- Les contrats sémantiques conservent jambes, hypothèses, validation, payoff,
  alternative tabulaire, limites et brouillon afin de préparer cette adaptation
  future sans calcul ni vérité distincte.

## États UI obligatoires

- `loading` : squelette sans valeur de payoff fictive.
- `refreshing` : ancien résultat conservé et daté pendant un recalcul autorisé.
- `empty` : compositeur initial guidé, sans structure présélectionnée arbitraire.
- `partial` : entrées manquantes et calculs impossibles explicités ; aucune valeur partielle présentée comme totale.
- `delayed` : snapshot delayed marqué dans les hypothèses et résultat non qualifié pour un usage live.
- `stale` : choix explicite « conserver » ou « rebaser » ; aucune mutation silencieuse.
- `offline` : simulations sauvegardées consultables, brouillons de jambes possibles, aucun nouveau résultat.
- `error` : validation/calcul isolé, dernier résultat valide préservé avec son hash.
- `invalid_input` : champ, unité, contrat ou hypothèse fautifs annoncés et focusés ; appel quant bloqué si structure invalide.

## Accessibilité, performance et sécurité

- WCAG 2.2 AA, ordre clavier cohérent, focus restauré entre étapes, erreurs associées aux champs, zoom 200 % et réduction des animations.
- Chaque graphique fournit conclusion, unités, hypothèses, méthode, limites, table équivalente et export du résultat, pas des secrets d'entrée.
- ECharts chargé uniquement sur la route ; interactions de curseur p95 ≤ 100 ms et 60 FPS sur la fixture de référence.
- Lecture d'un résultat cached p95 API ≤ 250 ms/p99 ≤ 750 ms ; calcul lourd exécuté hors event loop avec temps et mémoire enregistrés.
- Annulation et déduplication des requêtes de calcul ; aucun recalcul à chaque frappe ou déplacement de curseur.
- Contenus libres neutralisés, IDs opaques non devinables, contrôle d'accès local et aucune donnée compte/ordre dans DOM, API cliente, logs ou télémétrie.

## Tests obligatoires

- Unitaires frontend : composition des DTO d'entrée sans arithmétique, navigation
  du compositeur, erreurs et comparaison de snapshots.
- Contrats : jambe exacte, multiplicateur/devise, snapshots immuables, valeurs illimitées typées, seed et métadonnées de calcul.
- Unitaires/propriétés backend : payoff égal à la somme des jambes et coûts ; symétries/invariants documentés ; aucun NaN/infini/sentinelle dans les DTO.
- Références numériques : expiration, zéro volatilité, temps nul, strikes extrêmes, taux/dividendes, structures multi-jambes et tolérances QuantLib.
- Monte-Carlo : déterminisme à seed fixe, intervalle présent, tests de convergence bornés et cas de ressources maximales.
- Storybook/visuel : huit états plus `invalid_input`, payoff borné/illimité et
  trois viewports desktop ; `1024×768` seulement comme dégradation laptop utile.
- E2E : création, invalid input, stale conserver/rebase, multi-jambes, sauvegarde, duplication, offline et reprise.
- Architecture/sécurité : zéro calcul financier en TypeScript, zéro endpoint d'ordre et contrôle des payloads/logs.

## Critères de sortie mesurables

- Le payoff de chaque fixture égale la somme serveur des jambes et coûts dans la tolérance enregistrée.
- Deux exécutions avec même input hash, moteur et seed produisent le même result hash ou la tolérance versionnée attendue.
- Une simulation stale n'est jamais rebasée sans action explicite et conserve les deux snapshots après rebase.
- 100 % des résultats affichent snapshot, hypothèses, méthode, version, unités, `as_of` et avertissements accessibles.
- Zéro calcul financier en TypeScript et zéro capacité d'exécution dans le module.
- Tous les états, cas limites numériques, trois viewports desktop, budgets,
  accessibilité et scans sécurité passent en CI ; aucune QA mobile ne bloque la
  Beta.
