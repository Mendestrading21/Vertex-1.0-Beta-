# Première installation

## À installer sur l'ordinateur

1. Git for Windows ou Git officiel : https://git-scm.com/downloads
2. Claude Desktop/Claude Code : https://docs.anthropic.com/en/docs/claude-code/setup ; appliquer `CLAUDE_TOOLS.md` avant tout plugin.
3. PostgreSQL 18 (serveur + client, dont `createdb` et `pg_isready`) : https://www.postgresql.org/download/
4. TWS Offline ou IB Gateway : https://www.interactivebrokers.com/docs/tws-api/doc/download-tws-or-ib-gateway/download-tws-or-ib-gateway
5. TradingView Desktop facultatif pour le confort ; les alertes serveur ne dépendent pas de l'application ouverte.
6. Node.js 24 LTS : https://nodejs.org/en/download
7. `uv` : https://docs.astral.sh/uv/getting-started/installation/

La pile locale validée ne dépend pas de Docker : PostgreSQL tourne sur la machine et Vertex reste sur `127.0.0.1`. Docker Desktop est facultatif pour le développement futur. Wrangler reste nécessaire uniquement pour déployer le Worker TradingView. Éviter les installations globales non verrouillées.

## Dépôts GitHub déjà existants

1. Ne créer aucun dépôt : la cible d'écriture est
   `/home/user/Vertex-1.0-Beta-`, remote
   `Mendestrading21/Vertex-1.0-Beta-`.
2. Garder `/home/user/Vertex-`, remote `Mendestrading21/Vertex-`, strictement en
   lecture seule au baseline documenté.
3. Avant toute mutation, vérifier `pwd`, `origin`, branche, HEAD et état Git des
   deux dépôts ; une écriture dans le donneur impose l'arrêt.
4. Planifier puis installer le contenu de ce blueprint dans la cible selon
   `docs/07-delivery/BETA_REPOSITORY_BOOTSTRAP.md`, en préservant son README.
5. Ne pas importer l'historique du donneur ni copier un module sans classement
   `KEEP`, `ADAPT`, `REWRITE`, `REFERENCE` ou `DROP` et preuves associées.

Les protections existantes de la cible doivent être auditées sans les modifier
pendant le prévol. Tout changement de ruleset est une action séparée, humaine et
documentée.

## Vérifications

```text
git --version
node --version          # 24.x LTS
corepack pnpm --version  # pnpm fourni par Corepack
uv --version
psql --version
pg_isready --version
claude --version        # si CLI utilisée
```

## Installer les dépendances verrouillées

Depuis la racine du dépôt cible, ces deux commandes reproduisent les
environnements validés par la CI. Ne pas lancer Vertex avec le Python système.

```bash
uv sync --locked --all-extras --python 3.13
( cd apps/web && corepack pnpm install --frozen-lockfile )
test -x .venv/bin/python
```

Si l'une échoue, ne pas contourner le verrou et ne pas utiliser `pip install`
ou `npm install` à la place : corriger d'abord la version de Python, Node ou
le réseau.

## Premier démarrage de Vertex

Une fois les outils installés, Vertex se lance sans Docker, sans IBKR et sans
aucune source réelle :

```bash
createdb vertex
export VERTEX_DATABASE_URL='postgresql+psycopg://vertex:<mot-de-passe>@127.0.0.1:5432/vertex'
.venv/bin/python tools/bootstrap_local.py --with-demo-data
bash tools/start_local.sh
```

Puis ouvrir `http://127.0.0.1:4173/system` — cette page d'abord. Le détail,
les refus fail-closed et le tableau de dépannage sont dans `START_LOCAL.md`.

Tout ce qui s'affiche alors porte `population = SYNTHETIC`. Brancher TWS et
les droits IBKR réels appartient au LOT-24 et exige la machine cible.

## Démarrage Claude

1. Ouvrir Claude Code à la racine de `/home/user/Vertex-1.0-Beta-` et vérifier
   qu'aucun terminal d'écriture ne pointe vers le donneur.
2. Pour le pilotage téléphone, démarrer Remote Control selon `CLAUDE_REMOTE_CONTROL.md` ; l'exécution reste locale et aucune interface Vertex n'est exposée au téléphone.
3. Activer le mode Plan.
4. Depuis le kit extrait, utiliser le prévol de
   `PROMPT_DE_DEMARRAGE_CLAUDE.md` et lancer `PLAN BOOTSTRAP BETA`.
5. Lire le diff prévu, les fichiers préservés, le rollback et les risques ; ne
   lancer aucun code automatiquement.
6. Après validation humaine seulement, envoyer `EXÉCUTE BOOTSTRAP BETA`, puis
   `AUDITE BOOTSTRAP BETA`.
7. Toujours en mode Plan, transmettre `.claude/prompts/plan-full-journey.md`,
   lire le parcours `DOSSIER 00` à `DOSSIER 25`, puis répondre
   `VALIDE LE PARCOURS — EXÉCUTE DOSSIER 00`.

## Ce qu'il ne faut pas télécharger

- archives ou forks non officiels de TWS API ;
- « bots IBKR » ou scrapers TradingView ;
- dossiers copiés de LEAN, Nautilus, vectorbt ou de l'ancien Vertex ;
- GitHub Actions ou skills non vérifiés et non épinglés ;
- datasets d'options sans licence écrite.
