# Contrats des douze pages Vertex

## Règle commune

Le shell reste celui de `canonical-visual.md`. Chaque page change seulement la
question, la dominante, les preuves secondaires et l'inspecteur. Une page ne
doit pas répéter un bento générique ni inventer une donnée pour remplir l'espace.

Les planches dans `assets/` illustrent les compositions par paire. Elles peuvent
contenir du texte ou des chiffres générés : ils sont non contractuels. Les
libellés finaux sont français et les valeurs viennent uniquement des contrats.

## 1. Aujourd'hui

**Question :** que dois-je regarder maintenant, pourquoi et avec quelle qualité ?

- Planche : `pages-01-02-today-markets.png`, moitié gauche.
- Dominante : régime de marché + graphique global et événements superposés.
- Widgets : marché global, volatilité, prochain catalyseur, santé des sources,
  opportunités, risques actifs, secteurs, portefeuille manuel, calendrier.
- Inspecteur : thèse, catalyseurs vérifiés, risques, preuves et exclusions.
- Interdit : urgence, rang, santé ou recommandation inventés.

## 2. Marchés

**Question :** où se concentrent force, faiblesse, participation et risque ?

- Planche : `pages-01-02-today-markets.png`, moitié droite.
- Dominante : carte/treemap multi-actifs avec breadth et table exacte.
- Widgets : indices, secteurs, devises, taux, volatilité, couverture et rejets.
- Inspecteur : instrument/secteur sélectionné, contexte et sources.
- Interdit : taille ou classement fondé sur une donnée absente.

## 3. Opportunités

**Question :** quels candidats passent les règles et lesquels sont exclus ?

- Planche : `pages-03-04-opportunities-analysis.png`, moitié gauche.
- Dominante : file de candidats et gates serveur.
- Widgets : profil, horizon, groupes, preuves, exclusions, catalyseurs et qualité.
- Inspecteur : motif d'admission, abstention, contradictions et provenance.
- Interdit : score ou probabilité UI, ordre local modifiant la priorité canonique.

## 4. Analyse

**Question :** quels faits confirment ou invalident la lecture de l'instrument ?

- Planche : `pages-03-04-opportunities-analysis.png`, moitié droite.
- Dominante : chandeliers + volume, overlays contractuels et table OHLCV.
- Widgets : scénarios, niveaux, faits techniques, événements, contradictions.
- Inspecteur : thèse, invalidation, méthode, limites et sources.
- Interdit : indicateur, signal ou recommandation calculé dans le navigateur.

## 5. Options

**Question :** quelles cotations, échéances et contraintes sont exploitables ?

- Planche : `pages-05-06-options-simulator.png`, moitié gauche.
- Dominante : chaîne calls/puts par échéance, strike central et droits visibles.
- Widgets : sous-jacent, volatilité fournie, open interest, spread et couverture.
- Inspecteur : contrat, bid/ask, taille, greeks fournis, méthode et absences.
- Interdit : IV/grecques locales, cotation manquante transformée en zéro.

## 6. Simulateur

**Question :** comment le scénario fourni réagit-il aux hypothèses explicites ?

- Planche : `pages-05-06-options-simulator.png`, moitié droite.
- Dominante : payoff avec axe zéro, breakevens et points exacts serveur.
- Widgets : composeur de jambes, hypothèses, coûts, résultats et limites.
- Inspecteur : scénario, méthode, données absentes, comparaison et export.
- Interdit : calcul de payoff/breakeven UI ou bouton d'exécution.

## 7. Portefeuille

**Question :** que contient mon registre manuel et où sont ses concentrations ?

- Planche : `pages-07-08-portfolio-charts.png`, moitié gauche.
- Dominante : ledger manuel avec lots, mouvements, devise et date.
- Widgets : valeur calculée serveur, allocation, concentration, historique,
  anomalies et import CSV contrôlé.
- Inspecteur : ligne sélectionnée, provenance manuelle, corrections et impacts.
- Interdit : lecture de compte, positions, cash, NAV ou P&L IBKR.

## 8. Graphiques

**Question :** quelles relations puis-je explorer sans perdre méthode et contexte ?

- Planche : `pages-07-08-portfolio-charts.png`, moitié droite.
- Dominante : espace graphique configurable avec séries autorisées.
- Widgets : instrument, horizon, overlays serveur, comparaison, table et notes.
- Inspecteur : définition des séries, unités, source, fraîcheur et exclusions.
- Interdit : studio libre permettant une formule financière côté navigateur.

## 9. Risques

**Question :** quels risques sont actifs, mesurés, inconnus ou bloquants ?

- Planche : `pages-09-10-risks-catalysts.png`, moitié gauche.
- Dominante : matrice des risques avec exposition, horizon, sévérité et preuve.
- Widgets : concentration, liquidité, volatilité, macro, géopolitique, données.
- Inspecteur : mécanisme, déclencheur, mitigation, limites et état de mesure.
- Interdit : score global vert dérivé de mesures partielles.

## 10. Catalyseurs

**Question :** quels événements vérifiés peuvent modifier la thèse et quand ?

- Planche : `pages-09-10-risks-catalysts.png`, moitié droite.
- Dominante : timeline liée aux instruments et aux thèses.
- Widgets : importance, statut, consensus fourni, révisions, conflits et fenêtre.
- Inspecteur : source, fuseau, historique, instruments liés et incertitude.
- Interdit : événement extrapolé ou impact présenté comme certain.

## 11. Calendrier

**Question :** que se passe-t-il dans ma fenêtre temporelle et dans quel fuseau ?

- Planche : `pages-11-12-calendar-sources-reports.png`, moitié gauche.
- Dominante : agenda dense ou grille selon la population réelle.
- Widgets : catégories, filtres, compteurs, versions, révisions et conflits.
- Inspecteur : événement, source, fuseau, statut et instruments concernés.
- Interdit : date/heure naïve, élément sans source ou calendrier décoratif.

## 12. Sources & Rapports

**Question :** puis-je faire confiance aux données et exporter leurs preuves ?

- Planche : `pages-11-12-calendar-sources-reports.png`, moitié droite.
- Dominante : matrice des sources, méthodes, droits, fraîcheur et couverture.
- Widgets : incidents, versions, rapports, exports, sauvegardes et audit trail.
- Inspecteur : source/rapport sélectionné, limites, champs, licence et historique.
- Interdit : santé globale rassurante sans couverture complète ; export perdant
  provenance, état, unité ou étiquette de simulation.

## Livrable par page

Avant code, produire : question, décision préparée, dominante, données autorisées,
contexte partagé, états, action primaire, alternative accessible, budget,
interdits et critères binaires. Après code, joindre tests exacts, captures des
trois viewports, comparaison canonique, écarts, mesures et rollback.
