# LOT-02 — Contrats, identité, unités et temps

## Dépendances et préconditions

- Dépendance bloquante : LOT-01 fusionné, CI minimale verte et protections prouvées.
- Branche d'exécution : `lot/02-contracts-identity` depuis le commit sain de LOT-01.
- LOT-00 reste normatif pour la migration et la Constitution.
- Les contrats de ce lot deviennent l'autorité commune des lots 03 à 24 ; une ambiguïté non résolue bloque la sortie.

## Objectif

Implémenter et publier les contrats canoniques versionnés, l'identité exacte des instruments et options, ainsi que les règles d'unité, précision et temps. Les schémas générés doivent distinguer absence, zéro, retard, qualité et nature de la donnée sans dépendre d'IBKR, TradingView, PostgreSQL, FastAPI ou React.

La preuve principale attendue par la feuille de route est : schémas versionnés et tests d'identité d'instrument, notamment plusieurs classes d'options partageant une date d'expiration.

## Non-objectifs

- ouvrir une connexion IBKR/TradingView ou interroger un contrat réel ;
- persister les modèles, créer une migration SQL ou une outbox ;
- calculer IV, Greeks, prix, risque, score, probabilité ou verdict ;
- définir les DTO HTTP/OpenAPI finaux ou écrire un type TypeScript métier à la main ;
- résoudre une collision d'identité par heuristique silencieuse ;
- importer une donnée commerciale, personnelle ou issue de l'ancien Vertex.

## Lecture obligatoire

1. `CLAUDE.md`, la Constitution et `docs/99-status/NOW.md` ;
2. `docs/03-domain/CANONICAL_CONTRACTS.md` ;
3. `docs/03-domain/UNITS_TIME_AND_PRECISION.md` et `DATA_QUALITY.md` ;
4. `docs/00-foundation/GLOSSARY.md` ;
5. `docs/02-architecture/MODULE_BOUNDARIES.md` et `DATA_FLOW.md` ;
6. `docs/04-integrations/SOURCE_CAPABILITY_MATRIX.md`, `IBKR.md` et `TRADINGVIEW.md` pour les champs d'identité seulement ;
7. `docs/06-quality/TEST_STRATEGY.md`, `TEST_MATRIX.md` et `CI_GATES.md` ;
8. `docs/07-delivery/DEPENDENCY_MATRIX.md` et `DEFINITION_OF_DONE.md` ;
9. `docs/09-adr/001-modular-monolith.md`, `003-python-financial-authority.md`, `004-ibkr-information-only.md`, `005-tradingview-ingress.md` et `010-testing.md`.

## Livrables

1. Modèles Pydantic v2 stricts, immuables et versionnés pour toutes les familles listées dans `CANONICAL_CONTRACTS.md`.
2. Énumérations canoniques fermées : classes d'actifs, identité, qualité, délai, droits, statuts de calcul/gate/conseil et direction, sans variantes locales concurrentes.
3. `InstrumentId` à validité temporelle et `OptionContractId` exact incluant au minimum `ibkr_con_id`, sous-jacent, expiration, strike, right, multiplier, exchange, currency, `trading_class`, règlement et ajustement éventuel.
4. Résolveur d'identité déterministe retournant `RESOLVED`, `AMBIGUOUS`, `UNRESOLVED` ou conflit explicite avec preuves ; un symbole seul n'est jamais accepté comme identité stable.
5. `DataEnvelope[T]` préservant source, versions, identifiants d'événement, entitlement, horodatages, `as_of`, TTL, qualité, délai, epoch, droits et hash du payload.
6. Types temporels timezone-aware, UTC au repos, timezone exchange/affichage séparée, politique DST/demi-séance/calendrier versionnée.
7. Types et validateurs d'unités : Decimal aux frontières sensibles, ratios décimaux, devise/multiplicateur explicites, float64 limité aux modèles numériques et tolérances déclarées.
8. JSON Schemas générés de manière déterministe depuis l'autorité Python, registre de schémas/version/compatibilité et exemples synthétiques valides/invalides.
9. Contrôle de dérive garantissant que schémas et éventuels types consommateurs sont générés, jamais maintenus comme une seconde définition.
10. Golden fixtures synthétiques couvrant actions, ETF, indice, options, devises, collisions, symboles réutilisés et révisions temporelles.
11. Documentation des règles d'évolution : ajout compatible, rupture avec nouvelle version, dépréciation, conservation des anciennes enveloppes et aucun champ réinterprété en silence.

## Étapes d'exécution

1. Vérifier la preuve de LOT-01, l'état Git, les locks et les frontières ; passer `NOW.md` à `running`.
2. Établir une table exhaustive `concept → propriétaire → modèle → schéma → exemples → consommateurs futurs` et arrêter sur tout doublon d'autorité.
3. Implémenter d'abord les primitives : identifiants opaques, versions, timestamps, Decimal sérialisé, devises, unités, enums et erreurs typées.
4. Implémenter `InstrumentId`, `OptionContractId`, relations émetteur/instrument et intervalles de validité, sans résolution réseau.
5. Implémenter le résolveur sur mappings explicites ; conserver candidats et raisons lors d'une ambiguïté, sans choix automatique par symbole.
6. Implémenter `DataEnvelope[T]`, puis les contrats de marché, information fusionnée, portefeuille manuel, calcul, gates et `AdviceResult` décrits par la spécification.
7. Générer les JSON Schemas et exemples depuis les modèles. Normaliser ordre, titres et métadonnées pour obtenir des diffs reproductibles.
8. Écrire tests unitaires, propriétés, golden vectors, compatibilité et tests négatifs avant d'étendre les consommateurs.
9. Ajouter les contrôles statiques interdisant timestamp naïf, nombre non fini, valeur sentinelle, compte IBKR, ordre/exécution et modèle concurrent.
10. Exécuter toutes les gates, vérifier un checkout propre, mettre à jour documentation/statut et produire la preuve sans commencer le stockage.

## Tests obligatoires

### Identité

- deux instruments partageant un symbole mais différant par exchange/devise restent distincts ;
- un symbole réutilisé après un intervalle de validité ne modifie pas l'identité historique ;
- un mapping fournisseur absent produit `UNRESOLVED`, plusieurs candidats `AMBIGUOUS`, jamais le premier résultat ;
- deux options de même sous-jacent, expiry, strike et right mais de `trading_class` ou multiplier différents ont des identités distinctes ;
- le même `ibkr_con_id` ne peut représenter simultanément deux identités actives incompatibles ;
- égalité, hash, sérialisation et round-trip sont stables.

### Unités, précision et temps

- absence, chaîne vide interdite et zéro valide sont distingués ;
- prix et montants franchissent JSON comme chaînes décimales sans perte ;
- ratio `0.253` ne devient ni `25.3` ni une chaîne formatée dans le domaine ;
- `NaN`, infini, `-0`, timestamp naïf et timezone manquante sont rejetés ;
- DST, heure ambiguë/inexistante, demi-séance, jour férié et passage de date exchange/UTC sont couverts par fixtures versionnées ;
- conversion de devise, multiplicateur et unité implicite échoue.

### Schémas et compatibilité

- chaque modèle possède schéma, exemple valide, au moins un exemple invalide pertinent et round-trip JSON ;
- génération répétée produit un diff vide ;
- champs requis, enums, formats et `additionalProperties` suivent la politique stricte ;
- changement compatible et rupture volontaire sont détectés par les tests de compatibilité ;
- `AdviceResult` n'accepte aucun champ d'ordre et sépare `status`, `direction`, confiance descriptive et preuve de probabilité ;
- `DataEnvelope` ne peut être déclaré live ou valide sans métadonnées obligatoires cohérentes.

### Frontières et couverture

- le package contrats n'importe ni FastAPI, SQLAlchemy, IBKR, Cloudflare, React, IA ou persistance ;
- 100 % des branches des contrats critiques, validateurs d'identité et temps sont couvertes ;
- tests de propriétés recherchent collisions, round-trips, bornes Decimal et ordre temporel ;
- tous les tests utilisent des identifiants et données synthétiques.

## Sécurité et garde-fous

- Aucun champ `ibkr_account_id`, ordre, exécution, P&L courtier, token ou secret n'est accepté par les contrats. Les `PositionLot` permis restent exclusivement manuels.
- Les identifiants fournisseur sont opaques, validés et jamais interpolés dans un chemin, une requête ou un log.
- Les tailles de texte, collections et payloads ont des bornes raisonnables documentées pour prévenir l'épuisement mémoire futur.
- Les payloads inconnus sont rejetés ou mis en quarantaine par un appelant futur ; ils ne sont pas tolérés via `extra=allow`.
- Les fixtures ne contiennent ni données de marché réelles, ni export privé, ni identifiant de compte.
- Les erreurs de validation n'incluent pas le payload complet et permettent une redaction ultérieure.
- Aucun paquet de données, calendrier ou taxonomie à licence non vérifiée n'entre dans ce lot.

## Critères de sortie mesurables

- 100 % des familles de `CANONICAL_CONTRACTS.md` ont une autorité Python, un schéma versionné et des exemples de test.
- 0 modèle métier TypeScript écrit à la main et 0 seconde enum pour un concept canonique.
- 100 % des branches critiques d'identité, contrats, unités et temps sont couvertes ; aucune propriété critique n'échoue.
- 0 collision silencieuse dans la matrice instrument/option ; tous les cas ambigus restent explicitement non résolus.
- 0 timestamp naïf, nombre non fini, conversion implicite, valeur sentinelle ou confusion absence/zéro accepté.
- Génération des schémas répétée deux fois avec diff Git vide et hashes identiques.
- 0 import de framework/adaptateur/persistance dans le domaine des contrats.
- CI contrats, Python qualité, architecture, sécurité et supply chain verte.
- Revue humaine des contrats `InstrumentId`, `OptionContractId`, `DataEnvelope`, `GateResult` et `AdviceResult` obtenue avant `done`.

## Format de preuve de fin de lot

```text
LOT : 02 — Contrats, identité, unités et temps
ÉTAT : done | review | blocked
BRANCHE / COMMIT : lot/02-contracts-identity / <sha>
DÉPENDANCE : LOT-01 <sha fusionné + CI>
MODÈLES / SCHÉMAS : <n>/<n> ; exemples valides <n> ; invalides <n>
IDENTITÉ : collisions testées <n> ; ambiguïtés explicites <n> ; résolutions silencieuses 0
GÉNÉRATION : run 1 <hash> ; run 2 <hash> ; diff <vide/non vide>
TESTS : <commande exacte> → <exit code, durée, tests, couverture>, une ligne par gate
SÉCURITÉ : capacités interdites <résultat> ; données réelles <résultat> ; secrets <résultat>
FICHIERS MODIFIÉS : <nombre + chemins principaux>
RISQUE RESTANT : aucun | <risque concret>
BLOCAGE : aucun | <un seul blocage actionnable>
ROLLBACK : retour au commit LOT-01 <sha> ; aucun stockage à migrer
PROCHAINE COMMANDE : AUDITE LOT 02
```

Joindre le rapport de compatibilité, les hashes de schémas, les contre-exemples Hypothesis éventuels et la matrice d'identité. Une revue visuelle d'un JSON n'est pas une preuve de compatibilité.
