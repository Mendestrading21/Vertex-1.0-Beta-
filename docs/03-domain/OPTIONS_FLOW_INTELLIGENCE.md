# Intelligence des flux et anomalies options

## Position honnête

Vertex détecte des comportements inhabituels ; il ne prétend pas connaître
l'intention de l'acheteur. Volume, open interest, CALL/PUT, agressivité estimée
ou prime ne prouvent pas une direction : couverture, roll, spread, arbitrage,
fermeture et activité de teneur de marché peuvent produire les mêmes traces.

Le libellé interdit est `smart money detected`. Le libellé permis est
`activité inhabituelle à expliquer`, avec facteurs, limites et hypothèses.

## Données exploitables

| Famille | Exemples | Limite obligatoire |
|---|---|---|
| Contrat | sous-jacent, échéance, strike, type, multiplicateur, style | identité exacte avant tout calcul |
| Marché | bid, ask, last, tailles, timestamp, état de marché | last peut être ancien ou hors spread |
| Activité | volume, OI, volume/OI, volume relatif | OI est généralement une photographie différée |
| Volatilité | IV bid/ask/last/modèle, IV sous-jacent, HV, percentile | source et convention d'annualisation visibles |
| Greeks | delta, gamma, theta, vega, prix sous-jacent | tick et modèle identifiés ; valeurs manquantes distinctes de zéro |
| Structure | concentration strike/échéance, skew, terme, smile | ne pas sommer des unités incompatibles |
| Contexte | earnings, dividende, macro, secteur, news | événement horodaté et confirmé |

## Familles de détecteurs

### Activité relative

- volume du contrat contre sa propre distribution historique ;
- volume du sous-jacent CALL/PUT contre moyenne autorisée ;
- ratio volume/OI avec état `OI_DELAYED` ;
- concentration par strike, échéance, delta-bucket et moneyness ;
- rafales temporelles lorsque les données tick-by-tick sont autorisées.

### Volatilité et surface

- rupture d'IV contre historique du même bucket ;
- déplacement du skew et de la structure par terme ;
- divergence IV/HV ;
- surface incomplète, non monotone ou quotes croisées comme anomalie de donnée,
  pas comme opportunité.

### Liquidité et microstructure

- spread absolu et relatif ;
- profondeur et tailles bid/ask ;
- last hors fourchette ;
- stale quote, locked/crossed market, strike orphelin ;
- coût de passage estimé et pénalité de slippage.

### Contexte multi-source

- proximité d'un résultat, dividende ou événement macro ;
- anomalie prix/volume du sous-jacent ;
- nouveauté et diversité des actualités ;
- cohérence ou contradiction secteur/régime.

## Score d'anomalie

Chaque détecteur rend un percentile ou un score robuste séparé, une population
de référence, une fenêtre, une couverture et un diagnostic. La fusion ne se
fait qu'après contrôle de qualité :

```text
anomaly_evidence = detector_output × coverage × freshness × identity_quality
```

Le score final reste descriptif. La direction est une hypothèse distincte qui
peut valoir `UP`, `DOWN`, `VOLATILITY`, `HEDGE_LIKELY`, `MIXED` ou `UNKNOWN`.
`UNKNOWN` est normal.

## Historique

Si aucun flux historique licencié n'est disponible, Vertex construit uniquement
un historique local à partir des observations auxquelles l'utilisateur a droit.
Il ne rétro-invente pas une série et ne scrape pas un site. Les détecteurs dont
la fenêtre minimale n'est pas atteinte restent `WARMING_UP`.

## Validation

- données point-in-time et séparation stricte entre observation et outcome ;
- aucun usage du futur OI dans une décision passée ;
- tests synthétiques de rolls, spreads, hedges et quotes cassées ;
- évaluation par régime, liquidité, DTE et sous-jacent ;
- taux de faux positifs, stabilité, couverture et drift visibles ;
- revue humaine d'un échantillon avant activation.

## Sources primaires

- IBKR TWS API, calculs options : https://interactivebrokers.github.io/tws-api/option_computations.html
- IBKR Campus, TWS API : https://ibkrcampus.com/campus/ibkr-api-page/twsapi-doc/
- OCC, risques des options standardisées : https://www.theocc.com/getcontentasset/a151a9ae-d784-4a15-bdeb-23a029f50b70/dfc3d011-8f63-43f6-9ed8-4b444333a1d0/riskstoc.pdf
- OCC, open interest : https://www.theocc.com/market-data/market-data-reports/volume-and-open-interest/open-interest
- Cboe, statistiques options : https://www.cboe.com/us/options/market_statistics/daily/

