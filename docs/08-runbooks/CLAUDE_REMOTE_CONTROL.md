# Piloter Claude Code depuis le téléphone

## Choix retenu

Utiliser **Claude Code Remote Control**. La session Claude continue à tourner sur l'ordinateur Vertex : fichiers, terminal, outils locaux et futur environnement TWS restent sur cette machine. Le téléphone est uniquement la fenêtre de pilotage.

Documentation officielle : https://code.claude.com/docs/en/remote-control

Une session Claude Code cloud convient pour un travail GitHub sans dépendance locale, mais elle ne doit pas être utilisée pour prétendre tester TWS, IB Gateway, les droits IBKR ou le réseau local.

## Démarrage sur l'ordinateur

Depuis la racine du nouveau dépôt, après connexion Claude via l'abonnement :

```powershell
claude --remote-control "Vertex One"
```

Dans une session déjà ouverte, utiliser `/remote-control`. Ouvrir ensuite l'URL ou scanner le QR code dans l'application Claude, onglet Code.

Remote Control exige que l'ordinateur reste allumé et que la session locale fonctionne. Sur Team/Enterprise, l'administrateur peut devoir activer la fonction. L'authentification par clé API seule n'est pas prise en charge d'après la documentation actuelle ; le LOT-01 revérifie ces conditions.

## Séquence de travail

1. Démarrer sur ordinateur et vérifier le dossier courant.
2. Activer le mode Plan.
3. Envoyer le prompt top-level puis `.claude/prompts/00-master-plan.md`.
4. Depuis le téléphone, utiliser `STATUT`, `PLAN LOT NN`, `EXÉCUTE LOT NN`, `AUDITE LOT NN`, `CORRIGE LOT NN`, `PAUSE` et `REPRENDS`.
5. Lire les demandes de permission : ne jamais approuver globalement, publier, fusionner, déployer ou toucher un service externe par habitude.
6. Pour les probes IBKR, être physiquement ou via une session sécurisée capable de voir TWS en paper/read-only ; ne jamais supposer son état depuis le téléphone.

## Garde-fous

- aucun port TWS, PostgreSQL ou API Vertex ouvert pour piloter Claude ; Remote Control utilise son canal officiel sortant ;
- ne pas partager l'URL/QR de session ; révoquer un appareil perdu ;
- écran verrouillé, chiffrement disque et session OS dédiée ;
- `STOP` en cas de doute, puis inspection locale de Git et `NOW.md` ;
- aucun auto-approve pour shell, réseau, GitHub, Cloudflare, migrations ou secrets ;
- le téléphone ne donne jamais une autorisation implicite de push, PR, merge ou déploiement.

## Si la connexion tombe

La session locale peut continuer ou se reconnecter. Après retour, envoyer `REPRENDS` : Claude compare Git et `NOW.md` avant toute écriture. Ne relancer pas une commande interrompue sans savoir si elle a eu un effet.

