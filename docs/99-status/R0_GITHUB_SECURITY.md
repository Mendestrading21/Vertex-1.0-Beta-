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
- [x] La fusion globale de PR #14 est interdite et expliquée.
- [x] Les 23 commits Claude postérieurs au socle déjà absorbé sont inventoriés.
- [x] Aucun commit applicatif n'est repris dans R0.
- [x] Aucune référence n'est supprimée, déplacée ou réécrite.
- [ ] `main` applique le ruleset documenté ; cette action exige les réglages
      GitHub administrateur, non exposés par le connecteur de cette session.
- [ ] La visibilité publique est tranchée humainement avant toute remédiation
      d'historique.

## Validation

```bash
python .claude/skills/vertex-titanium-ledger/scripts/audit_titanium_ledger.py
bash tools/run_checks.sh
```

Le lot reste `PARTIAL / SECURITY HOLD` tant que les deux critères humains ne
sont pas clos.

## Exécution du 1er septembre 2026

- `verify_blueprint.py` : `ok: true`, 27 lots valides ;
- audit Titanium Ledger : empreinte canonique valide, écarts fonctionnels
  inchangés `charts` et `risks` ;
- `tools/run_checks.sh` : `== TOUT VERT ==` avec Python 3.13 du `.venv`,
  pnpm 10.33.0 et variables proxy retirées ;
- test HTTP local qui échouait avec le proxy SOCKS : vert isolément sans proxy ;
- aucune référence Git distante supprimée, déplacée ou réécrite.
