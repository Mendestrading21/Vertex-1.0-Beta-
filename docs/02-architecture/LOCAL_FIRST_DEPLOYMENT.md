# Déploiement local-first

## Machine principale

Le PC où TWS ou IB Gateway est ouvert exécute :

- `edge-ibkr` nativement sous un compte OS dédié ;
- `api`, `worker`, `web` et PostgreSQL dans des services locaux reproductibles ;
- PWA/API accessibles uniquement au navigateur desktop local ;
- sauvegarde chiffrée et supervision locale.

TWS écoute uniquement sur `127.0.0.1`. PostgreSQL n'expose aucun port hors réseau interne. Aucun runner GitHub déclenché par une PR non fiable ne s'exécute sur cette machine.

## Composant public minimal

Seul `ingress-tradingview` est public. Il valide et met en file ; il ne connaît ni TWS, ni PostgreSQL, ni portefeuille, ni moteur de décision. L'edge local récupère les messages en HTTPS sortant. Une panne Cloudflare ne rend pas le cœur public et ne transforme pas une alerte perdue en verdict.

## Téléphone et accès distant

Pendant la Beta Vertex 1.0, le téléphone sert uniquement à Claude Remote Control. Il n'accède ni à la PWA ni à l'API Vertex et ne rejoint aucune frontière d'authentification Vertex. Tailscale Serve et Funnel ne sont pas déployés pour Vertex. L'interface mobile reste `LATER` et devra réutiliser les contrats canoniques si elle est décidée.

## Processus et ordre de démarrage

1. horloge système synchronisée ;
2. PostgreSQL sain et migrations compatibles ;
3. API puis worker ;
4. TWS/IB Gateway en mode paper et read-only ;
5. edge IBKR ;
6. PWA desktop locale ;
7. consommation TradingView après validation de santé.

Chaque étape peut être `DEGRADED` sans être maquillées en `HEALTHY`. Le démarrage ne produit aucun conseil qualifié tant qu'une observation post-connexion et les portes nécessaires ne sont pas validées.

## Données locales

Les données personnelles et exports restent hors Git, chiffrés au repos et séparés des fixtures. Les sauvegardes comprennent base, configuration non secrète et métadonnées de version ; les secrets sont restaurés par une procédure séparée.
