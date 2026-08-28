# Prompt — Statut compact pour téléphone

**Commande :** `STATUT`

Ce prompt sert exclusivement au pilotage de Claude Code depuis Remote Control
officiel. Il ne décrit, n'ouvre et ne valide ni une UI mobile Vertex ni un accès
Tailscale à l'application. Vertex 1.0 Beta reste **DESKTOP ONLY** et
`Mobile UI = LATER`.

Travaille en lecture seule. Lis `CLAUDE.md`, `docs/99-status/NOW.md`,
`BLOCKERS.md` et l'état Git. Ne lance aucun test, n'installe rien, ne modifie
aucun fichier et ne reprends aucune tâche.

Réponds en français en huit lignes maximum, exactement dans ce format :

```text
LOT : NN — titre
ÉTAT : planned | running | blocked | review | done
BRANCHE : nom + propre/modifiée/divergente
FAIT : résultat vérifié le plus récent
TESTS : dernier résultat prouvé, jamais supposé
RISQUE : aucun ou risque principal
BLOCAGE : aucun ou un seul blocage précis
PROCHAINE COMMANDE : une seule commande sûre
```

Règles :

- une ligne par rubrique ;
- aucun tableau, préambule, historique, code ou explication après la huitième ligne ;
- `INCONNU` si une information n'est pas vérifiable ;
- ne jamais transformer `planned` en `running` ;
- ne jamais proposer le lot suivant si le lot courant n'est pas validé ;
- si Git contient des changements inconnus, la prochaine commande est une
  inspection ou une question, jamais une écriture.
