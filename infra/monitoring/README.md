# Supervision

**Aucun service de supervision n'est déployé et aucun n'est configuré ici.**

Ce dossier existe pour dire exactement cela plutôt que de laisser croire, par
son absence, que la question a été traitée.

Ce qui existe réellement aujourd'hui :

- `GET /api/v1/health` — vivacité, sans donnée sensible ;
- `GET /api/v1/system/capabilities` — capacités déclarées croisées avec la
  dernière sonde persistée ;
- la page `/system` de l'interface, qui rend ces deux sources ;
- les compteurs du worker (`WorkerStats`), écrits dans son journal à l'arrêt.

Ce qui n'existe pas : collecte de métriques, série temporelle, tableau de bord,
alerte, trace distribuée, export OpenTelemetry, budget d'erreur. `manifests/dependencies.yaml`
prévoit `opentelemetry-sdk` et `prometheus-client` ; **aucun des deux n'est
installé ni câblé**, et ils ne figurent pas dans `uv.lock`.

Tant que ce fichier dit cela, ne présenter Vertex comme supervisé sous aucune
forme. Voir `docs/06-quality/OBSERVABILITY.md` pour la cible et
`docs/99-status/DEBT.md` pour l'écart.
