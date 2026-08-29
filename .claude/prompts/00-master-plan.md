# Prompt — Plan directeur initial

Tu es l'architecte principal de Vertex One. Travaille exclusivement en mode Plan.

## Autorisation

Cette demande est en lecture seule. Tu ne dois :

- créer, modifier, déplacer ou supprimer aucun fichier ;
- installer ou mettre à jour aucune dépendance ;
- modifier Git, créer une branche, faire un commit, push, PR ou merge ;
- déclencher un déploiement, une migration ou une action sur un service externe ;
- accéder à l'ancien Vertex autrement qu'en lecture seule.

Les commandes d'inspection locales et non mutantes sont autorisées. Si une
commande peut créer un cache, un lockfile, un environnement ou modifier un état,
ne l'exécute pas : indique-la comme validation future.

## Lecture obligatoire

Lis complètement, dans cet ordre :

1. `CLAUDE.md` ;
2. `docs/00-foundation/CONSTITUTION.md` ;
3. `docs/00-foundation/PRODUCT_VISION.md` ;
4. `docs/00-foundation/SCOPE.md` ;
5. `docs/99-status/NOW.md` et `BLOCKERS.md` ;
6. `docs/02-architecture/` ;
7. `docs/03-domain/` ;
8. `docs/04-integrations/` ;
9. `docs/06-quality/` ;
10. `.claude/lots/LOT-00-*.md` s'il existe.

Ne te fonde pas uniquement sur les titres. Signale les références manquantes, les
contradictions et les documents qui se déclarent autoritaires sur la même vérité.

## Objectif

Construis le plan directeur du dépôt neuf sans reproduire l'ancien Vertex. Le plan
doit préserver les invariants suivants :

- IBKR est strictement limité aux données de marché autorisées ;
- le portefeuille reste manuel ;
- `vertex_core` Python est l'unique autorité des calculs financiers ;
- un unique `AdviceEngine` produit le `AdviceResult` canonique ;
- l'interface et l'IA ne calculent ni ne modifient le verdict ;
- les données absentes, partielles, retardées, périmées ou contradictoires ne sont
  jamais maquillées et ferment les portes qui en dépendent ;
- recherche, backtest et runtime de décision restent séparés ;
- aucun élément du dépôt donneur n'est réutilisé sans inventaire
  `KEEP / ADAPT / REWRITE / REFERENCE / DROP`, provenance et tests indépendants.

## Livrable attendu

Produis, dans cet ordre :

1. **Verdict de cohérence** : prêt à planifier, ou bloqué, avec preuves précises.
2. **Inventaire de l'environnement** : outils déjà prouvés, outils à vérifier et
   dépendances attendues, sans rien installer.
3. **Carte des autorités** : donnée, qualité, calcul, décision, persistance,
   interface et IA, avec un seul propriétaire par vérité.
4. **Carte des modules** : dépendances autorisées, contrats partagés et flux de
   données ; aucun cycle implicite.
5. **Séquence des lots** : ordre, dépendances, livrables, validations et critères
   de sortie de chaque lot.
6. **Plan détaillé de `LOT-00`** : fichiers concernés, travail atomique, tests à
   préparer, risques et condition d'arrêt.
7. **Registre des risques** : uniquement les risques concrets, classés
   critique/élevé/modéré, avec preuve et mitigation.
8. **Questions réellement bloquantes** : au maximum une question. N'en pose
   aucune si les documents donnent déjà un choix sûr et réversible.
9. **Prochaine commande** : une seule, sous la forme `EXÉCUTE LOT 00` si le plan
   est prêt, sinon une commande de correction documentaire précise.

## Règles de réponse

- Réponds en français ; garde les identifiants techniques en anglais.
- Cite chaque fichier concerné par son chemin exact.
- Ne propose pas plusieurs piles techniques lorsqu'un ADR décide déjà.
- N'invente ni version, ni test réussi, ni état de service.
- Distingue strictement « constaté », « prévu » et « à vérifier ».
- Ne fournis aucun code d'implémentation dans ce plan.
- Ne commence aucun lot.
