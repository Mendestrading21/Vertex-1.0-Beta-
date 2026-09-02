# Reprendre ici — état au 2026-09-02

Document de passation. La session suivante le lit **en entier** avant d'agir.

---

## 1. Où en est le dépôt

`main` porte la refonte visuelle Titanium Ledger complète (PR #14 fusionnée,
CI 7/7 verte) plus les adaptateurs de sources officielles (PR #15, #16).

**Branche de travail :** `claude/snapshots-confirmation-20260901`.
**En attente de fusion :** PR #18 (V11–V12, uniquement du CSS).

Preuves mesurées sur cette machine, codes de sortie relus :

| Contrôle | Résultat |
|---|---|
| `python -m pytest -q` | 3 927+ tests, 0 échec |
| `pnpm exec vitest run` | 486 tests, 0 échec |
| `pnpm exec playwright test` | 459 déclarés, 459 passés |
| `bash tools/run_checks.sh` | `== TOUT VERT ==`, code 0 |

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

> **Aucun mot de passe n'est écrit dans ce document.** La porte de détection de
> secrets a refusé la première rédaction, à juste titre : un secret de
> développement écrit dans Git reste un secret dans Git. La chaîne de connexion
> vit dans le `.env` local, ignoré par Git ; `.env.example` n'en porte que des
> valeurs fictives.

```bash
# 1. Base de données — premier démarrage ou après un redémarrage du conteneur
service postgresql start
python tools/bootstrap_local.py     # migrations Alembic réelles + semis du worker

# 2. Contrôles complets — la dernière porte avant tout push
bash tools/run_checks.sh            # attendu : == TOUT VERT ==, code 0

# 3. Interface
cd apps/web
pnpm exec vitest run                # 486 tests
# `VERTEX_TEST_DATABASE_URL` vient de l'environnement, jamais d'une commande
# copiée dans un document. La campagne écrit ses captures pleine page des douze
# destinations dans `e2e-artifacts/*-desktop-1600x1000.png`.
pnpm exec playwright test           # 459 tests
```

`tools/bootstrap_local.py` est la voie officielle : il ne réimplémente rien, il
appelle les mêmes migrations et le même semis que la campagne E2E, dont le
propriétaire unique est `vertex_worker.demo_seed`.

Les captures pleine page des douze destinations sont écrites dans
`apps/web/e2e-artifacts/*-desktop-1600x1000.png` à chaque campagne.

---

## MISE EN DIRECT 2026-09-02 — ce qui tourne, et ce qui a été mesuré

### Quatre collecteurs, quatre identifiants clients

| Collecteur | Client | Univers | Rythme |
|---|---|---|---|
| `tools/run_edge_history.py` (barres quotidiennes) | 72 | `univers-large.json`, 161 | **~1 instrument/min**, pacing IBKR — compter ~2 h sur 161 |
| `tools/run_edge_news.py` (dépêches) | 79 | idem | tous les fournisseurs habilités |
| `tools/run_edge_discovery.py` (scanner) | 73 | `scans.json`, 4 scans | quelques secondes |
| `tools/run_edge_ibkr.py` (temps réel, DÉMON) | 71 | **`univers-temps-reel.json`, 8 indices** | continu |

Les quatre tournent **ensemble** ; un identifiant partagé les déconnecterait
l'un l'autre.

### Deux réglages ajoutés à `~/.vertex/env.live`

- **`VERTEX_IBKR_PORT=7496`** — 7496 = Live, 7497 = Paper. Mesuré : 7496
  ouvert, 7497 fermé. Le défaut des collecteurs est 7497 : sans cette ligne,
  aucun ne se connecte. C'est un point d'arrêt de la spécification, levé
  explicitement par l'utilisateur. Vertex ne passe **aucun** ordre.
- **`VERTEX_AUTH_OPEN_LOCAL=1`** — voir plus haut.

### L'univers temps réel : 8 indices, aucun choisi par le code

Le collecteur temps réel borne son budget à **24 instruments**, volontairement
(« le budget de messages IBKR est volontairement borné »). L'univers large en
a 161 : refus. `univers-temps-reel.json` est la **réunion** de `indices.json`
et `indices-monde.json`, deux fichiers écrits par l'utilisateur — aucun titre
n'a été choisi par le code. Élargir ce périmètre est une décision
d'utilisateur.

### Habilitation temps réel, MESURÉE

| Indice | Temps réel |
|---|---|
| SPX, RUT, VIX, SMI, DAX | **oui** |
| NDX, ESTX50, N225 | **non** — `Error 354` / `10168`, différé disponible |

Le collecteur ne bascule **pas** sur le différé de lui-même :
`--allow-delayed-fallback` est un point d'arrêt. Ces trois indices restent
donc alimentés par les barres quotidiennes, pas par le flux.

### Deux défauts trouvés PAR la collecte, pas par les tests

1. **`time_unzoned` en `datetime` naïf faisait planter toute la collecte de
   dépêches** (`CanonicalizationError`, zéro dépêche depuis la modification
   de la veille). Corrigé en chaîne ISO — commit `732f7e5`. Le canonicaliseur
   n'a pas été assoupli : c'est le champ qui violait sa règle.
2. **L'API redemandait un code.** Le processus avait été relancé à 08:25 par
   une autre session **sans** `VERTEX_AUTH_OPEN_LOCAL` dans son environnement.
   Le code était intact. **Règle : toujours `set -a && . ~/.vertex/env.live
   && set +a` avant de lancer quoi que ce soit.** `tools/start_local.sh` ne
   le fait pas à votre place.

### Après un pull, TOUT relancer

Un pull de 28 commits a laissé tourner une API, un worker et un build web
d'avant le pull. Les pages tombaient à 450 caractères (squelette). Après un
pull : `vite build`, puis relancer worker, API et interface.
