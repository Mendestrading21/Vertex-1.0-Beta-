# Graphiques Titanium Ledger

## Contrat avant rendu

Tout graphique commence par un contrat écrit :

- question analytique ;
- données et champs serveur exacts ;
- unité, fuseau, période, fréquence et population ;
- méthode, exclusions, fraîcheur et provenance ;
- interaction utile ;
- états loading/empty/partial/degraded/error/stale ;
- équivalent textuel ou tabulaire ;
- moteur, coût de bundle et stratégie de chargement.

Si un champ n'existe pas, réduire la visualisation. Ne jamais l'inventer pour
ressembler à une référence.

## Anatomie commune

1. titre court et question ;
2. état global et fraîcheur ;
3. surface quadrillée discrète ;
4. géométrie issue des données serveur ;
5. axes, zéro, unités et seuils utiles ;
6. légende stable et sélection accessible ;
7. provenance, méthode et exclusions ;
8. table ou résumé exact.

Le tooltip aide l'exploration mais ne contient jamais l'unique accès à une valeur.
Le crosshair doit exposer date, série et valeur exactes. Les séries conservent la
même couleur à travers les vues comparables.

## Langage par type

| Type | Traitement | Point de vigilance |
|---|---|---|
| chandeliers + volume | hausse/baisse sémantique, volume neutre, OHLCV exact | table OHLCV et clavier |
| treemap | secteur puis ticker, surface proportionnelle, valeur signée | petites tuiles et légende |
| breadth | comptes et population, seuil zéro visible | ne pas présenter un score fabriqué |
| payoff | option violet, axe zéro, breakevens pointillés | points et hypothèses serveur |
| performance | valeur brute/nette, drawdown séparé | unités, jours exclus, valeurs non recomposées |
| heatmap | cellule + valeur ou absence | palette divergente, pas couleur seule |
| mini-série | contexte seulement, valeur et période adjacentes | pas de sparkline décorative sans données |

## Couleur et comparaison

- Limiter le nombre de séries simultanées ; ajouter forme, motif, style de trait
  ou marqueur lorsque les séries doivent survivre à une perception altérée.
- Réserver vert/rouge au signe financier. Utiliser argent, macro et option pour
  les séries non directionnelles.
- Une palette séquentielle représente une magnitude ; une palette divergente
  exige un centre significatif, généralement zéro.
- Une nouvelle couleur de série doit rester cohérente sur toutes les pages.
- Tester fond, grille, axe, texte, sélection, survol et état désactivé.

## Accessibilité

- Encapsuler la figure avec un titre et une description utile.
- Fournir la table exacte ou une liste structurée quand la table serait trop
  volumineuse ; prévoir un chemin pour l'ouvrir.
- Décrire la conclusion sans prétendre remplacer les données.
- Assurer navigation et sélection clavier lorsqu'une interaction est nécessaire.
- Avec ECharts, importer explicitement `AriaComponent` avant d'activer `aria` ;
  vérifier le DOM et la sortie lecteur d'écran.
- Avec Lightweight Charts, évaluer l'extension d'accessibilité compatible avec
  la version épinglée ; sinon maintenir figure, description, annonce et table
  contrôlées par Vertex. Aucun changement de version sans lot.
- Les annonces `aria-live` portent une modification utile, jamais chaque tick.

## Performance

- Conserver ECharts et Lightweight Charts hors du chargement initial, par route.
- Charger le moteur seulement lorsque la visualisation devient nécessaire.
- Préserver un espace de rendu fixe pour éviter les décalages.
- Mesurer le bundle initial et les chunks, puis le temps d'interaction sur une
  machine de référence. Une déclaration de lazy-loading sans mesure n'est pas une
  preuve.
- Agrégation, downsampling ou fenêtrage financiers appartiennent au serveur ou à
  un contrat explicitement validé ; ne pas les improviser dans le composant.

## Tests minimaux

- branche de chaque état serveur ;
- unités, dates, fuseau, valeurs négatives, nulles et absentes ;
- légende et sélection stables ;
- table exacte et libellés accessibles ;
- clavier, focus, tooltip/crosshair ;
- données extrêmes et séries d'un seul point ;
- absence de calcul financier interdit ;
- chargement par route et budget de bundle ;
- capture aux trois viewports desktop et revue humaine.

