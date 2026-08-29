# Pack Pine Vertex v1 — NON TESTÉ EN PLATEFORME

Statut : **NON TESTÉS EN PLATEFORME — validation au déploiement humain.**
Aucun de ces scripts ne peut être compilé ni exécuté dans l'environnement
local ; la compilation TradingView et le contrôle des golden payloads font
partie de la checklist de mise en service
(`apps/ingress-tradingview/README.md` et `docs/08-runbooks/TRADINGVIEW_SETUP.md`).

## Contenu

| Fichier | Rôle |
|---|---|
| `vertex_alert_contract.pine` | Library : fonction unique de construction du message JSON `vertex.tradingview.alert.v1` (source de vérité du contrat côté Pine) |
| `vertex_market_sensor.pine` | Régime SMA + cassures Donchian (`REGIME_CHANGE`, `BREAKOUT`, `BREAKDOWN`) |
| `vertex_company_sensor.pine` | Earnings, dividendes, splits via `request.earnings/dividends/splits` (`FUNDAMENTAL_UPDATE`, `EVENT`) |
| `vertex_macro_sensor.pine` | Publications macro via `request.economic` (`EVENT`) |

Tant que la library n'est pas publiée sur TradingView, chaque sensor embarque
une **copie synchronisée v1** des fonctions du contrat (l'import d'une library
exige sa publication préalable). Toute divergence entre une copie et la
library est un défaut à corriger immédiatement.

## Règles du pack

- Pine v6 ; signaux émis **uniquement sur barre confirmée**
  (`barstate.isconfirmed`) et `alert.freq_once_per_bar_close` ; chaque script
  documente en en-tête pourquoi il ne repeint pas.
- `request.*()` avec `barmerge.gaps_on` (+ `lookahead_off` quand le paramètre
  existe) : valeur seulement sur la barre de publication, aucune fuite du
  futur.
- Nonce déterministe = `time` (ouverture de barre, ms) dans `values.nonce` ;
  clé de déduplication ingress `alert_id + ":" + nonce`.
- **Aucun secret** dans un script ou un corps d'alerte ; la capacité de route
  vit uniquement dans l'URL webhook.
- Les alertes sont des **déclencheurs non autoritaires** : jamais un prix
  canonique, jamais un verdict — revalidation IBKR obligatoire (ADR-005).
- Toute modification d'un script impose d'incrémenter `script_version`
  (format `YYYY-MM-DD.N`), de mettre à jour le registre local
  (`vertex_ingress_tv.registry`) et de **recréer** les alertes TradingView.
