# Prompt — exécuter un dossier

Reçois `DOSSIER_ID`. Lis le skill, le programme dossier par dossier, le lot
propriétaire, la matrice donneur et `NOW.md`.

En mode Plan :

1. prouve que le cwd est `Vertex-1.0-Beta-` et le donneur est read-only ;
2. borne la capacité et ses non-objectifs ;
3. lance les auditeurs spécialisés en lecture seule ;
4. classe chaque module donneur `KEEP/ADAPT/REWRITE/REFERENCE/DROP` ;
5. écris le contrat cible et les tests qui doivent naître rouges ;
6. liste fichiers exacts, dépendances, migration, benchmark et rollback ;
7. vérifie qu'aucun autre dossier n'est actif ;
8. termine par `EXÉCUTE DOSSIER NN` ou une commande de déblocage unique.

En exécution, applique uniquement le plan accepté. Crée des fichiers de
production complets : aucun pseudo-code, `TODO`, écran factice, calcul navigateur,
mock présenté comme réel ou test annoncé sans exécution. Si une dépendance
externe n'est pas disponible, livre l'interface, le faux déterministe strictement
étiqueté fixture, les tests et l'état `NOT_ENTITLED`/`UNAVAILABLE` plutôt que de
simuler une réussite. N'ouvre jamais le dossier suivant automatiquement.
