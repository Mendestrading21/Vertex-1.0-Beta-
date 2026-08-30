# Vertex 1.0 Beta — système visuel Titanium Ledger

## Thèse

Titanium Ledger transforme Vertex en registre décisionnel premium : la densité
d'un terminal de marché, la sérénité d'un outil patrimonial et la précision
d'un poste d'analyse. Le métal sombre structure l'espace ; l'ambre identifie la
marque, la sélection et l'action. Les couleurs financières conservent un rôle
strictement sémantique.

Le thème synthétise les références fournies : grilles denses, bento asymétrique,
widgets compacts, grands graphiques, rail latéral et panneaux d'inspection. Il
écarte les glows permanents, les cartes 3D, les chiffres inventés et les couleurs
rouge/verte utilisées comme décoration.

## Signature de marque

### Logotype principal

- monogramme `VX` angulaire dans une plaque de métal brossé ;
- mot-symbole `VERTEX` en capitale, compact et stable ;
- signature secondaire `TITANIUM LEDGER` en mono, petite et espacée ;
- version produit `Vertex 1.0 Beta` séparée de la marque afin qu'elle puisse
  évoluer sans redessiner le logotype.

### Variantes autorisées

| Variante | Usage |
|---|---|
| plaque `VX` | rail compact, favicon futur, avatar produit |
| plaque + `VERTEX` | rail ouvert, écran d'accès |
| mot-symbole seul | documents et exports étroits |
| signature `Titanium Ledger` | barre de contexte et documentation visuelle |

Le monogramme n'emploie jamais le vert ou le rouge. Il ne représente ni une
hausse, ni un signal de marché.

## Palette

| Rôle | Token | Valeur | Usage |
|---|---|---:|---|
| noir absolu | `--vx-black` | `#030302` | texte sur action ambre, fond profond |
| canevas | `--vx-app` | `#080806` | arrière-plan global |
| dominante | `--vx-surface-0` | `#0d0d0b` | graphiques, grandes surfaces |
| widget | `--vx-surface-1` | `#141310` | cartes et panneaux |
| contrôle | `--vx-surface-2` | `#1b1915` | contrôles, en-têtes de tableau |
| métal clair | `--vx-silver` | `#d8d3c7` | valeurs principales et logo |
| titane | `--vx-titanium` | `#aaa497` | légendes, micro-typographie |
| ambre de marque | `--vx-signal` | `#d7a94a` | sélection, identité, action principale |
| ambre lumineux | `--vx-signal-bright` | `#f2c76b` | liseré actif et contraste du logo |
| positif | `--vx-positive` | `#50c992` | valeur financière positive seulement |
| négatif | `--vx-negative` | `#ef6f6c` | valeur financière négative seulement |
| options | `--vx-option` | `#a88ae8` | domaine options et payoff |
| macro | `--vx-macro` | `#6bc5bc` | contexte macro et série secondaire |

## Grammaire des objets

### Ledger Frame

Cadre dominant d'une page. Surface sombre, tranche ambre de 76 px, coin
métallique discret, titre court, question, provenance et pied technique. Une
page possède au maximum un Ledger Frame dominant.

### Metric Block

Valeur tabulaire alignée, libellé en mono et définition accessible. L'état
absent reste un tiret explicite. Une métrique bloquée explique la raison au lieu
d'afficher zéro.

### Evidence Row

Ligne compacte pour files, preuves et événements : identité à gauche, fait au
centre, état et heure à droite. Le survol ajoute un fond ambre très faible sans
modifier l'ordre.

### Ledger Table

En-tête mat en capitales mono, nombres tabulaires, séparateurs fins, première
colonne stable lorsque nécessaire et survol de ligne. Le tableau reste la
référence accessible exacte des graphiques.

### Inspector Sheet

Panneau latéral élevé pour provenance, contrat, thèse ou détail d'option. Il
ne crée aucune valeur ; il expose les faits, limites, sources et actions déjà
autorisées.

### State Plate

Badge rectangulaire compact pour fraîcheur, population, méthode et état de
source. Les formes, libellés et icônes accompagnent toujours la couleur.

## Grammaire des graphiques

Chaque graphique possède quatre couches :

1. titre et question analytique ;
2. surface quadrillée `36 × 36 px` ;
3. tracé ou géométrie provenant exclusivement du serveur ;
4. légende, unité, période, fraîcheur et équivalent tabulaire.

| Graphique | Page | Traitement Titanium Ledger |
|---|---|---|
| treemap secteurs → tickers | Marchés | tuiles sémantiques, cadre titane, libellé signé |
| breadth | Marchés | barres fines, seuils lisibles, compteurs exacts |
| chandeliers + volume | Analyse | grille chaude, prix rouge/vert sémantique, volume neutre |
| payoff | Simulateur | courbe options violette, breakevens pointillés, axe zéro explicite |
| valeur brute/nette + drawdown | Performance | argent, macro pointillé, drawdown négatif |
| heatmap mensuelle | Performance | cellule + valeur ou absence, jamais couleur seule |

Les moteurs restent chargés par route. Les tracés ne calculent ni score, ni
rendement, ni probabilité dans le navigateur.

## Architecture des douze pages

| Code | Page | Dominante | Widgets et objets |
|---:|---|---|---|
| TL/01 | Aujourd'hui | file d'attention | santé, population, Evidence Rows, Snapshot Rail, provenance |
| TL/02 | Opportunités | candidats admissibles | profil, groupes, gates, exclusions, calendrier lié, preuves |
| TL/03 | Analyse | chandeliers + volume | sélecteur, scénarios, avis, faits, limites, table OHLCV |
| TL/04 | Options | chaîne exploitable | groupes d'échéance, calls/puts, strike central, inspecteur |
| TL/05 | Simulateur | payoff | composeur de jambes, hypothèses, breakevens, résultats, points exacts |
| TL/06 | Calendrier | agenda | fenêtre, compteurs, événements, catégories, versions et révisions |
| TL/07 | Marchés | treemap | légende, breadth, filtres, table triable, rejets et couverture |
| TL/08 | Portefeuille | registre manuel | résumé, lots, ledger, concentration, transaction, import CSV |
| TL/09 | Suivi | file des thèses | échéances, raisons, table, fiche latérale, historique et action |
| TL/10 | Performance | valeur + drawdown | Metric Blocks, courbes, heatmap, mois et points quotidiens |
| TL/11 | Vertex IA | réponse sourcée | fournisseur, sujet, claims, références, contradictions, limites |
| TL/12 | Système | contrôle de santé | composants, méthodes, matrice des sources, probes inconnues |

Chaque route reçoit un code Ledger stable dans la coquille. Ce code est un
repère éditorial et ne doit jamais être interprété comme un rang ou un score.

## Composition et densité

- largeur utile maximale : 1600 px ;
- rail : 248 px ouvert, 68 px compact ;
- grille principale : 12 colonnes conceptuelles, gaps 16–24 px ;
- cadre dominant : 7–9 colonnes ; rail de preuve : 3–5 colonnes ;
- contrôle : rayon 6–10 px ; grande surface : rayon 16 px ;
- une seule action remplie par page ;
- le premier écran montre la question et le principal outil de décision.

À 1024 px, les grilles se replient mais aucune donnée n'est supprimée. La Beta
reste desktop : une navigation téléphone doit faire l'objet d'un lot distinct.

## Mouvement

- 90 ms pour survol de ligne ;
- 140 ms pour contrôle et badge ;
- 180 ms pour rail et panneau ;
- aucune animation financière continue ;
- réduction de mouvement respectée intégralement.

## Interdits

- glow généralisé, néon décoratif ou gradient arc-en-ciel ;
- vert/rouge dans le logo ou les éléments de marque ;
- carte 3D, illustration boursière ou chandelier décoratif ;
- KPI, score, prix, tendance, probabilité ou recommandation inventés ;
- graphique sans question, unité, période, source et équivalent accessible ;
- ambre utilisé pour signifier une performance positive ;
- différence d'état portée uniquement par la couleur ;
- action d'exécution, lecture du cash ou des positions IBKR dans cette Beta.

## Critères de validation

- identité reconnaissable dans le rail, la barre de contexte et les cadres ;
- les douze routes possèdent un code et une dominante cohérente ;
- tokens générés égaux à leur source TypeScript ;
- aucun changement des contrats API ni des calculs financiers ;
- navigation clavier et focus visibles ;
- lint, typecheck, tests et build verts ;
- revue humaine à 1280, 1440 et 1600 px avant fusion.
