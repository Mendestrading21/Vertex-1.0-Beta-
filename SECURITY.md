# Politique de sécurité

Ne pas publier d'informations de vulnérabilité sensibles dans une issue publique. Tant que le dépôt est personnel, documenter le canal privé dans les paramètres GitHub.

Secrets interdits dans Git : mots de passe, tokens IBKR/Cloudflare/IA, API keys, URLs secrètes, identifiants de compte, cookies, payloads et captures réelles.

Vertex ne contient aucune capacité d'ordre et ne doit jamais lire compte, positions, P&L, ordres ou exécutions IBKR. Toute découverte d'un tel chemin est critique et bloque la release.

