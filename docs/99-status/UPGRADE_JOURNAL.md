# Journal — Vertex Dashboard System Upgrade

Branche : `agent/vertex-1-0-dashboard-system-upgrade-v2`, ouverte depuis
`agent/vertex-1-0-dashboard-system-upgrade` (sept commits déjà livrés, conservés).
Base : `main` = `75f14d5`.

Ce journal enregistre, pour chaque changement majeur : le fichier, la raison, la
preuve. Il enregistre aussi ce qui a été REFUSÉ et pourquoi — un refus motivé est
une décision, et il vaut d'être retrouvé.

---

## Mesure « avant » — bundle, 2026-09-04

Relevé par `npm run build` depuis `apps/web`, sur `cdf0d9f`.

| Chunk | Brut | gzip | Chargé quand |
|---|---:|---:|---|
| `index` (fermeture initiale) | 319,00 kB | **96,08 kB** | toujours |
| `index.css` | 185,48 kB | **27,11 kB** | toujours |
| `moduleState` (partagé) | 139,96 kB | 45,77 kB | première page à modules |
| `echartsLoader` | 609,33 kB | **205,44 kB** | route qui rend une heatmap/treemap |
| `lightweightChartsLoader` | 163,98 kB | **52,96 kB** | route qui rend un prix |
| `PortfolioPage` | 69,16 kB | 17,55 kB | `/portfolio` |
| `AnalysisPage` | 53,05 kB | 14,99 kB | `/analysis` |
| `CatalystsPage` | 53,98 kB | 13,41 kB | `/catalysts` |
| `OptionsPage` | 42,81 kB | 12,00 kB | `/options` |
| `CalendarPage` | 41,95 kB | 10,51 kB | `/calendar` |
| `SimulatorPage` | 33,09 kB | 9,94 kB | `/simulator` |
| `OpportunitiesPage` | 30,39 kB | 8,01 kB | `/opportunities` |
| `RiskPage` | 29,48 kB | 8,70 kB | `/risks` |
| `MarketsPage` | 25,42 kB | 7,61 kB | `/markets` |
| `ChartsPage` | 23,91 kB | 7,00 kB | `/charts` |
| Polices Geist + Geist Mono | 141,01 kB | — | toujours (auto-hébergées, OFL-1.1) |

**Ce que cette mesure établit, et qui change le plan.** Le découpage par route
est DÉJÀ fait, page par page, et les deux moteurs graphiques sont DÉJÀ hors de
la fermeture initiale. L'exigence « lazy-load des moteurs » du programme est donc
tenue avant d'avoir commencé ; le travail de performance ne consiste pas à
découper, mais à ne pas défaire ce découpage en ajoutant des imports statiques
dans des modules partagés. Toute hausse du chunk `index` sera signalée ici.

ECharts pèse **quatre fois** Lightweight Charts en gzip. Une visualisation qui
peut se faire en SVG interne sans perdre en lisibilité ne doit donc pas tirer
ECharts sur une route qui ne l'a pas déjà.

---

## Dépendances — état et décisions

**Aucune dépendance ajoutée à ce stade.** Le produit tourne sur sept
dépendances de production :

`@tanstack/react-query` 5.102.8 · `echarts` 6.1.0 · `geist` 1.7.2 ·
`lightweight-charts` 5.2.1 · `react` 19.2.8 · `react-dom` 19.2.8 ·
`react-router-dom` 7.18.3.

### Refusées, avec le motif

| Paquet | Motif du refus |
|---|---|
| `cmdk` | La palette est un `combobox` + `listbox` : motif entièrement décrit par WAI-ARIA APG, écrit en une centaine de lignes de HTML natif. Le paquet aurait apporté un thème à neutraliser, une surface de bundle sur TOUTES les routes et une seconde convention de focus. Motif repris, paquet refusé. |
| `react-animated-numbers` | Une transition de chiffre est une interpolation et un `requestAnimationFrame`. Le paquet n'apporte ni format monétaire ni respect de `prefers-reduced-motion` conformes à nos règles. |
| `react-gauge-component` et alternatives | Les jauges Vertex sont servies : la position vient du serveur, le composant ne calcule rien. Une bibliothèque de jauges apporte surtout de la normalisation locale — exactement ce qui est interdit. |

### TanStack Table et TanStack Virtual — tranché par la mesure

Le programme les demande en priorité pour la chaîne d'options. La volumétrie
réelle a été relevée dans le code serveur, pas estimée :

| Mesure | Valeur | Preuve |
|---|---:|---|
| Strikes par échéance, données synthétiques | **12** | `packages/python/vertex_core/src/vertex_core/synthetic/options.py:108` (`_STRIKE_COUNT = 12`) |
| Contrats par échéance | **24** (12 × CALL/PUT) | même fichier, ligne 183 |
| Échéances par sous-jacent | **2** | même fichier, ligne 7 |
| Plafond serveur, toutes échéances | **240 lignes de contrat** | `apps/worker/src/vertex_worker/options.py:184` (`max_chain_rows: int = 240`) |
| Comportement au-delà | tronqué, et la troncature est PUBLIÉE | même fichier, lignes 723-725 et 767-772 (`truncated_rows`) |

**Décision : les deux sont REFUSÉS.**

*Virtualisation.* La chaîne rend **12 lignes de strike par groupe d'échéance**, et
ne peut structurellement pas dépasser **120 lignes** au total puisque le serveur
tronque à 240 contrats. Virtualiser 120 lignes ne fait rien gagner et coûte cher :
elle casse la sémantique de `<table>` native, donc la lecture par lecteur d'écran,
la recherche du navigateur (Ctrl+F), et la copie de la chaîne. Le composant actuel
porte déjà `content-visibility: auto` comme fenêtrage CSS léger si un instantané
approchait du budget.

*Table headless.* Ce qu'elle apporterait ici, c'est le tri et la visibilité des
colonnes. Le tri est la propriété du SERVEUR — le client ne réordonne pas une
priorité canonique, c'est une règle du produit, pas une préférence. Reste la
visibilité des colonnes, soit un état local d'une trentaine de lignes.

*Ce qui est fait à la place.* Les capacités demandées — sélection de colonnes,
colonne de strike collante, en-tête collant, navigation clavier, ligne
sélectionnée, mise en avant de l'ATM — sont implémentées sur `DataTable` et sur
la chaîne, avec les primitives Vertex. Le motif est repris ; le paquet ne l'est
pas, conformément au §29 du programme.

*Ce qui rouvrirait la décision.* Une configuration serveur portant
`max_chain_rows` au-delà de quelques milliers, ou une chaîne réelle IBKR non
tronquée. La mesure ci-dessus serait alors refaite avant d'ajouter quoi que ce
soit.

---

## Changements livrés

### Lot 1 — primitives (sept commits, branche parente)

| Fichier | Raison |
|---|---|
| `components/widgets/DataTable.tsx` | Remplace 21 familles de classes de table mesurées. Contrat tenu par le type : colonne numérique sans unité impossible, `rowKey` sans défaut, `emptyLabel` obligatoire, `servedOrder` explicitement nul quand le serveur ne trie pas. |
| `components/widgets/LiveDataIndicator.tsx` | Huit états de donnée. AUCUNE latence : le contrat n'en publie pas, un test gèle cette absence. |
| `components/widgets/BulletMetric.tsx` | Mesure quantitative sur axe linéaire, préférée à la jauge dès que plusieurs mesures se comparent. |
| `components/widgets/MicroBars.tsx`, `MicroRange.tsx`, `MiniHeatStrip.tsx` | Micro-visualisations sur positions SERVIES. Aucune normalisation locale. |
| `components/widgets/Skeleton.tsx` | Six squelettes par forme. Réservent la place réelle, donc suppriment le sursaut de mise en page. |
| `components/widgets/ChartFrame.tsx` | Anatomie commune des figures. `equivalent` tabulaire OBLIGATOIRE par le type. |
| `shell/CommandPalette.tsx` | Recherche globale ⌘K, HTML natif. Cherche dans ce que le serveur a publié, et dit quand l'instantané n'est pas chargé. |
| `app/workspace.tsx` | Contexte de travail partagé. L'URL reste propriétaire de ce qu'elle porte ; le contexte porte le reste. |

### Correctifs visuels — ce que seule la capture a montré

| Défaut | Cause exacte |
|---|---|
| Légende de `DataTable` rendue comme une cellule | `display: flex` sur un `<caption>` : un affichage non tabulaire dans une `<table>` est enveloppé dans des boîtes de tableau anonymes. |
| Déclencheur ⌘K en troisième rang | Posé entre la barre de contexte et le ticker, il coupait en deux la surface vitrée continue du bandeau. |

Les tests unitaires passaient dans les deux cas : ils vérifiaient que l'élément
EXISTE et qu'il est nommé, jamais sa place.

---

## Nuit du 4 au 5 septembre — ce qui a été livré

Neuf lots commités sur `agent/vertex-1-0-dashboard-system-upgrade-v2`. Chacun
est vérifié par `tsc`, Biome, la suite unitaire complète et la suite Playwright
sur les quatre projets (1280×800, 1440×900, 1600×1000, 1024×768).

### Ce que seule la CAPTURE a montré

Le fil rouge de la nuit. Aucun de ces défauts n'était visible dans un test :
tous les tests passaient, et tous les DOM étaient corrects.

| Défaut | Cause exacte |
|---|---|
| Quatre valeurs de la chaîne d'options dans UNE colonne, en-tête décalé de 400 px | `.vx-num` posée sur le `<td>`. La classe a reçu `display: inline-block` pour rendre effectif un plafond de largeur — et l'a retiré aux cellules leur `display: table-cell`. Un `<td>` qui n'est plus une cellule est enveloppé par le navigateur dans des boîtes de tableau ANONYMES. |
| Colonnes de la chaîne dimensionnées sur des groupes, pas sur leur contenu | `table-layout: fixed` tire les largeurs de la PREMIÈRE rangée — qui ne contient que « Calls », le strike et « Puts ». |
| « spot servi366.08 » | Chaque morceau du repère était `position: sticky` au MÊME décalage gauche : ils se superposaient. |
| Un tiers d'écran vide sur Aujourd'hui | « Marché global » déclarait une colonne et rendait six blocs. CSS Grid dimensionne la rangée sur son élément le plus haut : ~1 000 px contre ~300 aux voisines. |
| Deux colonnes invisibles sur Opportunités | Listes en puces : la largeur minimale de la colonne valait celle du plus long code, `entitlements_sufficient`. |
| « 4.413571428571428 SYN » écrasant son libellé | Le moteur publie ses flottants entiers. Personne ne lit la seizième décimale d'un ATR à l'écran. |
| « SYN » disparu derrière l'ellipse | Valeur et unité formaient une seule chaîne. Un nombre sans son unité n'est pas une information abrégée, c'est une information fausse. |
| Registre des sources coupé au milieu d'une fraction de seconde | Un horodatage est un mot de trente-deux caractères sans occasion de coupure, et une table ne descend jamais sous sa largeur min-content. |

### Deux pièges CSS qui se repaieront, donc écrits à côté de leur règle

1. **`max-width` est INERTE sur un élément inline non remplacé.** Sur un
   `<code>` inline, le plafond ne s'applique pas, et `text-overflow` non plus.
   Mesuré : valeur rendue à 149 px pour un plafond calculé à 86.
   `inline-block` le rend effectif — et interdit du même coup de poser la
   classe sur une cellule de tableau.
2. **`overflow-wrap: break-word` ne réduit PAS la largeur min-content ;
   `anywhere` si.** Les deux coupent un mot trop long à la mise en page, mais
   seul `anywhere` laisse une table rétrécir. Posé d'abord en `break-word`, le
   correctif du registre des sources n'a strictement rien changé.

### Portes ajoutées

| Porte | Ce qu'elle attrape, et pourquoi rien d'autre ne le pouvait |
|---|---|
| `e2e/table-integrity.spec.ts` | Un élément de tableau qui perd son `display` tabulaire, et un corps désaligné de son en-tête. jsdom ne fait pas de mise en page : ces défauts ne sont visibles qu'en navigateur. Une première version est passée au VERT sur `/options` alors que la chaîne y était cassée — la table n'était pas encore rendue, et une boucle sur zéro élément ne trouve jamais rien. Un minimum de tableaux par destination rend cette vacuité bruyante. |
| `e2e/served-number.spec.ts` | Un nombre visuellement rogné dont la valeur complète n'est atteignable nulle part. Rogner au rendu est légitime ; rogner SANS RECOURS ne l'est pas. |
| `src/design/css-var-defined.test.ts` | Une variable CSS référencée mais jamais définie — la déclaration est ignorée en silence. Elle en a trouvé une à sa première exécution : `--vx-text-primary` colorait la preuve chiffrée des dix gates d'Analyse, qui héritait donc du gris de son propre libellé. |
| `src/design/no-zero-fallback.test.ts` | Une conversion qui se replie sur `0`. Elle a trouvé une CINQUIÈME copie que l'audit des 33 agents n'avait pas listée : `riskView.ts`, où un compte de couverture non publié devenait « 0 retenu sur 0 déclaré ». |
| `src/design/signedScale.test.ts` | Une légende qui peint autre chose que ce que la carte peint. Vérifiée rouge par mutation délibérée avant d'être verte. |
| `contrast.test.ts` (deux ajouts) | Le texte sur chaque cran de l'échelle divergente, et les repères d'interface NON TEXTUELS à 3:1 (WCAG 1.4.11). L'option active de la palette de commandes tenait 1,21:1, et c'était le seul indicateur de la position du curseur clavier. |

### Décisions de conception

**La couleur est une mesure.** La carte des marchés peignait la teinte pleine
selon le seul signe : un +0,09 % et un +2,42 % recevaient le même vert. Sept
crans à bornes DÉCLARÉES et publiées dans la légende. Ce n'est pas une
normalisation : les bornes sont fixes, donc la même valeur donne toujours la
même couleur, d'un instantané à l'autre. La carte mensuelle de performance,
elle, normalisait bel et bien sur le maximum absolu des mois affichés — un mois
changeait de couleur selon ses voisins.

**Les opacités des deux familles diffèrent, et c'est mesuré.** Le vert est plus
clair que le rouge : à opacité égale il éclaircit davantage son fond et approche
plus vite le texte clair. `positive` à 0,55 tombait à 4,15:1 sur le fond de
survol. Les opacités sont réglées pour une LISIBILITÉ égale, pas pour une
transparence égale.

**La divulgation progressive n'est jamais une suppression.** Onze modules
absents mettaient près de 3 500 caractères de prose grise sous des cartes sans
données. Le motif court reste ; question, explication et note se replient. Tout
le texte demeure dans le document — clavier, technologies d'assistance,
recherche du navigateur, impression. Ce qui ne se replie JAMAIS : l'attribution
de licence (Apache-2.0 exige que la mention accompagne l'œuvre), l'unité, la
période, le fuseau, la source, la fraîcheur, l'état de la donnée, le motif d'une
absence.

**Une valeur illisible n'est jamais zéro.** Cinq copies d'un utilitaire de
géométrie rendaient `0` sur une chaîne non analysable : une clôture illisible
plongeait la courbe sur l'axe, une bougie OHLC tombait sur l'axe des prix, un
P&L se posait à l'origine du repère. Le module de géométrie du socle avait
NOMMÉ ce piège dans son en-tête et écrit le remède ; les copies ne l'avaient
jamais adopté. Un test unitaire gelait même le défaut (« 0 sinon ») : il est
RESSERRÉ, pas desserré — `null` dit strictement plus que `0`.

### Trois tentatives refusées par les tests, et elles avaient raison

1. Remplacer la phrase française de la nature de population par son code
   rouvrait le défaut P1-8, « la nature imprimée en ANGLAIS SEUL ».
2. Retirer le code servi de la même cellule cassait l'assertion qui exige que
   la valeur SERVIE apparaisse dans la ligne.
3. Replier l'attribution TradingView avec la méthode : le test e2e d'Analyse
   l'a rattrapée en une exécution.

### Ce que l'audit des 33 agents laisse ouvert

Reporté, avec sa mesure, pour un lot dédié :

- **`freshness_policy` est servi par 12 routes et lu par ZÉRO fichier
  d'interface.** Un contrat de fraîcheur existe et n'est pas branché.
- ~~38 modules servis figés à `state="ready"`~~ — **traité**. Marchés (6),
  Graphiques (6) et Opportunités (8) propagent désormais l'état servi de leur
  instantané. Le seul `ready` en dur qui reste est celui du journal manuel de
  Portefeuille, et il est JUSTE : un journal déclaré par l'utilisateur n'a ni
  fraîcheur, ni population, ni état servi — il n'y a rien à propager, et le
  code le dit à cet endroit. Analyse, Catalyseurs et Calendrier passent par
  d'autres cadres et restent à vérifier un par un.
- ~~Trois règles de signe concurrentes sur Portefeuille~~ — **traité**. Le
  comptage était sous-estimé : il y en avait CINQ dans le produit, dont trois
  fausses. Une autorité unique (`components/widgets/sign.ts`) et une porte les
  remplacent ; voir « Cinq règles de signe, dont trois qui mentaient ».
- **Sept composants sans consommateur de production** (1 408 lignes),
  `ChartFrame`, `LiveDataIndicator` et `Skeleton` compris : écrits et testés
  cette nuit, ils restent à poser sur leurs pages.
- **29 tables écrites à la main** contre une seule sur `DataTable`.
- **64 sélecteurs déclarés deux fois, 60 surcharges silencieuses**, 51 règles
  CSS mortes, 52 classes posées sans règle.
- **30 tailles de police sous le plancher AA de 13 px**, et la frontière d'un
  champ de saisie à 1,14:1 contre les 3:1 de WCAG 1.4.11.
- **93 champs servis ne sont affichés nulle part.**

### La date américaine dans un produit français

Le champ `<input type="datetime-local">` de Catalyseurs affichait
`mm/dd/yyyy, --:-- --`. Dans une page dont chaque libellé est français, la
lecture évidente était un défaut de produit.

Elle était fausse. `index.html` déclare bien `lang="fr"`, mais **`lang` ne
gouverne pas le formatage des contrôles natifs** : ceux-ci suivent la locale du
NAVIGATEUR, qu'aucune feuille de style et aucun attribut HTML n'atteint. Une
sonde autonome l'a mesuré directement :

| Locale du contexte | `new Date(…).toLocaleString()` |
|---|---|
| défaut de l'environnement (`en-US@posix`) | `9/5/2026, 2:30:00 PM` |
| `fr-FR` | `05/09/2026 14:30:00` |

Le produit, lui, était innocent : ses deux seuls formateurs épinglent déjà
`fr-CH` (`SnapshotRail`) et `fr-CA` (`calendarView`), et le seul appel qui
interroge le poste — `resolveViewerTimeZone()` — ne formate rien, il LIT un nom
de fuseau qui est ensuite affiché en toutes lettres.

Le défaut était donc dans la PHOTO, pas dans l'objet photographié. C'est un
piège méthodologique à retenir : la relecture des captures est l'outil qui a
trouvé presque tous les défauts de cette nuit, et il fallait ici lui refuser sa
première conclusion. `playwright.config.ts` fixe désormais `locale: 'fr-FR'` ;
les 672 tests des quatre projets restent verts. `timezoneId` reste
VOLONTAIREMENT non fixé : les instants servis sont en UTC et plusieurs
assertions lisent des heures rendues — déplacer le fuseau du navigateur
changerait ces heures sans rien prouver sur l'identité visuelle.

L'autre moitié du remède est une porte, `src/design/pinned-locale.test.ts` :
aucune source ne peut désormais appeler `toLocale…String()` ni construire un
`Intl.DateTimeFormat`/`NumberFormat` sans épingler sa langue. Prouvée rouge par
mutation sur ses deux motifs à la fois. L'enjeu n'est pas cosmétique :
`05/09/2026` et `09/05/2026` désignent deux jours différents, et une échéance
d'option lue à l'envers est une décision prise sur un fait faux.

### Cinq règles de signe, dont trois qui mentaient

Le signe n'est pas une décoration. Peindre un chiffre en vert AFFIRME un gain.
Cinq règles indépendantes décidaient cette affirmation dans le produit, et
trois se trompaient :

| Où | Règle | Ce qu'elle affirmait à tort |
|---|---|---|
| `PortfolioTable`, `PortfolioInspector` | `startsWith('-') ? 'negative' : 'positive'` | un P&L latent servi `0.00` peint **en vert** |
| `RiskModules` (drawdown) | `startsWith('-') ? 'down' : 'flat'` | un `-0.00` servi lu comme une perte |
| `PortfolioModules`, `SimResult` (deux copies de `signOf`) | tiret testé AVANT le zéro | `-0.00` = perte, et une chaîne positive **non signée** = gain |
| `marketsView.signGroupOf` | `+0.00`/`-0.00` reconnus à l'égalité EXACTE | `-0.000` lu comme une baisse |
| `KpiDelta.signGroupOfText` | **correcte** — mais logée dans un fichier de composant | — |

La cinquième était la bonne : le zéro reconnu AVANT le signe, et `null` quand
le signe n'est pas publié — car une chaîne positive sans « + » ne prouve pas un
gain, elle prouve que le serveur n'a pas publié de signe. Elle vivait dans
`KpiDelta.tsx`, où personne n'allait la chercher ; c'est très exactement
pourquoi quatre autres sont nées.

Elle est promue en `components/widgets/sign.ts`, seule autorité, et les cinq
sites d'appel y sont branchés. Aucun ré-export de compatibilité : une seule
voie d'accès.

**Le vocabulaire cachait la faute.** `positive`/`negative` n'était parlé par
aucune autre feuille de style du produit. Conséquence mesurée en lisant le
DOM : l'inspecteur de lot posait son `data-sign` **hors** de `.vx-pf-lots`,
donc son P&L n'était colorié par **rien** — du balisage mort, et deux vues du
même chiffre qui ne s'accordaient pas. La règle porte désormais sur `.vx-num`,
le marqueur des nombres servis, et parle le `up`/`down`/`flat` de `.vx-dt`.
`flat` ne reçoit aucune couleur de sens : un zéro n'est ni un gain ni une
perte.

Trois preuves, chacune rouge d'abord :

1. `components/widgets/sign.test.ts` — 21 cas, dont un reproducteur qui exécute
   l'ancienne règle binaire côte à côte avec l'autorité et montre leur
   désaccord sur `0.00` et `-0.00` ;
2. `pages/portfolio/PortfolioTable.test.tsx` — la LIGNE RENDUE, parce que c'est
   le site d'appel qui avait divergé : les 6 assertions échouent toutes quand
   on restaure la règle d'origine ;
3. `design/one-sign-rule.test.ts` — la porte : seule l'autorité lit un signe
   dans une chaîne, et aucun `data-sign` (balisage ou feuille de style) ne
   sort du vocabulaire canonique.

La porte s'est d'abord accusée elle-même : son commentaire d'explication
contient les mots `data-sign='positive'`. Les commentaires CSS sont désormais
retirés avant lecture — une porte qui lit de la prose ne lit pas des règles, et
symétriquement une règle cachée dans un commentaire n'est pas une règle.
