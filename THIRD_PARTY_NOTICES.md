# Third-party notices

Ce fichier est généré et vérifié au LOT-01 puis à chaque release. Il doit contenir nom, version, source, licence, copyright/NOTICE, usage et hash de chaque composant distribué.

Exigences connues :

- Polars : conserver la licence MIT et l'avis de copyright de la version Python distribuée (https://github.com/pola-rs/polars).
- Apache Arrow/PyArrow : conserver `LICENSE.txt`, `NOTICE.txt` et les notices des dépendances embarquées, sous Apache-2.0 (https://github.com/apache/arrow).
- pandas, utilisé uniquement aux frontières d'interopérabilité : conserver la licence BSD-3-Clause (https://github.com/pandas-dev/pandas).
- TradingView Lightweight Charts : conserver LICENSE/NOTICE et afficher l'attribution/lien TradingView demandé par le projet.
- Apache ECharts : conserver LICENSE/NOTICE et les notices des sous-composants.
- Radix Primitives et TanStack Query/Table/Virtual : conserver leurs licences MIT.
- Lucide React : conserver la licence ISC et les avis associés ; ne pas traiter les icônes comme des logos de marque (https://github.com/lucide-icons/lucide).
- QuantLib : conserver la licence BSD et notices incluses.
- Les polices Geist Sans et Geist Mono : conserver le fichier OFL-1.1 de la
  source Vercel vérifiée (https://github.com/vercel/geist-font).
- axe-core/Hypothesis : enregistrer MPL-2.0 comme dépendances de test.

Composants de recherche, seulement s'ils sont installés dans un environnement livré : River (BSD-3-Clause), ruptures (BSD-2-Clause), arch (NCSA) et MAPIE (BSD-3-Clause). Leur présence en recherche ne les autorise pas dans le runtime de production.

Tailscale Serve, l'interface/PWA mobile et toute bibliothèque d'informatique quantique sont différés ou exclus ; ils ne font donc pas partie des composants distribués de Vertex 1.0 Beta. Claude Code Remote Control est un service d'orchestration externe, pas un composant de l'application.

Aucun contenu tiers n'est encore distribué dans le blueprint.
