# Vertex 1.0 Beta

Vertex 1.0 Beta est la reconstruction propre de Vertex dans le dépôt existant
`Mendestrading21/Vertex-1.0-Beta-`. C'est un terminal local-first de bureau pour
l'analyse d'actions, d'ETF et d'options. Il collecte les informations
officiellement accessibles, les normalise, vérifie leur qualité et leurs droits,
puis présente des preuves, scénarios et probabilités calibrées avec la
possibilité explicite de s'abstenir.

Ce dépôt commence par un blueprint contraignant. Le runtime est construit
dossier par dossier ; aucune richesse visuelle ne précède les contrats, tests,
oracles et frontières de sécurité.

## Rôles Git immuables

| Rôle | Racine | Remote | Branche |
|---|---|---|---|
| Cible | `/home/user/Vertex-1.0-Beta-` | `Mendestrading21/Vertex-1.0-Beta-` | `claude/vertex-connection-kgkntr` |
| Donneur read-only | `/home/user/Vertex-` | `Mendestrading21/Vertex-` | `claude/vertex-connection-kgkntr` |

La baseline donneuse de cette livraison est
`c683c944f93f61d5fd22303df726fac6e79820fe`. Le donneur n'est jamais une cible
d'écriture. Tout écart de HEAD doit être réaudité avant extraction.

## Produit de phase 1

- application bureau/laptop uniquement ;
- références visuelles 1280×800, 1440×900 et 1600×1000 ;
- mobile, bottom navigation et breakpoint téléphone : `LATER` ;
- pilotage éventuel de Claude depuis un téléphone avec Remote Control, sans
  transformer ce téléphone en client Vertex ;
- Black Glass sobre, une question principale et un visuel dominant par page ;
- calculs financiers exclusivement dans l'autorité Python ;
- interface TypeScript limitée à l'affichage de résultats versionnés.

## Frontières non négociables

- aucune création ou transmission d'ordre ;
- aucune lecture automatique de compte, positions, P&L ou exécutions IBKR ;
- portefeuille Vertex saisi et tenu manuellement ;
- TradingView limité aux alertes Pine et imports/exports officiels, avec
  revalidation IBKR fraîche ;
- IA limitée à l'explication de sorties typées et sourcées ;
- probabilités calibrées et incertaines, jamais une promesse de précision à
  100 % ;
- social, actualité ou anomalie options insuffisants seuls pour qualifier une
  idée ;
- secrets, montants personnels et données sous licence exclus de Git.

## Ordre de lecture

1. `CLAUDE.md`
2. `docs/00-foundation/CONSTITUTION.md`
3. `docs/00-foundation/SCOPE.md`
4. `manifests/repositories.yaml`
5. `docs/07-delivery/BETA_REPOSITORY_BOOTSTRAP.md`
6. `docs/00-product/CURRENT_VERTEX_SALVAGE_MATRIX.md`
7. `docs/07-delivery/DONOR_EXTRACTION_PROTOCOL.md`
8. `docs/07-delivery/FOLDER_BY_FOLDER_PROGRAM.md`
9. `docs/02-architecture/SYSTEM_CONTEXT.md`
10. `docs/99-status/NOW.md`

## Méthode de construction

Le programme canonique est
`docs/07-delivery/FOLDER_BY_FOLDER_PROGRAM.md`. Pour chaque dossier, Claude
applique :

```text
PLAN -> DONOR AUDIT -> CONTRACT -> TESTS RED -> IMPLEMENT -> TESTS GREEN
-> MUTATION/PERF -> VISUAL QA si UI -> REVIEW -> ACCEPTED
```

Chaque module donneur est classé `KEEP`, `ADAPT`, `REWRITE`, `REFERENCE` ou
`DROP`. Une classe ne vaut pas autorisation : l'extraction exige provenance,
licence, frontière financière, tests, benchmark et rollback.

## Première séquence

1. `PLAN BOOTSTRAP BETA`
2. `EXÉCUTE BOOTSTRAP BETA` après validation
3. `AUDITE BOOTSTRAP BETA`
4. `PLAN PARCOURS COMPLET` avec `.claude/prompts/plan-full-journey.md`
5. `VALIDE LE PARCOURS — EXÉCUTE DOSSIER 00`

Le prompt initial est `.claude/prompts/bootstrap-beta.md`, puis Claude doit lire
et planifier le parcours entier avec `.claude/prompts/plan-full-journey.md`.
Les dossiers suivants utilisent `.claude/prompts/folder-wave.md`. Un seul dossier
peut être actif et Claude ne commence jamais le suivant automatiquement.

## Statut

Blueprint Beta. Aucun runtime de production n'est autorisé tant que ses preuves
de lot, de dossier et de release ne sont pas satisfaites.
