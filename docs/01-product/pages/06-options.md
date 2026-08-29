# Page 06 — Options `/options/:underlying`

## Question

Quels contrats sont réellement exploitables et quels risques portent-ils ?

## Dominante et modules

Dominante : chaîne virtualisée Calls / Strikes / Puts.

1. Sous-jacent, expiration, trading class et liquidité.
2. Chaîne dominante.
3. Smile/skew et structure à terme.
4. Inspecteur contrat : quote, IV, Greeks, hypothèses, anomalies et événement proche.

Action principale : envoyer le contrat ou la structure au Simulateur. Aucun bouton d'ordre.

## Données et logique

Contrats/quotes IBKR, sous-jacent, taux, dividendes, événements, modèles QuantLib et calculs Vertex. IV bid/mid/ask, parité, spreads, coverage et âge. GEX séparé et étiqueté estimation.

## États et adaptation desktop

Une expiration sans droit explique la permission. Stale : ne pas recalculer IV/Greeks. Cible Vertex 1.0 Beta : 1280, 1440 et 1600 px. À 1024 px, la chaîne Calls / Strikes / Puts conserve sa structure, autorise un défilement horizontal maîtrisé et place l'inspecteur sous la chaîne.

Mobile : **LATER**. Les contrats sémantiques des contrats, quotes, colonnes, états, sélection et action vers le Simulateur sont conservés, sans variante Vertex pour téléphone.

## Acceptation

- dates dupliquées par trading class correctement séparées ;
- lignes visibles seules abonnées ;
- saturation/pacing testés ;
- aucun ordre ou compte dans bundle, API et logs ;
- E2E chaîne partielle, quote croisée, delayed et reconnexion.
