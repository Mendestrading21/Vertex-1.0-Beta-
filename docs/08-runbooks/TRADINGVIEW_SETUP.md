# Configuration TradingView

## Préparation

- activer 2FA ;
- créer une watchlist Vertex avec symboles `EXCHANGE:TICKER` ;
- vérifier les fonctions Pine disponibles dans le plan actif ;
- créer un compte Cloudflare dédié ou un projet isolé ;
- commencer sur Workers/Queues Free lorsque ses limites suffisent ; ne jamais activer une offre payante ou une facturation sans validation humaine ;
- ne mettre aucun secret, compte ou position dans une alerte.

## Flux automatique

Le LOT-05 déploie Worker, Queue et DLQ. Une alerte Pine JSON utilise le contrat dans `contracts/json-schema/`. Le Worker répond en moins de trois secondes après mise en file.

Au 28 août 2026, la documentation Cloudflare annonce 10 000 opérations Queue par jour et 24 heures de rétention sur Free. Le LOT-05 doit revérifier les chiffres et le besoin réel avant création : https://developers.cloudflare.com/queues/platform/pricing/

Après chaque modification du script ou des paramètres, supprimer et recréer l'alerte ; augmenter `script_version`.

## Flux manuels riches

- watchlist → Advanced View → Download list as TXT ;
- screener actions/ETF/Pine → Export screen results CSV ;
- Supercharts → Download chart data CSV après chargement de la période voulue.

Vertex importe ces fichiers par glisser-déposer avec aperçu et provenance. Aucun dossier Downloads n'est surveillé sans consentement explicite.

## Contrôle

Comparer les derniers événements acceptés au Webhook Status/Alert Log TradingView. Une absence d'alerte n'est pas interprétée comme l'absence d'événement.
