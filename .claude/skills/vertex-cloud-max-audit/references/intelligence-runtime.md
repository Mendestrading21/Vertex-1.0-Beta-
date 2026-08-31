# Audit de l'intelligence et du runtime

## Chaîne d'autorité

Pour chaque capacité, remplir une ligne par maillon avec : fichier/symbole,
producteur, consommateur, test, état de réalisation, état de données, seuil de
fraîcheur, comportement d'abstention et défaut.

Capacités minimales :

- identité instrument, temps, unités et précision ;
- quotes, barres, volumes, scanners et entitlements ;
- options : chaîne, contrat, IV, Greeks, spread, OI, volume, liquidité, scénarios ;
- marché, breadth, régime, secteur, corrélations et anomalies ;
- actualités, earnings, calendrier, macro, fondamentaux et signaux sociaux ;
- portefeuille manuel, risque, concentration et performance ;
- opportunités, pertinence, dédoublonnage, contradictions et graphe de preuves ;
- simulation théorique, suivi de thèse et post-analyse ;
- gates, risque/rendement, verdict, abstention, raisons et explication IA.

## Calculs et décisions

- Recouper `CALCULATION_REGISTRY.yaml`, documentation, implémentation, exports,
  appelants runtime et tests oracle/propriétés/limites.
- Vérifier qu'aucun calcul faisant autorité n'est reproduit en TypeScript.
- Distinguer score descriptif, confiance de données, probabilité implicite,
  fréquence empirique et probabilité prédictive.
- Vérifier unités, devise, multiplicateur, calendrier, timezone, arrondi,
  dividende, taux, coûts, données manquantes, NaN/infini et bornes.
- Toute gate non évaluable doit bloquer ou conduire à l'abstention ; aucun score
  ne compense une gate bloquante.
- Vérifier qu'il existe un seul `AdviceEngine` et que l'IA ne calcule ni ne
  modifie le verdict.

## Intelligence réellement active

Chercher pour chaque moteur annoncé : définition, entraînement éventuel,
artefact/version, chargement, appelant, feature availability point-in-time,
sortie, calibration, monitoring, fallback, test et affichage. Classer comme
`PLANIFIÉ` tout moteur seulement décrit dans les documents.

Inspecter particulièrement : régime/secteur, anomalies, flux options, fusion de
signaux, attention/relevance, actualités/social, calibration, walk-forward,
drift, explicabilité et risque modèle.

## Boucle d'amélioration sûre

Vertex peut apprendre de son historique seulement hors runtime : journal
append-only des observations, snapshot de décision, action humaine, résultat et
contexte ; labels point-in-time ; séparation train/validation/holdout ; purge et
embargo ; comparaison à une baseline ; calibration ; tests par régime ; coûts ;
model registry ; shadow mode ; approbation humaine ; canary ; monitoring ;
rollback.

Interdire l'auto-promotion, l'auto-modification du code, le réentraînement sur
les propres prédictions non vérifiées et toute adaptation qui change un verdict
live sans version, preuve et approbation. Vérifier l'absence de fuite de cible,
biais de survivant, look-ahead, data snooping et boucle de confirmation.

## Données et intégrations

- IBKR : allowlist market-data-only, denylist compte/ordre, loopback, client ID,
  pacing, reconnexion, annulation des abonnements de données, droits, delayed,
  `NOT_ENTITLED`, horloge et sonde dry-run/persist.
- TradingView : schéma signé/versionné, idempotence, anti-rejeu, limites,
  déduplication et `REEVALUATE` seulement ; aucun prix/verdict canonique.
- Sources externes : droits, licence, rétention, attribution, quota, coût,
  timezone, corrections et fallback explicite.
- Dépôt : rechercher données de marché réelles, identifiants broker, réponses
  fournisseur et captures sensibles dans fixtures, tests, docs et historique.
  Les vecteurs de test doivent être synthétiques et clairement inventés ; une CI
  verte ne prouve pas ce contrôle si aucune porte ne le balaie.
- PostgreSQL : migrations, contraintes, append-only, outbox, concurrence,
  sauvegarde/restauration, moindre privilège et redaction.
- API/UI : schéma OpenAPI, compatibilité, cache, timeout, cancellation,
  pagination, backpressure et propagation des états.

## Exploitation

Auditer démarrage/arrêt coordonné, prévol, variables d'environnement, exemples
sans secrets, health/readiness, logs structurés, métriques, traces, IDs de
corrélation, budgets de latence, bundle, requêtes N+1, cache, chaos, reprise,
backup/restore, dépendances épinglées, SBOM, vulnérabilités et runbooks.

Toute validation nécessitant le poste doit devenir une recette locale bornée :
préconditions, commande, résultat attendu, données non sensibles à conserver et
rollback. Ne jamais demander à l'utilisateur de coller un secret dans le chat.
