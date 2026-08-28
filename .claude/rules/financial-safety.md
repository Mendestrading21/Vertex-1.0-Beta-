# Sécurité financière — interdictions absolues

Toute violation de ce fichier est critique : arrêter le lot, documenter le chemin découvert et conclure `NO-GO` jusqu’à suppression et preuve par tests.

## Périmètre IBKR strictement informationnel

- Ne jamais créer, prévisualiser, transmettre, modifier, annuler ou simuler un ordre via IBKR.
- Ne jamais appeler ni exposer les API IBKR de compte, résumé de compte, portefeuille, positions, P&L, ordres, exécutions, allocations ou identifiants d’ordre.
- Ne jamais demander un identifiant de compte, lire un compte connecté ni inférer une position depuis TWS.
- Ne jamais ajouter de bouton, route, outil IA, commande ou permission pouvant déclencher une transaction.
- TWS doit être configuré en lecture seule, sur loopback, avec un `client_id` non nul et des permissions minimales.
- Toute découverte d’une méthode interdite définie dans `manifests/forbidden-capabilities.yaml` échoue en CI et bloque la release.

Les seules données IBKR admises sont les informations de marché et de référence explicitement prévues par `docs/04-integrations/IBKR.md` : contrats, cotations, historique, chaîne/options, scanners, news et WSH, sous réserve des droits effectifs.

## Verdict fail-closed

- Une entrée requise absente, partielle, périmée, retardée, future, contradictoire ou sans droit ferme la gate concernée.
- Une exception, un timeout ou une source indisponible ne peut jamais produire `QUALIFIED` ni conserver silencieusement un ancien verdict.
- Aucun défaut ne doit être remplacé par zéro, moyenne, valeur théorique, autre source ou dernier cache sans contrat explicite et étiquette visible.
- `BLOCKED`, `INSUFFICIENT_DATA`, `OBSERVE`, `REVIEW` et `QUALIFIED` sont distincts de la direction `BULLISH`, `BEARISH`, `NEUTRAL`, `MIXED` ou `UNKNOWN`.
- Une probabilité prédictive n’est affichée que si sa calibration, son horizon, sa population, sa validation hors échantillon et sa version sont présents et valides.

## Exactitude et traçabilité

- Argent, primes, strikes et quantités contractuelles utilisent `Decimal` selon le registre de calculs ; aucune conversion flottante silencieuse.
- Unité, devise, multiplicateur, convention de signe et timezone sont obligatoires aux frontières.
- Chaque résultat financier conserve version du calcul, hash des entrées, hypothèses, provenance et instant de calcul.
- Les calculs critiques ont des invariants, tests de propriétés, limites numériques et oracle indépendant.
- Réel, retardé, théorique, simulé et démonstration ne partagent jamais le même statut visuel ou sémantique.

## IA et présentation

- L’IA explique uniquement un DTO validé ; elle ne lit pas directement les sources, ne complète aucune donnée et ne décide pas.
- Pine/TradingView fournit un signal ou un contexte, jamais une vérité d’exécution ni un verdict final.
- Aucun mock, fixture, placeholder ou résultat synthétique ne peut être montré comme réel, live ou issu d’un abonnement.
- Toute action proposée reste une action d’analyse humaine ; ne jamais écrire « acheter », « vendre » ou une instruction d’ordre exécutable.

