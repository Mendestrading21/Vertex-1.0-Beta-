# R0 — sécurité GitHub et récupération contrôlée

## Objectif

Empêcher qu'une branche divergente ou une donnée sensible historique entre dans
`main`, puis préparer la récupération sélective du travail Claude sans fusion
globale, force-push ni réécriture d'historique.

## Périmètre

- relever le SHA de `main`, les branches, PR et protections GitHub ;
- conserver une référence immuable du dernier HEAD Claude inspecté ;
- définir le ruleset obligatoire de `main` ;
- documenter la quarantaine et l'éventuelle remédiation d'historique ;
- classer chaque commit Claude `KEEP`, `ADAPT`, `REWRITE` ou `DROP` ;
- ouvrir une PR brouillon contenant uniquement gouvernance et documentation.

## Hors périmètre

- rendre le dépôt privé sans décision humaine explicite ;
- réécrire une référence, supprimer une branche ou forcer un push ;
- fusionner PR #9 ou PR #14 ;
- reproduire dans un document, log ou test une valeur de marché réelle ;
- reprendre du code applicatif Claude dans ce lot.

## Références

- `CLAUDE.md` ;
- `docs/00-foundation/CONSTITUTION.md` ;
- `SECURITY.md` ;
- `docs/08-runbooks/GITHUB_PROTECTION.md` ;
- `docs/08-runbooks/GIT_HISTORY_QUARANTINE.md` ;
- `docs/99-status/CLAUDE_RECOVERY_PLAN.md`.

## Critères binaires

- [x] Le SHA de `main` et le HEAD Claude sont consignés sans contenu sensible.
- [x] L'interdiction de fusion globale de PR #14 a été documentée avant son
      intégration externe à R0.
- [x] Les 23 commits Claude postérieurs au socle déjà absorbé sont inventoriés.
- [x] Aucun commit applicatif n'est repris dans R0.
- [x] Aucune référence n'est supprimée, déplacée ou réécrite.
- [x] `main` applique le ruleset `main-required` (`22076309`), actif et vérifié
      côté serveur le 2 septembre 2026.
- [x] La visibilité publique est tranchée humainement : le dépôt reste public.
      Le risque résiduel de contenu historique accessible est accepté ; aucune
      remédiation d'historique n'est autorisée dans R0.
- [ ] Les squashes de PR #14 (`505d4654`) et PR #18 (`beb24988`) présents dans
      `main` sont entièrement requalifiés contre le socle `a5b7d205` et la
      matrice de récupération.

## Validation

```bash
python .claude/skills/vertex-titanium-ledger/scripts/audit_titanium_ledger.py
bash tools/run_checks.sh
```

Le volet de protection GitHub est `PASS`. Le lot global reste
`PARTIAL / RECOVERY HOLD` tant que les squashes Claude déjà entrés dans `main`
ne sont pas requalifiés. Le maintien public et ces fusions ne valent jamais
autorisation de réécrire l'historique.

## Exécution du 1er septembre 2026

- `verify_blueprint.py` : `ok: true`, 27 lots valides ;
- audit Titanium Ledger : empreinte canonique valide, écarts fonctionnels
  inchangés `charts` et `risks` ;
- `tools/run_checks.sh` : `== TOUT VERT ==` avec Python 3.13 du `.venv`,
  pnpm 10.33.0 et variables proxy retirées ;
- test HTTP local qui échouait avec le proxy SOCKS : vert isolément sans proxy ;
- aucune référence Git distante supprimée, déplacée ou réécrite.
- décision humaine : le dépôt reste public, avec risque historique résiduel
  accepté et sans réécriture destructive.

## Événement et vérification du 2 septembre 2026

- ruleset `main-required` (`22076309`) actif sur la branche par défaut, sans
  acteur de contournement ;
- `main` annonce `protected: true` ; suppression, force-push et historique non
  linéaire sont bloqués ;
- pull request, résolution des conversations, branche à jour et sept checks
  exacts sont obligatoires ; seule la fusion squash est autorisée ;
- merge commit, rebase merge et auto-merge sont désactivés ;
- PR #14 a été fusionnée par squash hors de R0 à `05:55:06Z`, après le gel
  documentaire : `main` est passé de `a5b7d205` à `505d4654` ;
- le HEAD source `ef47b11a` avait une CI #159 verte, mais cette preuve ne
  remplace pas la requalification architecturale des 123 fichiers intégrés ;
- sur l'arbre réconcilié : `verify_blueprint.py` valide 27 lots, l'audit
  Titanium Ledger confirme l'empreinte canonique et ne conserve que l'écart
  cible `charts`, puis `tools/run_checks.sh` atteint `== TOUT VERT ==` avec
  3 950 tests Python réussis et 4 ignorés ; l'intégration PostgreSQL a depuis
  été prouvée par le job CI dédié (run `33601777661`, voir R1) ;
- pendant cette validation, PR #18 a été fusionnée par squash à `07:04:21Z` :
  son diff porte deux fichiers (`+329/-240`), son HEAD fusionné est `b8a0d4d6`
  avec une CI #165 verte, et le `main` courant devient `beb24988` ; ce second
  mouvement est ajouté au même périmètre de requalification ;
- aucun rollback, reset, force-push ou autre réécriture n'est entrepris : la
  suite est un audit du nouvel état puis, si nécessaire, des PR correctives.

## Actualisation R1 — 2 septembre 2026

Tout ce qui suit a été relevé par `gh` et `git` le 2 septembre 2026. Aucun
fichier applicatif n'est modifié par R1.

### SHA réellement audité

- `main` = `beb249881015147de11e270f8e0e48d843716e6e`, inchangé depuis le gel
  de l'audit Codex ; `origin/main` relu identique au SHA audité ;
- `lot/r0-github-security` part de ce SHA (merge-base = `beb24988`), 0 commit
  de retard, 10 commits de documentation en avance avant R1.

### CI standard — état exact

- workflow `ci`, run `33601777661` sur `main@beb24988` : **succès**, les sept
  checks requis inclus (dont `python — intégration PostgreSQL 18 (sérielle)`) ;
- workflow `ci` sur le HEAD de PR #17 `5f25dab` : **succès** (deux runs).

### Nightly — état exact et rouge

- workflow `nightly`, run `33605890223` sur `main@beb24988` (`schedule`,
  2026-09-02 07:53 UTC) : **échec** ;
- job `e2e — Firefox et WebKit (LOT-23)` : échec ; job `licences relues à leur
  source (strict)` : succès ;
- bilan Playwright : **753 réussis, 2 échoués, 2 ignorés** ; les deux échecs
  sont sur le seul projet `firefox-1440x900` :
  - `apps/web/e2e/options.spec.ts:187` — « inspecteur : identité complète,
    THÉORIQUE et CalculationRecord, Échap referme » ;
  - `apps/web/e2e/today.spec.ts:94` — « le panneau n'est PLUS modal et ne
    piège plus le clavier » ;
- **même assertion dans les deux** : `expect(sorti).toBe(true)` — après 20
  (Options) ou 12 (Aujourd'hui) tabulations, le focus n'est jamais sorti de
  l'inspecteur sous Firefox. Chromium et WebKit passent. Les nightly des
  1er et 31 août sur `main` étaient verts ;
- la nightly n'est **pas** l'un des sept checks requis du ruleset : elle ne
  bloque pas une fusion. C'est une dette de qualité à traiter, pas un blocage
  de gouvernance ;
- R1 ne corrige pas ce défaut : il touche du code applicatif, hors périmètre.

### PR #19 — existence et dépendances

- `#19` « DÉMARRAGE — l'URL des runbooks empêchait la création de passkey »,
  brouillon, branche `claude/vertex-connection-kgkntr` @ `e8ff5e6` → `main` ;
- cinq fichiers : `docs/08-runbooks/FIRST_INSTALL.md`,
  `docs/08-runbooks/REPRENDRE_ICI.md`, `docs/08-runbooks/START_LOCAL.md`,
  `docs/99-status/NOW.md`, `tools/tests/test_bootstrap_local.py` ;
- **dépend de PR #17** : elle touche `NOW.md` et `REPRENDRE_ICI.md`, que R1
  actualise. PR #19 ne doit être reprise qu'après la fusion humaine de #17,
  puis rebasée par une nouvelle PR bornée — jamais rebasée sur place.

### Commits Claude postérieurs à PR #18

La branche `claude/snapshots-confirmation-20260901` a reçu deux commits après
le squash de PR #18 (`b8a0d4d`). Son HEAD relevé est `f9af140`, 50 commits en
avance sur `main`, 1 en retard. Elle n'est **jamais** absorbée en bloc.

| Commit | Contenu | Décision R1 | Motif |
|---|---|---|---|
| `732f7e5` PRESSE — `time_unzoned` en chaîne ISO | 4 fichiers `apps/edge-ibkr/` (+51/−4) : `port.py`, `adapter.py`, `news.py`, `tests/test_news.py` | **ADAPT** | intention utile et mesurée : le champ `datetime` naïf de `0c79f78` faisait échouer le hachage canonique de toute enveloppe de presse (`CanonicalizationError`), donc zéro dépêche collectée. Le passage en chaîne ISO respecte la règle du canonicaliseur sans l'assouplir. À reprendre depuis `main` courant, dans la vague R2-C, avec un test de bout en bout (collecte → hachage → ingestion), pas seulement le test unitaire ajouté. |
| `f9af140` PASSATION — mise en direct | 1 fichier `docs/08-runbooks/REPRENDRE_ICI.md` (+62) | **REWRITE / DROP** | passation d'une session locale : ports, univers temps réel, habilitation mesurée sur le poste de l'utilisateur. Contient des faits utiles (port TWS, budget de 24 instruments du collecteur temps réel, habilitation NDX/ESTX50/N225 en différé seulement) mais ne doit pas être fusionné tel quel : il décrit un état local, non reproductible en CI, et double `NOW.md`. À réécrire depuis les preuves, comme R2-I. |

### Les 28 lots du rattrapage, consolidés

| Famille | Lots | Objet |
|---|---|---|
| R | R1, R2, R3, R4 | gouvernance GitHub et récupération contrôlée du travail Claude |
| S | S1, S2, S3, S4, S5 | sécurité, vérité financière et intégrations |
| V | V0, V1, V2, V3 | fondations visuelles canoniques |
| P | P01 … P12 | reconstruction des 12 pages |
| Q | Q1, Q2, Q3 | accessibilité, performances, architecture, sauvegarde, restauration et qualification live |

Règles de passage : toutes les sous-étapes d'un lot peuvent être accomplies
d'un trait ; **le lot suivant ne démarre pas sans contrôle Codex**. Les
libellés fins des lots S, V et Q sont fixés par Codex ; R1 n'en invente aucun.

Ce programme de 28 lots est distinct des « 27 lots valides » de
`verify_blueprint.py`, qui comptent le blueprint produit, pas le rattrapage.

### Blocages humains

1. visibilité du dépôt : **tranchée** — reste public, risque historique
   résiduel accepté, aucune réécriture d'historique (voir ci-dessus) ;
2. requalification des squashes `505d4654` (PR #14) et `beb24988` (PR #18)
   contre le socle `a5b7d205` : **ouverte**, c'est l'objet de R2 ;
3. R2-H accès local (`d357e4c`) : **HOLD**, décision de sécurité séparée ;
4. décisions produit qu'aucun code ne déduit : barème de sévérité de la page
   Risques, périmètre affiché de la matrice de corrélation, fenêtre et date de
   base de la page Graphiques ;
5. chaîne d'options : `style`, `settlement` et `dividend_yield` restent à
   trancher (FRED couvre le taux).

### Règle : aucun merge automatique

Le ruleset `main-required` (`22076309`) désactive l'auto-merge, le merge
commit et le rebase merge ; seul le squash est autorisé, après PR, branche à
jour, conversations résolues et sept checks verts. **Aucune PR — #9, #17, #19
ni aucune PR de lot — n'est fusionnée par Claude ou Codex.** La fusion est un
geste humain, pris après la revue indépendante de Codex. Le lot suivant ne
démarre pas avant.
