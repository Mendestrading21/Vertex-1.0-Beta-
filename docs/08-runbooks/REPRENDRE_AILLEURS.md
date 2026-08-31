# Reprendre Vertex sur une autre machine

Ce runbook répond à une question précise : *je travaille au bureau, je veux
continuer chez moi.* Il complète `FIRST_INSTALL.md`, qui installe une machine
neuve, et `START_LOCAL.md`, qui démarre la pile.

---

## Le piège : ne PAS télécharger le ZIP

GitHub propose « Download ZIP ». **Ne l'utilise pas.**

Un ZIP ne contient pas le dossier `.git`. Sans lui :

- aucun `git push` n'est possible — le travail fait chez toi resterait prisonnier
  de la machine sur laquelle il a été écrit ;
- aucun historique, donc aucun moyen de savoir ce qui a changé ni pourquoi ;
- aucune branche, donc aucune Pull Request.

La commande correcte, une seule fois par machine :

```bash
git clone https://github.com/Mendestrading21/Vertex-1.0-Beta-.git
cd Vertex-1.0-Beta-
git checkout codex/desktop-operational-readiness
```

Ensuite, `git pull` suffit pour récupérer ce qui a été fait ailleurs.

---

## Ce que le dépôt apporte, et ce qu'il n'apporte pas

| | Vient du dépôt ? |
|---|---|
| Tout le code, les tests, les runbooks | **oui** |
| Les gabarits de configuration (`*.exemple.json`, `.env.example`) | **oui** |
| Les versions exactes des dépendances (`uv.lock`, `pnpm-lock.yaml`) | **oui** |
| Ton mot de passe PostgreSQL, ton `~/.vertex/env.live` | **non — et c'est voulu** |
| Ton univers rempli (`univers.json`, `univers-large.json`) | **non** |
| **Les données de marché déjà collectées** | **non** |

Les trois derniers points sont le cœur du sujet. Un dépôt Git porte du **code**,
jamais des secrets ni une base de données. Sur la machine de la maison, tu
repartiras d'une base **vide** : les observations IBKR déjà collectées au bureau
n'y seront pas.

Ce n'est pas une limite de Vertex, c'est une propriété de Git. Déplacer les
données est un sujet distinct, traité par `BACKUP_RESTORE.md`.

---

## Installation sur la machine de la maison

1. **Prérequis** — suivre `FIRST_INSTALL.md` : WSL, PostgreSQL 18, Node 24,
   `uv`, TWS. Rien de tout cela ne vient du dépôt.
2. **Cloner** (voir plus haut), jamais dézipper.
3. **Dépendances verrouillées** :
   ```bash
   uv sync --locked --all-extras --python 3.13
   corepack pnpm -C apps/web install --frozen-lockfile
   ```
4. **Recréer la configuration locale** :
   ```bash
   mkdir -p ~/.vertex && chmod 700 ~/.vertex
   cp docs/08-runbooks/univers.exemple.json ~/.vertex/univers.json
   cp docs/08-runbooks/scans.exemple.json   ~/.vertex/scans.json
   chmod 600 ~/.vertex/*.json
   ```
   Puis écrire `~/.vertex/env.live` à la main, sur le modèle de `.env.example`.
   **Le mot de passe PostgreSQL se tape, il ne se copie pas depuis le dépôt.**
5. **Créer la base et migrer** :
   ```bash
   createdb vertex_live
   .venv/bin/python tools/bootstrap_local.py
   ```
6. **Démarrer** : `bash tools/start_local.sh`

À ce stade la pile tourne, les pages sont vides, et elles le disent
honnêtement — aucune donnée n'a encore été observée sur cette machine.

7. **Collecter** : TWS doit tourner sur CETTE machine, en API lecture seule.
   Découverte puis remplissage, comme au bureau :
   ```bash
   .venv/bin/python tools/run_edge_discovery.py
   .venv/bin/python tools/build_universe.py --out ~/.vertex/univers-large.json --max 500 --merge ~/.vertex/univers.json --force
   .venv/bin/python tools/run_edge_history.py
   ```

---

## La routine pour ne jamais rien perdre

**Avant de quitter une machine :**

```bash
git add -A
git commit -m "<ce qui a été fait, et pourquoi>"
git push
```

**En arrivant sur l'autre :**

```bash
git pull
```

Si `git pull` refuse parce que les deux machines ont divergé, ne force rien :
`git status` dit ce qui diverge, et un `git pull --rebase` recolle l'historique
proprement dans le cas courant.

**Ce qui n'est jamais commité, par construction :** `~/.vertex/` vit hors du
dépôt, et `.gitignore` exclut `.env`, `.venv/` et `node_modules/`. Une porte de
la CI (`tools/check_secrets.py`) refuse la moindre trace de secret dans l'arbre
suivi — elle a vérifié 712 fichiers au dernier passage.

---

## Vérifier que la machine est saine

Une seule commande fait foi, et elle ne ment pas :

```bash
bash tools/run_checks.sh --integration
```

Elle doit se terminer par `== TOUT VERT ==`. Tout autre résultat est un
problème réel, pas un détail d'environnement.
