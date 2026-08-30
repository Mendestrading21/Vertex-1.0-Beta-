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

La disponibilité dans l'interface TWS n'implique pas toujours le même droit API. Ne pas déduire un droit d'un écran TWS : le sonder.

## Sonder les droits RÉELS

`tools/probe_entitlements.py` lance la sonde décrite par
`docs/04-integrations/IBKR_ENTITLEMENT_PROBE.md` : six étapes bornées, une
seule sonde active, deux lignes de données au maximum, annulation dans un
`finally`. Elle n'appelle ni compte, ni positions, ni P&L, ni ordres, ni
exécutions.

### 1. Résolution — aucune ligne de données ouverte

```bash
python3 tools/probe_entitlements.py --symbol <SYMBOLE> --dry-run
```

Elle se connecte, qualifie le sous-jacent et imprime les définitions de chaîne
réellement renvoyées : exchanges, `trading_class`, multiplicateurs, échéances
et strikes. **Aucun symbole n'est proposé par défaut** : l'identité vient
entièrement de la ligne de commande, et toute ambiguïté (plusieurs contrats
qualifiés) arrête la sonde au lieu d'en choisir un.

### 2. Sonde

```bash
python3 tools/probe_entitlements.py --symbol <SYMBOLE> \
    --option-expiry <AAAAMMJJ> --option-strike <STRIKE> --option-right C \
    --option-trading-class <CLASSE> --option-exchange <BOURSE>
```

Les cinq arguments d'option sont obligatoires et vérifiés contre la chaîne
renvoyée à l'étape 1 : une échéance, un strike ou un couple
`exchange`/`trading_class` que la chaîne n'a pas annoncé est refusé.

La sortie est une matrice, un statut par champ, avec sa raison, son tick, son
type de marché et le code fournisseur éventuel. `ERROR` et timeout ne
signifient **jamais** `NOT_ENTITLED`.

Options utiles :

- `--allow-delayed-fallback` : re-demander en delayed si le live est REFUSÉ.
  Le résultat reste étiqueté `DELAYED`, jamais requalifié live.
- `--persist` : écrire l'observation de capacité en base (exige
  `VERTEX_DATABASE_URL`) pour que `/system` montre le RÉEL au lieu de
  `NEVER_TESTED`. Sans cette option, rien n'est écrit.
- `--tws-port` / `--client-id` : port et `client_id` API. Il n'existe
  **aucune** option d'hôte : l'adaptateur refuse tout hôte autre que
  `127.0.0.1`, et ne pas offrir le réglage est plus fort que le valider.

## Test d'acceptation

- connexion sur loopback ;
- heure serveur ;
- résolution du sous-jacent choisi, sans ambiguïté résiduelle ;
- chaîne avec expirations et `trading_class` distinctes, jamais fusionnées ;
- quote live ou delayed explicitement identifiée ;
- scanner ;
- fournisseurs news ;
- WSH ou statut `NOT_ENTITLED` ;
- aucun appel interdit dans trace/log/code.

