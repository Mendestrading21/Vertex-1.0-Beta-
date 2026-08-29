# Prompt — Reprise contrôlée après une pause

**Commande :** `REPRENDS`

Cette commande sert à retrouver un état fiable. Elle n'autorise pas à reprendre
l'exécution, modifier des fichiers, créer une branche, lancer une migration,
faire un commit, push, PR, merge ou déploiement.

## Inspection en lecture seule

Lis :

1. `CLAUDE.md` et la constitution ;
2. `docs/99-status/NOW.md`, `HISTORY.md` et `BLOCKERS.md` ;
3. le lot courant ;
4. les derniers résultats de tests enregistrés ;
5. l'état Git, la branche, le diff et le dernier commit, sans les modifier.

Compare le dépôt réel à `NOW.md`. Ne suppose pas qu'une opération interrompue est
terminée. N'efface pas de cache, ne restaure pas de fichier, ne fais pas de stash
et ne relance pas automatiquement une commande interrompue.

## Diagnostic

Détermine un seul des états suivants :

- `COHÉRENT` : Git et `NOW.md` concordent, prochaine étape certaine ;
- `À VÉRIFIER` : une preuve ou un test manque mais aucun conflit n'est constaté ;
- `DIVERGENT` : branche, diff ou statut contredit `NOW.md` ;
- `BLOQUÉ` : décision humaine ou précondition externe requise.

Si des modifications non attribuées existent, liste leurs chemins et arrête-toi.
Ne les adopte, ne les annule et ne les mélange pas au lot.

## Réponse compacte de pilotage Claude

Cette réponse peut être consultée depuis Remote Control sur téléphone. Elle sert
uniquement à piloter Claude Code et ne constitue ni une UI mobile Vertex ni un
accès Tailscale à l'application (`Mobile UI = LATER`).

Réponds en huit lignes maximum :

```text
REPRISE : COHÉRENT | À VÉRIFIER | DIVERGENT | BLOQUÉ
LOT : NN — titre
BRANCHE : nom + état
DERNIÈRE PREUVE : commit/test/étape vérifiée
EN COURS : opération atomique ou aucune
ÉCART : aucun ou description concise
RISQUE : aucun ou risque concret
PROCHAINE COMMANDE : une seule commande
```

La prochaine commande peut être `PLAN LOT NN`, `EXÉCUTE LOT NN`,
`AUDITE LOT NN`, `CORRIGE LOT NN` ou une question de clarification. Ne l'exécute
pas et ne commence jamais le lot suivant.
