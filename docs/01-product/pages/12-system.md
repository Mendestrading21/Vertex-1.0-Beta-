# Page 12 — Système `/system`

## Question

Puis-je faire confiance aux sources, traitements et sauvegardes maintenant ?

## Dominante et modules

Dominante : matrice sources × capacités × état.

1. Entitlements, fraîcheur et couverture IBKR/TradingView/sources primaires.
2. Jobs, Queue, DLQ et ingestions.
3. Sécurité, versions et sauvegardes sans secret.
4. Journal d'audit, incidents et diagnostics.

Action principale : exécuter un diagnostic idempotent.

## Données et logique

`SourceEntitlement`, `SourceCoverage`, santé TWS, pacing, alertes TV, imports, queue, DB, jobs, clock drift, backup/restore et versions. Séparer droits visibles dans l'UI fournisseur et droits API réellement testés.

## États et adaptation desktop

Le shell de santé doit rester accessible même si l'API principale est dégradée. Cible Vertex 1.0 Beta : 1280, 1440 et 1600 px. À 1024 px, la matrice conserve ses axes avec défilement interne et les diagnostics passent sous celle-ci ; les confirmations des actions sensibles restent inchangées.

Mobile : **LATER**. Les contrats sémantiques des capacités, statuts, diagnostics, états et actions sensibles sont conservés, sans surface Vertex pour téléphone. Claude Remote Control peut uniquement piloter la session desktop.

## Acceptation

- aucun secret/payload complet dans diagnostic ;
- affichage explicite `AVAILABLE/DELAYED/MANUAL_EXPORT/NOT_ENTITLED/UNSUPPORTED/ERROR` ;
- test restauration et alertes ;
- E2E TWS down, WSH absent, webhook rejeté, DLQ et sauvegarde trop vieille.
