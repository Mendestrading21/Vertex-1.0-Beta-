# Politique de sécurité

Ne pas publier d'informations de vulnérabilité sensibles dans une issue publique. Tant que le dépôt est personnel, documenter le canal privé dans les paramètres GitHub.

Secrets interdits dans Git : mots de passe, tokens IBKR/Cloudflare/IA, API keys, URLs secrètes, identifiants de compte, cookies, payloads et captures réelles.

Vertex ne contient aucune capacité d'ordre et ne doit jamais lire compte, positions, P&L, ordres ou exécutions IBKR. Toute découverte d'un tel chemin est critique et bloque la release.

Une suppression dans l'arbre courant ne suffit pas à traiter une exposition
historique. Dans ce cas, arrêter les merges et appliquer
`docs/08-runbooks/GIT_HISTORY_QUARANTINE.md`. Ne jamais publier dans une PR le
contenu retiré, son extrait ou une capture permettant de le reconstituer.

La branche `main` doit rester protégée par le ruleset décrit dans
`docs/08-runbooks/GITHUB_PROTECTION.md`. Toute exception est temporaire,
nommée et validée humainement.
