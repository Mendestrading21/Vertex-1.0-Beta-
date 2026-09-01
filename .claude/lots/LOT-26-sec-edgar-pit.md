# LOT-26 — SEC EDGAR point-in-time

## Références et dépendances

- LOT-25 et ADR-015 : bord HTTP officiel déjà livré.
- ADR-013 : sources officielles, corrections et preuve point-in-time.
- `docs/04-integrations/SOURCE_RIGHTS_AND_RETENTION.md`.
- `fundamental_filing/1.0.0` : fraîcheur de sept jours.

## Objectif borné

Transformer les réponses SEC Submissions et Company Facts d'un CIK
explicitement associé à un instrument en observations typées, persistables et
rejouables, puis publier un snapshot officiel par instrument et le relayer par
l'API. Aucun fait SEC ne devient automatiquement un ratio, un score, une
opportunité ou un avis.

## Livrables

1. Contrats immuables `Filing` et `FundamentalFact` avec accession, unité,
   période, `available_at`, amendement et provenance des deux réponses brutes.
2. Normaliseur déterministe `normalize_sec_edgar`, sans look-ahead : heure
   d'acceptation SEC, ou borne conservatrice au jour UTC suivant le dépôt.
3. Ingestion append-only idempotente et topic dédié
   `sec.fundamentals.ingested`.
4. Snapshot `sec_fundamentals/{instrument}` : corrections conservées,
   conflits simultanés publiés et jamais élus silencieusement, budgets de
   500 faits et 50 dépôts avec compte de troncature.
5. Relais protégé
   `GET /api/v1/sources/sec/{instrument}/fundamentals`, état vide/périmé
   honnête et signal SSE par préfixe.
6. Commande one-shot `tools/run_sec_edgar.py` : récupération des deux réponses,
   normalisation, reçu sans payload et persistance seulement avec `--persist`.
   Les corps bruts restent en mémoire car leur rétention maximale est 24 h ;
   les observations normalisées gardent leurs identifiants et hash sources.

## Non-objectifs

- calculer des ratios ou compléter un fait manquant ;
- alimenter `AdviceEngine`, Analyse ou Opportunités ;
- choisir automatiquement un CIK à partir d'un ticker ;
- archiver durablement les payloads bruts SEC ;
- planifier la collecte ou contourner la politique Fair Access ;
- intégrer FRED/ALFRED ou une autre famille du parcours.

## Tests rouges puis correctifs

- import du normaliseur absent : `ModuleNotFoundError` avant implémentation ;
- droits SEC avec ponctuation refusés par le contrat de relais, remplacés par
  le code canonique `R1_PUBLIC_FACT_SEC_EDGAR_POLICY_2026_08_28` ;
- conflit de faits de même clé et même disponibilité : valeur omise, conflit
  et candidats publiés ;
- CIK contradictoires pour un même instrument : identité non résolue, aucune
  valeur métier publiée.

## Contrôles

```bash
uv run --no-sync pytest -q apps/edge-official/tests/test_sec_normalize.py
uv run --no-sync pytest -q apps/worker/tests/test_sec_fundamentals.py
uv run --no-sync pytest -q apps/api/tests/test_sec_fundamentals_route.py
uv run --no-sync ruff check .
uv run --no-sync mypy
env -u ALL_PROXY -u HTTPS_PROXY -u HTTP_PROXY uv run --no-sync pytest -q
python3 tools/check_secrets.py
python3 tools/check_financial_boundary.py
bash tools/run_checks.sh
```

## Vérification réelle locale

```bash
export VERTEX_SEC_USER_AGENT='Vertex research contact@example.com'
uv run python tools/run_sec_edgar.py --cik 320193 --instrument AAPL

export VERTEX_DATABASE_URL='postgresql+psycopg://...'
uv run python tools/run_sec_edgar.py --cik 320193 --instrument AAPL --persist
```

La première commande ne persiste rien. La seconde exige une base explicite,
reste idempotente et ne journalise ni DSN ni payload.

## Rollback

Revenir au commit parent du lot retire le normaliseur, le topic, le snapshot,
la route et la commande. Les observations déjà écrites restent append-only ;
leur retrait éventuel relève d'une procédure de données séparée et ne doit
jamais être caché dans un rollback de code.

## Sortie

- les faits SEC ont une disponibilité prouvée et aucune visibilité future ;
- les corrections ne détruisent pas l'historique ;
- provenance, droits, conflits, troncature, âge et absence traversent la chaîne ;
- aucun verdict financier n'est modifié ;
- le lot suivant n'est pas démarré automatiquement.
