# Protocole d'extraction du Vertex actuel

## Baseline observée

- dépôt : `Mendestrading21/Vertex-` ;
- branche de travail observée : `claude/vertex-connection-kgkntr` ;
- commit : `c683c944f93f61d5fd22303df726fac6e79820fe` ;
- date du commit : 28 août 2026 à 19:55:51 UTC ;
- inventaire observé : 2 544 fichiers, dont 952 Python, 49 JavaScript,
  19 CSS, 527 fichiers sous `tests/` et 359 PNG ;
- le rapport du lot 46 annonce 4 471 tests passés et 152 ignorés ; cette annonce
  est une preuve documentaire, pas un test exécuté par le nouveau dépôt.

Le SHA doit être comparé à `origin/claude/vertex-connection-kgkntr` et au
`main` courant au début du LOT-00. Toute évolution ultérieure reçoit une
nouvelle baseline ; on ne mélange pas deux commits dans une vague.

## Principe

Le dépôt actuel est un **donneur de capacités**, pas une dépendance de
production. Le nouveau dépôt conserve son architecture, ses contrats et son
historique propres. Il peut néanmoins extraire du code appartenant au projet
lorsque la preuve montre qu'il est pur, utile, licencié, compatible et mieux
testé qu'une réécriture.

## Classes

| Classe | Action |
|---|---|
| `KEEP` | porter le code ou l'asset presque identique, avec provenance et tests |
| `ADAPT` | conserver l'algorithme ou le contrat, changer interfaces/stockage/autorité |
| `REWRITE` | conserver le besoin et les cas de test, réimplémenter |
| `REFERENCE` | consulter capture, test, vocabulaire ou comportement, sans code runtime |
| `DROP` | exclure capacité interdite, doublon, génération, cache ou provenance incertaine |

Le réaudit détaillé emploie parfois le libellé explicite
`KEEP_AS_REFERENCE`. Il s'agit strictement d'un alias documentaire de
`REFERENCE`, jamais d'une autorisation de copier du code runtime.

## Zones donneuses prioritaires

### Fort potentiel `KEEP/ADAPT`

- `vertex/validation/` : calibration, dérive et hors échantillon ;
- `vertex/research/` : contrats d'expérience, coûts, robustesse, walk-forward ;
- `vertex/visualization/` : schéma de graphique, palette et statuts ;
- fonctions pures de `vertex/options/` : unités IV, liquidité, payoff, scénarios
  et surface, après oracles indépendants ;
- `vertex/data_sources/quality.py`, `provenance.py`, `reconciliation.py` et
  contrats de données purs ;
- profils versionnés de `vertex/strategy/` comme exigences et vecteurs ;
- tests des invariants, fixtures synthétiques et scripts d'audit ;
- tokens Black Glass, polices dont la licence est prouvée, icônes et captures
  comme donneurs visuels.

### Potentiel `ADAPT/REWRITE`

- adapters IBKR market-data-only, après scan des appels interdits ;
- TradingView webhook/store, après nouveau schéma, signature et anti-replay ;
- stockage point-in-time et portefeuille manuel, après migration idempotente ;
- moteurs de régime, anomalies, secteurs et événements ;
- pages, composants, graphiques et service worker, vers le shell React décidé ;
- IA, uniquement derrière le nouveau gateway et le packet canonique.

### `DROP` par règle

- `terminal.py` comme runtime ou import de production ;
- toute route, fonction, bouton ou structure d'ordre, même paper ;
- toute lecture IBKR compte/positions/P&L/exécutions ;
- autorités de décision multiples et adapters legacy après parité ;
- données réelles, caches, bundles générés, environnements, secrets et logs ;
- mocks ou démos présentés comme données réelles ;
- assets tiers sans licence prouvée ;
- copie des 359 captures dans le nouveau dépôt.

## Vagues de migration

1. **Invariants et tests** : frontières, vocabulaire, statuts, cas adverses.
2. **Contrats purs** : instruments, temps, unités, provenance, graphiques.
3. **Calculs purs** : options, risque, performance et validation.
4. **Sources** : IBKR, TradingView, SEC/FRED/news avec nouveaux ports.
5. **État local** : point-in-time, journal, portefeuille manuel et migrations.
6. **Expérience** : tokens, icônes, widgets et parcours des 12 pages.
7. **IA et apprentissage** : explication, mémoire contrôlée et suivi modèle.

Une vague est une PR brouillon. L'approbation porte sur la vague et ses preuves,
pas sur chaque fichier, afin d'éviter des dizaines de microdécisions.

## Gate d'extraction

Pour chaque capacité :

1. épingler chemin et blob SHA ;
2. tracer imports, routes, consommateurs, données et tests ;
3. vérifier propriété, licence et dépendances transitives ;
4. exécuter le scanner des frontières et des secrets ;
5. écrire contrat et tests indépendants dans Vertex One ;
6. extraire le plus petit noyau sans import vers le donneur ;
7. comparer résultats à des oracles, propriétés et vecteurs donneurs ;
8. mutation-test et benchmarker les hot paths concernés ;
9. documenter divergences, rollback et statut de migration ;
10. supprimer les adapters temporaires seulement après migration des
    consommateurs et preuve de parité.

Un test vert ne suffit pas si le test reproduit la même erreur que le code
donneur. Les formules financières exigent un oracle indépendant.

## Traçabilité

Chaque module extrait reçoit dans la PR : dépôt, commit, chemins/blobs, classe,
raison, licence, tests et adaptations. Le code final ne dépend pas du chemin du
dépôt donneur et aucune donnée utilisateur ne migre par Git.
