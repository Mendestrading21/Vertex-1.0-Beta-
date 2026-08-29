# ADR-009 — Sécurité et frontières réseau privées

- Statut : Accepté
- Date : 2026-08-28
- Portée : GitHub, poste, conteneurs, session, réseau

## Contexte

Vertex traite données de marché, thèses et portefeuille sur le même poste que TWS. Une compromission du dépôt, d’un workflow ou d’un service public ne doit pas donner accès au broker ou à la base.

## Décision

- Le dépôt est privé, protégé par passkey ou 2FA, PR obligatoire, CODEOWNERS et fusion humaine.
- Les GitHub Actions ont permissions minimales et sont épinglées à un SHA complet.
- Aucun runner de PR non approuvée ne tourne sur le poste TWS.
- TWS écoute sur 127.0.0.1 ; PostgreSQL reste sur un réseau Compose interne.
- La PWA/API Vertex Beta ne sont accessibles que depuis le navigateur desktop local ; aucun Tailscale Serve/Funnel Vertex n'est déployé.
- Le téléphone sert uniquement à Claude Remote Control, hors runtime, session et surface réseau Vertex.
- Le Worker TradingView est le seul composant public.
- Cookies Secure, HttpOnly et SameSite, CSRF, CORS fermé, CSP et validation stricte sont obligatoires.
- Les conteneurs sont non-root, sans capabilities, avec filesystem racine en lecture seule lorsque possible.
- Secrets hors dépôt, journaux expurgés, rotation et accès minimum.
- Sauvegardes chiffrées, hors disque principal, avec restauration prouvée.

## Conséquences

### Positives

- Segmentation nette entre Internet, runtime local, base et TWS.
- Réduction du risque supply-chain et des fuites de secrets.
- Contrôles vérifiables dans la CI et les runbooks.

### Coûts et contraintes

- L'écoute locale de la PWA/API et l'absence d'exposition distante doivent être vérifiées à chaque release.
- Les mises à jour de dépendances et d’Actions nécessitent une revue.
- Certains modes de développement doivent utiliser des profils explicitement moins stricts.

## Options rejetées

| Option | Motif du rejet |
|---|---|
| API publique protégée par mot de passe | Surface d’attaque évitable |
| Tailscale Serve ou Funnel pour Vertex Beta | Accès distant hors périmètre desktop-only |
| Secrets dans env versionné ou alertes | Fuite durable possible |
| Action GitHub par tag flottant | Référence mutable |
| Runner GitHub sur la machine TWS | Pont supply-chain vers le broker |

## Critères de réexamen

Toute ouverture réseau, nouveau fournisseur ou runner exige mise à jour du threat model, tests d’abus, propriétaire, procédure de révocation et approbation humaine.
