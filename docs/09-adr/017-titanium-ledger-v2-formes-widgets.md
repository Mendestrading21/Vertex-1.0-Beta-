# ADR-017 — Titanium Ledger v2 : formes admises pour les widgets

- Statut : Accepté
- Date : 2026-09-03
- Décideurs : propriétaire produit (décision écrite du 2026-09-03 : « pour chaque widget trouve toujours le meilleur, crée tes propres visuels au max, que ça affiche au max »), responsable du design system
- Portée : `apps/web/src/design/tokens.ts` et le `tokens.css` généré ; primitives de widgets (`apps/web/src/components/widgets/`, lot L0) ; `docs/05-design/*` ; `.claude/skills/vertex-titanium-ledger/references/*` ; `manifests/widget-catalog.yaml` ; lots C0 (cette décision), L0 (socle), P1–P6 (pages)
- Remplace : aucun. Complète ADR-007 (« SVG ou CSS interne est réservé aux micro-visualisations simples ») : le périmètre des micro-visualisations est étendu ci-dessous ; la règle d'autorité — aucune valeur financière calculée en TypeScript — est inchangée.

## Contexte

Faits vérifiables :

1. Le canon v1 interdisait, par formulation, plusieurs formes : « jauges uniquement linéaires/segmentées … aucun cadran décoratif ou score opaque » et « gradients réservés à sélection/action principale » (`docs/05-design/DESIGN_SYSTEM.md`, règles visuelles) ; « Formes autorisées : barre linéaire, bullet chart et bande segmentée … Aucun speedometer, score opaque, aiguille animée ou 3D » (`docs/05-design/CHART_STANDARD.md`, jauges) ; « aucun compteur automobile, aiguille animée, volume 3D ou score composite opaque » (`docs/05-design/WIDGET_LIBRARY.md`, jauges factuelles) ; « SVG/CSS interne seulement pour sparklines, micro-barres et jauges factuelles … aucun globe, cadran ou particule » (`docs/05-design/DASHBOARD_COMPOSITION.md`, graphiques) ; `visual_contracts.gauges.allowed_forms` limité à `linear_bullet`, `segmented_band`, `progress_with_target` (`manifests/widget-catalog.yaml`). Le code a suivi : `CensusBars` remplace « tous les donuts des planches » par des barres de dénombrement (`apps/web/src/components/CensusBars.tsx`, en-tête ; `docs/05-design/REFONTE_TITANIUM_LEDGER.md`, lot A4).
2. La capture canonique (`.claude/skills/vertex-titanium-ledger/assets/vertex-dashboard-canonical.png`, SHA-256 `eb2eb0fc…c7ace`, **inchangée par cette décision**) et les six planches montrent des anneaux, des arcs et des aires : tension documentée entre la capture, qui a autorité de style (`SKILL.md`), et les formulations ci-dessus.
3. L'utilisateur a fourni vingt-sept références de style (vingt-trois dans l'étude, quatre en addendum) dont les formes récurrentes sont : anneaux/donuts à chiffre central, jauges en arc graduées, aires « montagne » à dégradé, rails visibles derrière les barres, matrices de bandes, quatuors d'anneaux, listes groupées par jour, et une seconde teinte sémantique par écran.
4. Les données servies le 2026-09-03 (08:40–09:05 UTC) sont majoritairement vides ou invalides : `markets/overview` `breadth INVALID` 0/161, `performance/1` `series.points []`, chaîne d'options vide, calendrier `empty`, `today/attention` 15 éléments, `analysis/AEHL` 27 barres. Toute forme nouvelle rendra donc d'abord des états honnêtes ; c'est un chantier de données (D0), pas une raison de fabriquer.
5. Les invariants qui ne se discutent pas : aucun calcul financier en TypeScript (`apps/web/src/design/no-authoritative-calculation.test.ts`) ; aucune valeur fabriquée (`no-fabricated-values.test.ts`) ; absence ≠ 0 ni tiret ambigu (`docs/05-design/UI_STATES.md`, huit états) ; couleurs par tokens uniquement (`no-raw-colors.test.ts`) ; une dominante par page (`one-dominant-per-page.test.ts`) ; `tokens.css` généré depuis `tokens.ts` (`tokens-css.test.ts`, dérive vérifiée en CI).

Une décision durable est nécessaire parce que la reconstruction page par page (lots P1–P6) ne peut pas arbitrer à chaque widget entre la capture, les références et les textes.

## Décision

Le canon Titanium Ledger passe en **version 2**. Une forme est admise si et seulement si **chaque grandeur qu'elle dessine est servie** (chaîne ou entier publié par l'API, ou position/pourcentage calculé par le serveur). Le navigateur ne calcule que de la géométrie (échelle, position) sur des propriétés renommées à noms neutres (`value`, `pct`, `parts`, `points`) et n'écrit jamais un nombre dérivé.

### Formes admises et donnée servie qu'elles exigent

| Forme | Donnée servie exigée | Primitive (lot L0) | Refus (état nommé, jamais 0) |
|---|---|---|---|
| Anneau / donut à chiffre central | parts en pourcentage servies (`*_pct`, chaînes) ; le chiffre central est une valeur servie verbatim (total, part principale ou compte), jamais une somme calculée | `RingShares` | part `null` → absente de l'anneau et listée « non publié » ; plus de quatre teintes → refus (protocole de nuance) |
| Quatuor d'anneaux | quatre parts ou valeurs bornées servies, chacune avec unité, période et `as_of` | `RingShares` ×4 en rangée | idem ; un anneau manquant reste un cadre qui dit l'absence |
| Jauge en arc à graduations | valeur bornée servie, bornes, seuils et **position en pourcentage servie** (coordonnées serveur), méthode/version, qualité, `as_of` | `ArcGauge` | position `null` ou statut `INVALID` → « non calculable » et raison servie, aucun arc de remplissage |
| Jauge linéaire, bullet, bande segmentée (v1, conservées) | idem | `LinearGauge` | idem |
| Aire à dégradé sous une série | série servie d'au moins deux points (chaînes), période nommée ; dégradé **vertical** de la teinte sémantique de la série vers sa transparence (tokens `<famille>-gradient-start` → `<famille>-gradient-end`) | `SparkFigure`, `MultiSeriesArea` | moins de deux points → « série insuffisante (n barre) » ; jamais sur un fond de carte |
| Sparkline en aire | idem, base pointillée = première clôture servie | `SparkFigure` | idem |
| Rail derrière les barres | comptes entiers ou parts servies ; le rail est la piste neutre (`titanium-soft`) qui rend la proportion lisible | `CensusBars`, `DayBars` | valeur `null` → aucune barre, cellule « non publié » ; toutes nulles → phrase d'absence |
| Matrice de bandes | cellules portant un **nom de bande servi** et un texte servi ; légende des bandes servie | `CellGrid` | bande absente → `data-band="unknown"` visible, jamais un défaut silencieux |
| Liste groupée par jour | horodatages ISO servis ; regroupement sur un champ servi non nul (ex. `provenance.last_received_at`, pas `first_published_at` lorsqu'il vaut `null`) ; montants en chaînes signées | `ActivityFeed` | montant `null` → « montant non publié » ; « aujourd'hui / hier » interdits sans `as_of` servi |
| Teinte sémantique secondaire par page | déclarée dans le catalogue de la page, une famille parmi `macro`, `option`, `positive`, `warning` (source typée `pageAccent`, `apps/web/src/design/tokens.ts`) ; exposée par `[data-page-accent="<famille>"]` → `--vx-page-accent`, `--vx-page-accent-soft`, `--vx-page-accent-gradient-start/-end` | attribut de composition | famille hors vocabulaire → erreur de type ; `signal` (ambre) n'est pas éligible |

Règles qui accompagnent ces formes :

- **Une famille par page.** La teinte secondaire garde le sens de sa famille (`positive`/`negative` = signe financier ; `macro` = contexte ; `option` = domaine options ; `warning` = prudence, retard, synthétique). Elle n'est jamais décorative, jamais choisie par un hex libre, et l'ambre de marque reste la seule lumière de la dominante (tranche, kicker, sélection).
- **Dégradés.** Trois familles de dégradé sont admises, aucune autre : (1) la variation de matériau déjà admise (dominante : `titanium-soft` → transparent) ; (2) la sélection / action principale et la tranche ambre de la dominante, dans la famille `signal` — c'est la règle « gradients : sélection/action principale » de `docs/05-design/DESIGN_SYSTEM.md` (règles visuelles), et les précédents en vigueur dans `apps/web/src/styles/global.css` à `main@4fc901a` : `[data-rank='dominant']::before` et `.vx-card[data-rank='dominant']::before` (`signal-bright` → `signal-deep`, lignes 4538 et 5271), `.vx-primary-action` (`signal-bright` → `signal`, ligne 4772 ; au survol `silver` → `signal-bright`, ligne 4780), `.vx-page-header::before` (`signal-bright` → transparent, ligne 4448) ; (3) l'aire sous une série servie, de `<famille>-gradient-start` vers `<famille>-gradient-end`. La restriction « jamais entre deux teintes » porte sur cette aire de série seulement : elle va toujours vers la transparence de sa propre famille (`.claude/skills/vertex-titanium-ledger/references/charts.md`, « Couleur et comparaison »). Aucune des trois familles n'est un fond plein de carte ni un dégradé décoratif.
- **Texte toujours présent.** Chaque anneau, arc, barre ou cellule porte sa valeur servie en texte, son unité et sa période ; la couleur n'est jamais seule.
- **Mouvement.** `--vx-motion-600` (nouveau token `motionDuration[600]`) sert à la surbrillance unique d'une valeur dont `snapshot_version` a changé. Sous `prefers-reduced-motion`, la durée générée tombe à 0 ms et l'attribut `data-updated` reste posé environ une seconde en contour statique (`docs/05-design/MOTION_AND_MICROINTERACTIONS.md`, « Valeur mise à jour »). Aucune animation continue, aucun compteur roulant.
- **Une dominante par page** reste un rang de carte (`rank="dominant"`), pas une teinte.

### Formes toujours interdites

- halos ou néons permanents, glow de sélection ;
- noir pur comme fond ou surface ;
- cartes translucides floues (le blur reste réservé au rail ou à la fiche superposée) ;
- couleur seule sans texte, signe ou motif ;
- compte à rebours, horloge client, ou toute fraîcheur déduite de `Date.now()` ;
- radar ou nuage de points sans dimension multiple servie ;
- dégradé de fond plein sur une carte ;
- pulsation, aiguille animée, compteur roulant ;
- valeur abrégée côté client (« 12.4K ») ;
- score composite opaque, cadran décoratif, 3D ;
- toute forme sur une valeur non servie.

## Conséquences

### Positives

- Les lots de pages disposent d'un vocabulaire fermé et testable au lieu d'arbitrer widget par widget entre capture, références et textes.
- La capture canonique et les textes cessent de se contredire sur les anneaux et les arcs ; l'empreinte de la capture ne change pas.
- Les références de l'utilisateur sont honorées là où la donnée existe, et refusées par un état nommé là où elle n'existe pas.

### Coûts et contraintes

- Tokens ajoutés (source typée, CSS régénéré et commité) : `motionDuration[600]` ; douze tokens de dégradé `<famille>-gradient-start/-end` pour `silver`, `positive`, `negative`, `warning`, `option`, `macro` ; vocabulaire `pageAccent` et blocs `[data-page-accent]`. Propriétaire : `apps/web/src/design/tokens.ts`.
- Le socle L0 doit livrer `RingShares`, `ArcGauge`, `LinearGauge`, `SparkFigure`, `DayBars`, `CellGrid`, `ActivityFeed`, `MultiSeriesArea` avec tous leurs états nommés et leurs tests ; aucune page ne dessine une forme v2 sans passer par ces primitives.
- Les documents du canon citent cette ADR à chaque interdiction levée ; un test de design (`apps/web/src/design/canon-v2-docs.test.ts`) refuse le retour des anciennes formulations et vérifie que les interdits maintenus sont toujours écrits.
- Plusieurs formes attendent une donnée serveur (lots S1–S6, D0) : comptes avancées/déclins, budget de fraîcheur avec position servie, séries rebasées, séries glissantes. En attendant, l'état honnête s'affiche.

## Options rejetées

| Option | Motif du rejet |
|---|---|
| Conserver le canon v1 (barres de dénombrement seules, jauges linéaires seules) | Contredit la décision écrite de l'utilisateur du 2026-09-03 et la capture canonique elle-même |
| Une dominante chromatique par page (vert, teal, violet, orange des références) | « une couleur = une signification » ; l'ambre est la seule lumière de marque ; refusé par `no-raw-colors` et `visual-identity.md` |
| Un hex libre par page pour la teinte secondaire | Porte `no-raw-colors` ; la création d'un alias de même hex est interdite par le protocole de nuance |
| Anneaux ou arcs dont le pourcentage est calculé dans le navigateur | Porte `no-authoritative-calculation` ; `WIDGET_LIBRARY.md` : le navigateur ne calcule ni pourcentage, ni seuil, ni position du marqueur |
| Speedometer à aiguille animée, cadran 3D | Décoratif ; contredit MOTION (aucune animation financière continue) et l'accessibilité |
| Dégradé de fond plein sur les cartes KPI (référence 23) | Un fond de carte est un matériau, pas une donnée ; contredit `canonical-visual.md` (cartes opaques, verre discret) |
| Nouvelle empreinte de la capture canonique | La capture n'a pas changé ; toute nouvelle empreinte exige une validation explicite |

## Preuves d'application

- `apps/web/src/design/tokens-css.test.ts` : durées `90/140/180/220/600`, couple de dégradé par famille de série (fin à alpha 0, même triplet RGB que la famille), blocs `[data-page-accent]` par famille existante, `signal` inéligible, aucune valeur par défaut silencieuse.
- `apps/web/src/design/canon-v2-docs.test.ts` : présence de cette ADR avec ses sections ; absence des formulations levées dans les documents du canon ; citation d'`ADR-017` par chacun ; liste des interdits maintenus.
- Portes inchangées : `no-raw-colors.test.ts`, `no-authoritative-calculation.test.ts`, `no-fabricated-values.test.ts`, `one-dominant-per-page.test.ts`, `no-uncalibrated-probability.test.ts`.
- `.claude/skills/vertex-titanium-ledger/scripts/audit_titanium_ledger.py` : empreinte de la capture canonique inchangée ; tokens de dégradé ajoutés aux tokens requis.
- Lot L0 : un fichier de test par primitive (`RingShares.test.tsx`, `ArcGauge.test.tsx`, …) couvrant les onze valeurs de `ModuleState`, la branche « non publié », l'absence de `<linearGradient>` hors aire de série servie, et l'absence de tout nombre dérivé écrit.
- Plan directeur : `docs/05-design/WIDGETS_V2_PLAN.md`.

## Critères de réexamen

Cette décision est réexaminée si l'utilisateur retire ou modifie sa décision du 2026-09-03, si une forme admise s'avère porter une information par la couleur seule ou dessiner une valeur non servie malgré les portes, si l'empreinte de la capture canonique change après validation explicite, ou si une autre ADR Acceptée la remplace.
