# Reprendre Vertex — passation du 2026-09-01

Ce document est écrit pour une session qui n'a **aucun** contexte de ce qui
précède. Tout ce qu'il affirme a été **mesuré** sur cette machine, pas supposé.
Ce qui n'a pas été vérifié est signalé comme tel.

---

## 1. Ce qu'est Vertex, et les règles qui ne se négocient pas

**Vertex 1.0 Beta** — terminal d'analyse de marché IBKR, **lecture seule**.
Aucun ordre, aucune exécution, jamais.

### Interdits absolus

- Ne **jamais** désactiver `Read-Only API` dans TWS.
- Ne **jamais** faire écouter un service sur `0.0.0.0`, ni remplacer
  `127.0.0.1` par une adresse de réseau, ni créer de redirection de port.
- Ne **jamais** écrire un secret dans un commit, un Markdown, un journal, une
  capture d'écran ou un message de synthèse.
- Ne **jamais** écrire `OPERATIONAL` pour un composant qui n'a pas été
  réellement testé sur cette machine.
- Ne **jamais** convertir un délai d'attente en `NOT_ENTITLED`, une donnée
  retardée en donnée en direct, une **absence** en zéro, ni une erreur en
  succès.
- Ne désactiver ni assouplir **aucun** test.

### Points d'arrêt — demander avant

Modification Windows/WSL en administrateur · changement de `.wslconfig` ou
redémarrage WSL · tout réglage TWS · toute requête IBKR avant confirmation
Read-Only/Paper · `--persist` · `--allow-delayed-fallback` · sonde d'options
complète · connexion IBKR **Live** · modification de compte · tout secret ·
webhook public · déploiement Cloudflare · fusion dans `main`.

### Dépendances

Pas de `pip install` flottant, pas de `npm install`, pas de suppression de
lockfile, pas de mise à jour automatique, pas de paquet global inutile, aucun
script téléchargé exécuté sans inspection.

---

## 2. Où sont les choses

| Quoi | Où |
|---|---|
| Dépôt | `/home/elio/Vertex-1.0-Beta-` (WSL Ubuntu) — **pas** sur `/mnt/c` (bit d'exécution) |
| Branche | `claude/snapshots-confirmation-20260901` |
| Distant | `github.com/Mendestrading21/Vertex-1.0-Beta-` |
| Configuration | `~/.vertex/env.live` — **contient le mot de passe PostgreSQL, ne jamais l'afficher** |
| Base de travail | `vertex_live` (45 007 observations réelles, 161 instruments, 6 108 dépêches) |
| Python | `.venv/bin/python` depuis la racine |

### Démarrer

```bash
cd ~/Vertex-1.0-Beta- && set -a && . ~/.vertex/env.live && set +a && bash tools/start_local.sh
```

Interface sur `localhost:4173`, API sur `127.0.0.1:8000`. **Aucune passkey
demandée** : `VERTEX_AUTH_OPEN_LOCAL=1` est posé dans `env.live` à la demande
explicite du propriétaire du poste. Retirer cette ligne referme l'accès.

### Vérifier

```bash
cd ~/Vertex-1.0-Beta- && . .venv/bin/activate && set -a && . ~/.vertex/env.live && set +a && bash tools/run_checks.sh --integration; echo "CODE REEL : $?"
```

Le `; echo "CODE REEL : $?"` n'est pas décoratif : un `| tail` avale le code
de retour et fait passer un échec pour un succès. C'est arrivé.

---

## 3. Ce qui vient d'être fait (8 commits)

```text
6cd65d5  RISQUES — la page, de l'API à l'écran (LEDGER 09)
9fe81a7  RELAIS — admettre le dollar des identifiants de presse (72 réponses en 500)
d357e4c  ACCÈS — ouvrir Vertex sans passkey
514ad2a  RISQUES — la route API, vérifiée contre l'instantané RÉEL
eb9ee54  RISQUES — la matrice de corrélation, du worker au périmètre déclaré
427f91f  RISQUES — risk.correlation, mesuré sur 8 indices réels
0c79f78  PRESSE — conserver l'horodatage ambigu au lieu de le jeter
6f918b2  FORCE RELATIVE — le troisième calcul approuvé qui n'avait jamais servi
```

État mesuré : **3 231 tests Python**, **458 frontaux**, ruff et mypy propres.
Le rail porte **11 destinations** sur 12 (Graphiques manque).

Les onze pages s'ouvrent et servent des données réelles. Vérifié navigateur
neuf, sans cookie : `0/11` page demande un code, `0` réponse 401.

---

## 4. Ce qui reste cassé — MESURÉ, avec les emplacements

### 4.1 Huit étiquettes qui mentent sur la nature des données

Le bandeau `population` est **juste** ; c'est le texte autour qui ment.

| Emplacement | Texte | Pourquoi c'est faux |
|---|---|---|
| `apps/web/src/pages/markets/MarketsPage.tsx:99` | « Carte des marchés synthétiques » | `population='REAL'`, 0/161 ticker synthétique |
| `MarketsPage.tsx:119` | « `synthetic-dev` via snapshot worker » | la source est `ibkr` |
| `MarketsPage.tsx:83` | repli « Carte des marchés synthétiques » | faux, latent |
| `MarketsPage.tsx:202` | « Poids = parts descriptives des clôtures (synthétiques) » | faux |
| `MarketsPage.tsx:206` | « Limites : données SYNTHÉTIQUES de développement » | faux |
| `apps/worker/src/vertex_worker/markets.py:362` | « Sur N instruments synthétiques attendus » | faux, **persisté** dans le contenu |
| `apps/worker/src/vertex_worker/portfolio.py:117` et `:825` | `MARK_POPULATION_SYNTHETIC` écrit **inconditionnellement** | les marques viennent de `markets_overview` en `REAL` |
| `apps/worker/src/vertex_worker/performance.py:136` et `:810` | `marks = "SYNTHETIC"` | même cause (`ledger: USER_DECLARED` est juste, lui) |

Nuance : `markets.py:362` est figé dans les instantanés déjà publiés
(append-only), mais `markets_overview` se republie en continu — ce littéral se
corrige de lui-même à la publication suivante.

### 4.2 `data_state='partial'` trompeur sur Marchés

`apps/worker/src/vertex_worker/markets.py:581` déclenche `partial` sur
`rejected_records`, alimenté par 3 cotations `GNL PRE` — des observations **en
trop**, hors univers, **pas** un trou de couverture. L'écran affiche « Données
partielles » puis, juste en dessous, « 161 couverts sur 161, 0 écartés » : un
texte qui se réfute lui-même. Confusion entre `discarded` (attendu manquant) et
`rejected_records` (non demandé). Même pollution sur `performance/1`.

### 4.3 500 latent sur Risques

`"value"` est dans `_DECIMAL_KEYS` (`apps/api/src/vertex_api/snapshot_views.py:890`,
classe **non signée**) alors que `extremes.most_opposed.value` vaut `-0.803` —
une corrélation « la plus opposée » est négative **par définition**.

La route rend 200 aujourd'hui parce que `apps/api/src/vertex_api/risk.py:300`
appelle son propre validateur `checked_risk_content`. Toute uniformisation qui
la brancherait sur le garde commun la mettrait en 500 sur données réelles.

**Correction** : déplacer `"value"` vers `_SIGNED_DECIMAL_KEYS` (`:896`).
**Commit séparé** — `value` sert aussi à `breadth.value` (`:1649`), et
desserrer une classe financière mérite son propre reproducteur.

### 4.4 Trou E2E

`apps/web/e2e/analysis.spec.ts` et `today.spec.ts` sont passés **au vert
pendant que 72 réponses partaient en 500**. Cause : le semis
(`apps/web/e2e/seed_synthetic.py`) ne produit **aucun** identifiant de
fournisseur — tout est frappé par Vertex
(`synthetic-dev:{seed}:{index:04d}`).

Semer au moins un cluster de presse en forme réelle
`ibkr:news:<provider>:<provider>$<hex>`.

### 4.5 Un dossier définitivement refusé

`analysis/GNL PRE` — le caractère fautif est l'**espace**, jamais adressé par
le correctif du `$`. Inatteignable de toute façon : `UNDERLYING_PATTERN`
(`apps/api/src/vertex_api/routes.py:150`) le refuse en **422** avant toute
lecture de base. **Ne pas annoncer « zéro identifiant hors forme ».**

---

## 5. Trois décisions qui appartiennent à l'utilisateur

Aucune ne se déduit du code. Ne pas les trancher seul.

1. **Barème de sévérité** de la page Risques. Le blueprint décrit « la matrice
   des risques avec exposition, horizon, **sévérité** et preuve » ; seule la
   matrice de corrélation est livrée.
2. **Périmètre affiché** de la matrice — 8 indices mondiaux aujourd'hui
   (`apps/worker/src/vertex_worker/profiles.py`, `RISK_PERIMETER`). Comparer
   les 161 titres ferait tomber l'intersection des calendriers, et une grille
   161×161 n'est pas un écran.
3. **Fenêtre et date de base** de la page Graphiques, non installée.

---

## 6. Ce qui n'a pas été vérifié

- `calendar/global` et `option_chain/*` n'ont **aucun** instantané publié :
  leurs relais n'ont jamais été exercés sur données réelles.
- La collecte de chaînes d'options n'existe pas ; l'habilitation aux cotations
  d'options reste **non concluante** (la sonde a tourné marché fermé).
- FX (EUR/CHF) et taux : IBKR ne sert pas de `TRADES`, il faut un contrat
  distinct avec une base déclarée.
- Matières premières : la sonde ne gère pas `CONTFUT` — résultat **non
  concluant**, pas un refus.
- Aucune source pour secteurs, fondamentaux, révisions d'analystes,
  catalyseurs (WSH est payant).
- `ai_explain._INTRA_WORD_SEPARATOR` normalise `- . _ * + ~ / \ | : ; '` mais
  ni `$` ni `@` : `a$c$h$e$t$e$z` échappe à `detect_forbidden_language`.
  Défaut réel, antérieur, à ouvrir séparément.

---

## 7. Pièges de cet environnement, appris à la dure

**Les variables `$var` sont EFFACÉES** quand une commande passe par
`wsl.exe -- bash -lc '...'`. Cela produit des mesures **fausses mais
silencieuses** — un compteur vide lu comme un zéro. **Toujours** écrire les
scripts dans un fichier et les exécuter par chemin.

**Les backticks aussi** sont mangés dans un heredoc passé de cette façon : les
identifiants entre backticks disparaissent des messages de commit.

**Ne jamais deviner un nom de colonne SQL.** Lire `information_schema`. Trois
fois dans la journée une supposition a échoué (`snapshot_heads.snapshot_id`,
`outbox_messages`, `observations.source_id` — le vrai nom est `source`).

**La batterie doit tourner avec le venv activé.** Sans lui, `run_checks.sh`
appelle le python système, qui n'a pas pytest, et la suite ne tourne **pas du
tout** — un vert invalide.

**`ruff format` sur un dossier entier reformate des fichiers sans rapport.**
Vérifier `git status` avant de commiter ; restaurer ce qui n'a pas été voulu.

**Le défaut le plus fréquent de ce dépôt**, rencontré **trois fois** dans la
journée : quelque chose **déclaré** à un endroit et **jamais branché** à un
autre, avec les deux suites de tests au vert parce qu'elles construisent la
charge *attendue* plutôt que la charge *produite*. La parade est un test qui
appelle le producteur et passe sa sortie au validateur —
`apps/api/tests/test_risk_contract_matches_worker.py` en est le modèle.

---

## 8. Discipline attendue

- `.claude/rules/testing.md` exige un **test reproducteur rouge AVANT** toute
  correction. Le respecter : voir le test échouer, puis corriger.
- `.claude/rules/frontend.md` interdit **tout calcul financier en
  TypeScript** — le serveur publie les chaînes déjà rendues, y compris les
  arrondis et les classements.
- Tout calcul financier passe par le registre
  `docs/03-domain/calculations/CALCULATION_REGISTRY.yaml`, avec ses 8 champs
  d'exécution obligatoires, et la porte `tools/check_calculation_registry.py`.
- Les tables `observations` et `snapshots` sont **append-only par déclencheur
  SQL** : `UPDATE` et `DELETE` y sont refusés. Aucune migration de données
  n'est possible dessus — en tenir compte AVANT de proposer une correction qui
  supposerait de réécrire l'existant.
