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

> **Première session avec un IBKR réel ?** `CE_SOIR.md` enchaîne cette page,
> `FIRST_INSTALL.md` et `IBKR_SETUP.md` en une seule séquence, et nomme
> d'avance ce qui marchera et ce qui ne marchera pas.

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

Ré-exécuté le 2026-09-05 sur `87a4e8b`, base neuve `vertex_soir_probe` :
**les sept compteurs sont identiques**, en 14,4 s. La pile complète est ensuite
montée en 8 s — migrations, API (`{"status":"alive"}`), worker et interface
servie depuis le build de production — et les douze destinations ont été
rendues par la campagne `smoke` (12 vertes, 55,8 s).

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

Il ne contacte ni TWS, ni IBKR, ni TradingView, ni Cloudflare. Sans source
connectée, le worker tourne en configuration synthétique de développement et
l'écrit dans son journal au démarrage ; tout ce qui s'affiche porte
`population = SYNTHETIC`.

Une version antérieure de cette page affirmait ici : « Aucune donnée réelle
n'a jamais été observée par ce logiciel. » **C'est faux depuis le
2026-08-31.** `docs/99-status/NOW.md` (`affichage_reel_mesure`) porte la
mesure : base `vertex_live`, `VERTEX_FUSION_PROFILE=real`, Marchés en
population `REAL` avec une clôture reçue 1/1, Analyse avec 251 barres du
2025-08-29 au 2026-08-28, 0 écartée. La sonde de droits du même jour
(`sonde_ibkr_reelle`) n'a démontré **aucun** droit manquant. Ce que ce
démarreur ne fait pas, c'est **collecter** ; il n'a jamais été vrai qu'il
était impossible de collecter. Rien de tout cela n'existe en intégration
continue : la collecte dépend de TWS, qui tourne sur la machine de
l'utilisateur, et toute population observée en CI reste `SYNTHETIC`.

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

`tools/start_local.sh` ne contacte JAMAIS TWS : il sert ce que la base contient.
Pour alimenter les pages avec du marché réel, un second processus tourne à
côté, une fois les droits sondés.

### Lequel ? Celui dont le schéma atteint un écran

C'est le piège le plus coûteux de ce runbook, et il a longtemps été écrit à
l'envers ici. Chaque page est **fermée par défaut sur le préfixe de schéma** :
elle déclare les familles qu'elle sait lire, et ignore le reste.

| Collecteur | Schéma produit | Lu par |
|---|---|---|
| `tools/run_edge_history.py` | `ibkr.daily-quote/1`, `ibkr.daily-bars/1` | **Marchés** (`vertex_worker.markets`), **Analyse** (`vertex_worker.analysis`) |
| `tools/run_edge_news.py` | `ibkr.news-headline/1` | file d'attention et preuves (`vertex_worker.handlers`) |
| `tools/run_edge_ibkr.py` | `ibkr.quote/1` | **personne, aujourd'hui** |
| `tools/run_edge_discovery.py` | `ibkr.scanner/1` | **personne, aujourd'hui** |

**C'est donc `tools/run_edge_history.py` qui peint l'écran.** Le collecteur
temps réel écrit une cotation instantanée — un carnet haut daté de l'instant,
sans jour de bourse ni clôture de séance. Ce n'est pas une cotation
quotidienne, et `vertex_worker.markets` ne l'admet pas. Le lancer seul remplit
la base sans rien changer à l'affichage. Ce n'est pas un défaut à contourner
par un préfixe plus large : c'est une famille de données qu'aucune page ne
sait encore lire.

### La séquence

```bash
export VERTEX_DATABASE_URL='postgresql+psycopg://vertex:…@127.0.0.1:5432/vertex'
export VERTEX_IBKR_UNIVERSE="$HOME/.vertex/univers.json"
export VERTEX_IBKR_PORT=7497          # le port CONFIRMÉ dans TWS, jamais supposé

# 1. remplir la base — c'est CE processus qui alimente les pages
.venv/bin/python tools/run_edge_history.py

# 2. puis servir, en profil réel, dans le MÊME shell
export VERTEX_FUSION_PROFILE=real
bash tools/start_local.sh
```

`VERTEX_FUSION_PROFILE=real` doit être exporté **avant** le démarreur : celui-ci
ne le pose jamais lui-même, `python -m vertex_worker` hérite simplement de
l'environnement du shell. Le profil réel exige EN PLUS `VERTEX_IBKR_UNIVERSE` :
il ne s'active jamais par omission. Le journal du worker au démarrage dit
lequel des deux a été pris — c'est lui qui fait foi.

L'univers est un fichier JSON **hors du dépôt** (il nomme les instruments
réellement suivis, donc une donnée personnelle). Chaque entrée porte un
`con_id` EXACT — relevé par `--dry-run` de la sonde :

```json
{
  "instruments": [
    {"con_id": 0, "sec_type": "STK", "symbol": "XYZ",
     "exchange": "SMART", "currency": "USD"}
  ]
}
```

`tools/build_universe.py --out <fichier>` l'écrit pour vous.

### Ce que le processus fait, et ne fait pas

- instantanés PÉRIODIQUES BORNÉS, pas un flux de ticks permanent ; chaque cycle
  acquiert une ligne de données, la relâche et annule sa souscription dans un
  `finally` ;
- au plus `VERTEX_IBKR_MAX_LINES` lignes simultanées (défaut **2**) ;
- l'historique avance à environ **6 requêtes par minute** : comptez quelques
  minutes pour 5 à 10 titres, et plusieurs heures au-delà de 500. Pour une
  première soirée, prenez un univers court ;
- il n'appelle ni compte, ni position, ni P&L, ni ordre, ni exécution.

**Ne pas semer `--with-demo-data` sur la base destinée au réel.** Une seule
observation synthétique dans la fenêtre suffit à faire porter `SYNTHETIC` au
snapshot — c'est voulu, et c'est irréversible sans repartir d'une base propre.

Séquence complète, univers, bornes et codes fournisseur : `IBKR_SETUP.md`,
section « Ingestion continue ». `/system` cesse alors d'afficher
`NEVER_TESTED` pour les seules capacités réellement observées.
