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

Un test d'architecture (`research/tests/test_boundary.py`) échoue si un import
de runtime apparaît sous `research/`.

## Ce que ce dossier fournit aujourd'hui

- `pipelines/walk_forward.py` — découpage **walk-forward purgé** avec écart
  (`gap`) au moins égal à l'horizon du label, plus embargo. C'est la seule
  façon d'évaluer un modèle sur des séries temporelles sans se mentir.
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
