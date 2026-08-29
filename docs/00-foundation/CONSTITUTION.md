# Constitution de Vertex One

Ces règles priment sur le backlog, les prompts et l'implémentation.

1. Vertex est un outil d'aide à l'analyse, jamais un système d'exécution.
2. Le portefeuille est saisi et tenu manuellement.
3. Toute donnée possède une source, une heure d'observation, une heure de réception, une unité, une qualité et une règle de fraîcheur.
4. Une donnée absente, périmée, future, retardée, partielle ou contradictoire réduit la confiance ou bloque le résultat.
5. Les portes de sécurité sont déterministes, versionnées et fail-closed.
6. Un seul `AdviceResult` constitue le verdict canonique.
7. Les calculs financiers vivent exclusivement dans le cœur Python et sont testés par invariants et oracles indépendants.
8. L'interface et l'IA ne peuvent modifier prix, calcul, porte, probabilité ou verdict.
9. Réel, retardé, estimé, simulé, théorique, historique et démonstration sont toujours séparés visuellement et dans les contrats.
10. Une page répond à une question principale et possède un visuel dominant.
11. Les mêmes contrats alimentent API, interface, tests et documentation.
12. Recherche et backtest sont séparés en lecture seule du runtime de décision.
13. Aucune dépendance n'entre sans provenance, licence, version, hash et responsable.
14. Aucun pourcentage prédictif n'est présenté sans protocole de calibration et validation hors échantillon.
15. Accessibilité, sécurité, observabilité, sauvegarde et comportement dégradé font partie du produit dès le premier lot.
16. Le Vertex actuel est un donneur en lecture seule ; seuls les éléments
    inventoriés `KEEP` ou `ADAPT` peuvent migrer, et aucun import runtime ne le
    relie au nouveau dépôt.
17. Toute donnée ou fonctionnalité incertaine est explicitement absente, jamais simulée en silence.
18. Une sauvegarde n'existe qu'après une restauration vérifiée.
