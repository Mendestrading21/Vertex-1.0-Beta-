# Page 08 — Portefeuille `/portfolio`

## Question

Quelles expositions et concentrations résultent de mon ledger manuel ?

## Dominante et modules

Dominante : table de positions manuelles.

1. Valeur, cash et P&L avec provenance.
2. Table dominante.
3. Concentrations instrument/secteur/devise et delta.
4. Risques, actualités et événements liés.

Action principale : ajouter ou modifier une position manuelle.

## Données et logique

Ledger manuel, market data IBKR, FX daté, Data Fusion Hub. P&L, allocations et risques calculés serveur. Import/export CSV avec aperçu ; jamais de compte ou positions IBKR.

## États et adaptation desktop

Stale : ledger éditable, valorisation marquée. Offline : brouillons locaux non synchronisés. Cible Vertex 1.0 Beta : 1280, 1440 et 1600 px. À 1024 px, la table des positions reste dominante et les concentrations, risques et informations liées passent sous celle-ci.

Mobile : **LATER**. Les contrats sémantiques du ledger manuel, positions, états, sélections et actions sont conservés, sans rendu Vertex pour téléphone et sans introduire de lecture de compte courtier.

## Acceptation

- conservation des lots et cashflows ;
- réel et simulé séparés ;
- aucun identifiant de compte courtier ;
- E2E ajout, modification, clôture manuelle, FX stale et CSV invalide.
