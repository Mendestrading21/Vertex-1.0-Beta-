---
name: vertex-cloud-max-audit
description: Auditer intégralement Vertex 1.0 Beta depuis GitHub, en lecture seule et en mode Plan, comparer si nécessaire l'ancien dépôt Vertex, et distinguer le code réellement transféré, branché et prouvé de ce qui reste planifié, dormant ou bloqué par le poste live.
---

# Vertex — audit cloud maximal

## Mission

Produire depuis GitHub la vérité technique la plus complète possible sur
`Vertex-1.0-Beta-`, cible de la reconstruction, sans modifier le dépôt et sans
prétendre avoir validé IBKR, TradingView ou le poste local. Lorsque `Vertex-`
est accessible, l'auditer séparément comme source historique et transformer les
écarts en plan de portage prouvé, lot par lot, pour Claude Code piloté depuis un
téléphone.

## Autorités

Lire avant l'audit :

1. `CLAUDE.md` ;
2. `docs/00-foundation/CONSTITUTION.md` ;
3. `docs/99-status/NOW.md`, `BLOCKERS.md` et `DEBT.md` ;
4. les ADR, contrats, lots et fichiers cités par les chemins inspectés.

Si `../vertex-one/SKILL.md` ou `../vertex-titanium-ledger/SKILL.md` existe au
SHA audité, le lire avant les références utiles. Sinon, utiliser les références
embarquées dans ce skill, signaler la dépendance absente et classer
`INCONNU` ou `BLOQUÉ` toute règle qui n'y figure pas ; ne jamais inventer son
contenu. Le code, ses appels, ses tests et les preuves GitHub priment sur un
document de statut ancien.

## Frontière du mode Plan

- Lecture seule : aucun fichier, branche, PR, issue, workflow, secret,
  configuration ou service n'est créé, modifié, fusionné, relancé ou déployé.
- Ne jamais checkout, reset, rebase, merge, push ou nettoyer un worktree.
- Ne jamais installer une dépendance, démarrer une migration ni contacter TWS,
  IB Gateway, TradingView, Cloudflare ou une API payante.
- Ne lancer ni build, test, serveur, formatteur ni commande susceptible de créer
  cache, base, artefact ou objet Git. Consommer les résultats CI existants et
  faire l'analyse statique par l'API GitHub. Si un checkout est indispensable,
  limiter les commandes à la lecture avec `GIT_OPTIONAL_LOCKS=0` et
  `GIT_NO_LAZY_FETCH=1` ; un objet absent devient `INCONNU` plutôt que téléchargé.
- Aucun ordre live ou paper et aucune API IBKR de compte, cash, position, P&L,
  ordre, exécution, `whatIf`, annulation ou exercice.
- L'iPhone sert au pilotage cloud ; Vertex reste une application bureau.
- Une impossibilité de preuve devient `BLOQUÉ`, jamais `OK` par supposition.

## Baseline GitHub obligatoire

Ne jamais supposer que `main`, la branche Claude ou le dossier ouvert contient
le travail le plus récent. Relever avec des opérations GitHub en lecture seule :

- dépôt, branche par défaut et visibilité ;
- toutes les branches avec SHA, date et protection ;
- PR ouvertes/brouillons et leur base/head ;
- derniers commits, auteurs et fichiers changés ;
- CI du SHA candidat, jobs, artefacts et échecs ;
- tags/releases, rulesets, Dependabot et alertes accessibles ;
- différences entre `main`, chaque PR active et la branche Claude.

Choisir le SHA candidat uniquement par preuve. Si plusieurs branches portent
des capacités distinctes, produire une matrice de comparaison et ne pas les
fusionner mentalement. Lire [references/cloud-evidence.md](references/cloud-evidence.md)
pour la taxonomie et les limites de preuve.

Figer séparément le SHA de `Vertex-1.0-Beta-` et celui de `Vertex-`. Ne jamais
conclure qu'une connexion legacy fonctionne encore parce que sa documentation,
sa capture ou son grand nombre de tests l'affirme. Lire
[references/cross-repo-portage.md](references/cross-repo-portage.md) avant toute
recommandation de reprise.

Immédiatement avant le verdict, relire la branche par défaut, son SHA, son tree,
l'état et le head de chaque PR candidate, puis la CI attachée au SHA final. Si
un head ou un état a bougé, comparer les deux SHA, réauditer tous les chemins
affectés et remplacer la baseline. Distinguer explicitement un nouveau commit de
merge d'un contenu réellement nouveau : deux commits peuvent pointer vers un
tree identique. Ne jamais livrer comme actuelle une analyse devenue obsolète
pendant son exécution.

## Audit intégral

Suivre chaque capacité de bout en bout :

`source -> droits -> ingestion -> enveloppe/provenance -> persistance -> qualité
et fraîcheur -> calcul -> fusion -> gates -> AdviceEngine -> explication IA ->
API -> vue -> états UI -> tests -> observabilité`.

Pour chaque maillon, citer le chemin et le symbole exacts, les producteurs,
consommateurs et tests. La présence d'un fichier, d'un test isolé ou d'une
documentation ne prouve pas que le maillon est relié au runtime.

Lire [references/intelligence-runtime.md](references/intelligence-runtime.md)
pour l'intelligence, les calculs, les données, les intégrations, la sécurité,
la performance et l'amélioration contrôlée.

Auditer les douze pages et leur fidélité au contrat approuvé avec
[references/pages-design.md](references/pages-design.md). Vérifier à la fois la
route, le hook, le schéma, l'API, le snapshot, le worker, la source, les états,
le rendu, le clavier, les trois viewports bureau, les graphes et les tests.

## Recherche externe

N'utiliser le Web que pour une lacune ou une pratique instable identifiée par
l'audit. Privilégier documentation officielle, normes et dépôts des auteurs.
Pour chaque proposition externe, noter URL, date, licence, maintenance,
compatibilité, coût, données envoyées et problème Vertex précis. Une bibliothèque
populaire ne devient pas une recommandation sans bénéfice mesuré et plan de
retrait.

## Sortie exigée

Lire [references/plan-output.md](references/plan-output.md) et produire :

1. verdict exécutif honnête ;
2. baseline GitHub figée au SHA ;
3. matrice de vérité des capacités ;
4. constats P0 à P3 avec preuves ;
5. matrice des douze pages ;
6. matrice IBKR/TradingView/cloud avec tests encore nécessaires sur le poste ;
7. architecture cible seulement lorsqu'un écart réel la justifie ;
8. carte legacy `REPRENDRE / ADAPTER / RÉÉCRIRE / REJETER / BLOQUÉ` ;
9. plan ordonné en lots atomiques, critères d'acceptation, tests et rollback ;
10. décisions humaines restantes ;
11. une seule prochaine commande recommandée.

Ne donner ni pourcentage global inventé, ni promesse de précision, ni formule
« tout fonctionne ». Signaler explicitement les contradictions entre documents,
code, branches et preuves.

Tenir un ledger compact des ancres `chemin:symbole` et le réutiliser dans les
matrices ; ne pas recopier de longs fichiers, logs ou réponses GitHub. Si le
contexte devient trop grand, conserver d'abord baseline, P0/P1, contradictions,
preuves négatives et décisions, puis résumer P2/P3 sans perdre leurs identifiants.

Terminer exactement par :

`PLAN CLOUD VERTEX TERMINÉ — AUCUNE MODIFICATION EFFECTUÉE`
