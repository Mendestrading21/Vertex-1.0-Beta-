# Exécution locale par Compose

Périmètre : **machine personnelle, boucle locale uniquement**. Rien dans ce
dossier n'expose Vertex sur le LAN, par Tailscale Serve/Funnel ou vers un
téléphone — l'exposition de l'application reste `LATER`
(`.claude/rules/security.md`).

## Ce qui est ici

| Fichier | Rôle |
|---|---|
| `compose.yaml` | PostgreSQL, API, worker, web servi statiquement |
| `Dockerfile.python` | image commune API + worker, **non-root**, base épinglée par digest |
| `Dockerfile.web` | build Vite puis service statique, **non-root**, base épinglée par digest |
| `.env.example` | noms de variables seulement, aucune valeur réelle |

## Ce qui n'est PAS ici, et pourquoi

- **`edge-ibkr` n'est pas conteneurisé.** L'adaptateur IBKR doit joindre TWS sur
  la boucle locale de la machine hôte, en lecture seule. Le faire tourner dans
  un conteneur ajouterait une traversée réseau sans bénéfice et brouillerait la
  frontière. Il se lance sur l'hôte (`docs/08-runbooks/IBKR_SETUP.md`).
- **`ingress-tradingview` n'est pas ici.** Il s'exécute sur Cloudflare, décision
  humaine `B-03` en attente. Rien n'est déployé.
- **Aucun service de supervision n'est démarré.** Voir `infra/monitoring/`.

## Invariants tenus par ces fichiers

- toutes les images sont épinglées par **digest immuable**, jamais par tag seul,
  jamais `latest` ;
- tous les services tournent en **utilisateur non privilégié** ;
- les ports ne sont publiés que sur `127.0.0.1` : rien n'écoute sur `0.0.0.0` ;
- aucun secret n'est écrit dans un fichier suivi par Git ; `compose.yaml` ne
  lit que des variables d'environnement, et démarre en échec si l'une manque ;
- le système de fichiers des conteneurs applicatifs est **en lecture seule**,
  avec un `tmpfs` explicite pour ce qui doit être écrit.

## Statut de preuve

Ces fichiers n'ont **jamais été exécutés** : cet environnement de travail n'a
pas de démon Docker. Ils sont écrits, relus et validés syntaxiquement, pas
prouvés. La preuve d'exécution appartient au LOT-24 (installation sur la
machine cible). Ne pas présenter ce dossier comme un déploiement vérifié.
