# Historique de construction

Ajouter une ligne après chaque lot fusionné : date UTC, lot, SHA, résultat des gates, décision humaine et lien de PR.

## Rectification — commit `0b178e8`

Son message décrit « edge-ibkr et ingress TradingView : deux modules jamais
audités ». Il contient bien cela, **mais aussi le correctif P0 du 6e audit
adversarial** — le garde de nature (`snapshot_views.py`, `portfolio.py` et
leurs tests, ~740 lignes sur les 1 306).

Cause : j'ai fait un `git add -A` alors que deux agents travaillaient encore
sur la branche. Le message ne mentionne donc pas le correctif le plus
important de la vague, et le commit mélange quatre périmètres — contrairement
à la règle « une PR cohérente par lot » de `CLAUDE.md`.

L'historique n'est pas réécrit : la règle interdit le force-push, et la
branche est partagée. Cette entrée est la rectification.

**Ce que `0b178e8` contient réellement, côté P0 :**

`mark_population` échappait entièrement au vocabulaire fermé ET au garde de
contradiction, parce que mon correctif de la vague précédente ne visait que la
clé littérale `population`. Or le relais portefeuille publie sa nature sous ce
nom. `mark_population="REAL"` avec `rights: SYNTHETIC` toujours présent était
accepté et affiché « DONNÉES RÉELLES » en ton neutre.

17 vecteurs sont désormais refusés (dont `LIVE`, `PRODUCTION`,
`DONNEES REELLES 100% FIABLES`, les natures IMBRIQUÉES par dossier, les
constantes du générateur `schema_version`/`generator`/`source_system`/
`adjustment_basis`, les identifiants `SYN*` et le préfixe `[SYNTHETIC] `).

Liste EXHAUSTIVE des clés de nature du produit établie par grep des
producteurs : `population` (tête, par dossier, contexte d'information),
`mark_population`, `populations.*`, `population_components.*`,
`population_counts` (les clés), `synthetic: bool`. Aucune autre.

Règle écrite pour deux natures contradictoires : **une nature gouverne le
conteneur où elle se trouve, et seule la SUR-REVENDICATION est refusée**. Une
tête `REAL` au-dessus d'un marqueur synthétique est refusée ; une tête
prudente `SYNTHETIC` au-dessus d'un dossier `REAL` est SERVIE — c'est
exactement la dégradation que le worker applique déjà volontairement, et la
refuser casserait un état légitime sans protéger personne.

Preuves : 12 reproducteurs rouges d'abord par la vraie route HTTP ;
`apps/api/tests` 979 passed ; 3 suites d'intégration en série sur base
jetable dédiée (65 / 17 / 96) ; **9 mutants ciblés du garde, 9 tués** ;
`caplog` DEBUG prouvant qu'aucun refus ne cite une valeur stockée.


## Rectification — commit `f726471`, et une faute répétée

Son message décrit le P0-2 (recensement de nature). Il contient AUSSI le
correctif **P1-6 de la fusion** — l'effacement du signe — et le travail sur le
portefeuille, soit trois périmètres.

C'est la DEUXIÈME fois. La rectification du commit `0b178e8` ci-dessus dit
exactement cela, je l'ai écrite moi-même, et j'ai recommencé : un `git add -A`
alors que des agents écrivaient encore. Écrire la règle n'a pas suffi ; le
changement de méthode est de ne plus faire de `git add -A` tant qu'un agent
travaille sur l'arbre, et d'ajouter les chemins un par un.

**Ce que `f726471` contient réellement, côté fusion (P1-6) :**

`dedup.py` supprimait tout caractère non alphanumérique, donc `+` et `-`.
Reproduit : `'SPX -3,2 % sur la seance'` et `'SPX +3,2 % sur la seance'`
donnaient la même empreinte `'spx 3 2 sur la seance'`, étaient fusionnés, et le
worker ne publiait qu'UN représentant élu à l'aveugle. Une hausse pouvait donc
s'afficher à la place d'une baisse, sans qu'aucune contradiction ne soit
signalée. Même chose pour `↑`/`↓`, `▲`/`▼`, `>`/`<`.

Règle retenue : **le signe accolé à un nombre est une donnée, pas de la
ponctuation.** Un caractère de signe n'est un marqueur que s'il précède
immédiatement un chiffre sans être précédé d'un alphanumérique — ce qui protège
`COVID-19`, `Compàny-1`, les dates et les fourchettes `3-5 %`. Les caractères de
direction et de comparaison sont toujours des marqueurs. Les variantes d'un même
sens sont canonicalisées (`↓`, `▼`, `−` → `-`) pour qu'une différence
typographique ne scinde pas deux dépêches du même événement. Un marqueur ABSENT
n'est jamais l'opposé d'un marqueur présent : `-5 %` et `5 %` donnent deux
clusters, mais AUCUN conflit — un nombre non signé est de polarité inconnue,
pas positive.

Séparer ou signaler ? **Les deux, selon le niveau qui a lié.** Sur l'empreinte
de titre, l'effacement ÉTAIT le défaut : deux titres opposés ne se rencontrent
plus. Sur l'identité fournisseur (`native_id`, URL canonique), la preuve est
plus forte que la formulation — deux dépêches sous un même identifiant sont un
seul item, typiquement une correction, et les séparer perdrait ce lien. Donc le
cluster est conservé et la **contradiction publiée**, la qualité du cluster
valant `CONFLICT`, ce qui ferme la gate `QUALITY_OK` : l'item passe en
`rejected` plutôt que d'être arbitré en silence.

`FUSION_RULESET_VERSION` passe de `1.0.0` à `2.0.0` : les empreintes d'avant et
d'après ne sont pas comparables en rejeu.

Non-régression vérifiée : 7 variantes typographiques de la MÊME dépêche
fusionnent toujours, et aucun marqueur parasite sur `Compàny-1`, `COVID-19`,
`2026-08-25`, `3-5 %`, `1 000 000`.


## `f726471`, suite — ce qu'il contient côté portefeuille (P1-4, P1-5, et un 3e défaut)

**P1-4 — amplification.** `POST /portfolio/import/preview`, 500 lignes portant
`1E+200000` :

| | requête | HTTP | durée | réponse | amplification | pic RSS |
|---|---|---|---|---|---|---|
| avant | 28 076 o (budget 262 144) | 200 | 1,50 s | **95,5 Mio** | **×3566** | 482 Mo |
| après | 28 076 o | 200 | **0,03 s** | 26 003 o | ×0,93 | 177 Mo |

**Borne retenue** : magnitude < 10²⁴ et au plus 18 décimales déclarées, lues
sur le coefficient sans jamais le développer — le contrôle ne coûte rien sur
l'entrée qu'il refuse. Vérité unique appliquée par le DTO du journal ET par le
codec CSV, avant tout `format(value, "f")`.

Le plafond est placé là où aucune déclaration honnête ne peut arriver, quelle
que soit la devise : 4 décades au-dessus du plus gros nominal jamais émis
(billet de 10²⁰ pengő, Hongrie 1946), 10 au-dessus de la masse monétaire
mondiale. Le plancher à 18 décimales est le miroir exact — `1E-200000` rend
autant de caractères que `1E+200000` — et reste 10 décades plus fin que la
fraction d'action la plus fine d'un courtier.

**`1E+100` USD est désormais REFUSÉ**, et l'accepter n'était pas neutre :
PostgreSQL `numeric` non contraint stocke jusqu'à `1E+131071` (vérifié :
131 072 caractères). Une telle ligne était donc ÉCRITE, puis re-rendue en
entier à chaque `GET /portfolio` et à chaque export — l'amplification devenait
permanente.

**P1-5 — fuite du journal de l'utilisateur dans les logs.** Sous uvicorn et
PostgreSQL réels, un `amount` hors bornes produisait un 500 non typé et
`sqlalchemy.exc.DataError` journalisait `[SQL: INSERT INTO
ledger_transactions …]` avec `'note': 'PEA Boursorama 40312 - achat perso'`.

Le gestionnaire est posé sur la CLASSE `sqlalchemy.exc.StatementError` — les 10
sous-classes portent `.statement` et `.params` — plus `PendingRollbackError`,
qui n'en est PAS une mais interpole l'exception d'origine dans son propre
message. Cette seconde classe est atteignable : `record_ledger_event` rattrape
justement un `IntegrityError` pour détecter une double compensation.

Preuve sur le vrai chemin, obtenue en rétrécissant `fees` en `numeric(6,2)`
dans une base jetable pour provoquer un vrai `DataError` qui passe la nouvelle
borne : `500 {"code":"DATABASE_STATEMENT_REJECTED"}`, et dans le log serveur
`'PEA Boursorama 40312'` 0 · `'INSERT INTO'` 0 · `'parameters:'` 0 ·
`'Traceback'` 0.

**Troisième défaut, trouvé en fermant les deux premiers** : une cellule CSV de
plus de 131 072 caractères fait lever `_csv.Error` par `csv.reader` — qui n'est
pas un `CsvImportError`, traversait `parse_import_csv` et atteignait le
gestionnaire par défaut en 500 non typé, tout en tenant sous le budget de
256 Kio. Fermé par un refus typé `CSV_MALFORMED`, dont le message stdlib n'est
jamais relayé : il peut citer un fragment du fichier.
