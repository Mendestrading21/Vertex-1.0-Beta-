# Modèle régime, secteurs et cohérence inter-marchés

## Question

Le contexte actuel autorise-t-il l'étude d'un nouveau risque, et le titre est-il
porté ou contredit par son secteur et ses facteurs ?

## Sortie canonique

Le régime est un état descriptif versionné, jamais une prévision certaine :

```text
RISK_ON | RISK_OFF | TRANSITION | STRESS | RANGE | UNKNOWN
```

Il contient les probabilités calibrées éventuelles, les observations, les
contradictions, la fenêtre, la fraîcheur et les changements depuis le snapshot
précédent. `UNKNOWN` bloque toute règle dépendante.

## Couches

1. tendance et volatilité des indices de référence ;
2. breadth, participation, dispersion et nouveaux hauts/bas ;
3. courbe des taux, crédit, dollar et volatilité lorsque les droits le
   permettent ;
4. rotation sectorielle et relative strength multi-horizon ;
5. corrélations et ruptures de corrélation ;
6. calendrier macro et événements de marché ;
7. détection de changement de régime hors ligne et dérive en ligne.

## Secteurs

La classification exacte et la source sont conservées. Un ETF sectoriel n'est
pas traité comme une entreprise et un thème n'est pas confondu avec un secteur.
Pour chaque titre : secteur principal, pairs, exposition géographique et thèmes
peuvent enrichir l'analyse, mais un lien non prouvé reste absent.

Les widgets montrent :

- leadership et accélération sectorielle ;
- largeur interne du secteur ;
- position du titre contre son secteur et son indice ;
- changement de corrélation ;
- preuves favorables, défavorables et contradictoires.

## Méthodes candidates

- règles robustes déterministes comme baseline ;
- `ruptures` pour les changements hors ligne ;
- River pour drift et anomalies en ligne ;
- modèles probabilistes seulement après protocole point-in-time et calibration ;
- aucun modèle profond ou quantum ajouté pour son prestige.

## Validation

- walk-forward chronologique, aucun split aléatoire de séries temporelles ;
- purge et embargo quand les horizons se chevauchent ;
- coûts, survivorship bias et révisions macro contrôlés ;
- stabilité par sous-période et stress ;
- comparaison à une baseline simple ;
- abstention si couverture, freshness ou calibration échoue.

