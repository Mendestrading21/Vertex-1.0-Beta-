# Budgets de performance

## Web

- LCP ≤ 2,5 s ;
- INP ≤ 200 ms ;
- CLS ≤ 0,1 ;
- bundle initial ≤ 300 Ko gzip recommandé ;
- ECharts et Lightweight Charts chargés par route ;
- navigation cached p95 ≤ 250 ms ;
- interactions usuelles 60 FPS ;
- aucun calcul quantitatif sur le thread UI.

## API et jobs

- lecture snapshot cached p95 ≤ 250 ms, p99 ≤ 750 ms ;
- opérations écriture idempotentes ;
- calculs lourds hors event loop ;
- budget mémoire explicite pour chaînes options ;
- backpressure avant dépassement IBKR ;
- temps/ressources de chaque calcul enregistrés.

## Données

PostgreSQL partitionné et indexé d'abord. TimescaleDB, Redis ou autre service ne sont justifiés que par benchmark reproductible et ADR.

