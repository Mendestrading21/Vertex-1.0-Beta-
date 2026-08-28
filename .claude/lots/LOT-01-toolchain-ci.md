# LOT-01 — Toolchain, dépôt et CI

## Dépendances et préconditions

- Dépendance bloquante : LOT-00 fusionné après validation humaine.
- Branche d'exécution : `lot/01-toolchain-ci` depuis le commit sain enregistré par LOT-00.
- Préconditions : dépôt privé, Constitution acceptée, inventaire de migration validé, aucun secret ni code ancien suivi.
- ADR applicables : ADR-001, ADR-002, ADR-009, ADR-010 et ADR-012.

Si une version, une licence, une action GitHub ou une capacité de sécurité ne peut être vérifiée depuis sa source officielle, elle n'est pas ajoutée. Toute nouvelle brique non inscrite dans le registre exige un ADR avant installation.

## Objectif

Créer le squelette reproductible du monorepo, verrouiller les toolchains et dépendances initiales, puis installer une CI minimale mais bloquante. Un checkout propre doit pouvoir installer, contrôler, tester et construire les squelettes sans accès aux comptes IBKR ou TradingView.

La preuve principale attendue par la feuille de route est : versions verrouillées, CI minimale verte et protections de dépôt documentées.

## Non-objectifs

- implémenter contrats métier, schéma PostgreSQL, outbox, calcul financier, API fonctionnelle ou interface produit ;
- connecter IBKR, TradingView, Cloudflare, Tailscale, une IA ou une source de
  données ; l'accès applicatif par Tailscale reste `LATER` et Remote Control sur
  téléphone concerne uniquement le pilotage de Claude Code ;
- créer un workflow de déploiement ou publier une image/release ;
- utiliser Redis, Celery, TimescaleDB, Kubernetes, GraphQL, Next.js ou un wrapper desktop ;
- ajouter un runner auto-hébergé, surtout sur la machine TWS ;
- rendre une action GitHub ou une règle de branche effective sans autorisation humaine explicite.

## Lecture obligatoire

1. `CLAUDE.md` et `docs/00-foundation/CONSTITUTION.md` ;
2. `docs/99-status/NOW.md`, `HISTORY.md` et `BLOCKERS.md` ;
3. `docs/02-architecture/REPOSITORY_MAP.md`, `MODULE_BOUNDARIES.md` et `THREAT_MODEL.md` ;
4. `docs/04-integrations/DEPENDENCY_REGISTER.md` et `manifests/dependencies.yaml` ;
5. `docs/06-quality/CI_GATES.md`, `TEST_STRATEGY.md` et `SECURITY_CONTROLS.md` ;
6. `docs/07-delivery/MASTER_ROADMAP.md`, `DEPENDENCY_MATRIX.md` et `DEFINITION_OF_DONE.md` ;
7. `docs/09-adr/001-modular-monolith.md`, `002-local-first.md`, `009-security-network.md`, `010-testing.md` et `012-migration-policy.md` ;
8. `SECURITY.md`, `CONTRIBUTING.md`, `.env.example` et les checklists `BEFORE_LOT.md` / `BEFORE_PR.md`.

## Livrables

1. Arborescence conforme à `REPOSITORY_MAP.md`, avec frontières visibles entre applications, packages Python/TypeScript, contrats, recherche, infra, fixtures et tests ; uniquement des squelettes exécutables ou importables.
2. Toolchain Python 3.13 gérée par `uv`, workspace et `uv.lock` exact ; compatibilité Python 3.14 testée sans en faire le runtime de production.
3. Toolchain Node 24 LTS, `pnpm` épinglé, workspace, TypeScript strict, Biome, Vitest et lockfile exact.
4. PostgreSQL 18 référencé par digest immuable pour les tests futurs ; aucun schéma métier dans ce lot.
5. Versions, hashes, licences, provenance et propriétaire de chaque dépendance initiale réconciliés entre manifests, lockfiles et notices tierces.
6. Commandes uniques et documentées pour bootstrap, format, lint, types, tests, build, vérification de politique et nettoyage des seuls artefacts générés.
7. CI de PR avec permissions minimales, timeouts, concurrence contrôlée, caches non sensibles et Actions épinglées à des SHA complets.
8. Contrôles initiaux : policy, qualité Python, qualité web, tests smoke, build, secrets, dépendances/licences et cohérence des lockfiles.
9. Configuration GitHub proposée : PR obligatoire, squash, branche à jour, conversations résolues, CODEOWNERS, interdiction force-push/suppression et contrôles requis. Une exportation ou capture expurgée prouve l'état réellement appliqué.
10. Documentation de bootstrap pour Linux/CI et poste Windows de marché, sans installer ni démarrer TWS dans la CI.

## Étapes d'exécution

1. Vérifier la preuve de LOT-00, le commit de base et l'état Git ; passer `NOW.md` à `running`.
2. Résoudre les versions exactes depuis les registres ou documentations officielles, vérifier licence et provenance, puis mettre à jour le registre avant installation.
3. Créer le squelette minimal du monorepo selon ADR-001 ; aucun import transversal interdit et aucun placeholder ne doit prétendre fournir une fonction métier.
4. Configurer le workspace Python, les groupes de dépendances et les contrôles Ruff, mypy strict et pytest ; générer un lockfile reproductible.
5. Configurer le workspace JavaScript, TypeScript strict, Biome, Vitest et builds minimaux ; générer un lockfile reproductible avec versions exactes.
6. Ajouter les contrôles de politique automatisés : locks présents et inchangés, aucune version `latest`, aucun tag mutable d'image, Actions sur SHA de 40 caractères et capacités interdites absentes.
7. Ajouter les workflows de PR par jobs minimaux. Définir `permissions: read-all` par défaut et n'élever que le job qui le justifie ; interdire `pull_request_target` avec code non fiable.
8. Ajouter les scans disponibles et licenciés : Gitleaks CLI, audit Python, OSV, CodeQL/dependency review si le plan GitHub les permet. Un outil indisponible devient une limite documentée, pas un succès.
9. Tester depuis un checkout propre et sans fichier d'environnement secret : installation verrouillée, lint, types, tests, builds et scans.
10. Vérifier la configuration GitHub en lecture seule ou préparer les réglages exacts. Toute mutation distante nécessite une commande humaine distincte.
11. Mettre à jour notices, runbook d'installation, `NOW.md`, `HISTORY.md` et `BLOCKERS.md`, puis produire la preuve sans commencer LOT-02.

## Tests et contrôles obligatoires

### Reproductibilité

- installation Python avec verrou strict depuis un cache vide, puis contrôle qu'aucun lockfile ne change ;
- installation pnpm avec lockfile gelé depuis un cache vide, puis contrôle qu'aucun lockfile ne change ;
- seconde installation identique donnant les mêmes versions résolues ;
- build et tests smoke sur checkout propre, sans `.env` réel et sans réseau applicatif.

### Qualité et architecture

- Ruff format/check, mypy strict et pytest sur tous les squelettes Python ;
- Biome check, `tsc --noEmit`, Vitest et build sur tous les workspaces TypeScript ;
- test d'architecture empêchant au minimum le domaine d'importer FastAPI, SQLAlchemy, IBKR, Cloudflare ou React ;
- détection de cycles de workspace et d'import interdit selon `MODULE_BOUNDARIES.md`.

### Politique et supply chain

- chaque Action référence un SHA complet, une permission et un timeout ;
- chaque image référence un digest immuable ; chaque package direct a version exacte, licence et source ;
- absence de `latest`, dépendance git flottante, archive vendored ou dépôt tiers copié ;
- Gitleaks et audits de vulnérabilités/licences sans constat critique/haut non traité ;
- génération d'un SBOM minimal ou, si l'outil complet est réservé à la release, preuve que la commande et le format retenus fonctionnent sur le squelette.

### Matrice CI minimale

- Python 3.13 obligatoire ; Python 3.14 en job de compatibilité autorisé à échouer uniquement avec blocage documenté et échéance ;
- Node 24 LTS obligatoire ;
- environnement GitHub hébergé uniquement ; aucun label de runner TWS ou local ;
- annulation des exécutions obsolètes, timeouts et logs sans variables sensibles.

## Sécurité et garde-fous

- Aucun secret n'est nécessaire au bootstrap ou à une PR provenant du dépôt ; les exemples utilisent des valeurs manifestement factices.
- Les permissions des workflows sont minimales ; aucune écriture de contenu, package, issue ou id-token n'est accordée sans job et justification dédiés.
- Aucun script de PR ne s'exécute sur l'ordinateur TWS et aucun port IBKR n'est ouvert par les tests.
- Les caches n'embarquent ni `.env`, ni credentials, ni payloads ; leurs clés incluent les lockfiles.
- Les scripts d'installation ne téléchargent aucun binaire non vérifié par checksum, signature ou gestionnaire officiel.
- Les Actions tierces, images et outils sont évalués avant pin ; Trivy reste différé conformément au registre tant que sa décision de sécurité n'est pas révisée.
- Une vulnérabilité acceptée exige propriétaire, justification, contrôle compensatoire et date d'expiration ; sinon le lot est bloqué.
- La configuration GitHub et les captures de preuve sont expurgées des noms d'utilisateurs, tokens et URLs sensibles inutiles.

## Critères de sortie mesurables

- Un checkout propre exécute bootstrap, lint, types, tests smoke et builds avec les lockfiles gelés, sans modification Git résiduelle.
- 100 % des dépendances directes ont version exacte, provenance, licence et propriétaire ; 0 dépendance non inventoriée.
- 100 % des Actions sont épinglées sur 40 caractères hexadécimaux ; 0 image `latest` ou tag mutable.
- CI requise verte sur Python 3.13 et Node 24 ; chaque job a permissions et timeout explicites.
- 0 runner auto-hébergé ou capacité de déploiement dans les workflows de PR.
- 0 vulnérabilité critique/haute exploitable, secret, archive tierce ou code ancien suivi.
- Arborescence conforme à `REPOSITORY_MAP.md` et test d'architecture initial vert.
- Protections GitHub réellement appliquées et prouvées, ou état final `review/blocked` si une action humaine reste nécessaire ; aucune protection n'est déclarée active sur la seule base d'un fichier.
- Documentation bootstrap reproduite sur au moins un environnement propre et `NOW.md` exact.

## Format de preuve de fin de lot

```text
LOT : 01 — Toolchain, dépôt et CI
ÉTAT : done | review | blocked
BRANCHE / COMMIT : lot/01-toolchain-ci / <sha>
DÉPENDANCE : LOT-00 <sha fusionné + preuve>
RUNTIMES : Python <exact> ; Node <exact> ; pnpm <exact> ; PostgreSQL <digest>
LOCKS : uv.lock <hash> ; pnpm-lock.yaml <hash> ; diff après install <propre/non propre>
CI : <URL/ID expurgé> ; <jobs verts/total> ; protections <prouvées/non prouvées>
TESTS : <commande exacte> → <exit code, durée, résumé>, une ligne par gate
SUPPLY CHAIN : actions SHA <n/n> ; dépendances inventoriées <n/n> ; scans <résultat>
SÉCURITÉ : secrets <résultat> ; vulnérabilités bloquantes <n> ; runners locaux <n>
FICHIERS MODIFIÉS : <nombre + chemins principaux>
RISQUE RESTANT : aucun | <risque concret et échéance>
BLOCAGE : aucun | <un seul blocage actionnable>
ROLLBACK : retour au commit LOT-00 <sha> ; aucune migration de données
PROCHAINE COMMANDE : AUDITE LOT 01
```

Joindre les logs complets comme artefacts, les hashes des lockfiles, la liste des versions et une preuve expurgée des règles de branche. Une case non prouvée vaut `NO-GO`.
