# Prompt — Correction ciblée d'un lot en échec

**Commande :** `CORRIGE LOT NN`

Cette commande autorise uniquement la correction des défauts déjà consignés pour
le lot NN. Elle n'autorise ni refonte générale, ni nouvelle fonctionnalité, ni
lot suivant, ni push, PR, merge ou déploiement.

## Sources de vérité des défauts

Lis complètement :

1. `CLAUDE.md` et la constitution ;
2. `docs/99-status/NOW.md` et `BLOCKERS.md` ;
3. le lot NN et ses critères de sortie ;
4. le dernier rapport `AUD-NN-*` fourni dans la conversation ou enregistré dans
   la documentation autorisée ;
5. les sorties de tests ou CI exactes liées à ces constats.

Si aucun défaut précis et reproductible n'est fourni, n'interprète pas la commande
comme une autorisation générale : reste en lecture seule et demande le rapport ou
propose `AUDITE LOT NN`.

## Prévol

- Vérifie la branche `lot/NN-slug` et l'état Git.
- Préserve toutes les modifications utilisateur ou non liées.
- Reproduis chaque défaut avec le test le plus étroit possible.
- Établis la liste fermée des identifiants `AUD-NN-*` à corriger.
- Relie chaque correction à un test de non-régression.

Si une correction requiert une nouvelle dépendance, une migration destructive, un
changement d'ADR, une exposition réseau, un fournisseur ou une modification de
l'autorité financière, arrête-toi et pose une seule question bloquante.

## Méthode

Pour chaque identifiant, dans l'ordre de sévérité :

1. confirme la cause racine ;
2. ajoute ou resserre le test qui reproduit l'échec ;
3. applique le correctif minimal dans le bon module propriétaire ;
4. exécute le test ciblé ;
5. exécute les gates du lot susceptibles d'être affectées ;
6. vérifie qu'aucun contrat, calcul ou fallback concurrent n'a été introduit.

Ne masque jamais un échec en supprimant un test, abaissant un seuil, ajoutant un
`skip`, ignorant une erreur, élargissant une tolérance sans justification ou
remplaçant une donnée absente par un mock.

## Clôture

Mets à jour `NOW.md`, `BLOCKERS.md` et les preuves concernées. Pour chaque constat,
indique `CORRIGÉ`, `NON CORRIGÉ` ou `BLOQUÉ`, avec la commande et le résultat qui
le prouvent.

Termine au format compact de pilotage Claude. Il peut être lu depuis Remote
Control sur téléphone, mais ne décrit ni une UI mobile Vertex ni un accès
Tailscale à l'application (`Mobile UI = LATER`) :

```text
LOT : NN — correction
ÉTAT : review | blocked
CORRIGÉS : identifiants
NON CORRIGÉS : identifiants ou aucun
FICHIERS : chemins principaux
TESTS : commandes exactes et résultats
RISQUE : aucun ou risque concret
PROCHAINE COMMANDE : AUDITE LOT NN
```

Ne commence aucune amélioration supplémentaire.
