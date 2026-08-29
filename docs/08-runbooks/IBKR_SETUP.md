# Configuration IBKR

## Compte technique

Utiliser si possible un nom d'utilisateur secondaire dédié à TWS API. Les abonnements de données peuvent être propres à l'utilisateur ; vérifier leur disponibilité réelle avec celui qui lance TWS.

## Réglages

- commencer en paper ;
- activer socket clients ;
- activer Read-Only API ;
- limiter à localhost ;
- client ID Vertex `71`, non nul et non Master ;
- TWS Offline recommandé pour maîtriser les mises à jour ;
- auto-restart autorisé, réauthentification hebdomadaire acceptée ;
- synchronisation horaire OS activée.

## Droits à vérifier séparément

- quotes actions/ETF/indices ;
- données options et Greeks ;
- historique ;
- news API par fournisseur ;
- Wall Street Horizon Corporate Event Data ;
- delayed market data en secours clairement étiqueté.

La disponibilité dans l'interface TWS n'implique pas toujours le même droit API. Le LOT-04 construit un probe de capacités sans appeler compte, positions, ordres ou exécutions.

## Test d'acceptation

- connexion sur loopback ;
- heure serveur ;
- résolution SPY ;
- chaîne avec expirations/trading classes ;
- quote live ou delayed explicitement identifiée ;
- scanner ;
- fournisseurs news ;
- WSH ou statut `NOT_ENTITLED` ;
- aucun appel interdit dans trace/log/code.

