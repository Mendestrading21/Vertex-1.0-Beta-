# Page 05 — Analyse `/analysis/:instrument`

## Question

Que disent les données certifiées sur cet instrument, et quelles limites restent ouvertes ?

## Dominante et modules

Dominante : chandeliers/volume Lightweight Charts, deux overlays maximum.

1. Carte `AdviceResult`, validité et gates.
2. Graphique prix/volume.
3. Rail de preuves : news, événements, fondamentaux, techniques et contradictions.
4. Scénarios baissier/neutre/haussier avec hypothèses.

Action principale : enregistrer ou mettre à jour une thèse.

## Données et logique

Quotes/bars IBKR, signaux Pine, clusters de news, calendrier, filings/faits, contexte portefeuille et résultat canonique. Les niveaux, tendances, volatilité et scénarios viennent du serveur. Une alerte TradingView est montrée comme preuve secondaire avec version du script.

## États et adaptation desktop

Avis expiré et watermark sur stale. Offline : snapshot consultable sans recompute. Cible Vertex 1.0 Beta : 1280, 1440 et 1600 px. À 1024 px, le graphique reste dominant et le rail de preuves passe sous le graphique en conservant le même ordre de lecture et de focus.

Mobile : **LATER**. Les contrats sémantiques du snapshot, des preuves, scénarios, états et actions sont conservés, sans rendu Vertex pour téléphone.

## Acceptation

- attribution TradingView conforme pour Lightweight Charts ;
- source/heure/unité visibles ;
- alternative tableau OHLCV ;
- E2E contradiction, alerte Pine, news cluster et gate bloquante.
