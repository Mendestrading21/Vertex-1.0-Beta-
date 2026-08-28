# Stratégie de tests

## Pyramide

- unitaires : contrats, règles et fonctions pures ;
- propriétés : invariants financiers avec Hypothesis ;
- différentiels : QuantLib, SciPy et oracle indépendant ;
- contrats : JSON Schema, OpenAPI et compatibilité événementielle ;
- intégration : PostgreSQL réel, migrations, outbox, TWS simulé et Cloudflare simulé ;
- résilience : déconnexion, duplication, désordre, panne, horloge, disque ;
- composants/visuels : Storybook et captures ;
- E2E : 12 parcours Playwright sur trois navigateurs ;
- sécurité, accessibilité, charge et soak.

## Couverture

- 100 % des branches des gates, décision, comptabilité, fraîcheur et contrats critiques ;
- ≥ 90 % branches du cœur financier ;
- ≥ 80 % autres modules backend ;
- ≥ 85 % frontend hors code généré ;
- mutation score ≥ 95 % sur modules critiques sans mutant dangereux survivant.

Les seuils ne remplacent pas les invariants.

## Matrices indispensables

- live/delayed/frozen/stale/partial/offline/error ;
- séance ouverte/fermée, DST, demi-séance, jour férié ;
- actions/ETF/indices/options, devises et multiplicateurs ;
- desktop Phase 1 à 1280×800, 1440×900 et 1600×1000 ;
- laptop dégradé à 1024×768, sans masquage de vérité financière ni d'action essentielle ;
- TWS codes 1100/1101/1102/1300/502 ;
- alertes TradingView valides, dupliquées, vieilles, futures, désordonnées, trop grosses et forgées ;
- news dupliquées et événements révisés ;
- entitlements disponibles, manuels, absents et erronés ;
- IA valide, invalide, indisponible et prompt injection.

## Données de test

Fixtures synthétiques uniquement. Golden vectors versionnés avec provenance mathématique. Les données commerciales ou personnelles ne sont jamais enregistrées dans Git.

La Beta n'exécute aucun QA d'interface téléphone. L'interface mobile reste `LATER` ; les contrats OpenAPI, états et DTO demeurent indépendants du viewport afin de permettre ce client futur sans fork métier.
