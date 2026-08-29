# Gates CI

| Check | Contenu | Bloque si |
|---|---|---|
| `policy` | SHA Actions, permissions, lockfiles, capacités interdites, aucun `latest` | anomalie |
| `python-quality` | Ruff, mypy strict, architecture/imports | erreur |
| `web-quality` | Biome, `tsc --noEmit`, Vitest | erreur |
| `contracts` | JSON Schema/OpenAPI, client généré, compat, exemples | diff/rupture |
| `migrations` | upgrade, rollback supporté, restauration sur PostgreSQL réel | échec |
| `finance-unit` | calculs, ledger, gates, décision | échec |
| `finance-property` | invariants Hypothesis/différentiels | contre-exemple |
| `fusion` | identité, déduplication, conflits, entitlements | dérive |
| `integration` | PostgreSQL, outbox, TWS fake, Queue fake | échec |
| `security` | secrets, SAST, dépendances, licence | non-conformité |
| `build` | images non-root/digest, web, agent Windows | échec |
| `e2e` | parcours critiques Chromium sur PR | échec |
| `a11y` | axe, clavier, focus, contraste | critique/sérieux |
| `performance` | bundle, Lighthouse, Locust smoke | budget dépassé |
| `release` | SBOM, provenance, signature, notices | preuve absente |

Nuit : Firefox/WebKit, visuels, mutations, charge, pannes et tests de données. Release : TWS paper/read-only, restauration, rollback et soak.

GitHub Actions : `permissions: read-all` par défaut, élévation par job, timeouts, aucun `pull_request_target` dangereux et chaque action épinglée à un SHA complet. Aucun runner de PR sur l'ordinateur TWS.

