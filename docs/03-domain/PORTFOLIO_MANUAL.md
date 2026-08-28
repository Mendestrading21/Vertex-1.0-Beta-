# Portefeuille manuel

## Autorité

Le portefeuille Vertex est un registre saisi par l'utilisateur. Il n'est jamais synchronisé depuis IBKR. Cette séparation supprime toute dépendance aux API de compte et oblige le produit à montrer la qualité réelle de la saisie.

## Événements du registre

- achat/vente saisi après exécution externe ;
- ouverture/fermeture d'une jambe option ;
- commission et frais ;
- dépôt/retrait ;
- dividende, intérêt, taxe et ajustement ;
- split, spin-off, assignment/exercise saisi manuellement ;
- correction par événement compensatoire, jamais modification silencieuse de l'historique.

Chaque événement a identifiant, heure effective, heure de saisie, instrument canonique, quantité signée, prix, devise, frais, source `MANUAL`, note et pièces facultatives hors Git.

## Lots et valorisation

La méthode de lot est choisie et versionnée ; elle n'est pas modifiée rétroactivement sans migration. P&L réalisé, non réalisé et flux externes sont séparés. Les quotes de valorisation portent source et fraîcheur. Une quote manquante produit une valorisation partielle, jamais zéro.

## Options

Un contrat utilise l'identité exacte, notamment `conId`, `tradingClass`, expiry, strike, right, multiplier, currency et exchange. Expiration, assignment, exercise ou corporate action ne sont appliqués qu'après confirmation manuelle ou événement explicitement validé.

## Réconciliation

Vertex fournit une checklist de comparaison avec le relevé courtier sans importer automatiquement le compte. Une différence crée un `ReconciliationIssue` avec statut, montant, devise et note. Elle ne modifie aucune opération seule.

## Garde-fous

- aucun bouton « synchroniser IBKR » ;
- aucun identifiant de compte requis ;
- aucun P&L consolidé si devise ou quote nécessaire manque ;
- données réelles et portefeuille de démonstration stockés dans des espaces distincts ;
- export chiffré et audit des modifications.

