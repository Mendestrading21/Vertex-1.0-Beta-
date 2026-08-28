# ADR-002 — Architecture local-first

- Statut : Accepté
- Date : 2026-08-28
- Portée : exécution, réseau, accès distant, continuité

## Contexte

TWS ou IB Gateway tourne sur l’ordinateur de marché. Les données et analyses doivent rester utilisables lorsque des services publics sont indisponibles. La Beta Vertex 1.0 est utilisée sur ce poste en desktop uniquement ; aucun accès Vertex depuis un téléphone n'est requis.

## Décision

Le runtime canonique est local.

- PostgreSQL, API, worker et web s’exécutent sur l’ordinateur Vertex, avec Docker Compose lorsque cela ne gêne pas TWS.
- L’agent IBKR s’exécute nativement sur l’hôte et communique avec TWS sur 127.0.0.1.
- Le web Vertex écoute uniquement pour le navigateur desktop local ; Tailscale Serve et Funnel ne sont pas déployés pour la Beta.
- Le téléphone sert uniquement à Claude Remote Control. Il n'est ni un client Vertex ni une voie d'accès à la PWA, l'API, PostgreSQL ou TWS.
- Le seul composant public est l’ingress TradingView séparé ; il ne possède ni portefeuille, ni calcul, ni secret IBKR.
- Les sauvegardes quittent le disque principal sous forme chiffrée et sont régulièrement restaurées.
- Une panne du cloud désactive les nouvelles alertes TradingView, jamais le portefeuille manuel ni la consultation locale.

## Conséquences

### Positives

- Surface d’exposition réduite et latence faible vers TWS.
- Données personnelles et financières conservées localement.
- Continuité de service partielle sans dépendance au cloud.
- Aucun service Vertex distant à sécuriser ou maintenir pendant la Beta.

### Coûts et contraintes

- Le poste doit gérer démarrage, mises à jour, stockage, sauvegardes et supervision.
- Claude Remote Control reste hors du runtime, des contrats et de l'authentification Vertex.
- Les performances et l’espace disque doivent être budgétés.

## Options rejetées

| Option | Motif du rejet |
|---|---|
| Backend entièrement cloud | Exposerait davantage les données et compliquerait le lien TWS |
| Port public ou redirection NAT | Surface d’attaque inutile |
| Tailscale Serve ou Funnel pour Vertex Beta | Créerait un accès distant et un périmètre mobile hors phase |
| Application desktop native en premier | Dupliquerait le web avant validation du produit |

## Critères de réexamen

Un composant peut être déplacé hors du poste uniquement après analyse de menace, chiffrement, réversibilité, coût, continuité et preuve qu’il ne peut pas accéder au portefeuille ou à TWS au-delà de son mandat.
