# Plan de nuit — Identité « Black Glass v3 » et planches bento

> **Ce document est le mandat de travail autonome.** Il survit à une perte de
> contexte : tout ce qu'il faut pour reprendre sans nouvelle instruction est
> ici. Les règles du dépôt (`CLAUDE.md`, `.claude/rules/*`, ADR-017) priment
> sur lui en cas de conflit.

## 0. Mandat

Demande utilisateur, 2026-09-03 : rapprocher Vertex des tableaux de bord de
référence fournis (dix captures : Stocky, Fundex, DSEX, Owari, ManyCrypto,
stoX, SaaSPro, Homies Lab, widgets de cotation). Textuellement :

- « les boutons des graphiques, les widgets, les couleurs, les textes, le côté
  glass black de chaque carte » ;
- « entre les cartes c'est toujours la même » → **faire du tetris** : des
  planches bento à tailles variées, pas des grilles uniformes ;
- « plus beau, plus soft » ;
- « moins de texte, du concret et de l'essentiel » ;
- « travailler toute la nuit sans mes accords », « peaufine, peaufine ».

Autonomie accordée : ouvrir, pousser et **fusionner** les lots quand les sept
checks requis sont verts. Une seule exception permanente : rien qui viole les
interdictions absolues du dépôt.

## 1. Ce que les références demandent, et ce que Vertex peut rendre HONNÊTEMENT

| Forme de référence | Primitive | Verdict |
|---|---|---|
| Tuile d'indice : nom, grand chiffre, pastille, mini-courbe | `InstrumentTile` | déjà posé (Aujourd'hui, Marchés, Options) |
| Grand chiffre + pastille de variation colorée | `Metric` + `KpiDelta` | posé (P4, P1) |
| Chips de période `1D 5D 1M YTD` | `PeriodTabs` | posé (P5) — à étendre |
| Aire à dégradé, marqueurs de points | `SparkFigure` variante `area` | posé — à étendre |
| Deux/trois séries superposées | `MultiSeriesArea` | posé (P5, bandes de Bollinger) |
| Barres verticales par période | `DayBars` | posé (P5, volume) |
| Anneau à total central + légende chiffrée | `RingShares` | posé (P4) |
| Jauge en arc « strength meter » | `ArcGauge` | posé (P1 breadth, P5 RSI) |
| Barres de progression avec reste | `LinearGauge`, `SharesBand`, `CensusBars` | posés |
| Pastille d'icône colorée sur une KPI | — | **T1** : ajouter `KpiTile` (icône + libellé + chiffre + delta) |
| Liste d'étapes / pipeline | `StepList` | **jamais posé** → P2, P6 |
| Ligne de provenance compacte | `ProvenanceLine` | **jamais posé** → toutes |
| Tags colorés en tableau | `StatusChip` | posé |
| Radar multi-axes | — | **refusé** : ADR-017 interdit un radar sans dimension multiple servie |
| **Mini-courbe par ligne de tableau** | — | **refusé** : aucune série par ligne n'est servie (vérifié sur `MarketsTicker`, `CandidateView`, peers, `PortfolioTable`). Substitut établi : la rangée de tuiles d'instrument au-dessus du tableau |
| **Valeurs abrégées « $78K »** | — | **refusé** : ADR-017, formes interdites |
| **Jauge âge / budget** | — | **refusée** tant que `FreshnessPolicyView` ne publie que `{budget_seconds, kind, version}` |

Ces quatre refus sont définitifs tant que le contrat serveur ne change pas.
Ils sont écrits ici pour ne pas être re-débattus à chaque lot.

## 2. Lots, dans l'ordre d'exécution

Chaque lot = une branche `lot/<slug>-20260903`, une PR, une fusion en squash
quand les sept checks sont verts. Aucun lot ne démarre avant que le précédent
soit fusionné.

### T1 — Black Glass v3 : la matière, partout (le plus fort levier)

Le socle visuel touche les douze destinations d'un coup.

1. **Jetons** (`src/design/tokens.ts` → `pnpm tokens:css`) :
   - profondeur de verre : `--vx-glass-veil` (voile de surface),
     `--vx-glass-edge` (liseré haut, 1 px), `--vx-shadow-glass` ;
   - deux crans de rayon supplémentaires si nécessaire (les références sont à
     16–20 px, le socle a `radius-18: 16px` et `radius-22: 20px` — suffisant) ;
   - `--vx-elev-1/2/3` : trois profondeurs, pas plus.
2. **Carte** (`.vx-card`) : surface `surface-1`, liseré haut clair 1 px
   (`glass-edge`), ombre douce, rayon 20 px, bordure presque invisible.
   La dominante garde `surface-2` + sa tranche ambre. **Aucun glow permanent,
   aucun flou de fond** (interdits par l'identité).
3. **Boutons et chips** (`.vx-primary-action`, `.vx-opp-inspect`,
   `.vx-w2-chip`, `PeriodTabs`) : hauteur unique, rayon pilule, état de survol
   et de focus visibles, segmenté actif en surface pleine (référence stoX,
   DSEX, ManyCrypto).
4. **Typographie** : échelle des chiffres resserrée (`metric` 34 → titres),
   libellés en capitales espacées, `tabular-nums` partout où il y a un chiffre.
5. **Densité** : `--vx-space-*` inchangés ; réduire les paragraphes explicatifs
   des modules à UNE phrase, déplacer méthode et lignée dans un
   `<details>` ou `ProvenanceLine`. **« Moins de texte » ne retire jamais une
   valeur, une unité, une période ou un aveu d'absence** — ce sont eux le
   « concret et essentiel ».
6. **Portes** : `no-raw-colors` et `tokens-css` restent verts ; toute teinte
   passe par un jeton.

Preuve : captures des douze destinations aux trois viewports, avant/après.

### T2 — `KpiTile` : la tuile de mesure des références

Nouvelle primitive `src/components/widgets/KpiTile.tsx` : pastille d'icône
(glyphe du catalogue, `aria-hidden`), libellé, chiffre servi en grand, unité,
`KpiDelta` en dessous, et une `SparkFigure` optionnelle en fond bas de tuile
quand une série est servie. Refus : sans valeur servie, la tuile DIT l'absence
et ne dessine ni fond ni pastille de variation.

Consommateurs : bande de tête de Portefeuille, Aujourd'hui, Marchés,
Performance, Sources.

### T3 — Planches bento (« tetris »)

Aujourd'hui, chaque planche est une grille d'aires nommées à colonnes égales.
Les références varient les tailles. Pour chaque planche, retravailler les
`grid-template-areas` (dans `widgets.css`, **après** les spans du socle) pour
que la dominante et les mesures de tête occupent des surfaces franchement
différentes des modules de support, avec des hauteurs de ligne variées
(`grid-auto-rows: minmax(...)`), et vérifier sur capture qu'aucune cellule ne
laisse un grand vide.

Ordre : Aujourd'hui → Marchés → Portefeuille → Risques → Graphiques →
Opportunités → Analyse → Options → Simulateur → Catalyseurs → Calendrier →
Sources.

### P2 — Analyse + Opportunités sur les formes v2

- Analyse : `InstrumentTile` en en-tête, `PeriodTabs` sur les chandeliers
  (bornées par `bars.count`), **`StepList` des dix gates** avec
  `observed_values` / `thresholds` publiés mais non lus aujourd'hui
  (`analysisView.ts:153-175`), `SparkFigure` sur les séries d'indicateurs
  (mêmes blocs S6 que Graphiques), `CellGrid` des scénarios, `ProvenanceLine`.
- Opportunités : `StatusChip` par candidat, `CensusBars` sur
  `coverage.status_counts` et `exclusion_reasons`, `StepList` compact des
  gates, `CellGrid` gate × statut. Accent `warning` reste suspendu.
- Les deux : `Card` → `Widget`, placement déplacé dans `widgets.css`,
  matière v2 étendue.

### P3 — Options + Simulateur

Poser `data-page-accent="option"` (déclaré depuis le socle, jamais posé),
`DayBars` du volume et de l'open interest **par strike**, `CensusBars` du
budget de lignes, `CellGrid` spot × temps des scénarios, `StepList` de la
méthode.

### P6 — Catalyseurs + Calendrier + Sources & Rapports

`ActivityFeed` sur la chronologie et l'agenda, `DayBars` de densité,
`CensusBars`, `StepList` du pipeline, `ProvenanceLine`. Refus documenté de
l'arc de fraîcheur.

### A — Audit complet, après T1→P6

Relancer l'audit des douze destinations : captures aux trois viewports,
relecture, liste des défauts, correction, puis un rapport unique dans
`NOW.md`. C'est la demande « relance une nouvelle analyse complète ».

## 3. Boucle de travail, à répéter pour chaque lot

```bash
cd /home/user/vertex-merge
git fetch origin main && git checkout -B lot/<slug>-20260903 origin/main
# … modifications, test rouge d'abord pour tout défaut corrigé …
cd apps/web
npx tsc --noEmit && npx biome check src && npx vitest run && npm run build
```

Puis, sérialisé derrière `flock`, **jamais `env.live`** :

```bash
S=/tmp/claude-0/-home-user/4123c2db-2e1f-53c8-9349-0817c587603b/scratchpad
flock "$S/.e2e.lock" env PATH="/home/user/Vertex-1.0-Beta-/.venv/bin:$PATH" \
  VERTEX_TEST_DATABASE_URL="postgresql+psycopg://vertex:$(cat $S/.pgpw)@127.0.0.1:5432/vertex_test" \
  VERTEX_ALLOW_TEST_DB=1 PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
  npx playwright test e2e/<page>.spec.ts e2e/shell-canonical.spec.ts e2e/accessibility.spec.ts
```

Enfin `bash tools/run_checks.sh` depuis la racine, **seul**.

**Relecture obligatoire des captures** aux trois largeurs avant commit. Outil
de découpe sans dépendance : `node $S/pngcrop.mjs <src> <dst> x y w h [échelle]`.

Les huit défauts les plus graves de cette session n'ont été vus QUE sur
capture, jamais par un test : media query jamais fermée, table tronquée,
chiffre débordant de l'anneau puis de l'arc, bandes de matrice invisibles,
« ok ok », jauge coupée, bornes « 0100 », **barre de `DayBars` jamais peinte**.

## 4. Invariants — non négociables, à chaque lot

- Aucune valeur, aucun pourcentage, aucun signe fabriqué pour remplir une forme.
- Une donnée absente reste absente et le DIT ; jamais un zéro, jamais un tiret.
- Le signe ne colore que s'il est **publié** (`signGroupOfText`), une seule
  règle sur toutes les planches.
- Vert et rouge réservés au signe financier servi ; la teinte de page n'en
  porte jamais.
- Une seule dominante par page, portée par `Card`.
- Test reproducteur **rouge d'abord** avant toute correction de défaut ; aucun
  test affaibli, aucune assertion desserrée pour faire passer une forme.
- Le placement d'une planche convertie vit dans `widgets.css`, **après** les
  spans du socle — piège déjà payé trois fois.
- Aucun ordre, aucune position de courtier, aucun résultat de compte.
- PR par lot, fusion en squash quand les sept checks requis sont verts.

## 5. Rouge connu, hors lot

`apps/edge-ibkr/tests/test_denylist.py::test_adapter_satisfies_the_port_protocol`
échoue sur cette machine en Python 3.11.15, **y compris sur `origin/main`
intact**. La CI cible 3.13 et le passe. Ne pas le traiter comme une régression.
