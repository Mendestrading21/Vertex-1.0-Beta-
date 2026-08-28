# Prompt — Planification ou exécution d'un lot

Remplace `NN` et `slug` avant utilisation.

**Commande autorisée :** `PLAN LOT NN` ou `EXÉCUTE LOT NN`
**Lot :** `.claude/lots/LOT-NN-slug.md`

## Règle de mode

- Si la commande est `PLAN LOT NN`, reste en lecture seule et rends uniquement le
  plan demandé.
- Si la commande est `EXÉCUTE LOT NN`, exécute uniquement ce lot.
- Toute autre formulation ambiguë est traitée comme `PLAN LOT NN`.
- Ne commence jamais le lot suivant.

## Prévol obligatoire

Lis complètement :

1. `CLAUDE.md` ;
2. `docs/00-foundation/CONSTITUTION.md` ;
3. `docs/99-status/NOW.md` et `BLOCKERS.md` ;
4. le fichier du lot ;
5. tous les ADR, contrats, spécifications et checklists référencés.

Vérifie ensuite :

- l'identifiant et le périmètre exacts du lot ;
- que ses dépendances sont terminées et leurs preuves présentes ;
- l'état Git, la branche et l'absence de modifications utilisateur non liées ;
- l'absence de secret ou donnée réelle dans les entrées prévues ;
- la liste exacte des fichiers à toucher ;
- les validations et critères de sortie définis par le lot.

Si l'état Git contient des changements non compris ou si le lot dépend d'une
décision bloquante, arrête-toi sans modifier et pose une seule question.

## Sortie en mode Plan

Fournis :

1. objectif et non-objectifs ;
2. préconditions prouvées et préconditions manquantes ;
3. fichiers à créer ou modifier ;
4. séquence d'étapes atomiques ;
5. contrats, migrations et ADR affectés ;
6. tests à écrire avant ou avec le code ;
7. contrôles CI et critères d'acceptation ;
8. risques et stratégie de retour arrière ;
9. une seule prochaine commande recommandée.

Ne fournis pas de code et n'effectue aucune écriture.

## Exécution autorisée

Avec `EXÉCUTE LOT NN` uniquement :

1. crée ou utilise la branche `lot/NN-slug`, jamais `main` ;
2. réalise la plus petite tranche verticale satisfaisant le lot ;
3. respecte les limites de modules et les contrats canoniques ;
4. ajoute ou adapte les tests en même temps que l'implémentation ;
5. n'ajoute aucune dépendance non inventoriée et non épinglée ;
6. n'utilise que des fixtures synthétiques ;
7. documente tout comportement dégradé et toute donnée indisponible ;
8. arrête immédiatement si une capacité IBKR interdite, une autorité financière
   concurrente, un fallback silencieux ou un secret apparaît.

Tu peux effectuer des modifications locales et des validations correspondant au
lot. Tu ne dois pas pousser, ouvrir/fusionner une PR, déployer ou publier sans une
commande humaine explicite distincte. Ne force jamais Git et ne supprime jamais
des modifications que tu n'as pas créées.

## Validation de fin de lot

Exécute les commandes réellement disponibles et exigées par le lot. Compare
l'état Git avant/après. Mets à jour :

- les tests et fixtures concernés ;
- la documentation et les ADR si la décision change ;
- la matrice ou les preuves de qualité concernées ;
- `docs/99-status/NOW.md` ;
- `docs/99-status/HISTORY.md` si le lot est terminé ;
- `docs/99-status/BLOCKERS.md` si un blocage subsiste.

Un contrôle non exécuté est noté `NON EXÉCUTÉ` avec sa raison. Ne transforme pas
un test absent ou ignoré en succès.

## Compte rendu compact de pilotage Claude

Ce format reste lisible depuis Remote Control sur téléphone, mais concerne
uniquement le pilotage de Claude Code. Il ne définit ni une UI mobile Vertex ni
un accès Tailscale à l'application ; `Mobile UI = LATER`.

Termine avec :

```text
LOT : NN — titre
ÉTAT : done | review | blocked
BRANCHE : lot/NN-slug
FICHIERS : nombre + chemins principaux
TESTS : commandes exactes et résultats
RISQUE : aucun ou risque concret
BLOCAGE : aucun ou un seul blocage
PROCHAINE COMMANDE : une seule commande
```
