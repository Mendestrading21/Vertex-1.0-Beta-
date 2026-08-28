# Règles de travail Claude — Vertex One

## Mission

Construire Vertex 1.0 dans ce dépôt neuf. Exploiter les capacités saines du
Vertex actuel par vagues inventoriées, sans fusionner son historique, importer
son monolithe ni créer une dépendance runtime vers le dépôt donneur.

Documentation et comptes rendus en français. Code, identifiants, schémas et messages techniques en anglais.

## Lecture obligatoire

Avant toute action :

1. `docs/00-foundation/CONSTITUTION.md` ;
2. `docs/99-status/NOW.md` ;
3. le lot demandé dans `.claude/lots/` ;
4. les ADR et spécifications référencés par ce lot.

## Une vérité, un propriétaire

- Observations : `market_data`.
- Qualité et fraîcheur : `data_quality`.
- Calculs financiers : `vertex_core` Python.
- Verdict final : un unique `AdviceEngine`.
- Persistance : PostgreSQL.
- Interface : affichage et interactions uniquement.
- IA : explication structurée uniquement.

## Interdictions absolues

- Envoyer, modifier, annuler ou prévisualiser un ordre IBKR.
- Appeler les API IBKR de compte, positions, P&L, ordres ou exécutions.
- Calculer côté TypeScript un prix, Greek, IV, risque, R:R, score, probabilité ou verdict faisant autorité.
- Présenter un fallback, mock, cache ou résultat théorique comme une donnée réelle ou live.
- Produire un avis positif avec une donnée requise absente, partielle, périmée, retardée ou contradictoire.
- Afficher une probabilité prédictive non calibrée et non validée hors échantillon.
- Mettre un secret, token, compte, payload sensible ou URL secrète dans Git ou les logs.
- Copier globalement un fichier ou dossier du dépôt donneur sans inventaire,
  provenance, licence, tests indépendants et plan de rollback.
- Ajouter un framework, une base ou un service sans ADR.
- Travailler directement sur `main`, force-push, fusionner ou publier sans validation humaine.

## Protocole de commande

- `PLAN` : aucune modification.
- `PLAN LOT NN` : plan du lot uniquement.
- `EXÉCUTE LOT NN` : un lot seulement.
- `PLAN PARCOURS COMPLET` : lecture seule de tout le blueprint et plan des
  dossiers `00` à `25`.
- `PLAN DOSSIER NN` : plan borné d'un dossier après le parcours accepté.
- `EXÉCUTE DOSSIER NN` : création complète d'un dossier seulement.
- `AUDITE LOT NN` : lecture et rapport, aucune correction.
- `CORRIGE LOT NN` : uniquement les défauts déjà listés.
- `STATUT` : huit lignes maximum.
- `PAUSE` : finir l'opération atomique, mettre `NOW.md` à jour et s'arrêter.
- `REPRENDS` : lire `NOW.md`, vérifier Git et proposer une seule action.
- `STOP` : aucune nouvelle modification.

Ne jamais commencer le lot ou dossier suivant automatiquement.

## Git

- Branche : `lot/NN-slug`.
- Une PR par lot.
- Squash merge après validation humaine.
- Aucun secret ni donnée de marché réelle dans les commits, fixtures ou captures.
- Les actions GitHub doivent être épinglées à un SHA complet.

## Questions

Poser une seule question à la fois uniquement si elle concerne coût, exposition publique, licence non standard, sécurité, destruction, fournisseur d'IA ou changement d'autorité financière. Pour tout choix réversible couvert par un ADR, appliquer l'ADR sans proposer plusieurs options.

## Fin de lot

Toujours :

1. exécuter les contrôles définis par le lot ;
2. mettre à jour tests, documentation et `docs/99-status/NOW.md` ;
3. fournir les commandes et résultats exacts ;
4. lister les fichiers modifiés ;
5. signaler le risque restant ;
6. terminer par une seule prochaine commande recommandée.

Format de statut compact pour Claude Remote Control : lot, état, branche,
fichiers, tests, risque, blocage, prochaine commande. Ce format de pilotage
téléphone n'est pas une interface Vertex et n'ajoute aucun critère mobile.
