# Réponse aux incidents

## Priorités

1. Bloquer toute nouvelle décision.
2. Préserver preuves et dernier état sain.
3. Isoler le connecteur ou service concerné.
4. Révoquer les secrets si nécessaire.
5. Restaurer/tester avant reprise.
6. Documenter cause, portée, données affectées et prévention.

## Runbooks obligatoires avant release

- TWS/IBKR hors ligne ou pacing ;
- données périmées/contradictoires ;
- webhook forgé ou secret divulgué ;
- Queue/DLQ bloquée ;
- dépendance compromise ;
- fuite de secret ;
- migration interrompue ;
- disque presque plein ;
- perte/corruption PostgreSQL ;
- IA indisponible ou injectée ;
- téléphone perdu ;
- rollback vers dernière release saine.

La désactivation de l'IA et de l'ingress externe doit être possible sans arrêter consultation, portefeuille manuel ou données historiques.

