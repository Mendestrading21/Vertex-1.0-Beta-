---
name: vertex-titanium-ledger
description: Auditer intégralement Vertex 1.0 Beta et concevoir, développer ou valider son identité Titanium Ledger Black Glass à partir de la capture canonique. Utiliser dès que la demande concerne Vertex et contient « analyse », « audite », « vérifie tout », « améliore le thème », une page, le dashboard, le shell, les widgets, graphiques, icônes, données, calculs, intégrations, sécurité, performance, accessibilité, tests, CI ou GitHub.
---

# Vertex 1.0 Beta — skill maître d'audit et d'identité

## Mission

Protéger simultanément deux vérités :

1. la vérité produit — aucune donnée, formule, source ou capacité inventée ;
2. la vérité visuelle — toutes les pages sont des descendantes directes de la
   capture canonique Black Glass choisie par l'utilisateur.

Le résultat attendu est un cockpit décisionnel dense, calme, traçable et
cohérent. Le design ne doit jamais masquer un état dégradé ni créer une seconde
autorité financière.

## Déclencheur « analyse »

Dans un contexte Vertex :

- `analyse`, `analyse tout`, `audite Vertex` ou `vérifie tout` déclenche un audit
  complet en lecture seule ;
- `analyse <page|lot|domaine>` déclenche le même protocole, borné au périmètre ;
- `corrige`, `implémente`, `exécute` ou `développe` est nécessaire pour modifier
  le produit ;
- une demande d'audit, de rapport ou d'avis n'autorise jamais une correction,
  un commit, un push, une PR, une publication ou une migration.

Pendant un audit, distinguer toujours : fait confirmé, écart confirmé,
inférence à vérifier et information indisponible.

## Ordre des autorités

Lire avant toute action :

1. `CLAUDE.md` ;
2. `docs/00-foundation/CONSTITUTION.md` ;
3. `docs/99-status/NOW.md` ;
4. le lot actif et ses ADR ;
5. `references/canonical-visual.md` et
   `assets/vertex-dashboard-canonical.png` ;
6. le code, les contrats, les tests, les mesures et les données présents ;
7. les autres références de ce skill utiles à la demande.

La capture canonique est l'unique autorité de style. Les planches des douze
pages illustrent leurs compositions ; elles n'ont pas autorité sur le shell,
la palette, le logo, la typographie ou les données. Le code courant décrit
l'existant, pas automatiquement la cible.

## Modes et références

Charger uniquement ce qui est nécessaire :

| Mode | Références |
|---|---|
| audit complet | `references/full-audit.md`, `references/data-truth.md`, puis les autres selon les écarts |
| identité / shell | `references/canonical-visual.md`, `references/visual-identity.md` |
| page | `references/pages.md`, `references/component-system.md`, `references/charts.md` |
| données / calculs | `references/data-truth.md` |
| exécution / QA | `references/workflow.md` |
| recherche fraîche | `references/research-sources.md` |

## Frontières absolues

- Vertex analyse ; il n'envoie, ne prépare et ne prévisualise aucun ordre.
- Le portefeuille Vertex est manuel. Ne jamais lire cash, NAV, positions, P&L,
  ordres, exécutions ou transactions du compte IBKR.
- TradingView peut déclencher une réévaluation ; IBKR peut fournir des données
  de marché autorisées. Aucun scraping ni contournement d'entitlement.
- Python reste l'unique autorité des calculs, portes, scores et verdicts.
- Le navigateur ne recalcule ni prix, grecque, IV, rendement, drawdown, risque,
  probabilité, classement, breakeven, payoff ou recommandation canonique.
- Réel, retardé, historique, manuel, estimé, simulé, théorique, démonstration et
  indisponible restent typés et visuellement distincts.
- Une absence n'est jamais transformée en zéro, exemple ou succès.
- Aucun secret, identifiant broker, payload sensible ou donnée personnelle dans
  Git, les logs, captures, rapports ou prompts.
- Desktop Beta : `1280x800`, `1440x900`, `1600x1000`; `1024x768` est une
  dégradation facultative. Ne pas inventer une UI mobile.

## Modèle de contexte partagé

Toute navigation entre pages doit préserver explicitement, quand applicable :

- `activeInstrument` et sa venue ;
- `horizon` et l'intervalle ;
- `currency = CHF` ou la devise sélectionnée ;
- `timezone = Europe/Zurich` ;
- `dataAsOf`, heure de réception et fraîcheur ;
- mode de donnée et statut d'entitlement ;
- portefeuille manuel sélectionné ;
- scénario actif et benchmark.

Un audit signale toute perte, duplication locale ou interprétation divergente de
ce contexte.

## Douze destinations cibles

1. Aujourd'hui ;
2. Marchés ;
3. Opportunités ;
4. Analyse ;
5. Options ;
6. Simulateur ;
7. Portefeuille ;
8. Graphiques ;
9. Risques ;
10. Catalyseurs ;
11. Calendrier ;
12. Sources & Rapports.

`Alertes` est une capacité globale de la barre supérieure, pas une page. Si les
routes actuelles diffèrent, établir une table `actuel -> cible -> décision`
avant de proposer renommage, fusion ou retrait. Ne pas modifier l'architecture
d'information pendant un simple audit.

## Protocole d'audit obligatoire

1. Relever dépôt, branche, HEAD, dirty state, worktrees, remote, PR/CI et lot.
2. Lire gouvernance, architecture, contrats, schémas, registre de calculs,
   routes, intégrations, tests, CI, déploiement et documentation.
3. Exécuter les contrôles non mutants disponibles et le script d'inventaire :

   ```bash
   python .claude/skills/vertex-titanium-ledger/scripts/audit_titanium_ledger.py
   ```

4. Auditer les couches dans l'ordre de `references/full-audit.md`.
5. Vérifier chaque page contre sa question, ses données autorisées, ses états,
   la capture canonique et sa planche de composition.
6. Reproduire chaque défaut avant de le déclarer lorsque l'exécution est sûre.
7. Classer les constats `CRITIQUE`, `ÉLEVÉ`, `MOYEN`, `FAIBLE` ; ne jamais
   gonfler la gravité pour la présentation.
8. Rendre un rapport exploitable, sans corriger.

## Format de rapport

Commencer par le verdict et les risques majeurs, puis fournir :

1. périmètre réellement inspecté et limites ;
2. état Git et preuves exécutées ;
3. constats classés avec `preuve`, `impact`, `fichier:ligne`, `correction
   recommandée` et `test attendu` ;
4. matrice des douze pages `conforme / partiel / absent / non vérifiable` ;
5. matrice de vérité des données et intégrations ;
6. dette sécurité, accessibilité, performance, qualité et exploitation ;
7. plan de correction ordonné par dépendances, sans l'exécuter ;
8. risques résiduels et une seule prochaine commande recommandée.

Ne pas présenter une recherche textuelle, une capture générée ou un test non
exécuté comme une preuve d'exécution réelle.

## Exécution autorisée

Si l'utilisateur demande explicitement de corriger ou développer :

1. convertir les constats acceptés en lot borné et critères binaires ;
2. préserver toutes les modifications utilisateur non liées ;
3. traiter une page ou une capacité à la fois ;
4. écrire le test rouge ou le reproducteur avant le correctif quand pertinent ;
5. utiliser les contrats et primitives existants avant d'en créer ;
6. exécuter les validations ciblées puis transversales ;
7. comparer les trois viewports à la capture canonique ;
8. documenter diff, mesures, limites, rollback et risque restant ;
9. ne jamais fusionner ou publier sans autorisation humaine.

## Condition de sortie

Un audit est terminé seulement si son périmètre et ses limites sont explicites,
chaque constat est relié à une preuve, les douze pages et la vérité financière
sont couvertes, et aucune correction n'a été glissée dans le rapport. Une
implémentation est terminée seulement lorsque la fidélité visuelle, les contrats,
les états, l'accessibilité, la performance, les tests et le rollback sont prouvés.
