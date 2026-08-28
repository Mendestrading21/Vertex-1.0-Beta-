# Checklist de release candidate

Une case non prouvée impose `NO-GO`.

- [ ] Les LOT-00 à LOT-23 sont fusionnés avec checks verts.
- [ ] Aucune capacité ordre/compte/position/P&L/exécution IBKR dans code, imports, routes ou permissions.
- [ ] Un seul `AdviceEngine` et aucun verdict frontend/IA/Pine concurrent.
- [ ] Aucun verdict qualifié avec entrée requise absente, partielle, périmée, retardée ou contradictoire.
- [ ] Les 12 pages passent E2E, accessibilité et budgets de performance à 1280×800, 1440×900 et 1600×1000.
- [ ] Les 12 pages restent utilisables en dégradation laptop à 1024×768, sans masquer vérité financière, provenance, alerte ou action essentielle.
- [ ] Le téléphone sert uniquement à Claude Remote Control : aucune UI/API Vertex et aucun Tailscale Serve/Funnel ne sont exposés pour la Beta.
- [ ] Déconnexion/reconnexion IBKR, pacing et redémarrage TWS testés.
- [ ] Duplications, rejeu, retard, désordre et DLQ TradingView testés.
- [ ] Panne réseau, redémarrage PostgreSQL, disque faible et dérive d'horloge testés.
- [ ] IA indisponible ou invalide n'affecte jamais données, calculs ou verdict.
- [ ] Aucun secret ni vulnérabilité critique/haute non acceptée.
- [ ] Actions et images épinglées ; SBOM, provenance et signature produits.
- [ ] Sauvegarde restaurée dans une base vide et intégrité vérifiée.
- [ ] Rollback vers la dernière version saine testé.
- [ ] Alertes d'exploitation réellement reçues.
- [ ] Cinq séances de marché de soak sans corruption, fuite mémoire ou décision incohérente.
- [ ] Matrice d'entitlements IBKR/TradingView vérifiée sur la machine cible.
- [ ] Runbooks testés par une personne autre que leur auteur.
- [ ] Validation humaine finale datée et release taguée de façon immuable.
