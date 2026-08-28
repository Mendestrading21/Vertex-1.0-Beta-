# ADR-013 — Fusion à partir de sources officielles et autorisées

- Statut : Accepté
- Date : 2026-08-28
- Portée : marché, options, actualités, événements, fondamentaux, macro

## Contexte

Vertex veut couvrir largement marché, options, nouvelles et événements. Les interfaces TWS et TradingView affichent des informations dont les droits d’automatisation diffèrent. Le scraping et les dépôts de données communautaires peuvent violer droits, fraîcheur, provenance ou qualité.

## Décision

- Le runtime consomme uniquement des APIs officielles, flux sous entitlement, exports utilisateur autorisés et sources primaires documentées.
- IBKR est prioritaire pour prix, contrats, options, scanners et informations disponibles par API.
- TradingView fournit alertes Pine et exports officiels TXT ou CSV ; son interface n’est jamais scrapée ni automatisée.
- SEC EDGAR, FRED ou ALFRED, organismes publics et pages ou flux explicitement autorisés des émetteurs sont les sources primaires retenues.
- Chaque source possède registre, responsable, licence ou droits, capacités, couverture, délai, fraîcheur, quota et méthode de révocation.
- Toute donnée porte DataEnvelope, entitlement, provenance, qualité et payload_hash.
- Déduplication et résolution d’identité conservent tous les originaux ; les conflits sont explicites et jamais écrasés par l’IA.
- Une source absente ou non autorisée produit UNSUPPORTED, NOT_ENTITLED ou MANUAL_EXPORT, jamais un fallback silencieux.
- Les projets GitHub tiers servent de références ou bibliothèques licenciées, pas de fournisseurs anonymes de données.

## Conséquences

### Positives

- Provenance, droits et fraîcheur vérifiables.
- Réduction du risque juridique et des données inventées.
- Comportement dégradé honnête et explicable.

### Coûts et contraintes

- Couverture parfois plus faible que des agrégateurs non officiels.
- Les abonnements et quotas doivent être sondés et surveillés.
- Certaines informations restent manuelles ou indisponibles.

## Options rejetées

| Option | Motif du rejet |
|---|---|
| Scraping TradingView ou TWS | Droits, stabilité et provenance insuffisants |
| Navigation de navigateur automatisée | Contourne les interfaces prévues |
| Dataset GitHub inconnu en production | Fraîcheur, licence et origine non garanties |
| Fusion IA des contradictions | Destruction possible de preuves |
| Fallback caché vers une source moins fiable | Trompe sur la qualité du résultat |

## Critères de réexamen

Une nouvelle source doit passer la matrice de capacité, la revue juridique et sécurité, les tests de qualité et un ADR ou amendement approuvé avant d’alimenter le runtime.
