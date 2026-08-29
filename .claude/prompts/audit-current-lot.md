# Prompt — Audit du lot courant

**Commande :** `AUDITE LOT NN`

Travaille en lecture seule. Cet audit n'autorise aucune correction, installation,
réécriture, génération, mise à jour de lockfile, commit, push, PR, merge,
migration ou déploiement.

## Préparation

Lis :

1. `CLAUDE.md` et la constitution ;
2. `docs/99-status/NOW.md`, `HISTORY.md` et `BLOCKERS.md` ;
3. le fichier du lot NN ;
4. les ADR, contrats, spécifications et critères de sortie référencés ;
5. le diff de la branche par rapport à sa base, sans modifier Git.

Relève l'état Git avant l'audit. N'efface, ne stash et ne restaure aucun fichier.
N'exécute un test que s'il est prouvé non mutant pour les fichiers suivis. Sinon,
inspecte ses preuves existantes et marque-le `NON EXÉCUTÉ — audit lecture seule`.

## Axes obligatoires

Audite avec preuves précises :

1. **Périmètre** : objectifs satisfaits, non-objectifs respectés, absence de travail
   anticipé sur un autre lot.
2. **Architecture** : limites de modules, direction des dépendances, ADR et absence
   d'autorité concurrente.
3. **Vérité financière** : calculs Python, `AdviceResult` unique, gates fail-closed,
   unités/temps/précision et calibration.
4. **Données** : provenance, observation, réception, qualité, fraîcheur,
   déduplication et traitement des contradictions.
5. **Intégrations** : aucune capacité IBKR interdite, aucun faux webhook signé,
   aucune donnée réelle dans les fixtures.
6. **Sécurité** : secrets, auth, permissions, validation, anti-rejeu, logs et
   dépendances.
7. **Qualité** : tests, invariants, contrats, migrations, erreurs et observabilité.
8. **Interface**, si concernée : huit états, viewports desktop `1280×800`,
   `1440×900` et `1600×1000`, accessibilité, alternative textuelle et budget de
   performance. `1024×768` est une dégradation laptop optionnelle. Ne réclame pas
   de QA mobile pour Vertex 1.0 Beta ; `Mobile UI = LATER` et les contrats
   sémantiques restent conservés.
9. **Livraison** : documentation, état courant, preuves, rollback et cohérence de
   la PR prévue.

## Sévérité

- `CRITIQUE` : risque de fausse décision, exécution financière, fuite de secret,
  contournement de sécurité ou corruption/perte de données.
- `ÉLEVÉE` : contrat faux, fail-open, résultat non reproductible, test critique
  absent ou fonctionnalité principale inutilisable.
- `MODÉRÉE` : défaut réel mais contournable sans altérer la vérité.
- `FAIBLE` : amélioration locale sans impact sur correction, sécurité ou usage.

Ne gonfle pas la liste avec des préférences stylistiques. Regroupe les symptômes
qui ont une cause unique.

## Rapport attendu

Commence par `VERDICT : PASS | PASS AVEC RÉSERVES | FAIL`.

Pour chaque constat :

```text
ID : AUD-NN-001
SÉVÉRITÉ : CRITIQUE | ÉLEVÉE | MODÉRÉE | FAIBLE
PREUVE : chemin et emplacement précis
CAUSE : cause racine démontrée
IMPACT : conséquence concrète
CRITÈRE : règle, ADR ou acceptation violée
CORRECTION ATTENDUE : résultat, sans écrire le patch
TEST DE NON-RÉGRESSION : preuve à exiger
```

Termine par :

- contrôles vérifiés et non vérifiés ;
- risques résiduels ;
- verdict `PRÊT À CORRIGER`, `PRÊT À PR` ou `BLOQUÉ` ;
- une seule prochaine commande, généralement `CORRIGE LOT NN` ou
  `PRÉPARE PR LOT NN`.

Ne corrige rien et ne commence pas le lot suivant.
