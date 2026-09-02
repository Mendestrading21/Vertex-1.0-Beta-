# Reprendre ici — état au 2026-09-02

Document de passation. La session suivante le lit **en entier** avant d'agir.

---

## 1. Où en est le dépôt

**Base R2 actuelle : `main@ecc50c1`** (squash humain de la PR #20, après
#17). `main` porte la refonte visuelle Titanium Ledger (PR #14 et #18) et les
adaptateurs de sources officielles (PR #15, #16).

**Branche de travail :** `lot/r2-pr19-demarrage-20260902`, base `main@ecc50c1`,
PR #21 en brouillon. Son SHA initial audité avant la présente correction est
`6d05603` ; la tête courante est celle que porte la PR, jamais un SHA écrit ici.

Preuves **datées** — mesurées le 2026-09-02 sur la branche d'origine (#19,
`e8ff5e6`/`ba749c1`), codes de sortie relus. Elles ne décrivent pas `main` :

| Contrôle | Résultat |
|---|---|
| `bash tools/run_checks.sh` | `== TOUT VERT ==`, code 0 |
| suite Python | 3 953 passés, 4 sautés sur 3 957 collectés, 0 échec |
| `mypy --strict` | 143 fichiers, 0 erreur |
| `pnpm exec vitest run` | 486 tests, 0 échec — **non rejoué ici**, aucun fichier web modifié depuis |
| `pnpm exec playwright test` | 459 déclarés, 459 passés — **non rejoué ici**, même raison |

Le « 3 927+ » qui figurait ici était une approximation avec un `+` : une
approximation n'est pas une mesure. Le chiffre ci-dessus est recoupé par deux
méthodes indépendantes (voir `docs/99-status/NOW.md`).

---

## 2. Ce qui a changé visuellement, et pourquoi

Le thème n'était **pas un système** : `global.css` déclarait 443 classes
`.vx-*`, dont **89 seulement** étaient atteintes par la couche thématique, à
travers **15 listes de sélecteurs énumérées à la main**. Un module ajouté à une
page n'héritait de rien. « Le même style partout » n'était pas seulement
absent — il était **impossible à garantir**, et aucune porte ne le détectait.

Preuve la plus nette : la largeur du rail était déclarée **trois fois**
(232 px en base, 248 px dans la couche thématique, 232 px en dégradation
laptop). Passer la base à 136 px ne changeait **rien** à l'écran.

Douze lots ont suivi. Ce qui existe maintenant :

- **`src/components/Card.tsx`** — la primitive unique, trois rangs
  (`dominant`, `default`, `quiet`). Une page choisit un RANG, jamais une
  apparence.
- **`src/design/one-dominant-per-page.test.ts`** — porte statique : au plus une
  carte dominante par fichier de page.
- **`shell-canonical.spec.ts`, test « une seule lumière dominante par écran »** —
  porte e2e : compte ce qui est RÉELLEMENT rendu sur les onze destinations.
- **`src/charts/theme.ts`** — le socle commun des quatre moteurs de graphique.
- Densité canonique : rail 248 → 136 px, gouttières dans la bande 12–16 px,
  tables et agendas bornés dans leur cadre.

Hauteurs de page mesurées à 1600×1000, avant → après :

| Page | avant | après |
|---|---:|---:|
| Calendrier | 6 928 | 1 577 |
| Opportunités | 5 425 | 2 031 |
| Analyse | 4 280 | 2 925 |
| Catalyseurs | 3 146 | 2 370 |
| Aujourd'hui | 2 096 | 1 696 |
| **Portefeuille** | 5 030 | **4 912** |

---

## 3. Cinq défauts réels trouvés par les CAPTURES, pas par les tests

Aucun des 486 tests unitaires ni des 459 e2e ne les voyait.

1. **La carte des marchés débordait son cadre.** Les tuiles du bas étaient
   coupées par `overflow: hidden`. Sur un treemap où la surface EST la donnée,
   un instrument disparaissait sans le dire. Cause : `width/height: '100%'` sur
   la série ECharts, remplacés par un ancrage aux quatre bords.
2. **Deux quadrillages superposés** sur chaque canevas — une grille CSS de
   36 px par-dessus celle du moteur, à un pas différent, qui ne s'alignaient
   jamais.
3. **Les poids de concentration s'affichaient sur 28 décimales**, la chaîne
   d'options sur 16 : colonnes désalignées, comparaison impossible.
4. **`#vx-inspector-slot` n'était atteignable au clavier que par ACCIDENT**,
   parce que le panneau monté contient 22 liens de citation. Entre l'instant où
   le nœud devient défilant et celui où ces liens existent, la région était
   inatteignable — violation axe « serious » sur un seuil déclaré à zéro.
5. **Une surcharge annulait un lot entier** : un bloc « signature de page »
   redonnait le rayon 18 px à quatre pages, après son unification à 10 px.

**Règle qui en découle : regarder la capture.** Elle voit ce que les tests ne
peuvent pas voir.

---

## 4. Quatre pièges de méthode, payés dans cette session

1. **Un « 377 passed » avec code de sortie 0 masquait 58 échecs.** Un total de
   campagne ne vaut que confronté au total DÉCLARÉ (`playwright test --list`)
   **et** à `e2e-artifacts/test-output/.last-run.json`.
2. **Le code de sortie d'une commande composée ne dit rien de l'étape qui
   compte.** `playwright test > log; echo; tail` rend le code du `tail`. Vu
   **trois fois**. Lancer la commande seule, ou capturer et relire son code.
3. **`tools/run_checks.sh` est la dernière porte avant tout push, sans
   exception.** Il a attrapé deux fois ce qu'aucune autre mesure ne voyait :
   une citation morte dans `manifests/traceability.yaml`, et un
   `noExportsInTest`.
4. **Une sonde doit attendre un témoin de CONTENU, jamais `main` visible.**
   Sinon elle mesure le squelette de chargement (`.vx-dsb-skeleton`). Cette
   erreur m'a fait annoncer « dix pages sur onze sans dominante » alors que la
   règle fonctionnait.

---

## 5. Décisions qui reviennent à l'utilisateur — NE PAS TRANCHER SEUL

1. **Portefeuille fait 4 912 px** et ce n'est **pas** un problème de style : la
   page porte **douze modules** depuis l'absorption de Performance (LOT-08), là
   où le contrat canonique en veut « trois à cinq ». Découper ou non est une
   décision d'architecture d'information.
2. **Largeur du rail.** Le contrat dit « environ 120 px ». Mesure des largeurs
   intrinsèques : « Sources & Rapports » exige 192 px, le cartouche 154 px, la
   tête 126 px. À 120 px stricts, les trois sont **tronqués**. Retenu : 136 px,
   sans rien couper. À revoir si les libellés du rail sont raccourcis.
3. **Les intitulés de groupes du rail** (`DÉCIDER`, `OBSERVER`, `PILOTER`,
   `ASSISTANCE`). La capture canonique montre une **liste plate**. Les retirer
   est une décision d'architecture d'information.
4. **Chaîne d'options — contrat de tranche.** Le collecteur exige `style`,
   `settlement`, `rate` et `dividend_yield`. FRED (PR #15) couvre le taux ;
   **dividende, `style` et `settlement` restent à trancher.**

---

## 6. Ce qui reste à faire

### Visuel
- **V13** : la dernière grosse énumération — 14 sélecteurs pour le matériau
  titane des surfaces. C'est la plus délicate : elle touche toutes les surfaces
  à la fois.
- Migration JSX des surfaces héritées vers la primitive `Card`.
- **Graphiques** : la 12ᵉ destination n'existe pas. `market.rebased_series` est
  publié côté serveur depuis `0c59afa`, donc la comparaison base 100 n'est plus
  bloquée.

### Branchements (« les connexions », explicitement remis à plus tard par
l'utilisateur)
- Inspecteur contextuel sur les 9 destinations qui ne le remplissent pas.
- Comparaison base 100 sur Portefeuille et Graphiques.
- Sessions de marché, largeur de marché, matrice de corrélation étendue.
- **Fondamentaux via SEC EDGAR** — PR #15/#16 sont fusionnées : revenus, BPA et
  actions en circulation viennent d'une source **publique et gratuite**. Ce
  n'est plus « abonnement requis » mais un contrat de calcul à écrire.

---

## 7. Ce qui n'a JAMAIS été vu sur données réelles

Le conteneur de développement **n'a pas de base `vertex_live`** (mesuré :
`count = 0`). Toutes les captures de cette session portent de la donnée
**synthétique** : elles prouvent la COMPOSITION, jamais le contenu.

Le rendu sur les 161 instruments IBKR se valide **sur le poste de
l'utilisateur**, et nulle part ailleurs.

---

## 8. Démarrer et regarder le logiciel

**L'autorité unique du démarrage est `docs/08-runbooks/START_LOCAL.md`.** Ce
paragraphe ne la duplique pas : une version antérieure l'avait fait, en plus
court et en faux — elle invoquait le Python système que `tools/start_local.sh`
refuse, ne déclarait aucun DSN (donc sortait en code 2), ne nommait jamais le
lanceur, et attribuait la chaîne de connexion à un fichier `.env` qui n'existe
pas et qu'aucun code Python de ce dépôt ne lit. Un second chemin d'autorité,
exactement ce que `.claude/rules/architecture.md` interdit.

Trois lignes suffisent :

```bash
export VERTEX_DATABASE_URL='postgresql+psycopg://vertex:<mot-de-passe>@127.0.0.1:5432/vertex'
bash tools/start_local.sh          # migrations, API, worker, build, interface
# puis ouvrir http://localhost:4173/system
```

`<mot-de-passe>` reste un placeholder. **Aucune valeur n'entre dans Git** —
`.claude/rules/security.md`. Le DSN vit dans l'environnement du shell, pas dans
un fichier du dépôt ; `.env.example` en montre la forme, avec `CHANGE_ME`.

`localhost` et non `127.0.0.1` : le RP ID WebAuthn est `localhost`
(`apps/api/src/vertex_api/auth/config.py`). Depuis une adresse IP,
`/api/v1/auth/register/options` est appelé et répond, puis
`navigator.credentials.create` échoue dans le navigateur ; aucun
`POST /api/v1/auth/register/verify` n'est alors envoyé. L'application peut
rester liée à `127.0.0.1`. Le détail est dans `START_LOCAL.md` §5.

Le reste — prérequis, création de la base, semis SYNTHETIC, tableau de
dépannage, ingestion IBKR continue — est dans `START_LOCAL.md` et
`FIRST_INSTALL.md`.

### Preuves relues sur cette machine le 2026-09-02, sur `ba749c1`

| Étape | Attendu | Mesuré |
|---|---|---|
| `bootstrap_local.py` sur base vide | code 0 | code 0, `migrations: à jour` |
| relance | code 0 (idempotent) | code 0 |
| `--with-demo-data` | code 0, `SYNTHETIC` | code 0, 11 familles de snapshots |
| relance du semis | refus code 2 | code 2, `ledger_transactions (5 ligne(s))` |
| sans `VERTEX_DATABASE_URL` | refus code 2 | code 2 |
| `pytest tools/tests/test_bootstrap_local.py` | aucun test sauté | 9 passés, 0 sauté |

### Contrôles complets

```bash
bash tools/run_checks.sh            # dernière porte avant tout push
cd apps/web && pnpm exec vitest run
pnpm exec playwright test           # écrit e2e-artifacts/*-desktop-1600x1000.png
```

Les captures pleine page des douze destinations sont écrites dans
`apps/web/e2e-artifacts/*-desktop-1600x1000.png` à chaque campagne.
