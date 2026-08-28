# Prompt — plan complet de reconstruction

Travaille exclusivement en **mode Plan**. Cette session est en lecture seule.

## Mission

Prépare le parcours complet de reconstruction de Vertex 1.0 Beta dans
`/home/user/Vertex-1.0-Beta-`, en utilisant `/home/user/Vertex-` uniquement
comme donneur audité et immuable. La cible est une application bureau ; mobile
reste `LATER`. Le téléphone sert uniquement à Claude Remote Control.

## Lecture obligatoire

1. Vérifie `pwd`, `git remote -v`, branche, HEAD et dirty state des deux dépôts.
2. Lis intégralement `CLAUDE.md`, la Constitution, les ADR, les manifestes, les
   contrats, les 25 lots, les 12 spécifications de pages et tous les runbooks.
3. Lis `docs/07-delivery/BETA_REPOSITORY_BOOTSTRAP.md`,
   `FOLDER_BY_FOLDER_PROGRAM.md`, `MIGRATION_POLICY.md`,
   `DONOR_EXTRACTION_PROTOCOL.md` et la matrice de récupération actuelle.
4. Compare le donneur au SHA
   `c683c944f93f61d5fd22303df726fac6e79820fe` sans jamais le modifier.
5. Lance les sous-agents d'audit en lecture seule prévus dans `.claude/agents/`
   et synthétise leurs preuves ; aucun sous-agent n'implémente dans cette phase.

## Livrable du plan

Produis un seul plan directeur ordonné couvrant les dossiers `00` à `25`. Pour
chaque dossier, indique : but, fichiers exacts à créer, contrats, dépendances,
éléments donneurs `KEEP/ADAPT/REWRITE/REFERENCE/DROP`, tests rouges puis verts,
oracles, benchmarks, contrôles de sécurité/licence, preuve visuelle éventuelle,
rollback et critère d'acceptation.

Le plan doit aussi contenir :

- la carte des autorités et l'absence de cycles ;
- les flux IBKR, TradingView, actualités, entreprises, ETF, macro et social ;
- le moteur quantitatif, l'incertitude, la calibration, la dérive et
  l'abstention ;
- les 12 pages, leur widget dominant, leurs jauges/graphiques et leurs huit
  états de données ;
- les budgets de latence, cache, mémoire, rendu, accessibilité et restauration ;
- le chemin critique complet jusqu'à la release bureau.

## Interdictions de cette session

Ne crée, ne modifie, ne copie, n'installe, ne commit, ne pousse et ne publie
rien. Ne pose qu'une seule question si un blocage matériel reste après lecture.
N'invente aucun test ou entitlement réussi.

Ne lance ce plan complet qu'après un bootstrap audité. Termine par un verdict
et une seule réponse attendue de l'utilisateur :

`VALIDE LE PARCOURS — EXÉCUTE DOSSIER 00`

Après cette réponse, exécute uniquement le dossier 00 selon le plan accepté.
Puis propose `PLAN DOSSIER 01`. Aucun dossier suivant ne démarre
automatiquement.
