# LOT-23 — Qualification qualité et sécurité

## Références et dépendances

- Dépendances bloquantes : LOT-00 à LOT-22 fusionnés, chaque PR verte et revue.
- Références obligatoires : `docs/06-quality/TEST_STRATEGY.md`, `TEST_MATRIX.md`, `CI_GATES.md`, `PERFORMANCE_BUDGETS.md`, `SECURITY_CONTROLS.md`, `OBSERVABILITY.md`, `docs/07-delivery/DEFINITION_OF_DONE.md`, `SECURITY.md` et `manifests/forbidden-capabilities.yaml`.

## Objectif

Prouver, sur un checkout propre et un environnement représentatif, que Vertex One respecte ses contrats financiers, ses interdictions, WCAG 2.2 AA, ses budgets de performance et ses exigences de résilience avant toute release candidate.

La qualification Vertex 1.0 Beta est **DESKTOP ONLY** : `1280×800`,
`1440×900` et `1600×1000`. `1024×768` est un scénario de dégradation laptop
optionnel. Toute QA `390`/`360`, mobile, bottom nav ou `MobileActionBar` est
`LATER` et ne bloque pas la Beta ; les contrats sémantiques restent inchangés.

## Non-objectifs

- ajouter une fonctionnalité, une source, une métrique ou une page ;
- assouplir une gate, un seuil ou une assertion pour obtenir du vert ;
- accepter une vulnérabilité, un test flaky ou une capacité interdite sans décision humaine explicite ;
- utiliser données commerciales réelles, compte IBKR, positions, P&L, ordres ou exécutions ;
- exécuter le code d’une PR non fiable sur l’ordinateur TWS.

## Livrables attendus

1. Matrice de traçabilité reliant chaque exigence et état UI à un test, sa commande et son résultat.
2. Suite E2E des 12 pages sur Chromium, Firefox et WebKit, avec parcours desktop
   `1280×800`, `1440×900` et `1600×1000` ; `1024×768` uniquement comme
   dégradation laptop si utile.
3. Rapport WCAG 2.2 AA : axe automatisé, clavier, focus, zoom 200 %, contraste, mouvement réduit et revue lecteur d’écran des parcours critiques.
4. Rapport de performance reproductible : Core Web Vitals, bundles, API p50/p95/p99, tables 10 000 lignes, chaîne options lourde, worker et backpressure IBKR.
5. Campagne de résilience/chaos : codes TWS 1100/1101/1102/1300/502, pacing, doublon/rejeu/désordre/DLQ TradingView, timeout IA, perte réseau, redémarrage PostgreSQL, disque faible et dérive d’horloge.
6. Dossier supply-chain : lockfiles, inventaire des licences, SBOM SPDX/CycloneDX, provenance, signature, digests d’images et Actions épinglées à SHA complet.
7. Résultats de détection de secrets, SAST, CodeQL, audit dépendances Python/Node, OSV, Syft/Grype et scan du manifeste des capacités interdites.
8. Registre des défauts triés par sévérité, preuve de correction et risques résiduels soumis à validation humaine.

## Scénarios bloquants

- Recherche statique et dynamique de toute API IBKR ordre, compte, position, P&L ou exécution dans code, import, route, permission et dépendance.
- Vérification qu’aucun calcul financier autoritaire ne réside en TypeScript, Pine ou IA.
- Injection de données absentes, partielles, retardées, périmées, futures et contradictoires : aucune ne doit produire `QUALIFIED`.
- Vérification qu’aucun mock, cache, fallback, snapshot ou théorie ne s’affiche comme réel/live.
- Recherche de scraping, contournement d’entitlement et accès public direct à l’API locale/TWS.
- Prompt injection dans news, Pine, CSV et contenu utilisateur : aucune modification de donnée, calcul ou verdict.

## Tests et seuils obligatoires

- Tous les checks de `CI_GATES.md` passent depuis un checkout propre, avec commandes et versions archivées.
- 100 % des gates/verdicts/contrats critiques, ≥ 90 % branches cœur financier, ≥ 80 % backend, ≥ 85 % frontend et mutation score critique ≥ 95 %.
- Zéro test flaky, skip/xfail non approuvé, violation axe critique/sérieuse, secret, licence inconnue ou vulnérabilité critique/haute exploitable.
- LCP ≤ 2,5 s, INP ≤ 200 ms, CLS ≤ 0,1, bundle initial ≤ 300 Ko gzip sauf ADR et lectures API snapshot p95 ≤ 250 ms/p99 ≤ 750 ms.
- Tests de chaos sans corruption, double traitement, verdict fail-open, retry infini ni perte silencieuse ; retour à un état sain observé et mesuré.

## Critères de sortie mesurables

- Les 12 pages et leurs huit états communs sont traçables vers une preuve verte.
- Les trois viewports desktop sont couverts ; l'absence de variante ou QA mobile
  n'est pas un défaut de Vertex 1.0 Beta.
- `manifests/forbidden-capabilities.yaml` ne produit aucune occurrence non explicitement autorisée dans un test négatif.
- SBOM, provenance, signature et notices correspondent exactement aux artefacts candidats.
- Tous les budgets et seuils sont respectés ; chaque risque résiduel porte propriétaire, impact, échéance et décision humaine.
- Une revue indépendante conclut que le LOT-24 peut commencer. Toute preuve absente ou échec non corrigé vaut `NO-GO`.

## Compte rendu final

Mettre `docs/99-status/NOW.md` à jour et fournir : branche, commit, environnement, commandes, durées, rapports, défauts corrigés, risques restants et une seule prochaine commande recommandée. Ne pas démarrer LOT-24 automatiquement.
