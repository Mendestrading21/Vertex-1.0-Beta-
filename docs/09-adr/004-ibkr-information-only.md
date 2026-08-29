# ADR-004 — IBKR est information-only

- Statut : Accepté
- Date : 2026-08-28
- Portée : TWS, IB Gateway, agent local, portefeuille

## Contexte

Vertex est un outil d’analyse. Lire comptes, positions ou PnL IBKR créerait une seconde vérité face au portefeuille manuel et augmenterait la sensibilité des données. La présence même de chemins d’ordre dormants élargirait le risque opérationnel.

## Décision

L’intégration IBKR est limitée à l’information autorisée.

- Capacités permises : connexion, contrats, quotes, historique, options, scanners, actualités et événements sous entitlement.
- Capacités interdites : comptes, positions, PnL compte, marge compte, ordres, exécutions, allocations et modification TWS.
- Le portefeuille canonique reste manuel et ne contient aucun identifiant de compte IBKR.
- L’agent utilise une allowlist de messages et méthodes ; toute capacité non déclarée est bloquée.
- TWS active le mode lecture seule lorsque disponible et écoute uniquement sur loopback.
- Les tests statiques recherchent les symboles et routes interdits ; les tests d’intégration vérifient qu’aucun message d’ordre ou de compte n’est émis.
- Les entitlements sont sondés et affichés sans fallback silencieux.

## Conséquences

### Positives

- Aucun chemin d’exécution de marché.
- Réduction des données personnelles et du risque de confusion.
- Portefeuille cohérent et révisable indépendamment du broker.

### Coûts et contraintes

- Les positions et transactions sont saisies ou importées manuellement.
- Les métriques de marge sont théoriques ou déclarées comme indisponibles.
- Certaines fonctions attrayantes de TWS ne sont volontairement pas utilisées.

## Options rejetées

| Option | Motif du rejet |
|---|---|
| Lecture automatique des positions | Crée une seconde autorité et importe des données de compte |
| Chemins d’ordre désactivés par configuration | Le code dormant reste une capacité dangereuse |
| Paper trading automatisé | Change la nature du produit et ses contrôles |
| Utilisation du PnL TWS comme référence | Contredit le ledger manuel canonique |

## Critères de réexamen

Tout changement exige un nouveau produit, une nouvelle analyse réglementaire et de menace, ainsi qu’une ADR remplaçant explicitement celle-ci. Il ne peut pas être ajouté comme simple option.
