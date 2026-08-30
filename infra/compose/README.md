# Exécution locale par Compose

Périmètre : **machine personnelle, boucle locale uniquement**. Rien dans ce
dossier n'expose Vertex sur le LAN, par Tailscale Serve/Funnel ou vers un
téléphone — l'exposition de l'application reste `LATER`
(`.claude/rules/security.md`).

## Ce qui est ici

| Fichier | Rôle |
|---|---|
| `compose.yaml` | PostgreSQL, migrations, API, worker, web servi statiquement |
| `Dockerfile.python` | image commune API + worker, **non-root**, base épinglée par digest |
| `Dockerfile.web` | build Vite puis service statique, **non-root**, base épinglée par digest |
| `initdb/10-least-privilege-roles.sh` | crée les rôles `migrate` et `runtime`, pose propriété et droits par défaut, au premier démarrage du volume |
| `check-least-privilege.sh` | **preuve** exécutable : se connecte AVEC le rôle du runtime et tente les contournements ; tout succès est un échec |
| `.env.example` | ne déclare plus rien : le modèle unique est `.env.example` à la RACINE |

## Ce qui n'est PAS ici, et pourquoi

- **`edge-ibkr` n'est pas conteneurisé.** L'adaptateur IBKR doit joindre TWS sur
  la boucle locale de la machine hôte, en lecture seule. Le faire tourner dans
  un conteneur ajouterait une traversée réseau sans bénéfice et brouillerait la
  frontière. Il se lance sur l'hôte (`docs/08-runbooks/IBKR_SETUP.md`).
- **`ingress-tradingview` n'est pas ici.** Il s'exécute sur Cloudflare, décision
  humaine `B-03` en attente. Rien n'est déployé.
- **Aucun service de supervision n'est démarré.** Voir `infra/monitoring/`.

## Modèle de rôles PostgreSQL

`POSTGRES_USER` de l'image officielle est un **superutilisateur**, et il devient
propriétaire de tout ce que la première connexion crée. Tant que `api` et
`worker` s'en servaient, ils **possédaient** les tables append-only — donc
pouvaient exécuter `ALTER TABLE snapshots DISABLE TRIGGER
snapshots_append_only`, réécrire l'historique, puis `DROP TRIGGER`. Les
déclencheurs de `0001`/`0003`/`0006` étaient auto-contournables par le rôle qui
sert les requêtes ; leur promesse « holds for every SQL client » ne tenait
contre **aucun** client du runtime.

| Rôle | Variable | Possède | Utilisé par |
|---|---|---|---|
| `vertex_admin` | `VERTEX_DB_SUPERUSER` | la base | l'amorçage seul, une fois |
| `vertex_migrate` | `VERTEX_DB_MIGRATE_USER` | schéma `public` et toutes les tables | le service `migrate` (Alembic) |
| `vertex_api` | `VERTEX_DB_RUNTIME_USER` | **rien** | `api` et `worker` |

Le rôle de runtime a `SELECT`/`INSERT` partout, `UPDATE`/`DELETE` seulement sur
les tables mutables, et **aucun** `UPDATE`/`DELETE`/`TRUNCATE` sur les quatre
tables append-only. Il n'a pas `CREATE` sur `public`, ne peut pas changer de
propriétaire, ni poser `session_replication_role`.

`api` et `worker` **partagent** ce rôle : leur besoin est le même. Les séparer
en deux rôles (l'API sans écriture sur `outbox`, par exemple) serait un
resserrement de plus — il n'est **pas** fait aujourd'hui.

Provisionnement : `initdb/10-least-privilege-roles.sh` au premier démarrage,
puis la migration `0007_least_privilege_grants` pour les droits table par table.
La migration ne peut rien resserrer sur une base à rôle unique : elle émet alors
un `NOTICE` et ne fait rien. **Un NOTICE n'est pas une preuve** — la preuve est
`check-least-privilege.sh`, qui échoue avec le code 1 sur une base non protégée.

## Invariants tenus par ces fichiers

- toutes les images sont épinglées par **digest immuable**, jamais par tag seul,
  jamais `latest` ;
- les services applicatifs (`api`, `worker`, `web`) tournent en **utilisateur
  non privilégié** (`USER 10001` / `USER 65532` dans leurs Dockerfiles) ;
- **exception assumée et écrite** : le service `db` démarre en root, parce que
  l'entrypoint officiel de l'image PostgreSQL en a besoin pour préparer son
  volume avant de dégrader le serveur vers l'utilisateur `postgres`. Il tourne
  avec `cap_drop: ALL` et seulement les cinq capacités que cette préparation
  exige ;
- les ports ne sont publiés que sur `127.0.0.1` : rien n'écoute sur `0.0.0.0` ;
- aucun secret n'est écrit dans un fichier suivi par Git ; `compose.yaml` ne
  lit que des variables d'environnement, et démarre en échec si l'une manque ;
- le rôle qui **sert les requêtes** ne possède aucune table et ne peut pas
  désactiver un déclencheur append-only ;
- le `healthcheck` de `db` exécute une **vraie requête** et exige que le rôle de
  runtime existe. `pg_isready` répondait « accepting connections » sans
  authentifier ni interroger quoi que ce soit : il déclarait sain un serveur
  dont le provisionnement des rôles avait échoué ;
- le système de fichiers des conteneurs applicatifs est **en lecture seule**,
  avec un `tmpfs` explicite pour ce qui doit être écrit.

## Statut de preuve

**Ce qui est prouvé.** `initdb/10-least-privilege-roles.sh`,
`check-least-privilege.sh` et la migration `0007_least_privilege_grants` ont été
exécutés contre un PostgreSQL réel, sur des bases jetables détruites ensuite :
provisionnement idempotent (deux passes), refus sur rôle de runtime confondu
avec le superutilisateur, refus sur mot de passe d'exemple, et les neuf
tentatives de contournement (`DISABLE TRIGGER`, `DROP TRIGGER`, `OWNER TO`,
`TRUNCATE`, `UPDATE`, `session_replication_role`, `CREATE TABLE`,
`DROP FUNCTION`, `CREATE` sur `public`) toutes refusées.

**Ce qui ne l'est PAS.** `compose.yaml` lui-même n'a **jamais été exécuté** :
cet environnement n'a pas de démon Docker. Ne sont donc pas prouvés — le
montage `./initdb` dans le conteneur, l'exécution du script par l'entrypoint
officiel de l'image `postgres:18`, le `healthcheck` tel qu'écrit en YAML,
l'ordonnancement `db → migrate → api/worker`, et le comportement du modèle de
rôles sur PostgreSQL **18** (les preuves ci-dessus sont sur PostgreSQL 16).
La preuve d'exécution appartient au LOT-24 (installation sur la machine cible).
Ne pas présenter ce dossier comme un déploiement vérifié.
