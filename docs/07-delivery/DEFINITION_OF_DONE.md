# Définition universelle de terminé

Un lot n'est terminé que si toutes les affirmations applicables ci-dessous sont prouvées par une commande, un test, une capture ou une revue. « Semble fonctionner » n'est pas une preuve.

## Périmètre et architecture

- objectif, non-objectifs et dépendances du lot respectés ;
- aucun framework, source, calcul ou autorité supplémentaire sans ADR accepté ;
- aucune copie globale du donneur ; chaque extraction est inventoriée,
  attribuée, testée et découplée ;
- contrats, propriétaires et frontières de modules inchangés ou migrés explicitement ;
- aucun `TODO`, mock, fallback ou feature flag critique caché ;
- documentation et `docs/99-status/NOW.md` à jour.

## Données et finance

- source, licence/droit, `observed_at`, `received_at`, unité, devise, qualité et fraîcheur conservés ;
- réel, retardé, estimé, théorique, simulé et démonstration séparés ;
- données absentes, nulles et égales à zéro non confondues ;
- calculs déterministes avec version, hash d'entrée et provenance ;
- 100 % des invariants, portes et transitions de décision critiques explicitement testés ;
- au moins 90 % de branches dans le cœur financier et 80 % ailleurs ;
- tests de propriétés, limites numériques et vecteurs de référence indépendants pour tout calcul sensible ;
- aucun `NaN`, infini, division par zéro ou troncature silencieuse ;
- donnée requise absente, future, partielle, périmée, retardée ou contradictoire ferme la porte concernée ;
- aucune probabilité prédictive affichée sans calibration et validation hors échantillon.

## Intégrations

- idempotence, replay, doublons, données hors ordre, pacing et reconnexion testés ;
- entitlement et couverture visibles ;
- absence de droit signalée sans substitution silencieuse ;
- IBKR reste information-only : aucune capacité ordre, compte, position, P&L ou exécution ;
- TradingView utilise seulement webhook, Pine et exports officiellement permis ; aucun scraping ;
- toute alerte TradingView est revalidée sur une observation IBKR fraîche avant un nouveau verdict.

## API et interface

- OpenAPI et client généré synchronisés ;
- validation stricte des entrées/sorties et compatibilité de schéma testée ;
- états `loading`, `refreshing`, `empty`, `partial`, `delayed`, `stale`, `offline` et `error` couverts ;
- rendu pleinement qualifié à 1280×800, 1440×900 et 1600×1000 ;
- dégradation laptop 1024×768 utilisable, sans vérité financière ni action essentielle masquée ;
- aucun critère d'interface téléphone pour la Beta ; mobile reste `LATER` sur les mêmes contrats canoniques ;
- parcours principal réalisable au clavier ;
- WCAG 2.2 AA, focus visible et zéro violation axe critique/sérieuse ;
- couleur jamais seule porteuse de sens ;
- chaque graphique essentiel a unité, timezone, source, fraîcheur, légende et alternative tabulaire/textuelle ;
- LCP ≤ 2,5 s, INP ≤ 200 ms, CLS ≤ 0,1 sur le scénario de référence ;
- bundle initial ≤ 300 Ko gzip sauf décision documentée ; graphiques lourds chargés à la demande.

## Sécurité et exploitation

- aucun secret ou payload sensible dans Git, logs, fixtures, captures ou erreurs ;
- aucune vulnérabilité critique/haute exploitable non acceptée avec échéance ;
- dépendances, images et Actions épinglées de manière immuable ;
- licences et provenance enregistrées ;
- logs structurés, `trace_id`, métriques de fraîcheur et erreurs observables ;
- sauvegarde et restauration vérifiées lorsqu'une donnée persistée change ;
- comportement de rollback documenté et testé pour migration ou release concernée.

## Livraison

- lint, formatage, types, tests, build, migrations et scans applicables passent depuis un checkout propre ;
- la PR liste commandes, résultats, captures, risques et choix de conception ;
- revue humaine obtenue ;
- aucune fusion automatique et aucun démarrage du lot suivant.
