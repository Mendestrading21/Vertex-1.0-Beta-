# Profils de stratégie Vertex One

## But

Un profil ne prédit pas le marché et ne déclenche aucune transaction. Il décrit
le contexte dans lequel une idée peut être étudiée, les données obligatoires,
les portes de refus, l'horizon de revue et les preuves à conserver. Les valeurs
sont configurables et versionnées ; aucun montant personnel n'est stocké dans
Git.

## Profils initiaux

### `equity_etf_swing_3_12m`

- instruments : actions et ETF liquides ;
- horizon de décision : 3, 6 ou 12 mois ;
- fréquence de revue : hebdomadaire et sur événement ;
- preuves minimales : identité du titre, prix/fraîcheur, liquidité, régime,
  secteur, fondamentaux, calendrier, thèse, invalidation et risque portefeuille
  manuel ;
- sortie analytique (ADR-014) : `BLOCKED`, `INSUFFICIENT_DATA`, `OBSERVE`,
  `REVIEW` ou `QUALIFIED`, jamais `BUY` ou `SELL`.

### `long_option_tactical_2_12w`

- instruments : CALL ou PUT acheté, perte maximale bornée par la prime ;
- durée d'intention : 2 à 12 semaines, avec jalons 2/4/6 semaines ;
- DTE d'entrée préféré : 120 à 240 jours, cible descriptive 180 jours ;
- DTE, delta et moneyness restent des contraintes configurables, jamais des
  nombres silencieusement forcés ;
- portes supplémentaires : spread, profondeur, volume/OI, IV, skew, structure
  par terme, événement avant la revue, cohérence spot/chaîne et qualité des
  Greeks ;
- aucun contrat n'est présenté si la prime, le multiplicateur, la devise, le
  style d'exercice ou l'échéance ne sont pas résolus.

### `long_leaps_directional`

- instruments : CALL ou PUT long ;
- DTE de recherche : 180 à 540 jours ;
- delta de recherche : valeur absolue 0,70 à 0,90 ;
- la prime payée, la valeur temps, le breakeven, le coût d'opportunité et la
  sensibilité IV restent visibles ;
- ce profil n'autorise ni vente nue ni transformation implicite en spread.

## Règles communes

1. IBKR est une source de marché en lecture seule ; le portefeuille Vertex est
   déclaré manuellement.
2. TradingView déclenche une réévaluation. Une alerte ne devient jamais une
   preuve de prix ni un verdict.
3. Une actualité ou un signal social isolé ne qualifie jamais une idée.
4. Un CALL inhabituel n'est pas automatiquement haussier ; un PUT inhabituel
   n'est pas automatiquement baissier.
5. Une probabilité n'est affichée que si elle est hors échantillon, calibrée et
   accompagnée de sa population, de sa fenêtre et de son incertitude.
6. Le moteur s'abstient dès qu'une donnée critique est absente, contradictoire,
   non autorisée, hors distribution ou trop ancienne.
7. Les sorties sont des scénarios conditionnels. L'utilisateur prend seul sa
   décision et agit hors de Vertex.

## Cycle de vie

```text
DRAFT -> VALIDATED -> SHADOW -> ACTIVE -> SUSPENDED -> RETIRED
```

- `VALIDATED` exige schéma, tests unitaires, données point-in-time et protocole
  hors échantillon.
- `SHADOW` calcule sans apparaître dans le flux principal.
- `ACTIVE` exige stabilité, calibration et absence de dérive bloquante.
- tout changement de seuil crée une nouvelle version ; il ne réécrit pas le
  passé.

## Personnalisation locale

Les univers, watchlists, positions déclarées, montants, limites et préférences
restent dans la base locale chiffrée. Le dépôt ne contient que des profils
génériques. L'interface doit montrer la version exacte du profil appliqué et
permettre de comparer le résultat avant/après sans modifier le snapshot source.

