# Dette technique et limites connues

Ce registre liste les défauts **connus et non corrigés**, ainsi que les limites
de preuve. Il est tenu à jour à chaque audit adversarial. Une entrée n'est
retirée que lorsqu'un test reproducteur rouge d'abord la ferme.

Ce fichier ne contient pas de décision humaine ; celles-ci restent dans
`BLOCKERS.md`.

## Défauts ouverts (3ᵉ audit adversarial, commit `2bc75cc`)

| ID | Sévérité | Fichier | Défaut | État |
|---|---|---|---|---|
| P1-C | P1 | `apps/api/src/vertex_api/ai_explain.py` | Le détecteur de langage d'ordre est une **liste noire best-effort** : contourné par une autre langue (espagnol), une formulation en toutes lettres (« Trois chances sur quatre ») ou un homoglyphe (U+0251). | ouvert — aucune garantie d'exhaustivité ne doit être annoncée |
| P1-D | P1 | `apps/api/src/vertex_api/ai_explain.py` | Le même détecteur **refuse des libellés financiers légitimes** (« Marge brute de 42 % », « Dividende de 2,5 % ») : faux positifs qui peuvent masquer une donnée réelle. | ouvert |
| P2-préc. | P2 | `docs/` | Les rapports de commit des vagues 3 à 5 ont **sur-promis** : ils annonçaient des fermetures que la reproduction contredisait. Correction de méthode appliquée (ne décrire que ce que le test prouve), mais l'historique Git conserve les messages fautifs. | méthode corrigée, historique inchangé |

## Limites de preuve (aucune n'est un défaut de code)

| Sujet | Limite exacte |
|---|---|
| Version Python | La suite tourne localement sur **3.11** (plancher). Le workflow CI exécute la cible **3.13**, mais il n'a **encore jamais tourné** : tant qu'un run vert n'existe pas sur GitHub, aucune preuve n'existe sur la version de production. |
| CI | Le workflow `.github/workflows/ci.yml` existe et couvre 15 portes (actions épinglées à un SHA de commit complet, images par digest immuable). Il n'a **jamais été exécuté** : GitHub n'a pas encore reçu la branche avec ce fichier. Un workflow non exécuté ne prouve rien. |
| Intégration | `tools/run_checks.sh --integration` couvre désormais les trois suites (`vertex_persistence`, `worker`, `api`), **en série obligatoire** : elles partagent la même base et recréent le schéma. Avant ce correctif, seule la suite `vertex_persistence` tournait — les mentions « TOUT VERT » antérieures ne couvraient donc **pas** les suites worker et api. |
| Mutation, charge, chaos | Non exécutés (LOT-23). Le seuil de mutation ≥ 95 % des règles de test n'est **pas** vérifié. |
| Supply-chain | `uv.lock` verrouille les 60 paquets Python en versions exactes + 1035 hachages sha256 ; `pip-audit --strict` et `pnpm audit --audit-level high` remontent **0 vulnérabilité** (exécutés localement) ; une SBOM CycloneDX 1.6 de 53 composants est produite. Manquent encore : **signature** (cosign), **provenance** SLSA, scan d'image de conteneur, et SBOM du volet Node. |
| Navigateurs | Playwright ne tourne que sur **Chromium**. Firefox et WebKit sont exigés avant release et n'ont jamais été lancés. |
| Données | **Aucune donnée réelle n'a jamais été observée.** Tout est `SYNTHETIC` étiqueté ; IBKR n'a jamais été contacté ; Cloudflare n'est pas déployé. |
| Détection de secrets | `tools/check_secrets.py` inspecte l'**arbre suivi**, pas l'historique Git. Un secret introduit puis retiré dans un commit antérieur ne serait pas vu. La détection est par motifs : une forme non listée passe. |
| Probabilités | `probability.calibration` est `NOT_IMPLEMENTED` au registre : aucune probabilité prédictive n'est affichable, et aucune ne l'est. |
