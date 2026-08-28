# Sécurité — règles obligatoires

## Secrets et données sensibles

- Aucun secret, token, cookie, mot de passe, URL signée, identifiant de compte, payload réel, donnée personnelle ou donnée commerciale brute dans Git, logs, fixtures, captures ou messages d’erreur.
- Charger les secrets depuis le gestionnaire prévu à l’exécution ; `.env` local reste ignoré et `.env.example` ne contient que des valeurs fictives.
- Refuser de démarrer si un secret obligatoire manque ou si une valeur d’exemple est utilisée hors test.
- Journaliser des identifiants techniques minimaux, hashes non réversibles et `trace_id`; appliquer allowlist et redaction avant émission.

## Réseau et accès

- TWS écoute uniquement sur loopback, en lecture seule et avec `client_id` non nul.
- Vertex 1.0 Beta ne livre aucun accès à l’interface produit depuis un téléphone :
  l’exposition de l’application par Tailscale Serve est `LATER`. L’API locale et
  les services métier restent privés et ne sont jamais exposés publiquement.
- Le webhook TradingView public termine sur l’ingress Cloudflare, jamais sur TWS ni sur l’API locale.
- Le pilotage de **Claude** depuis un téléphone utilise uniquement Remote Control
  officiel, avec session révocable. Ce canal pilote Claude Code ; il n’est ni une
  UI mobile Vertex ni un accès Tailscale à l’application. Ne jamais exposer
  terminal, SSH, TWS ou API pour le remplacer.
- Pour TradingView → Worker, vérifier capacité de route/secret, registre d'alerte, timestamp, fenêtre d’âge, taille, content type, schéma, allowlist, rate limit et idempotency key avant mise en file. Ne pas prétendre que TradingView fournit une signature cryptographique personnalisée.
- Refuser par défaut une origine, route, méthode, permission ou capacité non déclarée.

## Sources et contenu externe

- Utiliser exclusivement API, webhook, Pine ou export officiellement autorisé ; aucun scraping de TradingView, TWS, IBKR ou site tiers.
- Ne jamais contourner entitlement, paywall, limitation de débit, robots, session utilisateur ou condition de licence.
- Traiter news, Pine, CSV, texte utilisateur et réponse IA comme non fiables : validation stricte, échappement de sortie et protection contre prompt injection.
- Une alerte TradingView n’est jamais autoritaire ; revalider sur une observation IBKR fraîche avant un nouveau verdict.

## Supply-chain et CI

- Verrouiller les dépendances et images par version immuable/digest ; épingler chaque GitHub Action à un SHA complet.
- Permissions Actions `read-all` par défaut, élévation minimale par job, timeout obligatoire et aucun secret sur code non fiable.
- Interdire `pull_request_target` avec checkout/exécution du code de la PR et interdire les runners de PR sur l’ordinateur TWS.
- Produire SBOM, provenance, notices et signature ; exécuter détection de secrets, SAST, audit Python/Node, OSV et scan d’image.
- Ne pas adopter Trivy tant que le risque documenté dans `DEPENDENCY_REGISTER.md` n’est pas réévalué et accepté par ADR.
- Toute licence inconnue, dépendance non épinglée ou vulnérabilité critique/haute exploitable bloque la fusion.

## Réponse et validation

- Une erreur d’authentification/autorisation échoue fermée et ne révèle ni existence de ressource ni détail sensible.
- Les sauvegardes sont chiffrées, soumises au moindre privilège et restaurées périodiquement dans une base vide.
- Toute découverte d’une capacité IBKR interdite, d’un secret commité ou d’une exposition publique non prévue impose arrêt, rotation/révocation si nécessaire et `NO-GO`.
- Ne jamais publier une vulnérabilité exploitable dans une issue publique ; suivre `SECURITY.md`.
