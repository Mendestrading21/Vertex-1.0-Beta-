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
