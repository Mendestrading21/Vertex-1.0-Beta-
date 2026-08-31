# Portage de l'ancien Vertex vers la Beta

## Rôles immuables

- `Vertex-1.0-Beta-` est la cible et l'autorité d'architecture.
- `Vertex-` est une source de comportement, de scénarios et d'enseignements.
- Ne jamais fusionner les dépôts, copier un dossier entier, reprendre une base,
  un cache, un secret, une fixture réelle ou rendre le legacy importable au
  runtime de la Beta.

## Preuve par capacité legacy

Tracer séparément : point d'entrée réellement lancé, configuration, producteur
IBKR/TradingView, schéma, persistance, calculs, API, vue, tests et preuve CI.
Rechercher aussi les fallbacks démo, caches anciens, valeurs par défaut,
threads globaux, états mémoire, imports conditionnels, erreurs avalées et routes
qui renvoient un succès malgré une donnée absente.

Pour IBKR, vérifier les appels exacts. Tout accès compte, cash, position, P&L,
ordre, exécution, `whatIf`, annulation ou exercice est `REJETER`, même s'il
fonctionnait. Pour TradingView, ne reprendre qu'un signal authentifié,
versionné, anti-rejeu et limité à `REEVALUATE`. Ne qualifier le flux de
« signé » que si une signature cryptographique du message est réellement
produite et vérifiée de bout en bout ; un secret placé dans le JSON n'est pas
une signature.

## Classification de portage

| Décision | Condition |
|---|---|
| `REPRENDRE` | Reprendre sémantiquement un comportement, test ou invariant compatible ; jamais le fichier source. L'exprimer derrière les contrats Beta. |
| `ADAPTER` | Protocole ou algorithme valable dont le schéma, la concurrence, la provenance ou la dépendance exige une traduction explicite. |
| `RÉÉCRIRE` | Intention utile mais architecture globale, état mémoire, monolithe ou contrat incompatible. N'utiliser que tests de caractérisation et exemples synthétiques. |
| `REJETER` | Frontière financière, sécurité, droit de données, duplication d'autorité, calcul client ou comportement trompeur. |
| `BLOQUÉ` | Validation dépendant du poste, d'un secret, d'un entitlement, d'une licence ou d'une décision humaine. |

## Matrice obligatoire

| Capacité | Legacy chemin:symbole | Preuve legacy | Beta chemin:symbole | Écart de contrat | Décision | Test rouge Beta | Lot |
|---|---|---|---|---|---|---|---|

Une ligne `REPRENDRE` ne signifie jamais copier-coller. Écrire d'abord dans la
Beta un test rouge qui exprime le comportement sans donnée réelle, puis une
implémentation minimale conforme aux contrats, droits, états et observabilité de
la Beta. Comparer les sorties sur un corpus entièrement synthétique ou autorisé.

## Porte anti-régression

Chaque lot de portage doit :

1. rester market-data-only et sans compte/ordre ;
2. conserver la provenance, l'heure, les droits et les états manquants ;
3. ajouter un test contractuel du producteur jusqu'au consommateur Beta ;
4. ne créer aucune seconde autorité de calcul ou de verdict ;
5. mesurer latence, volume, reprise et coût ;
6. prévoir un feature flag, un shadow mode si nécessaire et un rollback ;
7. laisser le legacy inchangé jusqu'à acceptation de la parité.

Avant tout portage, contrôler licence, copyright, notices, provenance et droits
des données. Ne jamais reprendre bundles vendored/minifiés, polices, binaires,
captures, caches ou fixtures legacy ; réinstaller les dépendances depuis leur
source officielle et régénérer locks, SBOM et notices dans la Beta.

Ne supprimer ni archiver l'ancien dépôt dans le même lot que le portage.
