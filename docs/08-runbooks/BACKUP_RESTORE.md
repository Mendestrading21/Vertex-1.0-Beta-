# Sauvegarde et restauration

## Objectifs initiaux

- RPO ≤ 5 minutes après activation WAL/PITR ;
- RTO ≤ 30 minutes ;
- rétention : 7 quotidiennes, 4 hebdomadaires, 12 mensuelles ;
- trois copies, deux supports, une hors machine ;
- chiffrement avant transfert et clé séparée.

## Développement

`pg_dump` quotidien en format custom, copie chiffrée Restic, vérification hebdomadaire et restauration mensuelle automatisée dans une base vide.

## Production personnelle

Base backup + WAL/PITR, `pg_verifybackup`, restauration à un instant précis, comparaison des hashes et lancement des tests de cohérence.

Une tâche réussie de copie ne vaut pas sauvegarde. Seule une restauration vérifiée met `last_verified_restore_at` à jour.

