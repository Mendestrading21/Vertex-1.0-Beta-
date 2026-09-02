# Récupération contrôlée du travail Claude

## Référence figée de R0

- `main` : `a5b7d205388e58f4e2716deeba5ecbea0ca9af21` ;
- PR Claude : `#14`, brouillon au moment du gel et déclarée non fusionnable
  globalement par R0 ;
- branche : `claude/snapshots-confirmation-20260901` ;
- HEAD inspecté : `6226b8d5de934b7ced26d8a456cca6cfe614bce4` ;
- 31 commits dans la PR, dont 23 postérieurs au socle `895cbc4` à examiner ;
- 133 fichiers touchés au total par la PR divergente.

Cette empreinte n'arrêtait pas Claude. Elle reste la référence historique du
périmètre effectivement classé par R0.

## Événement postérieur au gel

- la branche Claude a reçu 13 commits supplémentaires après `6226b8d` ;
- le HEAD fusionné de PR #14 est
  `ef47b11a723ba9952389efcd4e08cc8361e90601` ;
- PR #14 totalisait alors 44 commits, 123 fichiers, `+10863/-1099` ;
- son HEAD source a passé la CI #159 ;
- PR #14 a été fusionnée par squash le 2 septembre 2026 à `05:55:06Z` ;
- `main` est passé de `a5b7d205388e58f4e2716deeba5ecbea0ca9af21` à
  `505d4654c7f0d9bf6186dc9b88e5cffc5fb1edc9`.

Pendant la validation R0, PR #18 a ensuite été fusionnée par squash le
2 septembre 2026 à `07:04:21Z`. Son HEAD fusionné est
`b8a0d4d6d927da5d4f0a44de7ab7515b2e6ee6ed`, son diff porte deux fichiers
(`+329/-240`), sa CI #165 est verte et `main` est devenu
`beb249881015147de11e270f8e0e48d843716e6e`. Le HEAD de la branche Claude reste
mouvant ; ces empreintes désignent uniquement les arbres effectivement
fusionnés.

Cette fusion a contredit le verrou de récupération sélective. Elle n'autorise
ni reset, ni revert implicite, ni force-push : l'état publié est requalifié en
place et toute correction passe par une nouvelle PR bornée.

## Règle de requalification après fusion

Les vagues ci-dessous ne sont plus des lots d'import ou de cherry-pick. Elles
forment la matrice d'audit du code désormais présent dans `main`. Chaque vague
compare le `main` observé `beb24988` au socle `a5b7d205`, vérifie le contrat
cohérent, les
dépendances et les tests, puis classe chaque écart `KEEP`, `ADAPT`, `REWRITE`
ou `DROP`. Une correction éventuelle repart du `main` courant, passe les sept
checks et ouvre sa propre PR brouillon.

## Vagues proposées

| Vague | Commits Claude | Décision R0 | Périmètre |
|---|---|---|---|
| R2-A vérité des relais | `6e4f183`, `9fe81a7`, `7928147`, `70512db`, `ec0eb06`, `fcf2f6e` | ADAPT | déclenchement Marchés, identités fournisseur, nature des marks et libellés |
| R2-B Analyse | `fcf2921`, `6fd5af9`, `6f918b2` | ADAPT | calculs déjà approuvés, relais API et affichage sans calcul TypeScript |
| R2-C Presse | `7880413`, `0c79f78` | ADAPT | actualités Aujourd'hui et horodatages ambigus conservés comme tels |
| R2-D Graphiques | `0c59afa` | ADAPT | `market.rebased_series` côté Python ; aucune page dans cette vague |
| R2-E Risques cœur | `427f91f`, `eb9ee54`, `514ad2a`, `6143f5a` | ADAPT | calcul, validation bornée, worker et API |
| R2-F Risques page | `6cd65d5` | ADAPT | route et page après R2-E seulement |
| R2-G shell vérité | `bafd8c5`, `812320d`, `6226b8d` | ADAPT | ordre canonique, modules absents et identité/fraîcheur du snapshot |
| R2-H accès local | `d357e4c` | HOLD | changement d'autorité d'authentification ; décision sécurité séparée |
| R2-I documentation | `d8031cb`, `7e21e5b` | REWRITE / DROP | réécrire l'état depuis les preuves actuelles ; ne pas rejouer la passation |
| R2-J surfaces post-fusion | PR #18, `b8a0d4d6` | AUDIT / ADAPT | règles CSS de formulaires, tables et boutons ; passation documentaire à revalider |

## Verrous de fichiers Claude / Codex

- Claude peut poursuivre ses branches, mais aucun de leurs HEAD mouvants ne
  devient une base Codex.
- Codex ne modifie pas la branche Claude.
- `global.css`, `tokens.ts`, `AppShell.tsx`, `routes.tsx`, OpenAPI et `NOW.md`
  ont un propriétaire unique par vague.
- Une vague backend est fusionnée avant la vague UI qui consomme son contrat.
- Les données réelles restent hors Git ; les preuves CI utilisent SYNTHETIC.

## Critères de requalification d'une vague

1. diff relu contre le `main` courant ;
2. dépendances et fichiers générés identifiés ;
3. aucune capacité IBKR interdite ;
4. aucune valeur financière fabriquée dans l'interface ;
5. test rouge ou reproducteur avant reprise ;
6. validations ciblées puis `tools/run_checks.sh` ;
7. PR brouillon, revue humaine et squash uniquement.

R0 transforme ces vagues en contrôles post-fusion ; il n'en exécute aucune.
