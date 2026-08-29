# ADR-010 — Tests fondés sur invariants et systèmes réels

- Statut : Accepté
- Date : 2026-08-28
- Portée : finance, contrats, intégrations, web, sécurité

## Contexte

Un grand nombre de tests ne prouve pas la justesse financière. Les erreurs critiques concernent les limites, les unités, la fraîcheur, la concurrence, les retries et les états dégradés. Les mocks seuls masquent les différences de PostgreSQL, navigateur et protocoles.

## Décision

- Les fonctions financières critiques ont exemples, invariants Hypothesis et oracle indépendant.
- Gates, décision, comptabilité, fraîcheur et contrats couvrent 100 pour cent de leurs branches.
- PostgreSQL réel valide migrations, transactions, partitions, outbox et concurrence.
- Des fakes protocolaires TWS et Cloudflare reproduisent succès, erreurs, doublons, ordre inversé et déconnexion.
- Les contrats JSON Schema et OpenAPI ont exemples valides et invalides et vérification de compatibilité.
- Playwright exécute les parcours critiques sur Chromium en PR, puis Firefox et WebKit la nuit.
- axe, clavier, focus, contraste, états dégradés et tables alternatives sont testés.
- Charge, soak, mutation, sécurité, sauvegarde et restauration font partie des gates prévues.
- Un test ignoré exige justification, propriétaire et date d’expiration.

## Conséquences

### Positives

- Les preuves ciblent les risques réels plutôt qu’un compteur.
- Les régressions de données, concurrence et rendu sont détectées tôt.
- Chaque release possède des éléments auditables.

### Coûts et contraintes

- La CI est plus longue et doit séparer PR, nuit et release.
- Les fixtures synthétiques et golden vectors doivent être entretenus.
- Les oracles tiers ne sont jamais aveuglément considérés comme vrais.

## Options rejetées

| Option | Motif du rejet |
|---|---|
| Couverture de lignes comme seul objectif | Ne prouve ni invariants ni limites |
| SQLite pour tester PostgreSQL | Sémantiques différentes |
| Mocks de bout en bout | Masquent les pannes d’intégration |
| Tests uniquement en navigateur simulé | Ne valide pas le rendu réel |
| Validation manuelle avant release | Non reproductible |

## Critères de réexamen

Les seuils peuvent évoluer à la hausse ou être remplacés par une preuve supérieure. Une réduction exige données de durée, risque couvert autrement et ADR explicite.
