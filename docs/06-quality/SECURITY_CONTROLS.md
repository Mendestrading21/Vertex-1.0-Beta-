# Contrôles sécurité

## GitHub

- dépôt privé, 2FA/passkey ;
- PR obligatoire, squash, branche à jour, conversations résolues ;
- aucun force-push/suppression de `main` et tags `v*` ;
- CODEOWNERS pour finance, contrats, migrations, intégrations, workflows et infra ;
- fusion et release humaines ;
- PAT fine-grained, dépôt unique, permissions minimales et expiration ;
- CodeQL/dependency review/push protection si disponibles.

## Supply chain

- Gitleaks CLI, pip-audit, OSV-Scanner, Syft, Grype et Cosign ;
- SBOM SPDX/CycloneDX, provenance et attestation ;
- images par digest, Actions par SHA, packages exacts ;
- Trivy différé au lancement après la compromission supply-chain documentée de 2026 ;
- exception vulnérabilité seulement avec propriétaire, justification, compensation et expiration.

## Conteneurs

Non-root, filesystem root read-only, tmpfs, `cap_drop: ALL`, `no-new-privileges`, limites CPU/mémoire/PID, healthchecks, réseaux internes et secrets montés hors dépôt.

## Application

- passkey/WebAuthn et session courte pour l'accès utilisateur ;
- l'écoute reste loopback-only en Beta (ADR-002/ADR-009 : ni Tailscale Serve ni
  exposition LAN) ; aucune protection réseau ne remplace la session ;
- validation stricte de toute entrée/import ;
- CSRF, CORS fermé, CSP, cookies Secure/HttpOnly/SameSite ;
- logs expurgés et identifiants de corrélation ;
- aucun compte, position ou secret transmis à IA, Cloudflare ou télémétrie.

## Ingress TradingView

POST JSON, taille, allowlist IP, secret constant-time, timestamp, nonce, rate limit, Queue/DLQ, idempotence et commit avant ack. mTLS seulement si la chaîne de certificat est réellement validée.

