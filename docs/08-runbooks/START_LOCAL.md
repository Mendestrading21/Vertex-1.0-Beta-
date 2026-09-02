# Démarrage local

Ce runbook est **exécutable**. Chaque commande ci-dessous a été lancée telle
quelle et son résultat est reporté.

Une version antérieure disait « Ce runbook devient exécutable au LOT-24. Avant
cela, ne pas inventer de commandes. » C'était honnête mais coûteux : la pile
complète démarrait déjà 402 fois par jour depuis l'échafaudage Playwright
(`apps/web/e2e/global.setup.ts`) — migrations Alembic réelles, worker réel,
API FastAPI réelle, build de production — sur une base jetable dont le schéma
était détruit à chaque lancement. Le produit se lançait donc **en CI et jamais
pour son utilisateur**. `tools/start_local.sh` est cette séquence, promue hors
des tests, sans base jetable et sans destruction de schéma.

## Prérequis

PostgreSQL 18, Node 24, Corepack et `uv` installés, puis les environnements
verrouillés créés exactement comme indiqué dans `FIRST_INSTALL.md`. Le
démarreur exige `.venv/bin/python` et refuse le Python système. Docker n'est
pas requis pour ce chemin.

## 1. Créer la base, une seule fois

```bash
createdb vertex          # ou: psql -c 'CREATE DATABASE vertex OWNER vertex;'
```

## 2. Déclarer le DSN

Le DSN vient de l'environnement, **jamais d'un fichier du dépôt**. Vertex ne
devine aucune base : sans cette variable, chaque composant refuse de démarrer.

```bash
export VERTEX_DATABASE_URL='postgresql+psycopg://vertex:<mot-de-passe>@127.0.0.1:5432/vertex'
```

## 3. Préparer la base

```bash
.venv/bin/python tools/bootstrap_local.py                    # migrations seules
.venv/bin/python tools/bootstrap_local.py --with-demo-data   # + population SYNTHETIC
```

Sans `--with-demo-data`, les pages seront **vides et le diront** — c'est le
comportement voulu tant qu'aucune source réelle n'est branchée. Avec, une
population de démonstration entièrement SYNTHETIC est semée et publiée, pour
que les 13 pages soient regardables sans IBKR.

Résultat mesuré sur une base neuve, le 2026-09-02, sur `ba749c1` :

```text
migrations: à jour (alembic upgrade head)
population SYNTHETIC semée et publiée: enveloppes=48 quotes=46 chaines=12
barres=4 calendrier=21 portefeuille=1 messages_traites=402
Tout ce qui précède porte population = SYNTHETIC jusqu'à l'écran.
Aucune donnée réelle n'a été observée.
```

Le `messages_traites=490` d'une mesure antérieure n'était pas inventé : il
était juste, sur un autre arbre. Un compteur de messages d'outbox dépend du
nombre de snapshots publiés, qui a changé depuis — 11 familles aujourd'hui.
Les six autres compteurs, eux, sont identiques. Un chiffre mesuré sans son SHA
redevient faux tout seul : d'où le SHA au-dessus.

**Le semis refuse d'écraser un journal.** Si la base contient déjà des
transactions ou des thèses, il s'arrête avec le compte exact des lignes
trouvées et sort en code 2. Le journal est saisi à la main : il est
irremplaçable. `--force` existe, à n'utiliser que sur une base jetable.

## 4. Démarrer

```bash
bash tools/start_local.sh
```

Il vérifie le DSN, les ports, les commandes requises et l'environnement Python
verrouillé, puis enchaîne : PostgreSQL, migrations, API (`uvicorn`,
`127.0.0.1:8000`), worker, build de production et interface (`vite preview`,
`127.0.0.1:4173`). Si un service tombe, les autres sont arrêtés au lieu de
laisser une pile partiellement vivante. `Ctrl-C` arrête les trois processus
proprement.

## 5. Ouvrir `/system` en premier

```text
http://localhost:4173/system     ← cette page d'abord
http://localhost:4173/today
```

**`localhost`, et non `127.0.0.1`.** `apps/api/src/vertex_api/auth/config.py`
fixe l'identifiant de la partie de confiance WebAuthn à `localhost` (ADR-002),
et la spécification exige que cet identifiant soit un suffixe de domaine
enregistrable de l'origine. Une origine en **adresse IP** ne peut donc pas le
porter. L'application, elle, peut rester liée à `127.0.0.1` : c'est l'URL
tapée qui change, pas l'adresse d'écoute.

Ce qui se passe réellement depuis `http://127.0.0.1:4173`, tracé dans le code
(`apps/web/src/pages/AuthPage.tsx`, `apps/api/src/vertex_api/auth/routes.py`) :
`POST /api/v1/auth/register/options` **est appelé et répond** — cette route ne
lit pas l'origine et renvoie `rp.id = "localhost"` ; puis
`navigator.credentials.create` **échoue dans le navigateur**, parce que ce RP ID
ne convient pas à une origine IP ; `POST /api/v1/auth/register/verify` n'est
donc **jamais** envoyé. L'API n'a rien refusé. Un message générique d'échec
apparaît, qui n'en donne pas la cause. Le refus lui-même est une règle du
navigateur : aucune ligne du dépôt ne le prouve ; ce que le dépôt prouve, c'est
l'ordre des appels et que la campagne e2e, seule à créer réellement une
passkey, passe par `localhost`.

`/system` dit ce que le système sait de lui-même : base, migrations, horloge,
sauvegarde, et l'état RÉEL de chaque capacité. Une capacité jamais sondée y
reste `NEVER_TESTED` — ce n'est pas un défaut d'affichage, c'est le refus
d'annoncer une capacité qu'on n'a pas vérifiée.

Le statut sain exige base, migrations, horloge, sauvegarde récente et aucune
source critique périmée.

## Ce que ce démarrage n'expose pas

Les trois services écoutent sur `127.0.0.1` **et rien d'autre**. Vérifié :
depuis l'adresse non-loopback de la machine, les deux ports refusent la
connexion. Aucun `0.0.0.0`, aucun Tailscale Serve, aucune exposition LAN,
aucun accès téléphone — `.claude/rules/security.md` classe l'exposition
applicative `LATER`. Claude Remote Control pilote Claude Code depuis un
téléphone ; il ne publie ni ne transporte l'interface Vertex.

Un test refuse tout `--host` autre que `127.0.0.1` dans le démarreur
(`tools/tests/test_bootstrap_local.py`).

## Ce que ce démarrage ne fait PAS

Il ne contacte ni TWS, ni IBKR, ni TradingView, ni Cloudflare. **Aucune donnée
réelle n'a jamais été observée par ce logiciel.** Sans source connectée, le
worker tourne en configuration synthétique de développement et l'écrit dans
son journal au démarrage ; tout ce qui s'affiche porte
`population = SYNTHETIC`.

Brancher une source réelle exige la machine cible : TWS ou IB Gateway en
lecture seule sur loopback avec un `client_id` non nul (`IBKR_SETUP.md`), et
le projet Cloudflare pour le webhook TradingView (`TRADINGVIEW_SETUP.md`,
blocage B-03).

La première commande à lancer, TWS allumé, est la sonde de droits :

```bash
python3 tools/probe_entitlements.py --symbol <SYMBOLE> --dry-run
```

Elle imprime les droits RÉELS champ par champ en moins d'une minute, au lieu
de les découvrir page par page. La séquence complète est dans
`IBKR_SETUP.md`, section « Sonder les droits RÉELS ». Avec `--persist`, la
page `/system` cesse d'afficher `NEVER_TESTED` pour les capacités
effectivement sondées — et pour elles seules.

## En cas d'échec

| Message | Cause | Geste |
|---|---|---|
| `VERTEX_DATABASE_URL n'est pas défini` | DSN absent — refus délibéré de deviner | exporter la variable de l'étape 2 |
| `PostgreSQL ne répond pas sur 127.0.0.1:5432` | serveur arrêté | le démarrer, puis relancer |
| `la base contient déjà des données utilisateur` | semis demandé sur une base non vierge | ne rien forcer ; utiliser une autre base |
| `ressemble à une base de test` | DSN pointant `vertex_test`/`vertex_e2e` | corriger le DSN, ou `VERTEX_ALLOW_TEST_DB=1` en connaissance de cause |
| message générique d'échec juste après la demande de passkey, alors que `/api/v1/auth/register/options` a répondu | interface ouverte depuis `127.0.0.1` alors que le RP ID est `localhost` : `navigator.credentials.create` échoue et `/api/v1/auth/register/verify` n'est pas envoyé | réouvrir sur `http://localhost:4173` |

`INCIDENT.md` couvre les pannes en cours de service.

## Brancher IBKR en continu

`tools/start_local.sh` ne contacte JAMAIS TWS : il sert la population
`SYNTHETIC`. Pour alimenter les pages avec du marché réel, un second processus
tourne à côté, une fois les droits sondés :

```bash
export VERTEX_IBKR_UNIVERSE="$HOME/.vertex/univers.json"
export VERTEX_IBKR_PORT=<port confirmé dans TWS>
.venv/bin/python tools/run_edge_ibkr.py
```

Séquence complète, univers, bornes et codes fournisseur : `IBKR_SETUP.md`,
section « Ingestion continue ». `/system` cesse alors d'afficher
`NEVER_TESTED` pour les seules capacités réellement observées.
