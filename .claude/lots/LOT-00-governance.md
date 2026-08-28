# LOT-00 — Gouvernance et inventaire

## Dépendances et état attendu

- Dépendance bloquante : aucune.
- Branche d'exécution : `lot/00-governance` créée depuis un `main` propre.
- Point de départ : nouveau dépôt privé Vertex One, sans historique ni dépendance vers l'ancien Vertex.
- Point de sortie : lot en `review` tant que la Constitution et l'inventaire n'ont pas reçu la validation humaine demandée.

L'ancien dépôt est consulté uniquement en lecture seule. Son indisponibilité, une provenance inconnue ou un doute de licence bloque la classification concernée ; Claude ne complète jamais un champ par supposition.

## Objectif

Transformer le blueprint en règles de travail vérifiables avant toute création de code : accepter la Constitution, figer le périmètre, classer l'héritage de l'ancien Vertex, établir la tenue des décisions et rendre les fichiers de statut utilisables pour le pilotage de Claude Code, y compris depuis Remote Control officiel sur téléphone.

Ce pilotage téléphonique concerne exclusivement Claude Code. Il ne constitue ni
une UI mobile Vertex, ni une voie Tailscale vers l'application. Vertex 1.0 Beta
est **DESKTOP ONLY** et `Mobile UI = LATER`.

La preuve principale attendue par la feuille de route est : Constitution acceptée, ancien Vertex classé et `docs/99-status/NOW.md` opérationnel.

## Non-objectifs

- créer l'arborescence applicative, une dépendance, un environnement ou une CI ;
- copier, adapter ou exécuter du code de l'ancien Vertex ;
- connecter IBKR, TradingView, une base, un fournisseur d'IA ou un service externe ;
- choisir de nouvelles fonctionnalités, calculs ou pages hors du périmètre adopté ;
- modifier les ADR techniques acceptés sans contradiction prouvée et nouvel ADR ;
- pousser, publier, fusionner ou modifier les protections GitHub sans commande humaine distincte.

## Lecture obligatoire

Lire intégralement, dans cet ordre :

1. `CLAUDE.md` ;
2. `docs/00-foundation/CONSTITUTION.md` ;
3. `docs/00-foundation/PRODUCT_VISION.md`, `SCOPE.md` et `GLOSSARY.md` ;
4. `docs/07-delivery/MASTER_ROADMAP.md`, `DEFINITION_OF_DONE.md` et `BACKLOG.md` ;
5. `docs/07-delivery/MIGRATION_POLICY.md` et `MIGRATION_INVENTORY.csv` ;
6. `docs/09-adr/001-modular-monolith.md`, `002-local-first.md` et `012-migration-policy.md` ;
7. `docs/02-architecture/THREAT_MODEL.md` ;
8. `docs/99-status/NOW.md`, `HISTORY.md` et `BLOCKERS.md` ;
9. `docs/07-delivery/checklists/BEFORE_LOT.md` et `BEFORE_PR.md`.

Toute contradiction entre ces textes est inscrite comme blocage. L'ordre de priorité est Constitution, ADR accepté, contrats, feuille de route, lot, puis backlog.

## Livrables

1. Constitution relue, sans contradiction non résolue, avec validation humaine traçable dans le compte rendu du lot.
2. Périmètre `IN`, `OUT` et `LATER` confirmé, notamment l'interdiction d'exécution, d'accès compte/positions IBKR automatiques et de scraping.
3. `MIGRATION_INVENTORY.csv` complet au niveau des familles réellement considérées : commit et source exacts, élément, classe `KEEP|ADAPT|REWRITE|REFERENCE|DROP`, cible éventuelle, raison, licence, risques, tests, statut et réviseur.
4. Toute famille considérée du Vertex actuel est inventoriée ; aucun fichier
   n'est implicitement réutilisable et l'absence d'inventaire signifie non migré.
5. Registre des ADR audité : numéro unique, statut explicite, portée et absence de décision concurrente.
6. `NOW.md` réduit à un état machine lisible et exact ; `HISTORY.md` append-only ; `BLOCKERS.md` sans blocage fictif ou masqué.
7. Règles Git et responsabilités de revue confirmées dans les documents existants : PR obligatoire, squash, validation humaine, aucun travail direct sur `main`.
8. Rapport de prévol sécurité et propriété intellectuelle ne contenant ni secret, ni donnée de marché réelle, ni copie de source ancienne.

## Étapes d'exécution

1. Capturer l'état initial : branche, commit, statut Git, fichiers suivis et visibilité attendue du dépôt. Arrêter si le dépôt n'est pas le nouveau Vertex One ou si des changements inconnus existent.
2. Passer `NOW.md` à `running` pour `LOT-00` et inscrire un blocage réel immédiatement s'il apparaît.
3. Vérifier la cohérence croisée de la Constitution, du scope, des ADR, du backlog, des frontières et de la roadmap ; lister chaque contradiction avant correction.
4. Examiner le Vertex actuel par familles et métadonnées. Inscrire chaque
   candidat dans l'inventaire avant toute extraction.
5. Appliquer `KEEP`, `ADAPT`, `REWRITE`, `REFERENCE` ou `DROP` selon le protocole.
   `KEEP/ADAPT` exigent propriété, licence, compatibilité Constitution, cible
   précise et tests indépendants ; aucun code n'est éligible implicitement.
6. Vérifier que l'inventaire n'emploie aucun chemin ambigu, statut vide interdit ou classe libre et qu'une ligne rejetée n'a pas de cible de migration active.
7. Vérifier le protocole de commande, les rôles de revue, le format de preuve et
   la procédure de pause/reprise de Claude Code depuis Remote Control officiel ;
   ne pas l'assimiler à l'interface produit.
8. Effectuer la revue sécurité et secret sur les seuls fichiers du nouveau dépôt ; ne jamais inclure le contenu détecté dans le rapport.
9. Mettre à jour `NOW.md`, `HISTORY.md` et, si nécessaire, `BLOCKERS.md`. Ne marquer `done` qu'après validation humaine ; sinon marquer `review`.
10. Produire le compte rendu de preuve sans commencer le LOT-01.

## Tests et contrôles obligatoires

- `git status --short --branch` et `git diff --check` : dépôt maîtrisé et aucun défaut d'espacement.
- Validation de tous les liens et chemins locaux référencés par les documents du lot.
- Validation CSV de `MIGRATION_INVENTORY.csv` : en-tête exact, identifiants uniques, nombre constant de colonnes et valeurs d'énumération autorisées.
- Recherche des marqueurs `TODO`, `TBD`, `UNKNOWN`, statut vide et décision contradictoire dans les éléments déclarés acceptés ; chaque occurrence est corrigée ou bloquée explicitement.
- Recherche des capacités interdites dans l'inventaire et le scope : ordre, exécution, compte courtier, positions IBKR automatiques, scraping, verdict IA et calcul TypeScript.
- Scan de secrets disponible localement, puis contrôle qu'aucune donnée de marché, identifiant de compte, export privé, cache, build ou dépôt tiers n'est suivi.
- Vérification que les fichiers de statut sont cohérents : un seul lot courant, un seul prochain ordre, aucun lot futur déclaré commencé.
- Revue humaine obligatoire de la Constitution et de la vague d'inventaire. Une
  revue séparée n'est requise que pour risque critique, licence, coût, donnée
  personnelle ou changement de frontière.

Un contrôle indisponible est noté `NON EXÉCUTÉ` avec motif et conséquence. Il n'est jamais compté comme vert.

## Sécurité et garde-fous

- Le dépôt doit être privé ; 2FA/passkey et accès minimaux sont requis, mais leur configuration n'est pas modifiée sans autorisation.
- Aucun PAT, cookie, clé API, URL de webhook, identifiant IBKR ou donnée utilisateur n'est copié dans un fichier, une commande enregistrée ou un rapport.
- L'ancien dépôt n'est ni ajouté comme remote, sous-module, package, archive ou dépendance.
- Les captures anciennes peuvent être `REFERENCE` seulement après contrôle de contenu sensible et de propriété.
- Toute licence inconnue produit `blocked`, jamais `KEEP` provisoire.
- Aucun scan n'affiche la valeur d'un secret ; seul le chemin, la règle et l'état de remédiation sont rapportés.
- Aucune action GitHub d'écriture, publication ou fusion ne fait partie de ce lot.

## Critères de sortie mesurables

- 100 % des lignes de l'inventaire ont un identifiant unique, une classe autorisée, une raison, une licence, deux niveaux de risque, des tests requis et un statut.
- 0 élément classé `KEEP` ou `ADAPT` sans provenance, licence, cible et tests
  indépendants définis.
- 0 copie, sous-module, dépendance ou remote runtime vers l'ancien Vertex.
- 0 contradiction ouverte entre Constitution, scope, ADR acceptés et roadmap ; toute question restante figure dans `BLOCKERS.md` avec propriétaire et condition de résolution.
- 0 secret ou donnée réelle suivi par Git.
- `NOW.md` indique exactement lot, branche, statut, dernier commit sain, contrôles, blocage et prochaine commande.
- Constitution et inventaire ont une validation humaine traçable ; sinon l'état final reste `review` ou `blocked`.
- `git diff --check`, validations documentaires et contrôles d'inventaire sont verts.
- Aucun fichier applicatif ou de toolchain n'a été créé.

## Format de preuve de fin de lot

Le rapport final reste compact pour le pilotage de Claude Code, ne contient
aucune valeur sensible et reprend des résultats réels :

```text
LOT : 00 — Gouvernance et inventaire
ÉTAT : done | review | blocked
BRANCHE / COMMIT : lot/00-governance / <sha>
DÉPENDANCES : aucune
LIVRABLES : <documents et inventaire vérifiés>
INVENTAIRE : <total> lignes ; KEEP <n> ; ADAPT <n> ; REWRITE <n> ; REFERENCE <n> ; DROP <n>
TESTS : <commande exacte> → <exit code et résumé>, une ligne par contrôle
SÉCURITÉ : dépôt privé <prouvé/non prouvé> ; secrets <résultat> ; données réelles <résultat>
VALIDATION HUMAINE : Constitution <qui/quand> ; vague <qui/quand>
FICHIERS MODIFIÉS : <liste exhaustive>
RISQUE RESTANT : aucun | <risque concret>
BLOCAGE : aucun | <un seul blocage actionnable>
ROLLBACK : restauration documentaire depuis <sha>, aucune donnée à migrer
PROCHAINE COMMANDE : AUDITE LOT 00
```

Les sorties complètes sont jointes comme artefacts de CI ou annexe locale ; le résumé ne remplace pas les commandes, codes de sortie et SHA.
