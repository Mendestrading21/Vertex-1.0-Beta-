# Feuille de route maîtresse

## Règle d'exécution

Vertex est construit par lots fermés, dans l'ordre ci-dessous. Un lot produit une PR autonome, passe ses contrôles, reçoit une validation humaine puis est fusionné avant l'ouverture du suivant. Claude ne démarre jamais un lot implicitement.

Les lots 00 à 10 établissent l'autorité des données, des calculs et de l'interface. Les lots 11 à 22 construisent ensuite exactement une page chacun. Les lots 23 et 24 prouvent que l'ensemble est exploitable.

## Phases

| Phase | Lots | Résultat obligatoire |
|---|---:|---|
| A — Fondation | 00–03 | Dépôt gouverné, contrats canoniques, stockage et qualité prouvés |
| B — Sources | 04–06 | IBKR, TradingView et Data Fusion collectent sans contourner les droits |
| C — Autorité | 07–09 | Calculs Python, portes, verdict unique et API traçable |
| D — Expérience | 10–22 | Design system puis 12 pages sobres et cohérentes |
| E — Qualification | 23–24 | Sécurité, résilience, restauration, soak et release candidate |

## Lots ordonnés

| Lot | Objet | Dépend de | Preuve de sortie principale |
|---:|---|---|---|
| 00 | Gouvernance et inventaire | — | Constitution acceptée, ancien Vertex classé, `NOW.md` opérationnel |
| 01 | Toolchain, dépôt et CI | 00 | Versions verrouillées, CI minimale verte, protections documentées |
| 02 | Contrats, identité, unités et temps | 01 | Schémas versionnés et tests d'identité d'instrument |
| 03 | PostgreSQL, outbox et qualité | 02 | Ingestion idempotente, provenance et fraîcheur testées |
| 04 | Edge IBKR information-only | 03 | Quotes/options/scanner/news/WSH acquis sans capacité de trading |
| 05 | Ingress et imports TradingView | 04 | Webhook anti-rejeu, file durable et imports officiels validés |
| 06 | Data Fusion Hub | 04, 05 | Déduplication, entitlements, événements, entreprise et ETF fusionnés |
| 07 | Moteur quantitatif | 02, 03 | Registre des calculs et invariants financiers prouvés |
| 08 | Gates, calibration et `AdviceEngine` | 06, 07 | Verdict canonique fail-closed et reproductible |
| 09 | API, jobs, accès et observabilité | 03, 08 | OpenAPI, worker, SSE, traces et autorisation bout en bout |
| 10 | Design system et shell desktop | 09 | Navigation, tokens, états et composants de base accessibles sur la matrice Beta |
| 11 | Aujourd'hui | 10 | Attention priorisée et justifiée en moins de 30 secondes |
| 12 | Calendrier | 10, 06 | Agenda unifié dédupliqué, filtrable et sourcé |
| 13 | Marchés | 10, 06, 07 | Régime, breadth et leadership lisibles sans surcharge |
| 14 | Opportunités | 10, 08 | Candidats classés avec raisons et exclusions visibles |
| 15 | Analyse | 10, 08 | Graphique, niveaux, scénarios et verdict réunis sans recalcul UI |
| 16 | Options | 10, 04, 07 | Chaîne exacte, liquidité, IV/Greeks et provenance visibles |
| 17 | Simulateur | 10, 07 | Hypothèses et résultats théoriques clairement séparés du réel |
| 18 | Portefeuille manuel | 10, 07 | Expositions saisies manuellement, jamais lues depuis IBKR |
| 19 | Suivi | 10, 08 | Thèses et revues historisées avec événements déclencheurs |
| 20 | Performance | 10, 07 | Rendement, risque et attribution cohérents avec les flux manuels |
| 21 | Vertex AI | 10, 09 | Explication structurée, sourcée et incapable de décider |
| 22 | Système | 10, 09 | Santé, couverture, droits, jobs, incidents et sauvegardes visibles |
| 23 | Qualification qualité et sécurité | 11–22 | E2E, WCAG, performance, chaos, supply-chain et scans verts |
| 24 | Installation et release candidate | 23 | Restauration, rollback et cinq séances de soak validés |

## Portes de phase

### Porte A — avant toute source réelle

- aucun contrat concurrent pour instrument, observation ou événement ;
- UTC, calendriers, devises, unités et `Decimal` définis ;
- données absentes et zéros distingués ;
- migrations montée/descente testées sur PostgreSQL réel ;
- données de test exclusivement synthétiques ou licenciées.

### Porte B — avant tout calcul live

- matrice de capacités réelle pour chaque abonnement ;
- aucune API ordre/compte/position/exécution présente ;
- source, droit, type live/delayed et fraîcheur attachés à chaque observation ;
- doublons, replay, reconnexion et pacing testés ;
- aucun scraping de TWS ou TradingView.

### Porte C — avant toute page de décision

- Python est l'unique autorité financière ;
- chaque calcul est versionné, traçable et reproductible ;
- gates fail-closed ;
- statut, direction, confiance et probabilité ont des sens distincts ;
- l'IA et le frontend consomment le verdict sans le modifier.

### Porte D — avant qualification finale

- les 12 pages couvrent tous les états communs ;
- un visuel dominant et une action principale au maximum par page ;
- alternatives textuelles aux graphiques essentiels ;
- desktop Phase 1 qualifié à 1280×800, 1440×900 et 1600×1000 ;
- dégradation laptop 1024×768 explicite et utilisable ;
- interface mobile `LATER`, sans fork des contrats canoniques ;
- aucun contenu de démonstration présenté comme réel.

### Porte E — GO release candidate

Tous les critères de `DEFINITION_OF_DONE.md` et de la checklist `RELEASE.md` sont démontrés. Une absence de preuve vaut `NO-GO`.

## Estimation et cadence

Les lots sont estimés après le LOT-01 à partir du dépôt réel. Claude ne doit pas inventer de date. Chaque lot est découpé jusqu'à pouvoir être revu dans une seule PR. Si un lot dépasse cette taille, il est scindé par un ADR sans ouvrir le suivant.
