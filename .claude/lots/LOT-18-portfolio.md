# LOT-18 — Page Portefeuille manuel

## Références et dépendances

- Fiche produit obligatoire : `docs/01-product/pages/08-portfolio.md`.
- Références : `docs/03-domain/CANONICAL_CONTRACTS.md`, `docs/03-domain/UNITS_TIME_AND_PRECISION.md`, `docs/03-domain/DATA_QUALITY.md`, `docs/03-domain/CALCULATION_CATALOG.md`, `docs/04-integrations/DATA_FUSION.md`, `docs/05-design/UI_STATES.md`, `docs/05-design/ACCESSIBILITY.md` et `docs/06-quality/TEST_STRATEGY.md`.
- Dépendances bloquantes : LOT-02 Contrats canoniques, LOT-03 Stockage et qualité, LOT-04 IBKR pour les seules données de marché, LOT-06 Data Fusion, LOT-07 Quant, LOT-09 API/jobs et LOT-10 Design shell.

Ce lot gère exclusivement un ledger Vertex manuel. Il est interdit de lire, synchroniser, inférer ou importer comptes, positions, cash, transactions et exécutions IBKR.

## Question à laquelle la page répond

Quelles expositions et concentrations résultent de mon ledger manuel ?

La route `/portfolio` doit expliquer la valorisation et ses limites tout en gardant ledger réel, hypothèses simulées et données de marché strictement séparés.

## Non-objectifs

- connecter un compte courtier ou appeler une API IBKR de compte, portefeuille, position, P&L, transaction, ordre ou exécution ;
- rapprocher automatiquement le ledger d'une position externe ou stocker un identifiant de compte courtier ;
- calculer P&L, coût moyen, cash, allocation, concentration, FX, delta ou risque en TypeScript ;
- modifier rétroactivement un lot sans révision ni audit ;
- fusionner réel et simulé, ou masquer un FX/mark stale ;
- accepter un CSV sans aperçu, validation, détection de doublon et confirmation.

## Contrats, autorité et règles financières

Entrées : `Portfolio`, `PortfolioBaseCurrency`, `PositionLot`, `Transaction`, `CashLedgerEntry`, instruments canoniques, quotes de marché IBKR, taux FX datés, événements/news liés, expositions et `CalculationRecord` serveur.

- Aucun de ces contrats ne contient `ibkr_account_id` ou équivalent. Une vérification de schéma et de code interdit aussi les types/clients compte, position, ordre et exécution.
- IBKR ne fournit ici que quotes/bars/FX ou données d'information autorisées. Le ledger manuel est l'unique source de quantité, coût, cashflow et statut réel.
- Le backend calcule P&L réalisé/non réalisé, valeur, cash, coût, allocations, concentrations, delta et risques à partir d'un snapshot versionné.
- Le frontend ne fait aucune somme, moyenne pondérée, conversion FX, agrégation ou approximation financière. Il affiche les DTO générés depuis OpenAPI et peut seulement filtrer/ordonner les lignes reçues.
- Chaque lot et cashflow est append-only avec correction par révision/contre-écriture, identité stable, provenance `MANUAL` ou `CSV_IMPORT`, et idempotency key.
- Les positions réelles et scénarios simulés utilisent des contrats, routes, couleurs, libellés et agrégats distincts ; aucun total commun par défaut.
- Tout mark et FX expose source, heure, devise, chemin de conversion et statut qualité.

## Livrables desktop

1. Route `/portfolio` avec valeur, cash et P&L attribués, date de valorisation et couverture.
2. Table dominante des positions manuelles : lots, quantité, coût, mark, valeur, P&L, devise et qualité, avec détail dépliable.
3. Concentrations instrument/secteur/devise et exposition delta, calculées serveur et accompagnées d'une alternative tabulaire.
4. Rail de risques, actualités et événements liés aux instruments du ledger.
5. Formulaires ajouter/modifier/clôturer par transaction ou révision, avec aperçu des effets fourni par le backend.
6. Import CSV en trois temps `fichier → aperçu/erreurs/doublons → confirmation`, plus export versionné.
7. Commutateur explicite Réel/Simulé qui ne permet jamais d'agréger les deux silencieusement.

## Périmètre Vertex 1.0 Beta

- Phase 1 **DESKTOP ONLY** : `1280×800`, `1440×900` et `1600×1000`.
- `1024×768` peut être contrôlé comme dégradation laptop, sans créer une vue
  cartes ou un parcours téléphone.
- Fiches pleine hauteur, formulaires mobiles, feuilles basses, bottom nav,
  `MobileActionBar`, gestes tactiles et QA `390`/`360` sont `LATER`.
- Les contrats sémantiques conservent devise, `as_of`, couverture, état FX, lots,
  cashflows, risques, aperçu/erreurs CSV et brouillons non synchronisés pour que
  l'adaptation future garde exactement la même vérité financière.

## États UI obligatoires

- `loading` : structure stable, aucune valeur zéro de remplacement.
- `refreshing` : ledger et valorisation précédents conservés avec leur date.
- `empty` : ledger réellement vide avec action d'ajout/import, jamais conséquence d'une panne de marks.
- `partial` : lots visibles, marks/FX/secteurs manquants et agrégats concernés explicités.
- `delayed` : sources delayed identifiées par ligne et dans les agrégats.
- `stale` : ledger toujours éditable ; valorisation watermarkée et aucun recalcul live implicite.
- `offline` : dernier snapshot en lecture, brouillons locaux non synchronisés et aucune nouvelle valorisation.
- `error` : erreur mark/news/FX isolée ; ledger durable jamais masqué ni détruit.
- `invalid_import` : aucune mutation, aperçu des lignes rejetées, cause et correction possible.

## Accessibilité, performance et sécurité

- Table sémantique opérable clavier, en-têtes/agrégats annoncés, focus
  visible/restauré, zoom 200 %, cibles interactives suffisantes et aucune
  information par couleur seule.
- Les graphiques de concentration sont secondaires, lazy-loadés si nécessaires et toujours doublés d'une table exacte.
- 10 000 lots synthétiques : virtualisation seulement après mesure, scroll 60 FPS et filtre local p95 ≤ 100 ms sans arithmétique financière.
- Snapshot cached API p95 ≤ 250 ms et p99 ≤ 750 ms ; imports/valorisations lourds hors event loop, idempotents et observables.
- Les CSV sont traités comme non fiables : taille/type bornés, parsing sûr, cellules neutralisées à l'export contre l'injection de formule, aucune conservation du fichier brut au-delà de la politique.
- Données locales chiffrées selon le modèle de menace, exports explicites et journaux sans lots complets ni données sensibles.
- Aucun endpoint IBKR compte/position/ordre/exécution, identifiant courtier ou secret dans le code client, DOM, stockage navigateur, logs et télémétrie.

## Tests obligatoires

- Unitaires backend : conservation des lots et cashflows, clôture partielle/totale, frais, dividendes, taxes, transferts, corrections et devise de compte.
- Propriétés : identité comptable, somme des lots, P&L réalisé/non réalisé, cash et conversions FX avec tolérances/version de méthode documentées.
- Contrats : absence d'identifiant courtier, provenance manuelle/import, révisions append-only, séparation réel/simulé et marks/FX datés.
- Unitaires frontend : affichage des DTO sans agrégation, états partiels, distinction réel/simulé et aperçu import.
- Import/export : CSV valide, colonnes inconnues, encodage, décimales locales, doublons, ligne invalide, fichier volumineux, formule malveillante et round-trip documenté.
- Storybook/visuel : neuf états, ledger vide/dense, textes longs, devises et trois
  viewports desktop ; `1024×768` seulement comme dégradation laptop utile.
- E2E : ajout, modification par révision, clôture manuelle, dividende/frais, FX stale, CSV invalide/dupliqué, offline et reprise.
- Architecture/sécurité : test négatif prouvant qu'aucune lecture IBKR de compte/position n'existe ; scans des routes, types, bundles et logs.

## Critères de sortie mesurables

- 100 % des quantités, lots, coûts et cashflows proviennent du ledger manuel ou d'un CSV confirmé, jamais d'IBKR.
- Zéro identifiant de compte courtier et zéro appel compte/position/P&L/ordre/exécution dans serveur, client, tests de production et logs.
- Les lots et cashflows restent reconstituables après ajout, révision, clôture, import et restauration.
- Réel et simulé ne partagent aucun total ni libellé ambigu ; le mode actif est toujours annoncé.
- Chaque valeur/P&L/FX/risque visible expose source ou calcul, devise, unité, qualité et `as_of`.
- Zéro calcul financier en TypeScript, confirmé par revue et tests architecturaux.
- Tous les états UI, cas comptables, imports hostiles, trois viewports desktop,
  budgets, accessibilité et sécurité passent en CI ; aucune QA mobile ne bloque la
  Beta.
