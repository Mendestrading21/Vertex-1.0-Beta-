# PLAN MAÎTRE VERTEX — de 0 à la finalité

> **Ce document remplace tous les plans précédents.** `REFONTE_TITANIUM_LEDGER.md`,
> `PLAN_NUIT_IDENTITE_V3.md`, `WIDGETS_V2_PLAN.md`, `CLAUDE_RECOVERY_PLAN.md` et la
> séquence R0→R17 deviennent des archives. Il n'existe qu'une seule séquence de
> lots, numérotée de 0 à 24, et elle est suivie dans l'ordre.
>
> Établi le 2026-09-04 sur `main` @ `20ec3f3`.

---

## 1. Verdict

Vertex a un squelette solide et une chair incomplète. Le socle technique tient :
douze destinations réelles, 28 endpoints, un moteur financier Python unique, neuf
portes de conception automatiques, 19 suites Playwright. Ce qui manque n'est pas
la rigueur — c'est **la matière** : sur 225 modules catalogués dans les douze
pages, **103 sont déclarés absents**, et la quasi-totalité le sont parce que
*personne n'a encore écrit le calcul côté Python*, pas parce que la donnée serait
inaccessible.

Le plan précédent concluait « ces 14 éléments ne seront pas affichés ». C'était
prudent mais faux comme finalité : la bonne réponse n'est pas de les cacher, c'est
de **les calculer dans `vertex_core`, avec provenance et validation**, puis de les
afficher. C'est le changement de cap de ce plan.

Deuxième constat : **le dépôt documentaire est en désordre mesurable** (§3). Un
dossier orphelin, un `NOW.md` de 2 386 lignes qui est un journal et non un état,
des normes mêlées à des plans périmés, une navigation documentée qui contredit la
navigation servie. Le lot 1 le remet en ordre.

---

## 2. État mesuré au 2026-09-04

| Mesure | Valeur |
|---|---:|
| `main` | `20ec3f3` |
| PR ouvertes | **15** (14 en cascade chaînée + #9 audit cloud jamais évaluée) |
| Branches locales | 48, dont ~40 fusionnées ou mortes |
| Destinations servies | 12 |
| Endpoints API | 28 |
| Modules catalogués | **225** |
| — servis par un contrat | **122** (54 %) |
| — déclarés absents avec motif | **103** (46 %) |
| Modules de calcul Python | 5 (`market`, `options`, `performance`, `portfolio`, `risk`) |
| Primitives visuelles | 21 widgets v2 + 14 composants racine |
| Portes de conception automatiques | 9 |
| Suites e2e | 19 |
| ADR | 19 |

### Les 103 absences, par nature

| Motif | Sens réel | Traitement dans ce plan |
|---|---|---|
| `SERVER_CONTRACT_MISSING` | le calcul existe ou est faisable, le contrat ne le publie pas | **à servir** — lots 8 à 13 |
| `NO_SOURCE` | aucune source ingérée ne porte la donnée | **à sourcer** — lot 7, puis servir |
| `SUBSCRIPTION_REQUIRED` | droit IBKR absent | **reste absent**, dit à l'écran |
| `DECISION_PENDING` | attend un arbitrage humain ou un ADR | **à trancher** — lot 2 |

C'est la table qui gouverne tout le plan : chaque page n'est refaite visuellement
qu'**après** que sa matière a été servie, sinon on rhabille du vide.

---

## 3. Le désordre trouvé, et où chaque chose ira

| # | Constat | Preuve | Destination |
|---|---|---|---|
| D1 | `docs/00-product/` : un dossier d'un seul fichier, doublon de numérotation avec `01-product/` | `CURRENT_VERTEX_SALVAGE_MATRIX.md` seul | → `docs/07-delivery/` (c'est un inventaire de reprise, pas un produit) |
| D2 | `docs/99-status/NOW.md` fait **2 386 lignes** : c'est un journal, pas un état | `wc -l` | `NOW.md` réduit à l'état courant ; le journal part dans `docs/99-status/journal/` |
| D3 | Quatre rapports historiques vivent dans « état courant » | `CLAUDE_RECOVERY_PLAN`, `HISTORY`, `R0_GITHUB_SECURITY`, `R2_REQUALIFICATION` | → `docs/99-status/archives/` |
| D4 | `docs/05-design/` mêle **13 normes et 3 plans de chantier terminés** | `PLAN_NUIT_IDENTITE_V3`, `REFONTE_TITANIUM_LEDGER`, `WIDGETS_V2_PLAN` | → `docs/99-status/archives/` |
| D5 | **Cinq documents se disputent l'identité visuelle** | `DESIGN_SYSTEM`, `TITANIUM_LEDGER_VISUAL_SYSTEM`, `VERTEX_ONE_VISUAL_DIRECTION`, `TOKENS`, `WIDGET_LIBRARY` | fusion en **trois** : `DESIGN_SYSTEM.md` (règles), `TOKENS.md` (valeurs), `WIDGET_LIBRARY.md` (vocabulaire) |
| D6 | `NAVIGATION.md` et `ROUTES.md` décrivent une navigation qui n'existe plus | y figurent Suivi, Performance, Vertex AI, Système ; le code sert Graphiques, Risques, Catalyseurs, Sources | réécrits sur la navigation du lot 6 |
| D7 | `docs/01-product/pages/` : 12 fiches nommées d'après l'ancienne navigation, **aucune** pour Graphiques ni Risques | `09-follow-up`, `10-performance`, `11-vertex-ai`, `12-system` | renommées et complétées au lot 6 |
| D8 | `.claude/lots/` : 27 lots `LOT-00`→`LOT-26` qui ne décrivent plus les vagues réellement exécutées (A2–A8, S0–S6, T1–T6, P2–P6, W2) | comparaison avec `git log` | remplacés par les 25 lots de **ce** plan |
| D9 | 48 branches locales, une par vague de nuit | `git branch` | élaguées après fusion (lot 0) |

---

## 4. Les quatre lois qui ne bougent pas

Elles sont déjà écrites dans `.claude/rules/` et `CONSTITUTION.md`. Ce plan ne les
assouplit sur aucun lot.

1. **IBKR est une source de marché.** Jamais de compte, cash, NAV, position, P&L,
   ordre ou exécution. Le portefeuille est déclaré à la main.
2. **Aucun ordre, jamais.** Aucun bouton, route, mot ou outil IA qui pourrait
   déclencher une transaction. Le vocabulaire « acheter / vendre / ordre » est déjà
   interdit par une porte automatique.
3. **Python calcule, TypeScript affiche.** Aucun prix, Greek, IV, ratio, score,
   probabilité ou verdict calculé dans le navigateur. Toute nouvelle intelligence
   de ce plan est écrite dans `vertex_core`, testée, versionnée, puis servie.
4. **Une absence n'est jamais un zéro.** Absent, zéro, retardé, périmé, estimé,
   théorique, simulé et réel restent sept états distincts, visuellement distincts.
   Aucun chiffre n'est inventé pour remplir une forme.

Et une cinquième, qui vient de l'expérience de cette session : **un test qui gèle
un défaut est resserré, jamais desserré.** Aucun test n'est désactivé, allégé ou
supprimé pour faire passer un lot.

---

## 5. La séquence — 25 lots, dans l'ordre

### PHASE I — Assainir (lots 0 à 2)

Rien de visible. On répare le terrain avant de bâtir.

---

**LOT 0 — Faire atterrir les quatorze PR en attente**

14 PR chaînées les unes sur les autres, toutes touchant les fichiers que la refonte
va réécrire. Les laisser ouvertes, c'est garantir un conflit à chaque lot suivant.

- Pour chacune, dans l'ordre #50 → #64 : rebaser la base sur `main`, **fusionner**
  `origin/main` (jamais rebaser une branche déjà poussée), résoudre, vérifier,
  pousser, attendre les deux runs CI, fusionner en squash.
- Deux conflits reviennent à chaque fois et ont un résolveur écrit : le plafond de
  dette de `no-ambiguous-dash.test.ts` (**on garde toujours le plus bas** — le
  cliquet ne remonte pas) et le récit de `NOW.md` (on garde les deux).
- Élaguer les branches locales fusionnées.
- Trancher le sort de **#9** (audit cloud du 31 août, jamais évaluée) : lire, en
  extraire ce qui est encore vrai, fermer.

*Fini quand :* `main` contient les 14 lots, zéro PR ouverte hors #9 tranchée, CI verte.

---

**LOT 1 — Remettre le dossier en ordre**

Les neuf constats D1→D9 du §3, exécutés. Aucun fichier supprimé sans que son
contenu utile ait été relogé ; chaque déplacement laisse une note de renvoi.

- `docs/00-product/` dissous.
- `NOW.md` devient un état de moins de 60 lignes : lot courant, branche, dernier
  `main` connu bon, CI, risque, prochaine commande. Le journal complet part dans
  `docs/99-status/journal/2026-08.md` et `2026-09.md`.
- `docs/99-status/archives/` créé, sept documents y sont relogés.
- Les cinq documents d'identité fusionnés en trois.
- `.claude/lots/` remplacé par les 25 fiches de ce plan.

**Trois chantiers ouverts depuis LOT-00 y sont rapatriés**, parce qu'ils portent sur
la vérité des données et qu'aucun plan récent ne les portait plus :

- **porte de provenance des fixtures** — une fixture doit déclarer son statut
  `SYNTHETIC` / `DEMO` et ne peut franchir aucune frontière de production ;
- **quarantaine des données réelles** — aucune donnée IBKR ou TradingView réelle,
  capture personnelle ou charge de production dans Git ;
- **registre et gouvernance** des fixtures.

Ce sont des règles déjà écrites dans `.claude/rules/testing.md` mais **non tenues par
une porte automatique**. Tant qu'aucune porte ne les vérifie, la règle est une
intention.

*Fini quand :* un lecteur qui arrive sur le dépôt trouve l'état courant en une page
et ne peut plus tomber sur deux documents qui se contredisent ; et trois portes
neuves refusent une fixture sans provenance.

---

**LOT 2 — Trancher les décisions en attente**

18 modules portent `DECISION_PENDING` : ils n'attendent ni source ni code, ils
attendent un arbitrage. Chacun est instruit, tranché, et devient soit un lot de
service (phase III), soit une absence définitive avec son motif écrit.

Y sont joints les trois arbitrages structurants :

- la **navigation cible** (§6) ;
- le **statut de la probabilité** : aucune probabilité prédictive ne sera affichée
  sans calibration, horizon, population et validation hors échantillon — donc les
  classifications de ce plan (régime, sentiment) sont **descriptives d'un observé**,
  jamais des prédictions, et le disent à l'écran ;
- le **périmètre du backtest** : recherche seulement, jamais d'écriture dans le
  runtime live (ADR-011 déjà en vigueur).

*Fini quand :* zéro `DECISION_PENDING` sans ADR ou sans lot assigné.

---

### PHASE II — Le socle visuel (lots 3 à 6)

Ce que le brief « Titan Ledger / Institutional Signal » demande, appliqué une fois,
partout, avant de toucher une seule page.

---

**LOT 3 — Doctrine visuelle**

- ADR-018 « Titan Ledger / Institutional Signal », statut `Accepté` — **déjà rédigé**,
  à finir et fusionner. Il supersède la palette d'ADR-017, conserve ses 13 formes
  interdites, et déclare les deux formes ajoutées (barres miroir d'open interest,
  matrice de P&L) avec la donnée servie qu'elles exigent.
- L'autorité de style devient **un contrat écrit** (`references/titan-ledger.md`) et
  non une empreinte d'image : les quinze références du brief ne sont pas versionnées,
  et fabriquer une empreinte serait inventer une preuve. La capture historique reste
  au dépôt comme témoin, son empreinte toujours vérifiée.
- La porte `canon-v2-docs.test.ts` est **étendue** à ADR-018 — jamais allégée.

**Deux défauts de contraste déjà mesurés et corrigés dans l'ADR** : `text-muted` du
brief donne 3,73:1 sur `surface-hover`, sous le seuil AA alors qu'il porte des
métadonnées — relevé à `#7E8897` (4,52:1 au pire) ; `text-disabled` à 2,15:1 est
conservé mais **restreint aux contrôles inactifs**, que WCAG 1.4.3 exempte.

---

**LOT 4 — Jetons et typographie**

`apps/web/src/design/tokens.ts` seul, puis régénération de `tokens.css` (vérifiée à
l'octet près par une porte existante).

- Palette du brief en **rôles sémantiques** : fonds, surfaces, bordures, textes,
  accent ambre, positif, négatif, avertissement, technique cyan, options violet.
- **Chaque paire texte/fond calculée et consignée.** Aucun contraste supposé.
- Échelle typographique complète, chiffres tabulaires partout où un nombre est lu.
- Correction de `radius[18] = '16px'` et `radius[22] = '20px'` — la clé ne vaut pas
  sa valeur — et **ajout de l'assertion clé ↔ valeur** qui manquait : l'écart existait
  sans qu'aucune porte le voie.

---

**LOT 5 — Coquille**

Rail 216–232 px avec repli compact à 72 px, barre supérieure 60–68 px (recherche,
état de session, état des données, notifications, profil), grille 12 colonnes,
gouttières 16–20 px. Pose de la teinte de page sur les douze destinations.

---

**LOT 6 — Primitives et navigation**

Le manque réel, mesuré : **21 familles de classes de table pour 24 fichiers**, une
grammaire par page. La primitive qui manque n'est pas décorative.

- **`DataTable`** d'abord : en-tête collant, première colonne collante, nombres à
  droite en Geist Mono, hauteur de ligne 42–46 px, tri visible et annoncé,
  virtualisation seulement sur mesure. Puis `FilterBar`, `SearchField`, `Drawer`,
  `Tabs`, `MetricDefinitionTooltip`, `Callout`, `ScenarioBadge`, `ChartContainer`.
- `Glyph.tsx` étendu — **aucune nouvelle bibliothèque d'icônes**.
- **Navigation cible** appliquée, avec redirection permanente pour chaque route
  retirée et aucune capacité perdue :

| Aujourd'hui | Cible | Décision |
|---|---|---|
| `today` `calendar` `markets` `opportunities` `analysis` `options` `simulator` `portfolio` | identiques | conserver |
| `catalysts` | **Suivi** | renommer et recentrer |
| `portfolio/performance/*` | **Performance** | extraire |
| `charts` | sous-vue d'**Analyse** | absorber |
| `risk` | sous-vue de **Performance** | absorber |
| `sources` | **Système** | renommer |
| inspecteur IA des pages hôtes | **Vertex IA** | extraire, **en conservant** l'inspecteur en place |

Douze espaces : Aujourd'hui, Calendrier, Marchés, Opportunités, Analyse, Options,
Simulateur, Portefeuille, Suivi, Performance, Vertex IA, Système.

*Risque nommé :* ré-extraire Vertex IA rouvre le défaut fermé au LOT-12 — un
sélecteur proposant des sujets qu'aucune page n'affiche. La page ne listera que les
trois sujets réellement explicables par le contrat.

---

### PHASE III — L'intelligence (lots 7 à 13)

**C'est le cœur du plan et sa vraie nouveauté.** Chaque lot écrit un calcul dans
`vertex_core`, avec tests de propriétés et oracle indépendant, le publie dans un
contrat versionné, l'expose par l'API, et **débloque des modules aujourd'hui absents**.

Aucun de ces calculs n'est une prédiction. Ce sont des descriptions d'un observé,
horodatées, sourcées, versionnées.

---

**LOT 7 — Sources manquantes**

Ce qu'aucune source n'apporte aujourd'hui, via les adaptateurs officiels déjà prévus
(ADR-013, ADR-015) — jamais par scraping, jamais en contournant un droit.

- **Courbe des taux** (source officielle de dette souveraine).
- **Horaires et calendrier de séance** des places — c'est ce qui manque au module
  « Sessions mondiales » de Marchés, aujourd'hui absent faute de contrat.
- **Historique d'IV et de chaîne d'options persisté** : sans lui, ni IV Rank ni
  activité inhabituelle ne sont calculables. C'est un lot de stockage autant que de
  source.
- **Séries d'indices de référence** pour la comparaison de portefeuille.

Chaque source arrive avec droits, rétention, fraîcheur et état dégradé déclarés.

---

**LOT 8 — Intelligence d'options**

Sur la chaîne déjà servie, contrat par contrat.

- **Ratio put/call** (volume et open interest), avec population et méthode publiées.
- **Max pain** : déterministe à partir de l'open interest par strike.
- **IV Rank et IV percentile**, dès que le lot 7 a un historique — et **absents tant
  qu'il ne l'a pas**, dit à l'écran, pas approximé.
- **Activité inhabituelle** : volume rapporté à une base historique explicite, jamais
  à une intuition. Une anomalie sans base est une absence.
- **Agrégation des Greeks** par échéance et par position — aujourd'hui jamais agrégés.
- Structure par terme et skew **agrégés**, pas seulement par groupe.

*Débloque :* 8 modules d'Options, 2 du Simulateur.

---

**LOT 9 — Intelligence de marché**

- **Rotation sectorielle** : performance relative des secteurs sur deux fenêtres,
  à partir de la carte sectorielle déjà servie.
- **Régime de marché** : classification **déterministe et publiée** (tendance,
  volatilité, ampleur), avec ses bandes écrites dans un ADR. Pas une prédiction —
  une étiquette de l'observé, datée.
- **Indice de conditions** (ce que le brief appelle « sentiment 0–100 ») : composite
  à formule publiée, composantes visibles et décomposables. Refusé s'il ne peut pas
  être décomposé à l'écran.
- **Courbe des taux** rendue, avec ses échéances et sa source.

*Débloque :* 9 modules de Marchés, 5 d'Aujourd'hui.

---

**LOT 10 — Décision décomposée**

L'`AdviceEngine` calcule déjà dix gates chiffrées avec leurs `observed_values` et
`thresholds`. Ces valeurs **sont servies et ne sont presque pas affichées.**

- Exposer la **contribution de chaque facteur** au verdict — c'est le « score
  décomposé » du brief, et il n'exige aucun modèle nouveau : il expose l'existant.
- Publier la **lignée complète** (`engine_version`, `input_hash`, `result_hash`,
  `method`) jusqu'à l'écran.
- Publier les gates d'Opportunités, qui les calcule et les jette aujourd'hui.

*Débloque :* 10 modules d'Analyse, 8 d'Opportunités.

---

**LOT 11 — Résultat et apprentissage**

Ce qui manque pour que Vertex mesure ce qu'il a dit.

- **Issue des thèses** : une thèse fermée porte son résultat réalisé. Sans ce champ,
  ni taux de réussite ni expectancy n'existent.
- **Taux de réussite** et **espérance** — historiques et comptés, **jamais** présentés
  comme une probabilité de succès futur, et toujours avec leur population.
- **Comparaison à un indice de référence** du portefeuille.
- **Attribution de performance** par position et par secteur.

*Débloque :* 10 modules de Portefeuille, 8 de Suivi.

---

**LOT 12 — Risque servi**

Le catalogue Risques a **14 modules absents sur 22** — le pire ratio du produit.

- Concentration, corrélation, extrêmes et bandes existent déjà en Python ; ce qui
  manque est le contrat qui les publie.
- Jours perdus à l'alignement, avertissement de synchronicité, Herfindahl.

*Débloque :* 14 modules de Risques.

---

**LOT 13 — Observabilité et recherche**

- **Latence** réelle des routes et des jobs, mesurée, pas déclarée.
- **Backtest** en runtime de recherche isolé, sans aucune écriture live, avec
  provenance et fenêtre déclarées. Un résultat de backtest ne partage jamais le
  statut visuel d'une observation.

*Débloque :* les modules de Système, et le dernier bloc du brief.

---

### PHASE IV — Les douze pages (lots 14 à 21)

Chaque page est refaite **une fois que sa matière est servie**. Deux pages par lot,
appariées par leur source commune. Méthode identique partout :

1. composition asymétrique avec un point focal unique ;
2. hiérarchie **SIGNAL → PREUVE → RISQUE → DÉCISION** ;
3. les modules servis habillés avec les widgets et graphiques justes ;
4. les modules encore absents **laissés absents**, avec leur motif ;
5. relecture de captures aux trois largeurs **avant** commit — c'est ce qui a trouvé,
   cette session, une règle CSS morte, un débordement de 118 px, un thème natif clair
   et un canal de texte confondu avec un canal de code serveur, dont aucun n'avait été
   vu par un test.

| Lot | Pages | Sert |
|---|---|---|
| **14** | Aujourd'hui · Marchés | lots 7, 9 |
| **15** | Opportunités · Analyse | lot 10 |
| **16** | Options · Simulateur | lot 8 |
| **17** | Portefeuille · Performance | lots 11, 12 |
| **18** | Suivi · Calendrier | lot 11 |
| **19** | Vertex IA · Système | lots 10, 13 |
| **20** | Graphiques (dans Analyse) · Risques (dans Performance) | lots 9, 12 |
| **21** | Passe de cohérence : les douze relues côte à côte | — |

Deux poses spécifiques du brief, toutes deux sur donnée réellement servie :

- **Options** — barres miroir Calls / strikes / Puts, ATM en ambre, sur l'open
  interest et le volume publiés par contrat. La notion de « mur » n'est pas servie et
  ne sera pas dérivée dans le navigateur.
- **Simulateur** — matrice de P&L colorée sur la grille de scénarios servie verbatim.

---

### PHASE V — Finir (lots 22 à 24)

**LOT 22 — Accessibilité et clavier.** WCAG 2.2 AA sur les douze espaces, axe sans
violation critique ni sérieuse, parcours complets au clavier, focus restauré,
zoom 200 %, `prefers-reduced-motion`, alternative tabulaire à chaque graphique.

**LOT 23 — Performance.** Budgets de `PERFORMANCE_BUDGETS.md` tenus et **mesurés** :
chaînes d'options lourdes, tables de 10 000 lignes, contre-pression, chargement
paresseux des deux moteurs graphiques.

**LOT 24 — Recette et release.** Captures des douze espaces aux trois largeurs dans
les états `loading`, `empty`, `partial`, `stale`, `offline`, `error`. Firefox et
WebKit réels. SBOM, provenance, audit de dépendances. Puis la décision de version
te revient.

---

## 5 bis. Défauts hérités de l'audit #9, vérifiés aujourd'hui

La PR #9 (audit du 2026-08-31, jamais évaluée) portait deux `P0` et onze `P1`.
Chacun a été **rejoué sur le `main` du 2026-09-04**, pas cru sur parole.

### Les deux P0 sont corrigés

| ID | Constat de l'audit | État vérifié |
|---|---|---|
| B-P0-01 | Le service IBKR continu n'atteignait jamais `connectAsync` : deux autorités rejouaient la même transition. | **Corrigé.** `tools/run_edge_ibkr.py` construit l'adaptateur avec `manage_connection_state=False` ; le runner est seul maître des transitions, et le commentaire le dit. |
| B-P0-02 | Des valeurs réellement issues d'IBKR étaient commitées dans un dépôt public. | **Corrigé.** La fixture de `apps/edge-ibkr/tests/test_normalize_bars.py` est un instrument inventé, `con_id` hors plage réelle, et porte la mention explicite qu'aucune observation réelle ne doit entrer dans l'historique Git. |

### B-P1-11 est RÉEL et VIVANT — un rendement faux affiché comme valide

**Le seul défaut de vérité financière ouvert du produit.** `xirr` vérifie
l'unicité de la racine par changement de signe sur une grille fixe de 25 taux,
dont les intervalles sont larges (0,4 → 0,7 → 1,0 → 2,0 → 5,0 → …). **Deux
racines situées dans un même intervalle ne produisent aucun changement de signe
à ses bornes : elles sont invisibles.** S'il en existe une troisième ailleurs,
la grille voit exactement un encadrement et la fonction conclut à l'unicité.

Reproducteur exécuté sur `main`, flux à trois racines réelles — 15 %, 45 %, 55 % :

```
flux : -38 690,33 / +160 564,88 / -220 438,17 / +100 000,00 sur quatre ans
statut : CalculationStatus.OK
taux   : 0.15000057319753943
raison : None
```

Le produit affiche **15,00 %** comme le rendement, sans réserve, alors que 45 %
et 55 % sont des réponses tout aussi valides. La limitation est écrite dans la
docstring, mais **une docstring n'est pas une porte** : l'écran, lui, ne dit
rien.

Le test existant `test_multiple_roots_return_invalid` ne l'attrape pas : ses
deux racines (7,2 % et 27,8 %) tombent dans des intervalles différents, donc la
grille les sépare. Aucun test ne couvre le cas rapproché.

**Traitement : LOT 2 bis, avant toute refonte visuelle.** Un chiffre faux
présenté comme valide passe devant l'apparence.

### Les dix autres P1 sont repris dans le plan

| ID | Sujet | Lot |
|---|---|---|
| B-P1-01 | Une top-of-book brute étiquetée `ibkr.daily-quote/1` : chaque cotation live devient `invalid_payload`. | LOT 7 |
| B-P1-02 | Les cotations brutes invalides peuvent évincer les cotations quotidiennes valides — Marchés peut se vider. | LOT 7 |
| B-P1-03 | Une observation peut être persistée après un code IBKR 1100/1300. | LOT 7 |
| B-P1-04 | L'intégration edge PostgreSQL n'est pas dans la CI. | LOT 13 |
| B-P1-05 | L'outbox reste `IN_PROGRESS` après un crash. | LOT 13 |
| B-P1-06 | Le démarrage local n'est pas un démarrage coordonné. | LOT 13 |
| B-P1-07 | Compose web non fonctionnel. | LOT 13 |
| B-P1-08 | Univers réel et fenêtre Marchés incompatibles. | LOT 9 |
| B-P1-09 | Le backfill amplifie l'outbox. | LOT 7 |
| B-P1-10 | TradingView n'est pas un runtime durable. | LOT 7 |

---

## 5 ter. LOT 2 bis — prouver l'unicité de la racine du XIRR

Inséré entre le lot 2 et le lot 3. Il ne touche à aucun pixel.

1. **Écrire le test rouge d'abord** : le flux à trois racines ci-dessus doit
   rendre `INVALID`, pas `OK`. Ajouter aussi le cas à deux racines rapprochées
   dans un même intervalle.
2. **Rendre le contrôle d'unicité solide**, au choix argumenté par ADR :
   raffinement adaptatif de la grille jusqu'à une résolution prouvée, comptage
   des changements de signe des coefficients (règle de Descartes) pour borner le
   nombre de racines, ou refus explicite des flux non conventionnels dont
   l'unicité n'est pas démontrée. Jamais un élargissement silencieux de la
   grille.
3. **`INVALID` ne porte jamais de chiffre** — la règle existe déjà et son test
   aussi ; le lot doit la laisser vraie.
4. **Tests de propriétés** sur des flux non conventionnels générés, avec un
   oracle indépendant du nombre de racines.
5. Vérifier les consommateurs : `/performance/{portfolio_id}`, le worker de
   performance, la page Portefeuille et l'explication IA doivent tous rendre
   l'absence, pas un chiffre de repli.

*Fini quand :* aucun flux ne peut produire un taux présenté comme unique sans
que l'unicité soit démontrée, et le reproducteur ci-dessus est vert en `INVALID`.

---

## 6. Ce que ce plan ne fera pas

- Afficher un chiffre qu'aucun calcul Python n'a produit, versionné et signé.
- Calculer quoi que ce soit de financier dans le navigateur.
- Présenter une classification descriptive comme une prédiction, ou une probabilité
  sans calibration ni validation hors échantillon.
- Lire un compte, un solde, une position, un P&L, un ordre ou une exécution IBKR.
- Écrire un bouton, une route ou un mot qui pourrait déclencher une transaction.
- Affaiblir, désactiver ou supprimer un test.
- Fusionner, publier, supprimer à distance ou migrer sans ta validation.

---

## 7. Preuve exigée à chaque lot

Depuis un checkout propre, aucune commande ne source `env.live` :

```bash
cd apps/web && npx tsc --noEmit && npx biome check src && npx vitest run && npm run build
```

Puis, sérialisé derrière `flock`, avec seulement `VERTEX_TEST_DATABASE_URL` et
`VERTEX_ALLOW_TEST_DB=1` :

```bash
npx playwright test
```

Côté Python : `ruff`, `mypy --strict`, `pytest`, et les tests de propriétés du
calcul ajouté.

Le compte rendu de lot donne : ce qui a changé, les fichiers, les composants créés
ou réutilisés, **les commandes et leurs résultats exacts**, les captures aux trois
largeurs, les états dégradés vérifiés, la dette restante, le SHA, et une seule
prochaine commande recommandée.

---

## 8. Où en est le plan

| Phase | Lots | État |
|---|---|---|
| I — Assainir | 0, 1, 2, **2 bis** | **lot 0 terminé** — 14 PR fusionnées, #9 instruite |
| II — Socle visuel | 3, 4, 5, 6 | lot 3 amorcé (ADR-018 rédigé) |
| III — Intelligence | 7 → 13 | à faire |
| IV — Les douze pages | 14 → 21 | à faire |
| V — Finir | 22, 23, 24 | à faire |

L'avancement réel est tenu dans `docs/99-status/NOW.md`, réduit à un état, à partir
du lot 1.

---

## Annexe — registre de cette branche

`docs/09-adr/018-titan-ledger-institutional-signal.md` est présent sur cette
branche. Il y est arrivé par mégarde : le commit `4b48284`, dont le message ne
parle que des chantiers de LOT-00, l'a embarqué parce que la commande de mise en
index balayait tout le répertoire de travail au lieu des seuls fichiers voulus.

Le message de ce commit ne peut plus être corrigé sans réécrire une branche déjà
poussée, ce que le protocole du dépôt interdit. La note ci-dessous fait donc foi :
**`4b48284` contient deux choses, l'amendement du plan et l'ADR-018.**

L'ADR reste ici plutôt que d'être déplacé, parce que cette branche porte la
doctrine et qu'un déplacement de plus ajouterait du bruit sans rien clarifier. Il
est le livrable du **lot 3**, et le lot 3 le tiendra pour acquis : son travail
restant est le contrat de style écrit, la réécriture du canon et l'extension de la
porte documentaire, pas la rédaction de l'ADR.
