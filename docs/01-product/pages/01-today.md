# Page 01 — Aujourd'hui `/today`

## Question

Qu'est-ce qui mérite réellement mon attention maintenant ?

## Dominante et modules

Dominante : file verticale de 8 à 15 éléments filtrés, jamais une mosaïque de KPI.

1. Bandeau séance, régime et santé des sources.
2. File d'attention fusionnant incidents, actualités, événements, risques, thèses et opportunités.
3. Fenêtre des prochaines 24 heures.
4. Expositions manuelles les plus concernées.

Action principale : ouvrir le dossier de l'élément prioritaire.

## Données et logique

`NewsCluster`, `CorporateEvent`, `MacroEvent`, `PortfolioRisk`, `Thesis`, `AdviceResult`, `SourceHealth`. Classement lexicographique : sécurité/qualité, position, thèse, watchlist, portée marché, nouveauté et fraîcheur. Chaque ligne montre jusqu'à trois `relevance_reasons` et ses sources.

## États et adaptation desktop

Squelette par lignes ; vide = « rien ne demande votre attention » ; delayed/stale = âge exact et calcul bloqué si nécessaire ; offline = dernier briefing daté. Cible Vertex 1.0 Beta : 1280, 1440 et 1600 px. À 1024 px, le rail reste replié et les modules secondaires passent sous la file d'attention sans changer sa priorité.

Mobile : **LATER**. Les contrats sémantiques de la file, des états, de l'action et du focus sont conservés, sans rendu Vertex pour téléphone ; Claude Remote Control ne fait que piloter la session desktop.

## Acceptation

- aucun doublon de news visible dans un cluster ;
- moins de 15 éléments par défaut malgré une ingestion large ;
- chemin clavier complet ;
- p95 API ≤ 250 ms sur snapshot préparé ;
- E2E : incident, news liée à une position, événement et état offline.
