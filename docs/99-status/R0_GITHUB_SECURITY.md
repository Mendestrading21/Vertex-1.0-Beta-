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
  3 950 tests Python réussis et 4 ignorés ; l'intégration PostgreSQL reste à
  prouver par le job CI dédié ;
- pendant cette validation, PR #18 a été fusionnée par squash à `07:04:21Z` :
  son diff porte deux fichiers (`+329/-240`), son HEAD fusionné est `b8a0d4d6`
  avec une CI #165 verte, et le `main` courant devient `beb24988` ; ce second
  mouvement est ajouté au même périmètre de requalification ;
- aucun rollback, reset, force-push ou autre réécriture n'est entrepris : la
  suite est un audit du nouvel état puis, si nécessaire, des PR correctives.
