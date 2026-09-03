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


## Fenêtre d'observation : familles déclarées avant la borne

La file d'attention (`attention/global`), la file de revue
(`review_queue/global`) et le rail de preuves (Analyse, Opportunités) sont
recalculés à partir d'une **fenêtre bornée** d'observations persistées :
`[now − lookback, now]` sur `as_of`, les plus récentes d'abord, au plus
`max_observations` lignes (500 ; lookback de 72 h en développement, 8 jours
en profil réel). Le contrat de cette fenêtre, mesuré et testé
(`apps/worker/tests_integration/test_attention_real_chain.py`,
`test_opportunities_real_chain.py`, `test_observation_window_families.py`) :

1. **Le consommateur déclare les familles de schéma qu'il sait lire** —
   `FusionConfig.content_schema_prefixes`, dont le défaut est
   `vertex_worker.handlers.CONTENT_SCHEMA_PREFIXES` (`synthetic-news/`,
   `ibkr.news-headline/`). Une déclaration vide ou mal formée est refusée à
   la construction ; rien n'est deviné (deny by default, même patron que
   `DAILY_QUOTE_SCHEMA_PREFIXES` pour Marchés et `DAILY_BARS_SCHEMA_PREFIXES`
   pour Analyse).
2. **Le chargeur applique ces familles AVANT la borne** —
   `load_recent_observation_records(schema_prefixes=…)`, paramètre
   obligatoire, sans défaut. Une famille non déclarée n'entre jamais dans la
   fenêtre : ni dans le classement, ni dans les compteurs.
3. **Un préfixe est un littéral, jamais un motif** — `%`, `_` et le
   caractère d'échappement sont échappés dans le `LIKE` émis
   (`LIKE :préfixe || '%' ESCAPE '/'`).
4. **La couverture publiée dit ce qui a été regardé** —
   `coverage.content_schema_prefixes` (familles), `observations_considered`
   (lignes de ces familles dans la fenêtre), `content_observations` (celles
   qui portent un titre), `non_content_observations`. `population` vaut
   `EMPTY` quand la fenêtre ne contient aucune ligne des familles
   déclarées — même si des cotations existent en base.
5. **Le rail de preuves est cadré par instrument, avant la borne** —
   Analyse et Opportunités demandent la fenêtre d'un `instrument_ref`
   (le `con_id` relevé sur les barres de l'instrument). Opportunités lit
   toutes les fenêtres en une requête
   (`load_recent_observation_records_by_instrument`, borne PAR
   instrument) ; un instrument sans barre garde la fenêtre globale, et un
   ticker absent de la table n'a aucune preuve — jamais celles d'un autre.

### Pourquoi (mesuré)

- 2026-09-01 : 1 376 dépêches sur 28 instruments — la fenêtre globale de
  500 ne contenait plus aucune dépêche de GOOG ; le rail de preuves
  affichait « aucune preuve » alors que 140 existaient en base.
- 2026-09-03, 08:40 UTC : `today/attention` servait 0 item sur données
  réelles. Le collecteur temps réel écrit une cotation instantanée par
  instrument et par cycle de 60 s (`ibkr.quote/1`, `ibkr.daily-quote/1`) :
  les 500 observations les plus récentes n'étaient plus que des
  instantanées, sans titre. Rien n'échouait, rien n'était journalisé.
- Même jour, page Opportunités : 3 dépêches de GOOG plus anciennes que 520
  dépêches de MSFT — Analyse voyait 3 grappes, Opportunités aucune.

Le remède n'est jamais une borne plus large : la famine reviendrait avec le
prochain instrument collecté.

### Ce qui n'est PAS du contenu (déclaré)

- Les familles de marché (`ibkr.quote/`, `ibkr.daily-quote/`, `ibkr.bars/`,
  `ibkr.daily-bars/`, `synthetic-daily-quote/`, `synthetic-daily-bars/`,
  chaînes d'options, sondes `source-capability/`, faits SEC) : sans titre,
  elles ne produiraient aucun item ; les déclarer rouvrirait la famine.
- Les événements de calendrier (`synthetic-calendar-event/`, familles de
  `vertex_worker.calendar.CALENDAR_EVENT_SCHEMA_PREFIXES`) : ils portent
  un titre mais ne sont pas des dépêches. La page Calendrier les sert,
  Catalyseurs les croise ; la file d'attention et le contexte
  d'information de la revue ne les lisent pas. Avant le 2026-09-03, un
  événement synthétique pouvait apparaître dans la file d'attention de
  développement ; ce n'est plus le cas, et c'est déclaré, pas subi
  (test-témoin `test_calendar_events_are_served_by_their_own_page_not_by_the_queue`).
  Les réintroduire — « proximité temporelle d'un catalyste » est un facteur
  positif de ce moteur — est une décision de produit : elle passe par la
  déclaration, jamais par une borne.

### Ajouter une famille

Une nouvelle source de dépêches (autre schéma que `ibkr.news-headline/`)
n'atteint l'écran que si sa famille est déclarée dans
`CONTENT_SCHEMA_PREFIXES` (ou dans la `FusionConfig` du profil) et si ses
observations portent `title` et `entities`. Le lot brut IBKR
(`ibkr.news-headlines/`, une liste par réponse, sans titre) n'en fait pas
partie : seule la dépêche dérivée (une ligne par titre) est du contenu.

### Coût connu

`observations` n'a d'index que sur `as_of` : chaque fenêtre cadrée parcourt
la plage du lookback puis filtre. Analyse exécute une lecture par
instrument à barres ; Opportunités une seule pour tous les candidats. Un
index `(instrument_ref, as_of)` relève d'un lot de migration dédié — voir
`docs/99-status/DEBT.md`, « Trouvé au lot SRV-S0 ».
