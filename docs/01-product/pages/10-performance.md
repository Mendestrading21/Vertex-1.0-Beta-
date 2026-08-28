# Page 10 — Performance `/performance`

## Question

Quelle performance ai-je réellement enregistrée, avec quels risques et contributions ?

## Dominante et modules

Dominante : courbe de valeur et drawdown synchronisés.

1. Capital/drawdown.
2. Bandeau de métriques définies.
3. Heatmap mensuelle.
4. Attribution lorsque la couverture le permet.

Action principale : exporter les données et hypothèses.

## Données et logique

Ledger manuel, cashflows, frais, FX et benchmark. TWR/XIRR séparés ; brut/net explicites ; Sharpe, volatilité et drawdown avec conventions. Populations réel, hypothétique, théorique et démo séparées.

## États et adaptation desktop

Si le mark live est stale, l'historique réalisé reste valide et la valeur actuelle est marquée. Cible Vertex 1.0 Beta : 1280, 1440 et 1600 px. À 1024 px, valeur, drawdown, métriques et attribution s'empilent dans cet ordre tout en conservant l'alternative tabulaire.

Mobile : **LATER**. Les contrats sémantiques des séries, métriques, populations, états et export sont conservés, sans rendu Vertex pour téléphone.

## Acceptation

- vecteurs de référence TWR/XIRR/drawdown ;
- aucune agrégation inter-populations ;
- alternative tabulaire ;
- E2E cashflow externe, changement FX et historique incomplet.
