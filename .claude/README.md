# Pilotage de Claude Code

Ce dossier contient les prompts de pilotage de Vertex One. Ils complètent
`CLAUDE.md` sans le remplacer. En cas de contradiction, l'ordre d'autorité est :

1. `docs/00-foundation/CONSTITUTION.md` ;
2. `CLAUDE.md` ;
3. les ADR acceptés ;
4. le lot demandé ;
5. le prompt utilisé.

## Principe

Le travail se déroule en deux temps distincts :

1. **Plan** : inspection en lecture seule, plan borné, risques et critères de sortie ;
2. **Exécution** : un seul lot autorisé, sur sa branche, avec ses validations.

Un prompt de plan ne donne jamais l'autorisation de modifier, installer, publier,
fusionner, pousser ou ouvrir une PR. Une exécution ne commence que sur la commande
explicite `EXÉCUTE LOT NN`.

## Démarrage recommandé

Depuis la racine du dépôt :

1. extraire cette livraison dans un dossier temporaire, hors des deux dépôts ;
2. ouvrir Claude Code sur le dossier extrait `vertex-one/` en mode Plan et
   transmettre `prompts/bootstrap-beta.md` ;
3. après le verdict, répondre `EXÉCUTE BOOTSTRAP BETA` pour installer uniquement
   le blueprint dans `/home/user/Vertex-1.0-Beta-` ;
4. rouvrir Claude Code à la racine de la Beta et lancer
   `prompts/plan-full-journey.md` en mode Plan ;
5. examiner le parcours complet des dossiers `00` à `25` ;
6. répondre `VALIDE LE PARCOURS — EXÉCUTE DOSSIER 00` ;
7. utiliser ensuite un dossier, un lot, une branche et une PR à la fois.

Claude doit lire avant toute action :

1. `CLAUDE.md` ;
2. `docs/00-foundation/CONSTITUTION.md` ;
3. `docs/99-status/NOW.md` ;
4. le fichier `.claude/lots/LOT-NN-*.md` demandé ;
5. les ADR et spécifications cités par ce lot.

Pour toute identité, composition de page, widget, tableau ou graphique, charger
ensuite `.claude/skills/vertex-titanium-ledger/SKILL.md`. Ce skill spécialisé
applique la grammaire Titanium Ledger sans déplacer la vérité financière.

## Prompts disponibles

| Fichier | Usage | Autorise des modifications |
|---|---|---:|
| `plan-full-journey.md` | Parcours complet des dossiers 00–25 avant création | Non |
| `bootstrap-beta.md` | Vérifier puis installer le blueprint dans la cible | Seulement avec `EXÉCUTE BOOTSTRAP BETA` |
| `folder-wave.md` | Planifier et construire un dossier complet | Seulement avec `EXÉCUTE DOSSIER NN` |
| `00-master-plan.md` | Établir le plan initial du dépôt | Non |
| `lot-template.md` | Planifier ou exécuter un lot précis | Seulement avec `EXÉCUTE LOT NN` |
| `page-template.md` | Construire une page selon sa spécification | Seulement avec `EXÉCUTE LOT NN` |
| `audit-current-lot.md` | Auditer le lot courant | Non |
| `fix-failing-lot.md` | Corriger des défauts déjà identifiés | Oui, avec `CORRIGE LOT NN` |
| `prepare-pr.md` | Produire les preuves et le texte de PR | Non pour push, ouverture ou fusion |
| `status-phone.md` | Obtenir un état en huit lignes | Non |
| `resume-work.md` | Reprendre après une pause | Non, jusqu'à nouvelle autorisation |

## Commandes courtes depuis un téléphone

- `STATUT` : huit lignes maximum, aucune action.
- `PLAN LOT NN` : plan en lecture seule.
- `EXÉCUTE LOT NN` : exécuter uniquement ce lot.
- `PLAN PARCOURS COMPLET` : lire tout le blueprint et planifier les dossiers 00–25.
- `PLAN DOSSIER NN` : plan détaillé du dossier, sans modification.
- `EXÉCUTE DOSSIER NN` : créer les fichiers complets du dossier accepté.
- `AUDITE LOT NN` : auditer sans corriger.
- `CORRIGE LOT NN` : corriger uniquement les défauts déjà listés.
- `PRÉPARE PR LOT NN` : produire le verdict et le brouillon de PR, sans publication.
- `PRÊT À MERGER ?` : verdict et preuves, sans fusion.
- `PAUSE` : finir l'opération atomique, mettre l'état à jour, puis s'arrêter.
- `REPRENDS` : vérifier l'état et proposer une seule prochaine action.
- `STOP` : ne lancer aucune nouvelle action.

## Questions et décisions

Claude ne pose qu'une question à la fois, et uniquement lorsqu'elle est réellement
bloquante : coût, exposition publique, licence non standard, sécurité, opération
destructive, fournisseur d'IA ou changement de l'autorité financière. Le choix
recommandé doit apparaître en premier. Toute décision réversible déjà couverte par
un ADR est appliquée sans rouvrir un débat.

## Format de fin d'exécution

Chaque lot se termine par un compte rendu compact :

1. lot et état ;
2. branche ;
3. fichiers modifiés ;
4. commandes et résultats exacts ;
5. risque restant ;
6. blocage éventuel ;
7. une seule prochaine commande recommandée.

Claude ne commence jamais le lot suivant automatiquement.
