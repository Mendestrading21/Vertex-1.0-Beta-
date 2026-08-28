# Modèle de menace résumé

| Menace | Contrôle principal | Preuve attendue |
|---|---|---|
| Ordre IBKR accidentel | TWS read-only + API étroite + denylist statique | test échoue sur toute méthode interdite |
| Lecture de compte/positions | aucun appel ni contrat correspondant | recherche de capacités en CI |
| Port TWS exposé | loopback et pare-feu | scan LAN externe |
| Webhook forgé/rejoué | Worker, allowlist, capacité secrète, registre, timestamp, clé de déduplication et schéma | tests négatifs |
| Message perdu/dupliqué | Queue, DLQ, idempotence, commit avant ack | tests de panne DB |
| Donnée périmée présentée live | TTL par usage, epoch de connexion, gate | scénario 1100/1101/1102 |
| Droit API absent | `SourceEntitlement` et couverture visible | matrice Système |
| Scraping contraire aux CGU | seuls API/export officiels | revue adaptateurs |
| Dépendance compromise | locks, SHA/digest, SBOM, scans | artefacts de release |
| Secret dans Git/logs | secret scanning et redaction | CI + tests de logs |
| IA trompeuse | contexte typé, citations, aucun outil d'écriture | tests de refus |
| Runner GitHub compromis | aucun runner non fiable sur machine TWS | politique GitHub |
| Perte locale | sauvegardes 3-2-1 et restauration | rapport mensuel |
| Téléphone volé | session Claude Remote Control révocable, verrouillage appareil et session courte ; aucune UI Vertex sur le téléphone | runbook de révocation |
