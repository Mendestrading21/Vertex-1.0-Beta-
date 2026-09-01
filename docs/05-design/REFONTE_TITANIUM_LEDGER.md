# Refonte Titanium Ledger — plan complet des douze destinations

**Périmètre : identité visuelle uniquement.** Aucune route API, aucun contrat
Python, aucune intégration IBKR ou TradingView, aucune fusion dans `main`.

**Autorité de style.** `.claude/skills/vertex-titanium-ledger/assets/vertex-dashboard-canonical.png`
(SHA-256 `eb2eb0fc…c7ace`) est la seule autorité pour le shell, le matériau, la
palette, la densité et la hiérarchie. Les planches de pages illustrent des
compositions ; elles n'ont autorité ni sur le shell, ni sur la palette, ni sur
les données.

> **Note sur la dernière demande.** Le message « voici toutes les… » n'est
> arrivé **sans pièce jointe** de mon côté. Ce plan est donc construit sur la
> capture canonique et sur les quatre planches déjà fournies plus tôt dans la
> session. Si de nouvelles planches devaient m'être transmises, elles se
> replacent dans le §4 (déclinaison par page) sans toucher au §2, qui ne
> dépend que de la capture canonique.

---

## 1. Le fait qui commande tout le reste

Le thème Titanium Ledger n'est **pas** un système : c'est une **liste de noms**.

Mesuré sur `apps/web/src/styles/global.css` (4 863 lignes) :

| Mesure | Valeur |
|---|---:|
| classes `.vx-*` déclarées | **443** |
| classes atteintes par la couche thématique | **89** |
| listes de sélecteurs énumérées à la main | **15** |

Concrètement, la tranche métallique, le coin de registre, la bordure titane et
l'ombre sont posés par des blocs de la forme :

```css
.vx-chartframe,
.vx-today-primary,
.vx-snapshot-rail,
.vx-health-item,
.vx-perf-metric,
.vx-pf-summary,
…                 /* 15 listes de ce genre */
```

**Conséquence directe, et c'est la raison d'être de ce plan :** un module ajouté
à une page n'hérite de rien. Il faut penser à l'inscrire dans les 15 listes,
sinon il tombe silencieusement hors du thème. « Le même style sur toutes les
pages » n'est donc pas seulement absent — il est aujourd'hui **impossible à
garantir**, et aucune porte ne le détecte.

Un plan qui se contenterait de retoucher des valeurs reproduirait l'écart au
module suivant. La colonne vertébrale de cette refonte est donc :
**une primitive de carte, une seule, et une porte qui refuse les surfaces qui
ne s'y appuient pas.**

---

## 2. Le système commun — identique sur les douze pages

### 2.1 Écarts de densité mesurés (viewport 1600×1000)

| Élément | Contrat canonique | Mesuré aujourd'hui | Écart |
|---|---|---:|---|
| Rail de navigation | ≈ 120 px | **248 px** | +107 % |
| Marge de la zone de travail | gouttières 12–16 px | **40 / 32 / 48 px** | 2 à 3× |
| Espace interne de carte | 14–18 px | 16–24 px selon module | dispersé |
| Inspecteur | 300–340 px | `clamp(300px, 22vw, 340px)` | **conforme** |
| Gouttière travail ↔ inspecteur | 12–16 px | 16 px | **conforme** |
| Largeur utile bornée | — | 1 600 px | conforme |

Le rail est l'écart dominant : il mange **128 px** de largeur utile sur chaque
page, et le contrat interdit nommément un « rail gauche large ».

### 2.2 La primitive de carte (`.vx-card`)

Une seule surface, trois variantes, aucune énumération.

| Variante | Rôle | Tranche métallique | Ombre |
|---|---|---|---|
| `.vx-card` | module secondaire | non | plate |
| `.vx-card[data-rank="dominant"]` | visuel dominant de la page | oui | panneau |
| `.vx-card[data-rank="quiet"]` | mesure, légende, pied | non | aucune |

Anatomie fixe, dans cet ordre : **kicker** (mono, capitales, ≤ 24 car.) →
**titre** (≤ 32 car.) → **corps** → **pied de provenance** (source, `as_of`,
fraîcheur). La provenance reste **près de la donnée**, jamais reléguée en bas de
page.

Espace interne : `--vx-space-16` ; gouttières inter-cartes : `--vx-space-12`.

### 2.3 Une seule lumière dominante par carte

Règle canonique : « une lumière dominante maximum par carte, deux par écran
hors rouge/vert ». La tranche `::before` ambre est aujourd'hui posée sur cinq
familles de classes sans arbitrage de page. Elle devient l'attribut
`data-rank="dominant"`, et une porte compte les porteurs : **au plus un par
page**.

### 2.4 Ce qui ne change pas

- Palette et tokens : déjà centralisés dans `src/design/tokens.css`, aucun écart
  détecté par `audit_titanium_ledger.py` (`missing_color_tokens: []`).
- Vert/rouge : sens financier uniquement, toujours doublé par le signe.
- Ambre : intention et focus de navigation uniquement.
- Les huit états de données et leurs libellés : intouchés.

---

## 3. Les lots, dans l'ordre des dépendances

Chaque lot : reproducteur d'abord, `run_checks.sh` vert avant push, captures
1280 / 1440 / 1600 comparées à la capture canonique, une PR brouillon.

### V1 — La primitive et sa porte *(fondation, rien de visible)*
- `src/components/Card.tsx` + `.vx-card` et ses trois variantes.
- **Porte neuve** `src/design/one-card-primitive.test.ts` : balayage AST de
  `src/pages/**` refusant toute surface de page (`section`/`article` portant un
  fond ou une bordure) qui n'est pas construite sur la primitive. Exemptions
  nommées une par une, motif écrit — jamais par fichier.
- **Porte neuve** « une seule lumière dominante » : au plus un
  `data-rank="dominant"` par page.
- Aucune page migrée : le lot livre l'outil et la mesure de l'écart.

### V2 — La densité du shell *(le changement le plus visible)*
- Rail 248 → **136 px** (voir §5, décision 1), tête, groupes et cartouche
  resserrés à l'échelle.
- `.vx-main` : `40/32/48` → `16/20/32`.
- Reproducteur : test e2e refusant un rail hors bande 120–140 px et une
  gouttière de travail hors bande 12–20 px, aux trois viewports.
- Gain mesurable : **+128 px** de largeur utile sur les douze pages.

### V3 → V8 — Migration page par page, deux pages par lot

Chaque page : modules sur la primitive, un seul dominant, kicker/titre/pied
normalisés, provenance rapprochée de la donnée.

| Lot | Pages |
|---|---|
| V3 | Aujourd'hui, Marchés |
| V4 | Opportunités, Analyse |
| V5 | Options, Simulateur |
| V6 | Portefeuille, Risques |
| V7 | Catalyseurs, Calendrier |
| V8 | Sources & Rapports *(+ Graphiques si la page existe alors)* |

### V9 — Retrait des 15 listes énumérées
Une fois les douze pages migrées, la couche thématique par noms n'a plus de
raison d'être. Elle est supprimée, et la porte de V1 devient la garantie.
**Ce lot est la preuve que la refonte a tenu** : tant que les listes existent,
la cohérence repose encore sur la discipline.

---

## 4. Déclinaison par page — « le même style, selon la page »

Le style est identique ; ce qui change est **quelle carte est dominante**. Une
page = une question, un dominant, trois à cinq modules, un inspecteur.

| # | Page | Question servie | Carte **dominante** | Modules secondaires | Inspecteur |
|---|---|---|---|---|---|
| 1 | Aujourd'hui | Qu'est-ce qui mérite mon attention maintenant ? | File d'attention | régime, instantané publié, couverture | item sélectionné |
| 2 | Marchés | Dans quel contexte vais-je analyser ? | Carte sectorielle | breadth, table équivalente, écartés | instrument |
| 3 | Opportunités | Quels candidats méritent une analyse ? | Table des candidats | filtres, profil, motifs | candidat |
| 4 | Analyse | Que dit le dossier de cet instrument ? | Chandeliers | indicateurs, presse, attribution | explication IA |
| 5 | Options | Quels contrats sont exploitables ? | Chaîne cotée | échéances, liquidité | contrat |
| 6 | Simulateur | Comment la structure réagit-elle ? | Courbe de payoff | composeur, hypothèses, breakevens | jambe |
| 7 | Portefeuille | Quelles expositions résultent du ledger ? | Concentration | synthèse, performance, journal | ligne |
| 8 | Graphiques | *(page non créée — hors périmètre visuel)* | — | — | — |
| 9 | Risques | Qu'est-ce qui bouge ensemble ? | Matrice de corrélation | périmètre, extrêmes | paire |
| 10 | Catalyseurs | Quels événements modifient la thèse ? | File des catalyseurs | non reliés, file de revue | événement |
| 11 | Calendrier | Quels événements affectent mes instruments ? | Fenêtre calendaire | compteurs, groupes | événement |
| 12 | Sources & Rapports | Puis-je faire confiance aux sources ? | Matrice de santé | filtres, sondes, rapports | source |

Deux invariants transversaux :

- **Un module sans source garde sa géométrie et NOMME son absence** avec
  `AbsentModule` (LOT-A0) — jamais un chiffre de maquette, jamais un rectangle
  gris muet. Un chiffre affiché est un chiffre servi.
- **La provenance suit la donnée** : source, `as_of`, fraîcheur et nature dans
  le pied de la carte qui porte la valeur, pas dans un bandeau lointain.

---

## 5. Décisions qui vous reviennent

Je ne les tranche pas.

1. **Largeur du rail.** Le contrat dit « environ 120 px ». Mesure de la largeur
   intrinsèque des libellés actuels : « Sources & Rapports » exige **192 px**,
   le cartouche `VERTEX 1.0 BETA` **154 px**, la tête **126 px**. À 120 px, ces
   trois éléments sont **tronqués**. Trois voies :
   - **(a)** rail **136 px**, libellés en corps `meta`, cartouche resserré, et
     « Sources & Rapports » abrégé en **« Sources »** dans le rail seulement
     (le titre de page reste entier) — *ma recommandation* ;
   - **(b)** rail 120 px strict, libellés sur deux lignes ;
   - **(c)** rail 168 px, écart au canon assumé et documenté.
2. **Les intitulés de groupes du rail** (`DÉCIDER`, `OBSERVER`, `PILOTER`,
   `ASSISTANCE`). La capture canonique montre une **liste plate**, sans groupes.
   Les retirer est une décision d'architecture d'information, pas de style : je
   ne la prends pas seul.
3. **Ordre des lots.** V2 (densité du shell) est le plus spectaculaire et le
   moins risqué ; V9 est celui qui rend la cohérence irréversible. Si vous
   préférez voir le résultat plus tôt, V2 peut passer avant V1 — au prix de
   devoir repasser sur les pages en V3+.

---

## 6. Vérification, à chaque lot

```bash
cd apps/web
pnpm exec tsc --noEmit && pnpm exec biome check src e2e && pnpm build
pnpm exec vitest run
VERTEX_TEST_DATABASE_URL=… pnpm exec playwright test
cd ../.. && bash tools/run_checks.sh
```

Trois règles non négociables, chacune payée au moins une fois :

1. **Le total d'une campagne se confronte au total DÉCLARÉ** (`--list`) **et à**
   `.last-run.json`. Un « 377 passed » avec exit 0 a déjà masqué 58 échecs.
2. **Le code de sortie d'une commande composée ne dit rien de l'étape qui
   compte.** Un `playwright test; echo; tail` rend le code du `tail`. Vu deux
   fois.
3. **`tools/run_checks.sh` est la dernière porte avant tout push**, sans
   exception.

Et une quatrième, apprise au LOT-A1 : **regarder la capture**. Le placement de
grille du ticker renvoyait les cours sur une seconde rangée, tronqués — 453
tests e2e verts, et c'est l'image qui l'a montré.

---

## 7. Ce que ce plan ne promet pas

- Il ne rapproche **aucune** page de « la planche avec de vraies données » : il
  ne touche ni source, ni contrat, ni intégration. Une carte non branchée reste
  une absence nommée.
- Il ne crée pas la page **Graphiques** : c'est une destination nouvelle, pas
  une refonte.
- Les captures produites montrent la donnée **synthétique** de l'environnement
  de développement. Elles prouvent la composition, **jamais** un contenu réel.
  Le rendu sur les 161 instruments IBKR se valide sur votre poste.
- Aucune fusion dans `main`, aucune publication sans votre validation.
