# Configuration IBKR

## Compte technique

Utiliser si possible un nom d'utilisateur secondaire dédié à TWS API. Les abonnements de données peuvent être propres à l'utilisateur ; vérifier leur disponibilité réelle avec celui qui lance TWS.

## Réglages

- commencer en paper ;
- activer socket clients ;
- activer Read-Only API ;
- limiter à localhost ;
- client ID Vertex `71`, non nul et non Master ;
- TWS Offline recommandé pour maîtriser les mises à jour ;
- auto-restart autorisé, réauthentification hebdomadaire acceptée ;
- synchronisation horaire OS activée.

## Droits à vérifier séparément

- quotes actions/ETF/indices ;
- données options et Greeks ;
- historique ;
- news API par fournisseur ;
- Wall Street Horizon Corporate Event Data ;
- delayed market data en secours clairement étiqueté.

La disponibilité dans l'interface TWS n'implique pas toujours le même droit API. Ne pas déduire un droit d'un écran TWS : le sonder.

## Sonder les droits RÉELS

`tools/probe_entitlements.py` lance la sonde décrite par
`docs/04-integrations/IBKR_ENTITLEMENT_PROBE.md` : six étapes bornées, une
seule sonde active, deux lignes de données au maximum, annulation dans un
`finally`. Elle n'appelle ni compte, ni positions, ni P&L, ni ordres, ni
exécutions.

### 1. Résolution — aucune ligne de données ouverte

```bash
python3 tools/probe_entitlements.py --symbol <SYMBOLE> --dry-run
```

Elle se connecte, qualifie le sous-jacent et imprime les définitions de chaîne
réellement renvoyées : exchanges, `trading_class`, multiplicateurs, échéances
et strikes. **Aucun symbole n'est proposé par défaut** : l'identité vient
entièrement de la ligne de commande, et toute ambiguïté (plusieurs contrats
qualifiés) arrête la sonde au lieu d'en choisir un.

### 2. Sonde

```bash
python3 tools/probe_entitlements.py --symbol <SYMBOLE> \
    --option-expiry <AAAAMMJJ> --option-strike <STRIKE> --option-right C \
    --option-trading-class <CLASSE> --option-exchange <BOURSE>
```

Les cinq arguments d'option sont obligatoires et vérifiés contre la chaîne
renvoyée à l'étape 1 : une échéance, un strike ou un couple
`exchange`/`trading_class` que la chaîne n'a pas annoncé est refusé.

La sortie est une matrice, un statut par champ, avec sa raison, son tick, son
type de marché et le code fournisseur éventuel. `ERROR` et timeout ne
signifient **jamais** `NOT_ENTITLED`.

Options utiles :

- `--allow-delayed-fallback` : re-demander en delayed si le live est REFUSÉ.
  Le résultat reste étiqueté `DELAYED`, jamais requalifié live.
- `--persist` : écrire l'observation de capacité en base (exige
  `VERTEX_DATABASE_URL`) pour que `/system` montre le RÉEL au lieu de
  `NEVER_TESTED`. Sans cette option, rien n'est écrit.
- `--tws-port` / `--client-id` : port et `client_id` API. Il n'existe
  **aucune** option d'hôte : l'adaptateur refuse tout hôte autre que
  `127.0.0.1`, et ne pas offrir le réglage est plus fort que le valider.

## Test d'acceptation

- connexion sur loopback ;
- heure serveur ;
- résolution du sous-jacent choisi, sans ambiguïté résiduelle ;
- chaîne avec expirations et `trading_class` distinctes, jamais fusionnées ;
- quote live ou delayed explicitement identifiée ;
- scanner ;
- fournisseurs news ;
- WSH ou statut `NOT_ENTITLED` ;
- aucun appel interdit dans trace/log/code.


## Reprise périodique

`tools/run_edge_history.py` fait UNE passe sur l'univers, puis sort. C'est le
bon défaut pour un premier remplissage, et le mauvais pour une session : Vertex
n'a aucun ordonnanceur, donc plus rien ne remet de travail en file une fois la
passe finie, et les pages restent figées.

`VERTEX_IBKR_REPEAT_SECONDS` enchaîne les passes :

```bash
export VERTEX_IBKR_REPEAT_SECONDS=900   # nouvelle passe 15 min après la fin
```

- **opt-in** : sans la variable, le comportement d'origine est exactement
  conservé ;
- **plancher 300 s**, refusé en dessous — jamais corrigé en silence. IBKR
  n'accorde que 60 requêtes par fenêtre glissante de dix minutes : une passe de
  K instruments ne peut pas durer moins de K/6 minutes, et repartir plus vite
  ne produit que des reconnexions ;
- `Ctrl-C` (ou SIGTERM) arrête proprement : la requête en cours se termine et
  aucune passe supplémentaire n'est lancée, y compris si le signal arrive
  PENDANT l'attente ;
- une passe qui échoue REMONTE l'erreur au lieu d'être avalée pour « continuer
  quand même » : un transport perdu doit être lu, pas masqué ;
- les compteurs du journal final sont CUMULÉS sur toutes les passes, et la
  ligne le dit.

Ce n'est pas un ordonnanceur, ni un service, ni une dépendance : c'est un
paramètre du même outil, qui refait la même passe.

## Ingestion continue (après la sonde)

La sonde répond « quels droits ai-je », une fois. Elle ne remplit pas les pages.
C'est `tools/run_edge_ibkr.py` qui le fait, en boucle :

```bash
export VERTEX_DATABASE_URL='postgresql+psycopg://vertex:…@127.0.0.1:5432/vertex'
export VERTEX_IBKR_UNIVERSE="$HOME/.vertex/univers.json"
export VERTEX_IBKR_PORT=7497          # le port CONFIRMÉ dans TWS, jamais supposé
.venv/bin/python tools/run_edge_ibkr.py
```

L'univers est un fichier JSON **hors du dépôt** (il nomme les instruments
réellement suivis, donc une donnée personnelle). Chaque entrée porte un
`con_id` EXACT — relevé par `--dry-run` de la sonde :

```json
{
  "instruments": [
    {"con_id": 265598, "sec_type": "STK", "symbol": "XYZ",
     "exchange": "SMART", "currency": "USD"}
  ]
}
```

Ce que le processus fait, et ce qu'il ne fait pas :

- instantanés PÉRIODIQUES BORNÉS, pas un flux de ticks permanent. Chaque cycle
  acquiert une ligne de données, la relâche, et annule sa souscription dans un
  `finally` ;
- au plus `VERTEX_IBKR_MAX_LINES` lignes simultanées (défaut **2**). Ce n'est
  PAS une mesure du droit réel du compte : Vertex ne le connaît pas et ne
  l'invente pas. L'élever exige de MESURER l'allocation réelle ;
- budget de messages volontaire (38/s), files bornées, refus EXPLICITE et
  compté quand une file est pleine — jamais un abandon silencieux ;
- `1101` (données perdues) incrémente l'epoch et force un réabonnement complet ;
  `1102` attend une observation du nouvel epoch avant de se dire sain ; `1300`
  (port socket changé) **arrête** l'ingestion au lieu de reconnecter à l'aveugle ;
- une observation estampillée d'un epoch antérieur n'est JAMAIS persistée ;
- `SIGTERM`/`SIGINT` terminent le cycle en cours puis rendent la main.

L'écriture passe par `ingest_envelope`, exactement comme le reste de Vertex :
l'observation est insérée (idempotente sur `event_id`) et le travail de fusion
mis en file ; c'est le worker existant qui publie les instantanés. Il n'y a
donc AUCUN second chemin de publication.

Variables : `VERTEX_IBKR_PORT` (7497), `VERTEX_IBKR_CLIENT_ID` (71),
`VERTEX_IBKR_MAX_LINES` (2), `VERTEX_IBKR_POLL_SECONDS` (60),
`VERTEX_IBKR_UNIVERSE` (obligatoire). Il n'existe **aucune** variable d'hôte :
`127.0.0.1` est en dur.

## Les trois régimes de collecte

Une seule commande ne peut pas couvrir à la fois la largeur, la profondeur et
la fraîcheur : IBKR impose trois contraintes de nature différente. Vertex a
donc trois processus, et il faut savoir lequel répond à quelle question.

| Régime | Commande | Question | Limite réelle |
|---|---|---|---|
| Découverte | `tools/run_edge_discovery.py` | « quoi regarder ? » | 50 lignes/scan, 1 scan/s |
| Profondeur | `tools/run_edge_history.py` | « quel historique ? » | **60 requêtes / 10 min** |
| Temps réel | `tools/run_edge_ibkr.py` | « quel prix maintenant ? » | **une ligne de données par instrument** |

Chacun utilise un `client_id` DISTINCT — **71**, **72**, **73**. Deux clients
API portant le même identifiant se déconnectent mutuellement ; les faire
tourner ensemble exige donc trois identifiants.

### Découverte — la largeur

```bash
export VERTEX_IBKR_SCANS="$HOME/.vertex/scans.json"
.venv/bin/python tools/run_edge_discovery.py
```

Le classement est calculé chez IBKR sur tout le marché ; seules les lignes
retenues reviennent. **Un classement est un DÉCLENCHEUR, jamais un verdict** :
ni prix canonique, ni décision. La revalidation appartient aux deux autres
régimes — même frontière que pour les alertes TradingView (ADR-005).

Format (`scans.json`) :

```json
{"scans": [
  {"instrument": "STK", "location_code": "STK.US.MAJOR",
   "scan_code": "TOP_PERC_GAIN", "number_of_rows": 50}
]}
```

### Profondeur — les milliers

```bash
export VERTEX_IBKR_UNIVERSE="$HOME/.vertex/univers-large.json"
.venv/bin/python tools/run_edge_history.py
```

`reqHistoricalData` ne consomme **aucune ligne de données**, mais obéit à un
pacing propre : 60 requêtes par fenêtre glissante de 10 minutes, soit
**6 par minute** en régime soutenu. Ordres de grandeur mesurés :

| Instruments | Durée d'une passe |
|---|---|
| 500 | ~1 h 25 |
| 1 000 | ~2 h 50 |
| 5 000 | ~14 h |

C'est un travail de nuit, et c'est la vitesse réelle du fournisseur : rien ici
ne prétend l'accélérer. Quand la fenêtre est pleine, le processus **attend** —
un dépassement produit un refus IBKR, pas de la vitesse.

Le plafond d'univers y est de **5000** instruments, contre **24** pour le temps
réel. Ce ne sont pas deux réglages du même curseur : le temps réel est borné
par les lignes de données, l'historique par le temps.

Le remplissage est **reprenable** : `ingest_envelope` est idempotent sur
`event_id`, donc relancer une passe interrompue ne duplique rien.

### Temps réel — les dizaines

Voir « Ingestion continue » ci-dessus. C'est le seul régime qui consomme des
lignes de données, et c'est pourquoi il reste petit.

### Ce qui ne se fait PAS

Des milliers d'instruments en temps réel simultané. Le plafond de lignes
d'IBKR (~100 par défaut) l'interdit — chez tout le monde, pas seulement ici.
Un scanner désigne quoi regarder, l'historique donne la profondeur, et le
temps réel n'est dépensé que là où il compte.

## Faire APPARAÎTRE les données réelles à l'écran

Ingérer n'est pas afficher. Les six registres de fusion du worker sont
**deny-by-default** : une observation dont la `source` ou les `rights` ne sont
pas déclarés est refusée avant toute publication. C'est la garantie « rien de
non vérifié n'atteint l'écran ».

Le profil par défaut n'autorise que le synthétique. Pour ouvrir la porte au
réel, deux variables — et rien ne s'ouvre par omission :

```bash
export VERTEX_FUSION_PROFILE=real
export VERTEX_IBKR_UNIVERSE="$HOME/.vertex/univers.json"
python -m vertex_worker
```

Au démarrage, le worker DIT lequel des deux profils tourne. Sans
`VERTEX_IBKR_UNIVERSE`, le profil réel refuse de démarrer : il n'analyse que
des instruments explicitement déclarés.

### Ce que le profil réel déclare, et ce qu'il refuse

| | |
|---|---|
| Source autorisée | `ibkr` uniquement |
| Droits utilisables | `IBKR_MARKET_DATA_DISPLAY_ONLY` uniquement |
| Instruments | ceux de `univers.json` — ce qu'on collecte est ce qu'on analyse |
| Niveau de confiance IBKR | **non promu** (`DEFAULT_SOURCE_TIER`) |
| Secteur | un seul, `IBKR_NON_CLASSE` |

Deux choix méritent d'être expliqués plutôt que subis :

- **Le profil réel REFUSE le synthétique**, et réciproquement. Accepter les
  deux ferait mentir l'étiquette `population` : une seule observation
  synthétique dans la fenêtre suffit à faire avouer `SYNTHETIC` au snapshot.
- **Aucun secteur n'est inventé.** Vertex n'a aujourd'hui aucune source de
  classification sectorielle pour des instruments réels. Répartir des `con_id`
  dans des secteurs plausibles serait une fabrication ; ils vivent donc tous
  dans un secteur unique dont le libellé le dit.

### Sur l'étiquette `population`

Elle n'est pas une description de ce qui est affiché : c'est un **aveu sur la
fenêtre d'entrée**. Un semis synthétique résiduel en base fera donc avouer
`SYNTHETIC` au snapshot même si de vraies données s'affichent — c'est
volontaire, et c'est un signal utile : la base n'est pas propre.

### Comment la page Analyse est alimentée

La page **Analyse** ne lit pas une clôture : elle calcule des tendances et
exige donc l'**OHLC complet plus le volume**. C'est la MÊME barre quotidienne
qui l'alimente, dérivée une seconde fois par `daily_bars_envelope`, sous le
schéma `ibkr.daily-bars/1`.

Un seul enregistrement porte tout l'historique d'un instrument. Ce n'est pas
un détail : le consommateur retient « le dernier enregistrement utilisable »
et lit son tableau `bars` entier. Émettre une observation par barre ferait
gagner la plus récente SEULE, et la page n'afficherait qu'un seul jour.

| Refus | Pourquoi |
|---|---|
| `bar_size` ≠ `1 day` | une bougie de 60 minutes n'est pas une séance |
| `what_to_show` ≠ `TRADES` | `MIDPOINT` n'est pas un cours de transaction |
| `symbol` ou `currency` absent | l'enregistrement entier serait rejeté plus loin, sans cause visible |
| barre partielle (OHLC incomplet) | écartée et **comptée** — l'OHLC est un tout, jamais réparable |
| volume fractionnaire | écartée et comptée, **jamais arrondie** |

**La barre BRUTE n'est délibérément pas admise.** Le schéma `ibkr.bars/`
couvre toutes les tailles de barre ; l'accepter tel quel laisserait une bougie
horaire se faire passer pour une séance. Seule la forme dérivée, dont le nom
dit qu'elle est quotidienne, franchit la porte.

**Pourquoi cette page était vide.** Mesuré le 2026-08-31 : 251 barres réelles
en base, zéro lue. `DAILY_BARS_SCHEMA_PREFIXES` ne déclarait que la famille
synthétique. Rien n'échouait, rien n'était journalisé — la donnée était
simplement ignorée. Une page vide sans message est le pire des échecs : elle
ressemble à « pas de données » alors qu'elle signifie « données ignorées ».

**Fraîcheur.** L'enregistrement est daté par sa barre la plus récente, jamais
par l'instant de la requête. Un lundi, la dernière séance est celle de
vendredi : la page l'avoue (`fresh=false`, âge publié) au lieu de paraître à
jour. Élargir la fenêtre empêche la donnée de DISPARAÎTRE ; elle ne la rend
pas fraîche.

### Un ticker, pas un `con_id`

Toutes les pages comparent un **ticker** porté par la charge utile
(`payload['ticker']`, `payload['underlying']`) à leur univers déclaré — jamais
`instrument_id`. Le `con_id` reste l'identité technique : il dédoublonne
l'univers et voyage dans `instrument_id`, sans jamais atteindre l'écran ni les
URL. `symbol` est donc **obligatoire** dans `univers.json` pour le profil réel.

### Comment la page Marchés est alimentée

La page **Marchés** lit une cotation quotidienne portant `ticker`, `sector`,
`trading_day`, `close`, `currency` et `adjustment_basis`. Une cotation temps
réel IBKR porte `con_id`, `bid`, `ask`, `last` : **ce ne sont pas les mêmes
objets**. Un carnet haut instantané n'est pas un cours de clôture quotidien,
et les faire passer l'un pour l'autre serait une falsification sémantique.

C'est donc la **barre quotidienne** qui alimente cette page — elle a bien un
jour de bourse et une clôture. `tools/run_edge_history.py` produit les deux :
la barre brute ET la cotation dérivée, dans la MÊME transaction.

`apps/edge-ibkr/src/vertex_edge_ibkr/normalize.py` porte la transformation, et
refuse explicitement quatre cas :

| Refus | Pourquoi |
|---|---|
| `bar_size` ≠ `1 day` | une barre horaire n'a pas de clôture de séance |
| `what_to_show` ≠ `TRADES` | `MIDPOINT`/`BID_ASK` sont des prix de carnet, pas des transactions |
| clôture absente, nulle ou négative | barre écartée et **comptée**, jamais changée en zéro |
| `symbol` absent | l'instrument est refusé, en nommant son `con_id` |

Deux champs sont déclarés explicitement plutôt que devinés :

- **secteur** : `NON_CLASSE`. IBKR ne fournit aucune classification sectorielle
  et Vertex n'en invente pas. Le libellé le dit à l'écran.
- **base d'ajustement** : `ibkr-trades-unadjusted`. Une barre `TRADES` d'IBKR
  n'est PAS ajustée des dividendes ni des splits. Écrire `adjusted` serait faux.

**Identité et affichage sont deux champs distincts.** Le `con_id` reste
l'identité (apparié sur `instrument_id` par l'analyse, les options et le
calendrier) ; le `symbol` est ce que la page Marchés affiche et compare à son
univers. `symbol` est donc **obligatoire** dans `univers.json` pour le profil
réel.

**Relancer un remplissage ne duplique rien** : l'identité de la cotation
dérivée est `ibkr:daily-quote:<con_id>:<jour>`, stable d'une exécution à
l'autre, et `ingest_envelope` est idempotent dessus.
