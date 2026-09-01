# Matrice des capacités de sources

| Capacité | IBKR TWS API | TradingView officiel | Vertex |
|---|---|---|---|
| Quotes/historique | automatique selon droits | alertes Pine ou export CSV | IBKR canonique |
| Options/Greeks | automatique, lignes limitées | contexte/alertes et interface | IBKR + calculs Vertex |
| Scanners | API, 10 scans actifs, 50 résultats par scan | Pine Screener et export CSV | fusion/dédoublonnage |
| News | API live/historique/articles selon abonnement API | interface riche, pas d'API générale supposée | IBKR + liens/sources primaires |
| Calendrier société | WSH avec abonnement séparé | calendrier UI et fonctions Pine ciblées | WSH + Pine + sources primaires |
| Fondamentaux | capacités et droits à sonder | `request.financial()` FactSet via Pine | SEC canonique US + signaux Pine |
| Macro | limité | `request.economic()` ciblé | FRED/ALFRED canonique |
| Earnings/dividendes/splits | WSH/ticks selon droits | fonctions Pine dédiées | événement canonique multi-source |
| ETF | contrats, quotes, news | screeners/fondamentaux/export | profil Vertex + documents officiels |
| Watchlists | liste IBKR si souhaitée sans compte | export TXT | liste canonique manuelle |
| Signaux techniques | calcul Vertex sur prix IBKR | alertes Pine versionnées | comparaison, jamais double verdict |

## Règle d'honnêteté

L'interface distingue la richesse visible dans une application de la capacité réellement exposée par une API ou un export autorisé. « Disponible dans TradingView » ne signifie pas « récupérable automatiquement par Vertex ».

## Sources officielles complémentaires

| Capacité | Source primaire | État Vertex après LOT-25 |
|---|---|---|
| Filings et faits US | SEC EDGAR | client livré, normalisation/persistance non branchées |
| Macro US point-in-time | FRED/ALFRED | client livré, clé locale obligatoire |
| Macro zone euro | BCE Data API | client livré, allowlist de séries à définir |
| Macro suisse | BNS Data Portal | client livré, allowlist de cubes à définir |
| Correspondance d'identifiants | OpenFIGI | client livré, ambiguïtés conservées |
| Événements société | IBKR WSH | adaptateur existant, abonnement séparé à sonder |
| Fondamentaux/estimations agrégés | FMP | désactivé en attente du plan et des droits |
| Analytique options payante | ORATS | désactivé en attente du plan et des droits |
