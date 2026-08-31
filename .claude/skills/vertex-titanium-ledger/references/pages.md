# Architecture détaillée des douze écrans

## Règle commune

Chaque page possède une question, une dominante et une cadence propres. Les
widgets secondaires expliquent la dominante ; ils ne rivalisent pas avec elle.
L'ordre ci-dessous est l'ordre de reconstruction, pas la numérotation Ledger.

## 1. Aujourd'hui — TL/01

**Question :** qu'est-ce qui exige mon attention maintenant, et avec quelle
qualité de données ?

- Dominante : Attention Queue en Evidence Rows, tri serveur préservé.
- Bande supérieure : santé, couverture, population et fraîcheur.
- Rail : Snapshot Rail, provenance, raisons de blocage et état des recalculs.
- Action primaire : ouvrir l'élément sélectionné, jamais « acheter ».
- Interdit : indice inventé, sparkline sans série, carte prix si le DTO ne la
  fournit pas.

## 2. Marchés — TL/07

**Question :** où se concentrent force, faiblesse et participation ?

- Dominante : treemap secteurs vers tickers, légende divergente autour de zéro.
- Supports : breadth, filtres, couverture et rejets.
- Table exacte : ticker, secteur, valeur signée, méthode et fraîcheur.
- Interaction : sélection synchronisée graphique/table, conservée au clavier.
- Interdit : surface proportionnelle à une donnée inexistante ou classement local.

## 3. Analyse — TL/03

**Question :** quels faits confirment ou invalident la lecture de l'instrument ?

- Dominante : chandeliers + volume avec table OHLCV accessible.
- En-tête : instrument, venue, intervalle, heure, source et qualité.
- Rail : scénarios, invalidations, preuves, contradictions et limites.
- Sous-zone : faits techniques fournis, événements liés, historique de sélection.
- Interdit : indicateur calculé dans le navigateur ou recommandation maquillée.

## 4. Options — TL/04

**Question :** quelles cotations et échéances sont réellement exploitables ?

- Dominante : chaîne calls/puts groupée par échéance, strike central lisible.
- Bande : sous-jacent, timestamp, droits, couverture et statut de source.
- Inspecteur : contrat, bid/ask, taille, greeks fournis, méthode et absences.
- Navigation : clavier bidimensionnel seulement si la grille interactive est
  pleinement implémentée ; sinon table native.
- Interdit : IV ou grecques recomputées localement, cotation manquante transformée
  en zéro.

## 5. Simulateur — TL/05

**Question :** comment le scénario fourni se comporte-t-il selon ses hypothèses ?

- Dominante : payoff avec axe zéro, breakevens, zones et points exacts.
- Composeur : jambes, quantité, sens, strike, expiration et validation.
- Rail : hypothèses, résultats serveur, limites, coûts et données absentes.
- Table : points de payoff et résultats exacts.
- Interdit : calcul de payoff ou breakeven côté navigateur.

## 6. Portefeuille — TL/08

**Question :** que contient mon registre manuel et où sont ses concentrations ?

- Dominante : Manual Ledger, lots et mouvements.
- Résumé : métriques serveur, marques absentes, lots exclus, devise et date.
- Supports : concentration, historique, transaction manuelle, import CSV contrôlé.
- Actions : ajouter/corriger un mouvement manuel avec récapitulatif explicite.
- Interdit : lecture IBKR du compte, cash, NAV, positions, P&L ou transactions.

## 7. Calendrier — TL/06

**Question :** quels événements vérifiés peuvent affecter les instruments suivis ?

- Dominante : agenda chronologique ou grille selon densité réelle.
- Supports : fenêtre, catégories, compteurs, versions et révisions.
- Détail : source, fuseau, statut, instruments liés et historique de correction.
- Clavier : appliquer le pattern grille/dialogue WAI si un date picker est utilisé.
- Interdit : événement extrapolé ou horaire sans fuseau.

## 8. Opportunités — TL/02

**Question :** quels candidats passent les règles et lesquels sont exclus ?

- Dominante : candidats admissibles par profil/groupe, ordre serveur conservé.
- Supports : gates, exclusions, calendrier lié, preuves et fraîcheur.
- Fiche : faits, contradictions, motif d'admission/abstention et provenance.
- Interdit : score, rang ou probabilité non calibrés calculés dans l'UI.

## 9. Suivi — TL/09

**Question :** quelles thèses demandent revue, confirmation ou clôture manuelle ?

- Dominante : Thesis Queue avec raisons et échéances.
- Supports : états, filtres, historique, fiche latérale et actions autorisées.
- Une modification affiche son effet sur le registre local avant confirmation.
- Interdit : état rassurant par défaut ou clôture automatique silencieuse.

## 10. Performance — TL/10

**Question :** quelle performance le serveur peut-il réellement établir, avec
quelles exclusions ?

- Dominante : valeur brute/nette et drawdown, unités et périodes explicites.
- Supports : Metric Blocks, heatmap mensuelle, mois et points quotidiens.
- Dégradation : jours/lots exclus visibles à côté de la courbe.
- Interdit : rendement, agrégation, annualisation ou drawdown recalculés localement.

## 11. Vertex IA — TL/11

**Question :** que peut expliquer l'IA à partir du packet validé et sourcé ?

- Dominante : réponse structurée en claims et références.
- Supports : fournisseur, sujet, contradictions, limites et état de disponibilité.
- Chaque claim renvoie à une source ou est marqué comme limite/interprétation.
- Interdit : chiffre nouveau, verdict modifié, source inventée ou IA présentée
  comme disponible lorsqu'elle est désactivée.

## 12. Système — TL/12

**Question :** quelles sources et capacités sont saines, dégradées ou inconnues ?

- Dominante : matrice des sources, méthodes et droits.
- Supports : composants, probes, versions, fraîcheur, fallback et incidents.
- Les probes inconnues restent inconnues ; une absence de mesure n'est pas saine.
- Interdit : état global vert dérivé de contrôles partiels.

## Livrable par page

Pour chaque page, joindre au lot : contrat de composition, inventaire de champs,
matrice d'états, composants touchés, captures des trois viewports, tests exécutés,
budget mesuré, écarts connus, rollback et validation humaine requise.

