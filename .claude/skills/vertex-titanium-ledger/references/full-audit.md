# Audit intégral de Vertex

## Principe

Un audit n'est ni une impression générale ni une recherche de mots. Il croise
architecture, contrats, exécution, tests, mesures, interface et documentation.
Rester en lecture seule et annoncer immédiatement toute zone non accessible.

## Couches à inspecter

### 1. Gouvernance et Git

- dépôt, branche, HEAD, dirty state, worktrees, remote, lot, PR et CI ;
- conformité de la branche et des actions au protocole du dépôt ;
- changements utilisateur non liés, fichiers générés et dérive documentaire ;
- dépendances entre lots, ADR manquants et décisions contournées.

### 2. Architecture et propriétaires

- frontières web/API/worker/ingress/edge/core/persistance ;
- propriétaire unique de chaque observation, calcul, état et verdict ;
- dépendances inversées, imports runtime vers un donneur, duplication d'autorité ;
- routes, état partagé, jobs, événements, cache et persistance.

### 3. Contrats et vérité financière

Appliquer `data-truth.md` aux schémas, DTO, modèles, migrations, formateurs,
calculs et rendus. Chercher les conversions silencieuses, valeurs par défaut,
arrondis, timezone, devise, unités, qualité et provenance perdues.

### 4. Intégrations et droits

- IBKR market-data-only, appels réellement autorisés et entitlements ;
- TradingView comme déclencheur, validation serveur et anti-rejeu ;
- fournisseurs de données, licences, quotas, fraîcheur, fallback et cache ;
- aucun compte IBKR, scraping, secret, identifiant ou payload sensible.

### 5. Sécurité et vie privée

- authentification, autorisation, sessions, CSRF/CORS/CSP, validation d'entrée ;
- gestion et rotation des secrets, logs et télémétrie ;
- dépendances, lockfiles, provenance, SBOM et licences ;
- sauvegarde/restauration, moindre privilège, réseau et exposition publique ;
- scénarios fail-closed, concurrence, rejeu et idempotence.

### 6. Calculs, décision et recherche

- registre central des calculs et versions ;
- invariants, oracles indépendants, propriétés, bornes et cas limites ;
- calibration hors échantillon et abstention ;
- séparation recherche/backtest/runtime ;
- absence de formule ou verdict autoritaire côté TypeScript ou IA.

### 7. Produit et douze pages

Pour chaque destination de `pages.md`, vérifier : route, question, dominante,
actions, contrats, états, contexte partagé, source, fraîcheur, unité, clavier,
alternative accessible, performance et fidélité à la capture canonique.

### 8. Design system

- source unique de tokens et absence de couleurs/espaces/z-index sauvages ;
- shell exact, logo, rail, ticker, inspecteur, verre, contraste et densité ;
- matrice complète des états ;
- primitives réellement mutualisées sans imposer le même bento aux pages ;
- graphiques exacts, chargés par route et dotés d'un équivalent textuel/tabulaire.

### 9. Accessibilité

- structure, titres, landmarks, noms, descriptions et ordre de lecture ;
- clavier, focus, dialogues, menus, tableaux et graphiques ;
- contraste, couleur non exclusive, zoom/reflow, textes longs ;
- mouvement/transparence réduits et couleurs forcées ;
- axe automatisé complété par une revue humaine lecteur d'écran.

### 10. Performance et résilience

- budgets réellement mesurés, chunks, lazy loading et stabilité de layout ;
- p95/p99 seulement avec population suffisante ; labo distinct du terrain ;
- cache, reconnexion, offline, stale, backpressure, timeouts et retries ;
- charge, chaos, reprise, sauvegarde restaurée et observabilité actionnable.

### 11. Tests et CI

- tests unitaires, contrats, propriétés, intégration, E2E, visuels et a11y ;
- faux positifs, assertions faibles, tests sautés, fixtures irréalistes ;
- reproductibilité locale/CI, services partagés et ordre d'exécution ;
- portes réellement câblées, actions épinglées, permissions et timeouts.

### 12. Maintenabilité et livraison

- code mort, duplication, TODO/FIXME, complexité et conventions ;
- documentation correspondant au code exécuté ;
- migrations, rollback, runbooks, monitoring, sauvegarde et release ;
- dette explicitée, responsable, échéance et preuve attendue.

## Gravité

| Niveau | Définition |
|---|---|
| CRITIQUE | perte financière/sécurité, secret exposé, ordre possible, vérité falsifiée ou corruption sans barrière |
| ÉLEVÉ | calcul/contrat/source erroné, fail-open, page majeure inutilisable, absence de preuve d'une frontière absolue |
| MOYEN | incohérence réelle, accessibilité/performance dégradée, dette susceptible de devenir défaut produit |
| FAIBLE | maintenabilité, cohérence ou finition sans impact immédiat sur la vérité ou le parcours principal |

Un risque hypothétique sans chemin démontré reste une hypothèse, pas un constat
critique.

## Fiche de constat

```text
ID / gravité / statut : confirmé | inféré | non vérifiable
Zone :
Preuve : commande, sortie, test ou fichier:ligne
Comportement observé :
Comportement attendu :
Impact :
Cause probable :
Correction recommandée :
Test de non-régression :
Dépendances / rollback :
```

## Matrice de couverture finale

Rendre au minimum :

- 12 pages × visuel, données, états, accessibilité, performance, tests ;
- sources × droits, fraîcheur, couverture, fallback, incidents ;
- calculs × propriétaire, version, unité, oracle, tests ;
- frontières absolues × preuve actuelle ;
- constats × gravité, coût, dépendance et ordre de correction.
