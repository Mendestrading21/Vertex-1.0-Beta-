# LOT-25 — Adaptateurs de sources officielles

## Références et dépendances

- `docs/09-adr/013-data-fusion-official-sources.md`
- `docs/09-adr/015-official-source-edge.md`
- `docs/04-integrations/OFFICIAL_SOURCE_MAP.md`
- `docs/04-integrations/SOURCE_RIGHTS_AND_RETENTION.md`
- `docs/03-domain/CANONICAL_CONTRACTS.md`
- LOT-02, LOT-03 et LOT-06 terminés.

## Objectif borné

Créer un bord HTTP lecture seule, testable sans réseau, pour SEC EDGAR,
FRED/ALFRED, OpenFIGI, la BCE et la BNS. Documenter Wall Street Horizon et les
fournisseurs payants sans les activer.

## Livrables

1. Package `vertex-edge-official` sans nouvelle dépendance tierce.
2. Allowlist HTTPS, refus des redirections, timeout et taille maximale.
3. Clients stricts et `DataEnvelope` pour les cinq sources.
4. Registre de capacités, droits, secrets locaux et fallbacks explicites.
5. Tests synthétiques de routes, provenance, ambiguïté et pannes.
6. Documentation d'installation et ADR.

## Non-objectifs

- persister ou normaliser les payloads dans PostgreSQL ;
- alimenter une page, un snapshot, un calcul ou un verdict ;
- appeler une API payante ou accepter des conditions au nom de l'utilisateur ;
- ajouter un fallback silencieux ;
- écrire une clé ou une donnée réelle dans Git.

## Contrôles

```bash
uv lock --check
uv run --no-sync ruff check .
uv run --no-sync mypy
uv run --no-sync pytest -q apps/edge-official/tests
python3 tools/check_secrets.py
python3 tools/check_financial_boundary.py
bash tools/run_checks.sh
```

## Sortie

- chaque source utilise uniquement son hôte officiel ;
- toute réponse sort dans un `DataEnvelope` honnête ;
- aucun secret n'apparaît dans payload, erreur, test ou commit ;
- les sources payantes restent explicitement désactivées ;
- aucune fusion ni publication automatique.
