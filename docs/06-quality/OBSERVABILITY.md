# Observabilité

OpenTelemetry dans API, worker, edge et ingress. Logs JSON avec `trace_id`, `event_id`, version de calcul et hash de configuration.

## Métriques

- âge, type de délai, qualité et couverture par source ;
- état/epoch/reconnexions/pacing IBKR ;
- droits news/WSH/market data ;
- alertes TradingView acceptées/rejetées/dupliquées ;
- retard Queue, tentatives et DLQ ;
- imports TV réussis/échoués ;
- conflits d'identité/news/événements ;
- temps de calcul, erreurs numériques, gates bloquées ;
- DB, outbox, disque, migrations ;
- âge backup et dernière restauration ;
- API p50/p95/p99, erreurs et Web Vitals ;
- dérive d'horloge.

Ne jamais utiliser ticker, texte utilisateur ou identifiant de portefeuille comme label métrique à forte cardinalité.

## Alertes initiales

- source critique stale ;
- IBKR down pendant période surveillée ;
- pacing > budget ;
- DLQ > 0 ;
- hausse d'échecs webhook ;
- taux erreur > 1 % sur cinq minutes ;
- disque < 20 % ;
- backup > 26 h ;
- restauration testée > 35 jours ;
- horloge > 2 s ;
- entitlement critique perdu.

Prometheus/Alertmanager sont retenus pour les métriques. Grafana est facultatif et isolé, sa licence AGPL étant inventoriée. Aucun payload financier complet n'est exporté vers un SaaS d'observabilité.

