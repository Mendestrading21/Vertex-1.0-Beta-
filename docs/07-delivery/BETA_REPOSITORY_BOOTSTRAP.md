# Démarrage dans `Vertex-1.0-Beta-`

## Dépôts déjà disponibles

| Rôle | Dépôt | État |
|---|---|---|
| Donneur | `Mendestrading21/Vertex-` | complet, lecture seule, baseline `c683c944…` |
| Cible | `Mendestrading21/Vertex-1.0-Beta-` | quasi vide, branche de travail déjà poussée |

Les deux branches locales portent le même nom
`claude/vertex-connection-kgkntr`. Ce nom identique ne prouve pas le rôle du
dépôt. Avant chaque écriture, Claude vérifie `pwd`, le remote `origin` et le nom
complet attendu. Une écriture dans `Vertex-` est un incident et provoque l'arrêt.

## Variables locales

Configurer hors Git :

```text
VERTEX_DONOR_ROOT=/home/user/Vertex-
VERTEX_BETA_ROOT=/home/user/Vertex-1.0-Beta-
```

Ne pas ajouter ces chemins dans un `.env` suivi. Le manifeste
`manifests/repositories.yaml` contient les identités GitHub et les exemples de
chemins, pas de secret.

## Prévol en mode Plan

Claude doit produire les résultats de ces vérifications sans modifier :

1. la cible est bien `Mendestrading21/Vertex-1.0-Beta-` ;
2. la branche active est la branche de travail annoncée ;
3. l'état Git de la cible est compris ;
4. le donneur résout le commit `c683c944…` ou documente le nouveau HEAD ;
5. aucun remote de la cible ne pointe vers le donneur ;
6. le donneur n'est pas dirty à cause d'une action Claude ;
7. la cible ne contient encore aucun code à préserver hors README ;
8. les outils requis sont seulement inventoriés, pas installés.

Le script `tools/check_repository_role.py` automatise l'identité du remote.

## Installation du blueprint

Le contenu du dossier `vertex-one/` de cette livraison est destiné à la racine
de `Vertex-1.0-Beta-`. Claude le place dans un lot de bootstrap après le plan,
en préservant le README initial comme preuve ou en intégrant son contenu dans le
nouveau README. Il ne touche pas au donneur.

Le blueprint apporte documentation, contrats, manifestes, skill, agents,
prompts, icônes et validateurs. Il ne prétend pas apporter un runtime terminé.

## Première séquence

1. `PLAN BOOTSTRAP BETA` : vérifier les deux rôles et produire le diff prévu.
2. `EXÉCUTE BOOTSTRAP BETA` : installer uniquement le blueprint dans la cible.
3. `AUDITE BOOTSTRAP BETA` : parser tous les fichiers et vérifier Git.
4. `PLAN PARCOURS COMPLET` : utiliser
   `.claude/prompts/plan-full-journey.md` pour planifier `DOSSIER 00` à
   `DOSSIER 25` sans écrire.
5. `VALIDE LE PARCOURS — EXÉCUTE DOSSIER 00` : créer uniquement la gouvernance
   et l'inventaire donneur selon le plan accepté.

Aucun dossier applicatif ne commence avant que le bootstrap et le DOSSIER 00
soient validés.

## Bureau seulement

La première version de Vertex est une application bureau/laptop. Le pilotage de
Claude depuis le téléphone via Remote Control reste autorisé, mais il ne change
pas la cible produit : aucune UI Vertex mobile n'est construite dans cette
phase.
