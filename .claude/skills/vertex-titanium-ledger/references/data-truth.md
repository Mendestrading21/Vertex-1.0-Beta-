# Vérité des données et des calculs

## Typage obligatoire de toute valeur

Chaque valeur affichée ou exportée doit permettre de répondre à :

- nature : fait réel, historique, manuel, estimation, simulation, théorie,
  démonstration ou indisponible ;
- source et méthode ;
- heure d'observation et heure de réception ;
- fraîcheur et règle qui la détermine ;
- unité, devise, précision et timezone ;
- qualité, couverture, entitlement et exclusions ;
- version du calcul ou du contrat quand la valeur est dérivée.

Une valeur ne doit jamais changer de nature entre le contrat, l'API, le cache,
le navigateur, le graphique, le rapport et l'explication IA.

## Registre central des calculs

Pour chaque calcul financier, l'audit exige :

| Champ | Attendu |
|---|---|
| identifiant/version | stable, versionné, présent dans le résultat |
| propriétaire | module Python unique |
| entrées | types, unités, timezone, qualité et règles d'absence |
| formule/méthode | documentée et non dupliquée côté client |
| arrondi | point d'application et mode explicites |
| sorties | type, unité, bornes et états d'abstention |
| preuve | tests unitaires, propriétés, oracle indépendant, cas limites |
| consommateurs | API, page, rapport et IA identifiés |

Chercher activement les formules dupliquées, conversions implicites, `float`
inadaptés, dates naïves, agrégations locales et valeurs par défaut rassurantes.

## États et absence

Les états `PARTIAL`, `DEGRADED`, `MISSING`, `NOT_ENTITLED`, `UNSUPPORTED`,
`INSUFFICIENT_DATA`, `STALE`, `OFFLINE`, `ERROR` et `UNKNOWN` sont des résultats
normaux. Ils doivent :

1. survivre jusqu'au rendu ;
2. expliquer la cause et la conséquence ;
3. empêcher un verdict positif lorsque la donnée requise manque ;
4. ne jamais être fusionnés silencieusement en `success` ou zéro.

## Intégrations

### IBKR

Autorisé : données de marché prévues par les contrats et les entitlements.
Interdit : compte, solde, cash, NAV, positions, P&L, ordres, exécutions,
transactions, envoi ou prévisualisation d'ordre.

### TradingView

Autorisé : signal entrant authentifié qui déclenche une réévaluation serveur.
Le payload n'est pas automatiquement la vérité affichée. Vérifier signature,
anti-rejeu, idempotence, mapping d'instrument et nouvelle lecture canonique.

### IA

Autorisé : expliquer un packet validé, citer ses faits et ses limites.
Interdit : inventer une source, calculer une nouvelle métrique, modifier un gate,
le verdict ou sa confiance.

## Continuité inter-pages

L'audit suit un même instrument de bout en bout : Marchés -> Opportunités ->
Analyse -> Options -> Simulateur -> Portefeuille -> Graphiques -> Risques ->
Catalyseurs -> Calendrier -> Sources & Rapports. Vérifier que l'identité,
l'horizon, la devise, le fuseau, le `dataAsOf`, le mode, les droits et les états
ne changent pas silencieusement.

## Rapports et exports

Un export garde les mêmes valeurs, unités, libellés d'état, sources, temps,
exclusions et version de calcul que l'écran. Une capture ou un PDF ne peut pas
faire disparaître `fictif`, `simulé`, `retardé`, `incomplet` ou `indisponible`.
