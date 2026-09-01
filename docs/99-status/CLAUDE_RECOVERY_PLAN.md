# Récupération contrôlée du travail Claude

## Référence figée de R0

- `main` : `a5b7d205388e58f4e2716deeba5ecbea0ca9af21` ;
- PR Claude : `#14`, brouillon, non fusionnable globalement ;
- branche : `claude/snapshots-confirmation-20260901` ;
- HEAD inspecté : `6226b8d5de934b7ced26d8a456cca6cfe614bce4` ;
- 31 commits dans la PR, dont 23 postérieurs au socle `895cbc4` à examiner ;
- 133 fichiers touchés au total par la PR divergente.

Cette empreinte n'arrête pas Claude. Tout nouveau commit après `6226b8d` sera
inventorié dans une vague ultérieure et ne change jamais silencieusement le
périmètre ci-dessous.

## Règle d'intégration

PR #14 ne doit pas être fusionnée ni rebasée en bloc. Chaque vague repart du
`main` courant, reprend un contrat cohérent, ajoute ses tests, passe les sept
checks et ouvre sa propre PR brouillon. La reprise privilégie la réapplication
compréhensible ; un cherry-pick n'est accepté qu'après diff et dépendances.

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

## Verrous de fichiers Claude / Codex

- Claude peut poursuivre ses branches, mais aucun de leurs HEAD mouvants ne
  devient une base Codex.
- Codex ne modifie pas la branche Claude.
- `global.css`, `tokens.ts`, `AppShell.tsx`, `routes.tsx`, OpenAPI et `NOW.md`
  ont un propriétaire unique par vague.
- Une vague backend est fusionnée avant la vague UI qui consomme son contrat.
- Les données réelles restent hors Git ; les preuves CI utilisent SYNTHETIC.

## Critères de récupération d'un commit

1. diff relu contre le `main` courant ;
2. dépendances et fichiers générés identifiés ;
3. aucune capacité IBKR interdite ;
4. aucune valeur financière fabriquée dans l'interface ;
5. test rouge ou reproducteur avant reprise ;
6. validations ciblées puis `tools/run_checks.sh` ;
7. PR brouillon, revue humaine et squash uniquement.

R0 prépare ces vagues ; il n'en exécute aucune.
