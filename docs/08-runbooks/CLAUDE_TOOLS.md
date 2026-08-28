# Outils et skills Claude autorisés

## Principe

Le meilleur outil est celui dont le mandat est étroit et vérifiable. Vertex n'installe pas une collection de skills de trading : ils pourraient réintroduire une autorité parallèle, du scraping, des secrets ou des fonctions d'ordre.

## Socle

- Claude Code officiel, mode Plan puis un lot à la fois : https://code.claude.com/docs/en/overview
- Remote Control officiel pour le téléphone : https://code.claude.com/docs/en/remote-control
- GitHub CLI officiel pour branches et PR, après authentification minimale : https://cli.github.com/
- dépôt GitHub privé, ruleset et validations humaines ;
- prompts versionnés dans `.claude/prompts/` et règles dans `.claude/rules/`.

## Plugin GitHub facultatif

Claude Code publie un marketplace officiel et documente un plugin GitHub officiel. Le LOT-01 peut proposer son installation après vérification des permissions et de la version :

```text
/plugin install github@claude-plugins-official
```

Documentation : https://code.claude.com/docs/en/discover-plugins

Le plugin ne donne pas le droit de push, ouvrir/fusionner une PR, modifier un ruleset ou publier sans commande humaine distincte. `gh` seul suffit si le plugin n'est pas nécessaire.

## Skills internes Vertex

Ne pas créer un skill métier avant que les lots aient stabilisé les contrats. Les règles et prompts fournis couvrent déjà : plan, exécution, audit, correction, PR, statut téléphone et reprise.

Un futur skill interne doit être :

- versionné dans le dépôt ;
- sans secret ni URL personnelle ;
- borné à un cas d'usage ;
- incapable de contourner `CLAUDE.md`, les ADR et `forbidden-capabilities.yaml` ;
- évalué sur des cas normaux et adversariaux ;
- approuvé par une PR humaine.

## Interdictions

- plugin, MCP ou skill communautaire « trading bot », IBKR orders, portfolio sync ou scraper TradingView ;
- installation directe depuis une branche, un gist ou un script inconnu ;
- skill capable de déployer, merger ou modifier des secrets sans confirmation ;
- serveur MCP IBKR exposant plus que l'interface information-only définie par Vertex ;
- partage d'un token GitHub, IBKR, TradingView ou Cloudflare dans le prompt.

Chaque outil externe suit : provenance officielle, licence, permissions, version/hash, revue du code, test dans un environnement sans secrets puis inscription au registre des dépendances.

