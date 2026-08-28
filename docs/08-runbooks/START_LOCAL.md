# Démarrage local cible

Ce runbook devient exécutable au LOT-24. Avant cela, ne pas inventer de commandes.

Ordre cible :

1. vérifier horloge, disque et secrets ;
2. lancer PostgreSQL/API/worker/web via Compose ;
3. appliquer uniquement les migrations approuvées ;
4. lancer l'agent IBKR natif ;
5. vérifier les probes et entitlements ;
6. activer le consommateur Queue TradingView ;
7. servir le web sur l'interface loopback de la machine locale, sans Tailscale
   Serve, Funnel, exposition LAN ou accès téléphone ;
8. ouvrir `/system` avant toute autre page.

Le statut sain exige DB, migrations, horloge, backup récent et aucune source critique périmée. TWS ou IB Gateway doit rester connecté pour les données IBKR ; TradingView Desktop peut être fermé pour les alertes serveur. Claude Remote Control peut piloter Claude Code depuis un téléphone, mais ne publie ni ne transporte l'interface Vertex.
