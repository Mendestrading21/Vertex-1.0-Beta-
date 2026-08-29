---
name: vertex-one
description: Construire, migrer, auditer et valider Vertex One, logiciel local d'intelligence de marché en lecture seule pour actions, ETF et options, avec IBKR market-data-only, TradingView déclencheur, portefeuille manuel, calculs Python et interface Black Glass.
---

# Vertex One — skill maître

## Mission

Faire converger le nouveau dépôt vers une aide à la décision traçable, rapide,
accessible et honnête. Exploiter les capacités saines de l'ancien dépôt après
preuve, sans importer sa dette, son monolithe ni une seconde autorité métier.

## Ordre des autorités

1. sécurité, vie privée et droits de données ;
2. identité, temps, unités, qualité et provenance ;
3. contrats et calculs Python ;
4. moteur de décision et abstention ;
5. continuité des données locales ;
6. performance et observabilité ;
7. accessibilité et système visuel.

Un document historique ne prime jamais sur le code courant, les tests, un ADR
accepté ou une mesure reproductible.

## Frontières absolues

- analyse seulement ; aucun ordre live ou paper ;
- aucune lecture IBKR de compte, solde, cash, NAV, positions, P&L, ordres,
  exécutions ou transactions ;
- portefeuille Vertex uniquement manuel ;
- Vertex 1.0 Beta est **DESKTOP ONLY** : QA aux viewports `1280×800`,
  `1440×900` et `1600×1000`, avec `1024×768` comme dégradation laptop
  optionnelle ; aucune UI mobile, bottom nav, `MobileActionBar` ou QA `390`/`360` ;
- `Mobile UI = LATER` sans supprimer des contrats la sémantique des états, de la
  provenance, du risque, du contenu et des actions ;
- aucun scraping IBKR ou TradingView ;
- TradingView déclenche une réévaluation, IBKR revalide les observations ;
- un seul moteur Python possède les calculs et le statut canonique ;
- l'IA explique un packet validé et sourcé, sans calculer ni modifier le verdict ;
- une probabilité non calibrée n'est pas affichée ;
- `INSUFFICIENT_DATA` et `UNKNOWN` sont des résultats normaux ;
- aucun secret, identifiant broker ou donnée personnelle dans Git, logs,
  captures, télémétrie ou prompts.

## Sélection du mode

- `plan` : lire constitution, ADR, état et lot ; aucune écriture.
- `donor` : lire `docs/07-delivery/DONOR_EXTRACTION_PROTOCOL.md` et la matrice
  actuelle ; produire une vague `KEEP / ADAPT / REWRITE / REFERENCE / DROP`.
- `data` : lire contrats, qualité, fusion, droits, IBKR et TradingView.
- `quant` : lire registre des calculs, anomalies, fusion, validation et risque
  modèle.
- `options` : lire profils, flux options, registre de features et OCC/IBKR.
- `interface` : lire design, icônes, widgets, pages, accessibilité et budgets.
- `performance` : lire hot paths, latence, observabilité et tests de charge.
- `qa` : lire stratégie de test, CI, sécurité, release et rollback.

Charger uniquement les références du mode, plus les frontières transversales.

## Baseline obligatoire

Avant toute écriture :

1. relever dépôt, branche, HEAD, dirty state, PR/CI et worktrees ;
2. exécuter les contrôles non mutants du lot ;
3. inventorier propriétaires, appels, consommateurs, tests et données ;
4. distinguer `REAL`, `PARTIAL`, `DEGRADED`, `MISSING`, `NOT_ENTITLED`,
   `UNSUPPORTED` et `UNKNOWN` ;
5. écrire le résultat attendu, le rollback et les preuves ;
6. arrêter si un coût, une licence, une donnée personnelle ou une frontière
   financière change.

## Migration du dépôt actuel

Le dépôt `Mendestrading21/Vertex-` est un donneur épinglé en lecture seule. Ne
pas décider fichier par fichier dans le vide : migrer par vague de capacité.

- `KEEP` : code pur/asset exact après licence, frontière et tests.
- `ADAPT` : logique saine portée vers les nouveaux contrats.
- `REWRITE` : comportement utile, implémentation incompatible.
- `REFERENCE` : test, capture ou besoin seulement.
- `DROP` : interdit, mort, dupliqué, généré ou sans provenance.

Une vague passe : inventaire -> tests indépendants -> extraction minimale ->
parité -> mutation tests -> benchmark -> revue -> retrait éventuel. Aucun import
runtime vers le dépôt donneur.

## Exécution par lot

- un seul lot actif ;
- une branche et une PR brouillon par lot ;
- pas de fusion automatique ;
- aucun élargissement silencieux ;
- tout changement financier fournit tests unitaires, propriétés, oracles et cas
  limites ;
- toute page fournit les trois viewports desktop de phase 1, clavier, états
  dégradés et budget ; `1024×768` n'est contrôlé que si utile et la UI mobile ne
  bloque pas la Beta ;
- tout fournisseur fournit droits, entitlements, fraîcheur, limites et fallback ;
- terminer avec faits, tests réellement exécutés, risques restants, rollback et
  une seule prochaine commande.

## Sous-agents

Utiliser les auditeurs de `.claude/agents/` en parallèle pour des inspections
bornées. Ils restent en lecture seule et rendent des preuves ; l'agent principal
arbitre et seul applique les changements du lot.

## Sources officielles Claude Code

Le statut compact pour téléphone et Remote Control concernent exclusivement le
pilotage de Claude Code. Ils ne constituent ni une interface mobile Vertex ni une
voie d'accès Tailscale à l'application.

- skills : https://docs.anthropic.com/en/docs/claude-code/skills
- sous-agents : https://docs.anthropic.com/en/docs/claude-code/sub-agents
- hooks : https://docs.anthropic.com/en/docs/claude-code/hooks
- Remote Control : https://docs.anthropic.com/en/docs/claude-code/remote-control
