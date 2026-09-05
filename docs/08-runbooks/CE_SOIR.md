# Ce soir — brancher Vertex sur votre IBKR, en direct

Une page, dans l'ordre où vous taperez. Elle ne remplace pas
`FIRST_INSTALL.md`, `START_LOCAL.md` et `IBKR_SETUP.md` : elle les enchaîne
pour une première session réelle, et nomme d'avance les pièges qui coûtent une
soirée.

**Ce document ne contient aucun secret, aucun mot de passe et aucun identifiant
de compte, et il ne doit jamais en contenir.**

---

## 0. Avant de commencer, deux choses à savoir

**La chaîne réelle a déjà fonctionné.** `docs/99-status/NOW.md`
(`affichage_reel_mesure`) porte la mesure du 2026-08-31 : base `vertex_live`,
`VERTEX_FUSION_PROFILE=real`, Marchés en population `REAL`, Analyse à 251
barres, 0 écartée. La sonde du même jour n'a démontré **aucun droit manquant**.
Vous ne défrichez pas ; vous rejouez une séquence déjà prouvée.

**Une soirée d'installation, pas de découverte.** L'ingestion historique avance
à environ **6 requêtes par minute**. Un univers de 5 à 10 titres se remplit en
quelques minutes ; 500 titres demandent près d'une heure et demie. Pour ce
soir : **prenez court**.

---

## 1. Environnements verrouillés (si ce n'est pas déjà fait)

```bash
uv sync --locked --all-extras --python 3.13
( cd apps/web && corepack pnpm install --frozen-lockfile )
test -x .venv/bin/python
```

Ne pas contourner un verrou, ne pas remplacer par `pip install` ou
`npm install`. Le démarreur refuse le Python système.

## 2. Une base dédiée au réel

```bash
createdb vertex
export VERTEX_DATABASE_URL='postgresql+psycopg://vertex:<mot-de-passe>@127.0.0.1:5432/vertex'
.venv/bin/python tools/bootstrap_local.py        # migrations SEULES
```

La forme `postgresql+psycopg://` est **obligatoire** : il n'y a pas de
`psycopg2` dans le verrou, et `postgresql://` fait échouer l'API et le worker
au démarrage.

> **Ne pas ajouter `--with-demo-data` sur cette base.** Une seule observation
> synthétique dans la fenêtre suffit à faire porter `SYNTHETIC` au snapshot —
> c'est voulu, et cela ne se défait pas sans repartir d'une base propre. Si
> vous voulez aussi une base de démonstration, faites-en une **seconde**.

## 3. TWS

- commencer en **paper** ;
- **Read-Only API** activé ;
- socket clients activé, **limité à localhost** ;
- client ID **71** (non nul, non Master) ;
- synchronisation horaire OS activée.

Le port est celui que **TWS affiche** — 7497 en paper, 7496 en live selon la
configuration. Ne jamais le supposer. Il n'existe aucune variable d'hôte :
l'adaptateur fixe `127.0.0.1` en dur et refuse tout le reste.

## 4. Sonder les droits RÉELS, et relever les `con_id`

```bash
.venv/bin/python tools/probe_entitlements.py --symbol AAPL --dry-run
```

Aucun symbole n'est proposé par défaut, et toute ambiguïté arrête la sonde au
lieu d'en choisir un. La sortie imprime `con_id`, `symbol`, `exchange`,
`currency` — les quatre champs dont l'univers a besoin — puis les définitions
de chaîne réellement renvoyées.

Répétez pour chaque titre que vous voulez suivre ce soir. Puis, une fois, avec
`--persist` :

```bash
.venv/bin/python tools/probe_entitlements.py --symbol AAPL \
    --option-expiry <AAAAMMJJ> --option-strike <STRIKE> --option-right C \
    --option-trading-class <CLASSE> --option-exchange <BOURSE> --persist
```

`--persist` écrit l'observation de capacité en base : `/system` cesse alors
d'afficher `NEVER_TESTED` pour les capacités effectivement sondées — et pour
elles seules. `ERROR` et timeout ne signifient **jamais** `NOT_ENTITLED`.

## 5. Écrire l'univers, hors du dépôt

Le fichier nomme les instruments que vous suivez réellement : c'est une donnée
personnelle, il vit hors de Git.

```bash
mkdir -p "$HOME/.vertex"
cat > "$HOME/.vertex/univers.json" <<'JSON'
{
  "instruments": [
    {"con_id": 0, "sec_type": "STK", "symbol": "XYZ",
     "exchange": "SMART", "currency": "USD"}
  ]
}
JSON
```

Remplacez chaque entrée par les valeurs EXACTES relevées à l'étape 4. Le
`symbol` est obligatoire, le `con_id` doit être exact.

`tools/build_universe.py` existe, mais il construit l'univers **depuis des
scanners déjà collectés** — donc pas ce soir. Pour une première session, le
fichier s'écrit à la main.

Bornes : **24 instruments** au maximum pour le temps réel, 5000 pour
l'historique.

## 6. Remplir la base — c'est CE processus qui peint l'écran

```bash
export VERTEX_IBKR_UNIVERSE="$HOME/.vertex/univers.json"
export VERTEX_IBKR_PORT=<le port CONFIRMÉ dans TWS>
export VERTEX_IBKR_CLIENT_ID=71          # facultatif, 71 par défaut

.venv/bin/python tools/run_edge_history.py
```

**C'est le piège principal de Vertex aujourd'hui, alors il est dit deux fois.**
Chaque page est fermée par défaut sur le préfixe de schéma : elle déclare les
familles qu'elle sait lire et ignore le reste.

| Collecteur | Schéma produit | Lu par |
|---|---|---|
| `tools/run_edge_history.py` | `ibkr.daily-quote/1`, `ibkr.daily-bars/1` | **Marchés**, **Analyse** |
| `tools/run_edge_news.py` | `ibkr.news-headline/1` | file d'attention, preuves |
| `tools/run_edge_ibkr.py` | `ibkr.quote/1` | **personne, aujourd'hui** |
| `tools/run_edge_discovery.py` | `ibkr.scanner/1` | **personne, aujourd'hui** |

Le collecteur temps réel écrit une cotation instantanée — un carnet haut daté
de l'instant, sans jour de bourse ni clôture de séance. Ce n'est pas une
cotation quotidienne. Le lancer seul remplit la base **sans rien changer à
l'affichage**.

## 7. Servir, en profil réel

Dans le **même shell**, une fois l'historique passé :

```bash
export VERTEX_FUSION_PROFILE=real
bash tools/start_local.sh
```

`VERTEX_FUSION_PROFILE` doit être exporté **avant** le démarreur : celui-ci ne
le pose jamais lui-même, `python -m vertex_worker` hérite simplement de
l'environnement. Le profil réel exige EN PLUS `VERTEX_IBKR_UNIVERSE` ; il ne
s'active jamais par omission.

**C'est le journal du worker au démarrage qui fait foi**, pas la bannière : il
écrit « profil de fusion RÉEL actif » ou « configuration DÉVELOPPEMENT
SYNTHETIC active ». Le profil réel refuse le synthétique, et réciproquement.

## 8. Ouvrir — `localhost`, jamais `127.0.0.1`

```text
http://localhost:4173/system     ← cette page d'abord
http://localhost:4173/today
```

L'identifiant WebAuthn de la partie de confiance est `localhost` (ADR-002), et
la spécification exige qu'il soit un suffixe de domaine enregistrable de
l'origine. Depuis une adresse IP : `/api/v1/auth/register/options` répond, puis
`navigator.credentials.create` échoue **dans le navigateur**, et
`/api/v1/auth/register/verify` n'est jamais envoyé. Le message affiché n'en
donne pas la cause. L'adresse d'écoute, elle, reste `127.0.0.1`.

**Si la passkey vous bloque quand même**, et seulement en local :

```bash
export VERTEX_AUTH_OPEN_LOCAL=1
```

Seule la valeur exacte `1` l'active. La session porte alors le sujet
`acces-local-ouvert` et l'étiquette `LOCAL_OPEN` : elle est reconnaissable dans
un journal. C'est un contournement de dépannage, fermé par défaut — le retirer
une fois la passkey créée.

---

## Ce qui marchera ce soir

Sur données IBKR réelles, déjà mesuré : **Marchés**, **Analyse**,
**Aujourd'hui**, **Opportunités**.

Sans IBKR, sur votre saisie : **Portefeuille** (journal manuel, transactions,
import CSV avec prévisualisation, valorisation, concentration, performance
TWR/XIRR), **Catalyseurs** (création et révision de thèse, réellement
persistées), **Simulateur** (payoff, points morts, grille de scénarios calculés
serveur).

## Ce qui ne marchera pas, et pourquoi

| Quoi | Pourquoi |
|---|---|
| **Options** vide sur données réelles | aucun collecteur de chaîne **cotée** n'existe ; l'adaptateur ne produit que la *définition* de chaîne |
| **Calendrier** vide sur données réelles | `vertex_worker.calendar` n'admet que `synthetic-calendar-event/` ; les événements WSH sont un abonnement distinct |
| **Risques** presque vide | 12 modules sur 19 sont déclarés absents : VaR, CVaR, volatilité, stress, facteurs, budget de risque, alertes. La matrice de corrélation et le drawdown sont servis, et exigent au moins 2 indices dans l'univers collecté |
| **Marchés** partiel | aucun indice, taux, devise ni VIX n'existe dans le dépôt : ces sources ne sont pas encore branchées |
| **Aucune IA** | blocage B-05 : `/api/v1/ai/status` répond `DISABLED`. L'inspecteur produit une explication déterministe, traçable, sans modèle |
| **Aucune alerte TradingView** | blocage B-03 : l'ingress Cloudflare n'est pas déployé |
| Le **Simulateur** ne sauvegarde rien | capacité déclarée `NON_IMPLÉMENTÉ` |
| **Rien ne se rafraîchit tout seul** | il n'existe aucun ordonnanceur. Un instantané reste figé tant qu'une ingestion ne remet pas de travail en file : relancez `run_edge_history.py` pour rafraîchir |

Une page qui n'a pas sa donnée le **dit** — elle ne fabrique ni zéro, ni
moyenne, ni valeur d'exemple. Un module vide n'est pas une panne d'affichage.

## Si quelque chose refuse

| Message | Cause | Geste |
|---|---|---|
| `VERTEX_DATABASE_URL n'est pas défini` | refus délibéré de deviner une base | exporter la variable de l'étape 2 |
| `VERTEX_IBKR_UNIVERSE absent` | l'ingestion n'abonne aucun instrument par défaut | étape 5 |
| `VERTEX_FUSION_PROFILE=real exige VERTEX_IBKR_UNIVERSE` | le réel ne s'active jamais par omission | exporter les deux |
| `ressemble à une base de test` | DSN pointant `vertex_test` / `vertex_e2e` | corriger le DSN |
| `la base contient déjà des données utilisateur` | semis demandé sur une base non vierge | ne rien forcer ; utiliser une autre base |
| message générique juste après la demande de passkey | interface ouverte depuis `127.0.0.1` | réouvrir sur `http://localhost:4173` |
| une capacité reste `NEVER_TESTED` sur `/system` | elle n'a pas été sondée | étape 4 avec `--persist` |

`INCIDENT.md` couvre les pannes en cours de service.

## Ce que ce démarrage n'expose jamais

Les trois services écoutent sur `127.0.0.1` **et rien d'autre** : aucun
`0.0.0.0`, aucune exposition LAN, aucun accès téléphone. Et Vertex n'envoie, ne
prépare et ne prévisualise **aucun ordre** : il ne lit ni compte, ni solde, ni
position, ni P&L, ni exécution. TWS reste en lecture seule.
