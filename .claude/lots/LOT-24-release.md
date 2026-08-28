# LOT-24 — Installation et release candidate

## Références et dépendances

- Dépendance bloquante : LOT-23 fusionné avec qualification indépendante `GO`.
- Références obligatoires : `docs/07-delivery/checklists/RELEASE.md`, `docs/07-delivery/DEFINITION_OF_DONE.md`, `docs/08-runbooks/FIRST_INSTALL.md`, `docs/08-runbooks/CLAUDE_REMOTE_CONTROL.md`, `docs/08-runbooks/START_LOCAL.md`, `docs/08-runbooks/IBKR_SETUP.md`, `docs/08-runbooks/TRADINGVIEW_SETUP.md`, `docs/08-runbooks/BACKUP_RESTORE.md`, `docs/08-runbooks/INCIDENT.md` et `docs/06-quality/OBSERVABILITY.md`.

## Objectif

Installer la release candidate sur la machine cible, démontrer restauration et rollback, puis observer cinq séances de marché complètes sans corruption ni dérive avant une décision humaine GO/NO-GO.

La release candidate Vertex 1.0 Beta est **DESKTOP ONLY**. Elle reprend les
preuves `1280×800`, `1440×900` et `1600×1000` du LOT-23 ; `1024×768` reste une
dégradation laptop optionnelle. `Mobile UI = LATER` et ne bloque pas le GO.

## Non-objectifs

- ajouter ou corriger discrètement une fonctionnalité pendant le soak ;
- activer ordre, compte, positions, P&L ou exécutions IBKR ;
- exposer TWS ou l’API locale à Internet ;
- livrer l'interface produit sur téléphone ou l'exposer par Tailscale Serve ;
- déclarer GO sur absence d’incident sans preuve de télémétrie ;
- fusionner, taguer ou publier automatiquement.

## Livrables attendus

1. Installation reproductible depuis une machine propre avec versions, digests, prérequis, temps total et résultat de chaque smoke test.
2. Configuration TWS paper/read-only sur loopback et matrice réelle des entitlements IBKR/TradingView, sans identifiant de compte enregistré.
3. Accès applicatif local vérifié depuis le poste desktop, avec WebAuthn/passkey et
   preuve qu'aucun port local n'est publiquement exposé. L'accès produit par
   Tailscale Serve est `LATER`. Remote Control officiel peut piloter Claude Code
   depuis un téléphone, mais n'est ni une UI Vertex ni une voie vers l'application.
4. Sauvegarde chiffrée puis restauration dans une base PostgreSQL vide ; comptages, hashes, contraintes, outbox et échantillons synthétiques vérifiés.
5. Rollback complet de l’application et de chaque migration compatible vers la dernière version saine, puis redémarrage et smoke tests.
6. Runbooks exécutés par une personne autre que leur auteur : démarrage, arrêt, incident IBKR, incident TradingView, panne PostgreSQL, sauvegarde, restauration et rollback.
7. Journal de soak couvrant cinq séances de marché complètes, avec ouverture/fermeture, reconnexion, événements, options, mémoire, CPU, stockage, files, fraîcheur et cohérence des verdicts.
8. Dossier final GO/NO-GO, liste de risques, preuves immuables, SBOM/provenance/signature et proposition de tag.

## Protocole de sauvegarde, restauration et rollback

- Produire une sauvegarde avant installation et avant migration ; vérifier chiffrement, rétention et accès minimal.
- Restaurer dans une base vide isolée, jamais par-dessus la base cible, puis exécuter contrôles d’intégrité et tests applicatifs.
- Tester le rollback binaire et base avec artefacts épinglés ; aucun téléchargement `latest` ni reconstruction différente.
- Mesurer RPO/RTO obtenus et les comparer aux objectifs documentés.
- En cas d’échec, corruption ou migration irréversible non acceptée : interrompre, revenir à la version saine et conclure `NO-GO`.

## Protocole de soak — cinq séances

Chaque séance est complète et consécutive selon le calendrier de marché cible. Un jour incomplet ne compte pas.

- Capturer au début et à la fin : versions, uptime, CPU, mémoire, disque, connexions, backlog outbox/queues, DLQ, erreurs, latence, fraîcheur et entitlements.
- Échantillonner des actions, ETF et options autorisées ; vérifier identité exacte, doublons, événements/news et type live/delayed.
- Rejouer au moins une reconnexion TWS contrôlée et une indisponibilité d’une source sans produire de verdict fail-open.
- Vérifier quotidiennement absence de fuite mémoire, croissance non bornée, corruption, perte silencieuse, décision incohérente et donnée démo présentée comme réelle.
- Toute correction redémarre la qualification affectée et, si elle touche runtime, données, sécurité ou décision, remet le compteur de cinq séances à zéro.

## Conditions GO

Toutes les conditions sont cumulatives :

- checklist `RELEASE.md` entièrement prouvée et signée par un humain ;
- cinq séances valides sans incident bloquant ni dérive non expliquée ;
- restauration et rollback réussis sur les artefacts exacts ;
- zéro capacité IBKR interdite, secret, vulnérabilité critique/haute exploitable ou exposition publique non prévue ;
- alertes d’exploitation reçues, runbooks indépendamment testés et risques résiduels explicitement acceptés ;
- artefact, SBOM, provenance, signature, commit et tag proposé concordent ;
- les trois viewports desktop sont prouvés ; aucune capture ou QA `390`/`360`
  n'est requise pour cette Beta.

## Conditions NO-GO

Une seule des situations suivantes suffit : preuve absente, test rouge/flaky/ignoré, écart WCAG ou performance non accepté, corruption ou perte, fuite mémoire, verdict fail-open, donnée fictive présentée comme réelle, droit incertain, sauvegarde/restauration/rollback non démontré, capacité interdite, secret, vulnérabilité bloquante ou validation humaine manquante.

## Critères de sortie

- Produire un procès-verbal daté `GO` ou `NO-GO` avec signataire humain, commit et digests exacts.
- En `GO`, créer le tag immuable uniquement après instruction humaine explicite ; aucune publication automatique.
- En `NO-GO`, consigner le blocage, restaurer l’état sain, ouvrir un lot correctif explicite et ne pas publier.
- Mettre `docs/99-status/NOW.md` et `HISTORY.md` à jour sans lancer de travail suivant.
