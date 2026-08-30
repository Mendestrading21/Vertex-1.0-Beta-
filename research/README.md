# Recherche

Ce dossier existe pour **répondre à une question, pas pour alimenter le
runtime**. Il n'a aucun droit d'écriture sur la base de production, aucun
import depuis `vertex_api`, `vertex_worker` ou `vertex_persistence`, et rien
de ce qu'il produit ne peut être affiché à l'utilisateur sans passer par une
décision humaine explicite.

## Frontière, sans exception

| Interdit ici | Pourquoi |
|---|---|
| Écrire dans la base du runtime | « Aucune donnée de recherche ou de notebook ne peut écrire dans le runtime live » (`.claude/rules/architecture.md`) |
| Importer `vertex_api` / `vertex_worker` / `vertex_persistence` | La recherche ne doit pas pouvoir déclencher un effet de production |
| Publier une probabilité prédictive | `probability.calibration` est `NOT_IMPLEMENTED` au registre des calculs ; aucune valeur ne peut être affichée tant qu'un humain n'a pas accepté une calibration validée |
| Utiliser une donnée non point-in-time | Une variable connue après l'instant de décision est une fuite, pas un signal |

Un test d'architecture (`research/tests/test_boundary.py`) analyse chaque
module `.py` **et chaque cellule de code de chaque notebook `.ipynb`** sous
`research/`, et échoue s'il y trouve un import de runtime écrit en clair, un
import dynamique dont le nom de module est un littéral
(`importlib.import_module("vertex_persistence")`), ou le lancement d'un
exécutable de base de données ou de service runtime (`psql`, `pg_dump`,
`alembic`, `uvicorn`…) nommé littéralement.

Ce contrôle est une analyse **statique** : il rend le chemin évident
impossible par inadvertance. Il ne détecte pas un nom de module construit à
l'exécution, un `exec` de source assemblée, une socket brute vers PostgreSQL
ni un exécutable renommé. La liste exacte de ce qui est couvert et de ce qui
ne l'est pas est en tête de `research/tests/test_boundary.py` ; elle ne
remplace ni la revue humaine ni les droits d'accès.

## Ce que ce dossier fournit aujourd'hui

- `pipelines/walk_forward.py` — découpage **walk-forward purgé**. La fenêtre
  d'entraînement est contiguë au test ; la non-fuite vient de la **purge**,
  qui retire les observations dont le label se résout pendant le test — pas
  d'un écart fixe, qui rendrait la purge inutile en masquant combien de
  données il jette. L'**embargo** est distinct et facultatif : il met en
  quarantaine les observations déjà évaluées par un pli, pour qu'elles ne
  reviennent pas immédiatement entraîner le pli suivant. C'est la seule façon
  d'évaluer un modèle sur des séries temporelles sans se mentir.
- `pipelines/calibration.py` — Brier score, log loss, diagramme de fiabilité,
  intervalles par **bootstrap en blocs** (les observations voisines ne sont pas
  indépendantes), et surtout la **règle d'abstention** : la fonction dit
  `VALID`, `INSUFFICIENT_SAMPLE`, `MISCALIBRATED` ou `UNSTABLE`, et seule
  `VALID` autoriserait un affichage — décision qui reste humaine.

## Ce que ce dossier ne fournit PAS

Aucun modèle entraîné, aucun jeu de données, aucun résultat de backtest,
aucune probabilité calibrée. Les outils d'évaluation existent ; **rien n'a été
évalué**, parce qu'aucune donnée réelle n'a jamais été observée
(`docs/99-status/DEBT.md`). Ne pas présenter ce dossier comme une validation.

`datasets-manifest/` est vide et le restera tant que la licence des chaînes
d'options historiques n'est pas tranchée (blocage **B-04**).
