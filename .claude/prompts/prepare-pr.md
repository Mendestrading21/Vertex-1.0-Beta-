# Prompt — Préparation d'une PR de lot

**Commande :** `PRÉPARE PR LOT NN`

Prépare les preuves et le texte de la PR du lot NN. Cette commande n'autorise pas
à pousser une branche, ouvrir une PR sur GitHub, fusionner, publier ou déployer.
Elle n'autorise pas non plus à corriger du code : si une anomalie apparaît,
retourne vers `CORRIGE LOT NN`.

## Contrôles préalables

Lis `CLAUDE.md`, la constitution, le lot, `NOW.md`, `BLOCKERS.md`, les ADR et la
checklist de PR disponible. Vérifie sans action destructive :

- branche `lot/NN-slug`, jamais `main` ;
- diff borné au lot et absence de fichiers inconnus ;
- absence de secrets, données réelles, caches, builds et artefacts locaux ;
- migrations et rollback documentés si concernés ;
- contrats et clients générés cohérents si concernés ;
- inventaire et notices des dépendances à jour ;
- tous les critères de sortie traçables à une preuve ;
- tous les checks requis exécutés, ou explicitement non exécutés avec raison ;
- `NOW.md`, historique et documentation cohérents.

Ne prétends jamais qu'une CI distante, un runner TWS, une restauration ou un test
de release a réussi sans preuve consultable.

## Verdict

Rends d'abord :

- `PRÊT À PR` si aucun blocage ne reste ;
- `NON PRÊT` si un critère, un test requis ou une preuve manque.

Si le verdict est `NON PRÊT`, liste uniquement les blocages et termine par une
seule commande `CORRIGE LOT NN` ou la commande de validation manquante.

## Texte de PR attendu

Si le verdict est `PRÊT À PR`, produis un brouillon copiable :

```markdown
## Lot

LOT-NN — titre

## Objectif

Résultat utilisateur et technique atteint.

## Périmètre

- Changements inclus
- Non-objectifs respectés

## Fichiers et contrats

- Modules principaux
- Contrats/migrations/ADR affectés

## Vérité financière et données

- Autorité utilisée
- Qualité, fraîcheur et comportement dégradé
- Confirmation de l'absence de capacité IBKR interdite

## Validation

| Commande | Résultat | Preuve |
|---|---|---|

## Interface

- Viewports desktop `1280×800`, `1440×900`, `1600×1000`, accessibilité, états et
  captures, si applicable ; `1024×768` seulement comme dégradation laptop utile
- Confirmation qu'aucune QA `390`/`360`, bottom nav ou `MobileActionBar` ne bloque
  Vertex 1.0 Beta ; `Mobile UI = LATER`, contrats sémantiques conservés

## Sécurité et dépendances

- Scans, licences, secrets et permissions

## Risques et rollback

- Risque résiduel
- Procédure de retour arrière

## Checklist

- [ ] Périmètre du lot uniquement
- [ ] Constitution et ADR respectés
- [ ] Documentation et NOW.md à jour
- [ ] Contrats et migrations validés
- [ ] Tests requis réussis
- [ ] Aucun secret ou donnée réelle
- [ ] Validation humaine requise avant merge
```

Ajoute un titre de PR `LOT-NN: résultat concis`, un résumé du diff et la liste des
captures ou artefacts à joindre. Termine par une seule prochaine commande humaine,
sans exécuter cette commande.
