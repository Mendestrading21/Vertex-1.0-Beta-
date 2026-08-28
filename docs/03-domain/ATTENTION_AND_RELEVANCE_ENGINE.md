# Moteur d'attention et de pertinence

## Objectif

Vertex peut ingérer beaucoup d'informations sans obliger l'utilisateur à tout
lire. Le moteur d'attention déduplique, relie, classe et explique pourquoi un
élément mérite une place. Il ne cache jamais un blocage critique et ne transforme
pas la popularité en vérité.

## Pipeline

```text
ingestion autorisée -> identité -> droits -> horodatage -> déduplication
-> cluster d'événement -> enrichissement -> score de pertinence
-> portes de qualité -> budget d'attention -> explication
```

## Facteurs positifs

- appartenance au portefeuille manuel, watchlist ou univers du profil ;
- proximité temporelle d'un catalyste ;
- gravité potentielle et caractère nouveau ;
- fiabilité de la source et confirmation inter-source ;
- impact secteur/entreprise/option explicitement relié ;
- divergence ou anomalie mesurée ;
- action analytique claire : surveiller, vérifier, invalider ou approfondir.

## Pénalités

- doublon ou reprise de communiqué ;
- source unique, rumeur ou auteur non résolu ;
- spam, bot ou engagement artificiel probable ;
- donnée ancienne, sans timezone ou modifiée sans historique ;
- ambiguïté d'entité ou de ticker ;
- hors univers et sans propagation sectorielle prouvée ;
- contenu non réutilisable selon les droits.

## Portes avant classement

`RIGHTS_OK`, `IDENTITY_OK`, `TIME_OK`, `SOURCE_OK` et `QUALITY_OK` doivent être
vrais. Une actualité réglementaire critique peut franchir le budget de volume,
mais jamais une porte de droits ou d'identité.

## Budgets d'attention

- Aujourd'hui : 3 événements majeurs, 3 changements et les blocages ;
- Calendrier : événements dans la fenêtre du profil ;
- Marchés : un récit de régime et ses contradictions ;
- Opportunités : raisons principales et raisons de refus, pas tous les signaux ;
- Analyse : preuves groupées par thèse ;
- Options : anomalies expliquées, jamais une pluie de contrats ;
- Système : problèmes techniques uniquement.

Un compteur indique toujours combien d'éléments ont été regroupés, filtrés ou
écartés, avec accès à l'audit. Le classement est déterministe et rejouable pour
un snapshot donné.

## Score

Les sous-scores sont conservés séparément. Une somme opaque est interdite.
L'interface expose au minimum `why_now`, `source_diversity`, `novelty`,
`strategy_fit`, `portfolio_relevance`, `quality` et les pénalités.

Le moteur peut apprendre à ordonner seulement après collecte d'un feedback
explicite et après comparaison hors échantillon à la règle déterministe. Il ne
réécrit jamais rétroactivement le journal.

