# Protection GitHub de Vertex

## État de référence

Relevé le 1er septembre 2026 :

- dépôt public ;
- branche par défaut `main` au SHA
  `a5b7d205388e58f4e2716deeba5ecbea0ca9af21` ;
- `main` non protégée ;
- aucun ruleset ;
- auto-merge désactivé ;
- merge commit, rebase merge et squash merge autorisés.

Les réglages GitHub sont une autorité serveur. Un fichier dans le dépôt ne peut
pas les remplacer et un test local ne prouve pas leur activation.

## Ruleset obligatoire pour `main`

Créer un ruleset actif visant la branche par défaut avec les règles suivantes :

1. interdire suppression et force-push ;
2. exiger une pull request ;
3. exiger une approbation humaine si un reviewer indépendant est enregistré ;
   sur un dépôt personnel sans second reviewer, exiger la PR mais conserver
   zéro approbation serveur afin de ne pas verrouiller définitivement `main` ;
4. révoquer l'approbation après nouveau commit lorsqu'elle est exigée ;
5. exiger la résolution des conversations ;
6. exiger une branche à jour avant fusion ;
7. exiger les sept checks ci-dessous ;
8. appliquer les règles aux administrateurs ;
9. autoriser uniquement le squash merge ;
10. laisser l'auto-merge désactivé.

Checks requis, recopiés exactement depuis `.github/workflows/ci.yml` :

- `garde-fous (rôle, blueprint, frontière, registre, verrouillage)` ;
- `python — lint Ruff et typage mypy strict (cible 3.13)` ;
- `python — unitaires, propriétés, oracles (cible 3.13)` ;
- `python — intégration PostgreSQL 18 (sérielle)` ;
- `web — lint, types, tests, build, budget, dérive de contrat` ;
- `e2e — Chromium, 3 viewports desktop, axe` ;
- `supply-chain — audit des dépendances, SBOM`.

## Geste administrateur restant

Dans GitHub : `Settings` → `Rules` → `Rulesets` → `New branch ruleset`.

Nom recommandé : `main-required`. Cible : `Default branch`. État : `Active`.
Dans `Settings` → `General` → `Pull Requests`, désactiver merge commits et
rebase merge pour ne conserver que squash merge.
Après sauvegarde, relire l'API `GET /repos/{owner}/{repo}/rulesets` et vérifier
que `branches/main` annonce `protected: true`.

## Preuve et rollback

La preuve est le JSON GitHub du ruleset actif et une PR synthétique dont un
check volontairement rouge bloque réellement la fusion. Le rollback consiste
à désactiver temporairement le ruleset, jamais à déplacer `main` ou forcer un
push. Toute exception doit nommer son propriétaire, sa durée et sa raison.
