# Frontières des modules

| Module | Possède | Ne possède jamais |
|---|---|---|
| `contracts` | Schémas, identités, unités, versions | Accès réseau ou calcul métier |
| `instruments` | Résolution et symbologie | Prix ou verdict |
| `market_data` | Observations et snapshots | Conseil |
| `news_events` | Actualités, événements, déduplication | Sentiment autoritaire |
| `data_quality` | Entitlements, fraîcheur, qualité, couverture | Fallback silencieux |
| `quant` | Prix, IV, Greeks, indicateurs, scénarios | HTTP, UI ou stockage direct |
| `portfolio` | Ledger manuel, cashflows, expositions | Lecture de compte IBKR |
| `decision` | Gates et `AdviceEngine` unique | Génération de texte libre |
| `application` | Cas d'usage et transactions | Formules dupliquées |
| `persistence` | SQLAlchemy, migrations, outbox | Règles financières |
| `adapters` | IBKR, TradingView, SEC, FRED | Décision |
| `api` | REST, SSE, auth, OpenAPI | Calcul CPU dans l'event loop |
| `web` | Présentation et interactions | Calcul financier autoritaire |
| `ai` | Explication de DTO certifiés | Outils à effet de bord ou verdict |
| `research` | Snapshots copiés, Parquet, backtests | Écriture dans le runtime live |

Le domaine pur ne dépend pas de FastAPI, SQLAlchemy, IBKR, Cloudflare, React ou d'un fournisseur IA.

