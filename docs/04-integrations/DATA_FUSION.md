# Data Fusion Hub — IBKR, TradingView et sources primaires

## Principe

Vertex maximise la collecte autorisée, puis réduit le bruit. Il ne se limite pas aux cours ou à quelques indicateurs. Les familles d'information sont :

- marché : quotes, volume, volatilité, historique, breadth et scanners ;
- options : contrats, chaînes, bid/ask, IV, Greeks, OI et volumes ;
- actualités : headlines, articles, historique et sources ;
- calendrier : macro, résultats, dividendes, splits, expirations, conférences, IPO et opérations sur titres ;
- entreprise : identité, secteur, rapports, fondamentaux, estimations disponibles et événements ;
- ETF : identité, benchmark, actifs, exposition, performance et documents officiels lorsque disponibles ;
- technique : signaux Pine, price action, volume, régimes et conditions multi-timeframe ;
- utilisateur : watchlists, portefeuille manuel, thèses, alertes et historique de consultation.

## Règle de source par domaine

| Domaine | Source prioritaire | Complément | Limite affichée |
|---|---|---|---|
| Prix live/options | IBKR API | TradingView alerte comme déclencheur | type live/delayed et abonnement |
| Contrats | IBKR `conId` + métadonnées | symbologie TradingView | ambiguïtés en quarantaine |
| Scanner | IBKR scanner | export/Pine Screener TradingView | couverture et heure du scan |
| Actualités | fournisseurs news IBKR API | source primaire/IR autorisée | droits article et fournisseur |
| Événements société | IBKR WSH si souscrit | SEC, Pine `request.earnings/dividends/splits` | source et certitude |
| Fondamentaux US | SEC XBRL/filings | Pine `request.financial` FactSet | période, devise, date de dépôt |
| Macro | FRED/ALFRED + organismes | Pine `request.economic` | vintage point-in-time |
| Techniques | calcul serveur sur données IBKR | Pine TradingView | version du script et timeframe |
| Watchlist | liste canonique Vertex | import TXT TradingView | synchro manuelle horodatée |
| Screeners TV | import CSV officiel | scanner IBKR | fichier et filtres conservés |
| News/calendrier UI TradingView | non aspiré | lien profond vers TradingView | pas d'API grand public supposée |

## Contrats de fusion

Créer au minimum :

- `NewsItem`, `NewsCluster`, `ArticleAccess` ;
- `CorporateEvent`, `MacroEvent`, `EventRevision` ;
- `FundamentalFact`, `Filing`, `EtfProfile`, `EtfExposure` ;
- `TechnicalSignal`, `ScannerResult`, `WatchlistSnapshot` ;
- `SourceEntitlement`, `SourceCoverage`, `FusionDecision` ;
- `RelevanceReason`, `EntityLink`, `ConflictRecord`.

## Déduplication

1. Identifiant natif du fournisseur.
2. URL canonique et horodatage.
3. Empreinte normalisée du titre et des entités.
4. Fenêtre temporelle et similarité comme aide, jamais comme suppression irréversible.
5. Un cluster conserve tous les fournisseurs, droits et dates de mise à jour.

L'IA peut résumer un cluster après regroupement déterministe. Elle ne décide pas que deux faits contradictoires sont identiques.

## Classement personnel

Le classement est décomposable : lien direct à une position, thèse, watchlist ou instrument ouvert ; portée marché ; proximité temporelle ; nouveauté ; fiabilité ; qualité ; fraîcheur. L'écran montre trois raisons maximum et permet d'ouvrir le détail complet.

## Entitlements

Un abonnement visible dans TWS ou TradingView ne garantit pas un accès automatisé identique. Au démarrage, Vertex sonde uniquement les capacités autorisées et construit une matrice : `AVAILABLE`, `DELAYED`, `MANUAL_EXPORT`, `NOT_ENTITLED`, `UNSUPPORTED` ou `ERROR`.

Un manque de droit ne déclenche jamais un remplacement silencieux. La page Sources & Rapports explique l'abonnement ou l'export nécessaire.

## Imports TradingView officiels

- watchlist TXT : import idempotent avec aperçu du diff ;
- screener CSV : conserve date, colonnes, filtres et univers ;
- graphique CSV : conserve symbole, timeframe, timezone, indicateurs et plage ;
- aucun import de données de compte ou de stratégie n'alimente le portefeuille réel.

