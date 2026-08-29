# Univers d'information

Le but n'est pas d'afficher tout ce que les abonnements rendent visible. Vertex collecte ce qui est officiellement accessible, conserve le contexte et présente uniquement ce qui répond à la tâche de la page.

## Marché et actions

- identité exacte, exchange principal, devise, calendrier et statut ;
- bid, ask, last, close, volume, tailles et type live/delayed ;
- barres intraday/journalières, ajustements et trous de couverture ;
- scanners, breadth, leaders/retardataires, volatilité et régime ;
- actualités liées, événements imminents et documents primaires.

## Options

- expirations, strikes, right, multiplier, classe de trading et `conId` ;
- bid/ask/last, volume, open interest, IV/Greeks fournisseur et horodatage ;
- couverture de chaîne, lignes non souscrites et contraintes de pacing ;
- courbes, dividendes, modèle, IV/Greeks Vertex et hypothèses séparés ;
- smile/skew, structure à terme, liquidité, payoff et scénarios.

## Entreprise

- identité, secteur/industrie, pays, devise et relations entre titres ;
- résultats, guidance, dividendes, splits, conférences et corporate actions ;
- faits financiers par période, devise, date de dépôt et révision ;
- filings SEC/EDGAR pour les émetteurs US et liens IR officiels ;
- estimations seulement si le fournisseur et le droit sont explicites.

## ETF

- émetteur, benchmark, type, domicile, devise et calendrier ;
- AUM, frais, performance et distributions lorsque sourcés ;
- expositions secteur/pays/facteur, holdings datées et couverture ;
- documents officiels et date de mise à jour ;
- chevauchement ou concentration calculés uniquement sur holdings suffisamment complètes.

## Actualités

- headline, fournisseur, article ID, heure, langue, droits et instruments ;
- accès au texte seulement si le droit API le permet ;
- regroupement multi-source conservant les divergences ;
- nouveauté, proximité temporelle et lien à watchlist/thèse/position manuelle ;
- résumé IA facultatif après cluster déterministe, avec citations.

## Calendriers

- macro : publication, consensus disponible, précédent, réel, importance et vintage ;
- société : earnings, dividende, split, conférence, IPO et corporate action ;
- marché : horaires, jours fériés, expirations et événements de contrat ;
- toute heure est conservée en UTC et affichée dans le fuseau choisi avec zone explicite ;
- prévision, confirmé, publié, révisé et annulé sont des états distincts.

## TradingView

- alertes techniques Pine versionnées ;
- faits ciblés via fonctions `request.*()` dans leurs limites ;
- watchlists TXT, screeners CSV et graphiques CSV importés manuellement ;
- lien profond vers l'interface pour le reste ; aucune aspiration automatisée de News Flow ou Calendars.

## Règle de sélection

Chaque élément reçoit des raisons déterministes : lien direct, portée marché, imminence, nouveauté, fiabilité, qualité et fraîcheur. La page montre au maximum trois raisons et permet d'ouvrir la provenance complète. Une absence d'entitlement ou de couverture reste visible dans Système.

