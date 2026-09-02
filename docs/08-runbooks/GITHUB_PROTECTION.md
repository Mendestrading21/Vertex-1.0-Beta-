# Protection GitHub de Vertex

## État de référence initial — 1er septembre 2026

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

## Activation vérifiée le 2 septembre 2026

L'autorité serveur GitHub confirme :

- dépôt public et branche par défaut `main` ;
- ruleset `main-required`, identifiant `22076309`, état `active`, cible
  `~DEFAULT_BRANCH` et liste de contournement vide ;
- `branches/main` annonce `protected: true` ;
- suppression et mise à jour non fast-forward interdites ; historique linéaire
  obligatoire ;
- pull request et résolution des conversations obligatoires ; zéro approbation
  serveur sur ce dépôt personnel ;
- branche à jour et sept checks nommés ci-dessus obligatoires ;
- squash merge seul autorisé ; merge commit, rebase merge et auto-merge
  désactivés.

## Preuve et rollback

La preuve API du ruleset actif est acquise. La preuve comportementale négative
par une PR synthétique volontairement rouge n'a pas été exécutée dans R0 ; elle
reste distincte et ne doit jamais contaminer une PR applicative. Le rollback
consiste à désactiver temporairement le ruleset, jamais à déplacer `main` ou
forcer un push. Toute exception doit nommer son propriétaire, sa durée et sa
raison.

## Ce que le ruleset ne couvre pas — relevé R1

Le workflow `nightly` (e2e Firefox et WebKit, licences strictes) **n'est pas**
l'un des sept checks requis. Une nightly rouge sur `main` — c'est le cas du
run `33605890223` du 2 septembre 2026, deux échecs Firefox — ne bloque donc
aucune fusion. Elle doit être lue et traitée comme une dette de qualité
explicite, jamais ignorée parce que la CI standard est verte.
