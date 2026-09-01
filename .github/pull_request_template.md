## Lot et objectif

- Lot : `LOT-NN`
- Issue :
- Objectif vérifiable :
- Hors périmètre confirmé :

## Changements

- Modules touchés :
- Contrats/migrations :
- ADR appliqué ou ajouté :
- Captures ou preuves visuelles synthétiques :

## Autorités et sécurité financière

- [ ] Aucune capacité IBKR d’ordre, compte, position, P&L ou exécution n’a été ajoutée, importée, exposée ou autorisée.
- [ ] Aucun calcul financier ou verdict faisant autorité n’a été ajouté en TypeScript, Pine ou IA.
- [ ] Les données requises absentes, partielles, retardées, périmées, futures ou contradictoires échouent fermées.
- [ ] Aucun mock, cache, fallback, snapshot, théorie ou démonstration n’est présenté comme réel/live.
- [ ] Aucun scraping ni contournement de droit, abonnement, pacing ou licence.
- [ ] Source, droit, unité, devise, timezone, provenance et fraîcheur restent traçables.

## Vérifications exécutées

| Commande exacte | Résultat | Durée/preuve |
|---|---|---|
|  |  |  |

- [ ] Lint, formatage et types passent.
- [ ] Tests unitaires, propriétés, contrats et intégration applicables passent.
- [ ] E2E, accessibilité, responsive et performance applicables passent.
- [ ] Migrations montée/rollback et sauvegarde/restauration applicables passent.
- [ ] Scans secrets, SAST, dépendances, licences et capacités interdites passent.
- [ ] L'historique des commits repris a été contrôlé ; aucun payload réel ou
      sensible retiré de l'arbre courant n'est réintroduit.
- [ ] OpenAPI et client généré sont synchronisés.

## Supply-chain

- [ ] Lockfiles à jour sans dépendance flottante ni `latest`.
- [ ] GitHub Actions épinglées à un SHA complet et permissions minimales.
- [ ] Images épinglées par digest lorsque applicable.
- [ ] Licence/provenance/SBOM mises à jour lorsque applicable.
- [ ] Aucun runner de PR n’utilise l’ordinateur TWS.

## Interface

- [ ] États `loading`, `refreshing`, `empty`, `partial`, `delayed`, `stale`, `offline` et `error` couverts.
- [ ] Clavier, focus, zoom 200 %, contraste, lecteur d’écran et mouvement réduit vérifiés lorsque applicable.
- [ ] Beta desktop-only vérifiée à 1280×800, 1440×900 et 1600×1000 ; smoke laptop 1024×768 si UI touchée ; budgets respectés.
- [ ] Chaque graphique essentiel expose unité, timezone, source, fraîcheur et alternative textuelle/tabulaire.

## Risques et exploitation

- Risques résiduels :
- Rollback exact :
- Impact sauvegarde/restauration :
- Observabilité/alertes :

## Revue et sortie

- [ ] `docs/99-status/NOW.md` et la documentation concernée sont à jour.
- [ ] Aucun TODO, skip/xfail, feature flag critique ou fallback caché.
- [ ] Une revue humaine est requise avant squash merge.
- [ ] La branche part du `main` courant ; aucune PR Claude/Codex divergente
      n'est fusionnée ou rebasée globalement.
- [ ] Le lot suivant ne démarrera pas automatiquement.

Verdict proposé : `GO` / `NO-GO`
