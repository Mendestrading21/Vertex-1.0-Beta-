# États d'interface

| État | Affichage | Autorité |
|---|---|---|
| `loading` | squelette seulement au premier chargement | aucun résultat nouveau |
| `refreshing` | ancienne donnée visible + activité discrète | conserve sa date |
| `empty` | cause et action corrective | jamais valeur zéro |
| `partial` | couverture et champs manquants | gates selon usage |
| `delayed` | badge et retard annoncé | jamais « live » |
| `stale` | watermark, heure exacte | recalcul live bloqué |
| `offline` | snapshot local daté | lecture/brouillons seulement |
| `error` | dernière donnée valide si possible + diagnostic | pas de faux succès |

`DataStateBoundary` reçoit l'état du backend. Il ne déduit pas la fraîcheur à partir de l'heure du navigateur.

Les erreurs d'une source ne vident pas les autres sections. Chaque module peut être disponible, partiel ou indisponible indépendamment, tandis que la page expose un résumé global honnête.

