# Preuves cloud et classification

## Taxonomie de réalisation

| État | Preuve minimale |
|---|---|
| `PROUVÉ` | Code au SHA figé, chemin runtime relié et contrôle pertinent vert sur ce même SHA. |
| `PRÉSENT_NON_PROUVÉ` | Implémentation visible, mais appel runtime, test actuel ou preuve d'environnement manquant. |
| `PLANIFIÉ` | Lot, ADR, documentation, interface ou registre sans implémentation reliée. |
| `BLOQUÉ` | Preuve exigeant poste local, entitlement, secret, coût ou décision humaine. |
| `ABSENT` | Capacité attendue introuvable au SHA après recherche des synonymes et appelants. |
| `CONTREDIT` | Deux autorités actives, documents ou branches affirment des états incompatibles. |
| `INCONNU` | Accès ou preuve insuffisants ; ne pas convertir en réussite ou échec. |

Les états de données runtime (`REAL`, `SYNTHETIC`, `PARTIAL`, `DEGRADED`,
`MISSING`, `NOT_ENTITLED`, `UNSUPPORTED`, `UNKNOWN`, `STALE`) restent distincts
de cette taxonomie de réalisation.

## Sévérités

- `P0` : frontière financière violée, secret exposé, corruption/perte de données,
  donnée fictive présentée comme réelle, calcul matériel faux ou démarrage
  impossible pour le parcours principal.
- `P1` : décision potentiellement trompeuse, fraîcheur/provenance défaillante,
  maillon runtime essentiel déconnecté, fail-open, page clé inutilisable ou
  intégration live annoncée sans preuve.
- `P2` : résilience, performance, observabilité, accessibilité, couverture ou
  organisation insuffisante sans erreur financière immédiate.
- `P3` : cohérence, dette documentaire et finition sans incidence critique.

## Hiérarchie des preuves

1. comportement reproductible au SHA candidat ;
2. CI complète et logs du même SHA ;
3. test ciblé pertinent et code appelé par le runtime ;
4. code sans preuve d'appel ;
5. contrat/ADR accepté ;
6. lot, backlog, commentaire ou promesse.

Une CI verte prouve ses contrôles déclarés, pas un flux live qu'elle ne peut pas
contacter. Une capture prouve un rendu ponctuel, pas la provenance ni la
fraîcheur. Un mock prouve un contrat, pas un entitlement.

## Baseline à consigner

| Champ | Valeur attendue |
|---|---|
| Dépôt | `owner/repo` et visibilité |
| Heure | UTC et timezone de l'utilisateur si connue |
| Branche par défaut | nom + SHA |
| Candidat audité | branche/PR + SHA immuable |
| Branches concurrentes | SHA + capacités exclusives |
| PR actives | numéro, draft, base, head, conflits/review |
| CI | run, jobs, conclusion, SHA, artefacts |
| Gouvernance | protection, rulesets, reviews, signatures |
| Limites | accès absent, live non joignable, secrets non inspectés |

Relever deux fois le SHA candidat : au début et immédiatement avant la sortie.
Un écart invalide la baseline jusqu'à comparaison des nouveaux commits.

## Règle de comparaison

Comparer les graphes de commits et les fichiers changés avant de choisir un
candidat. Ne jamais additionner les capacités de branches non fusionnées dans
une même conclusion. Marquer les statuts `NOW.md`, historiques ou bloquants qui
citent un SHA/PR obsolète.
