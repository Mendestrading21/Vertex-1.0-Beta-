# LOT-19 — Page Suivi

## Références et dépendances

- Fiche produit obligatoire : `docs/01-product/pages/09-follow-up.md`.
- Références transversales : `docs/03-domain/CANONICAL_CONTRACTS.md`, `docs/03-domain/DATA_QUALITY.md`, `docs/03-domain/DECISION_ENGINE.md`, `docs/04-integrations/DATA_FUSION.md`, `docs/05-design/UI_STATES.md`, `docs/05-design/ACCESSIBILITY.md`, `docs/05-design/RESPONSIVE.md` et `docs/06-quality/TEST_STRATEGY.md`.
- Dépendances bloquantes : LOT-02 Contrats canoniques, LOT-03 Stockage et qualité, LOT-04 IBKR, LOT-05 TradingView, LOT-06 Data Fusion, LOT-08 Décision, LOT-09 API/jobs et LOT-10 Design shell.

Le lot ne commence qu'avec une identité instrument stable, des snapshots immuables et un mécanisme d'écriture idempotent. Une nouvelle donnée peut augmenter l'urgence d'une revue, jamais modifier automatiquement une thèse.

## Question à résoudre

Quelles thèses, alertes et informations dois-je revoir maintenant, pourquoi, et qu'est-ce qui a changé depuis ma dernière révision ?

## Objectif

Livrer `/follow-up`, une file de revues concise et traçable. La page rassemble thèses manuelles, anciens `AdviceResult`, alertes, niveaux, événements et clusters d'information, puis permet d'enregistrer une note et une décision de suivi non transactionnelle dans un historique append-only.

## Non-objectifs

- modifier une thèse, une échéance ou un statut sans action explicite de l'utilisateur ;
- transformer une alerte, une news ou un changement de score en décision d'achat ou de vente ;
- recalculer urgence, priorité, niveaux ou verdict dans le navigateur ;
- réécrire, fusionner ou supprimer une révision historique ;
- synchroniser un ordre, une position ou un identifiant de compte IBKR ;
- laisser l'IA décider de l'urgence, résoudre une contradiction ou écrire une note.

## Contrats et autorité

Entrées minimales : `Thesis`, `AdviceResult`, `NewsCluster`, `CorporateEvent`, `MacroEvent`, `TechnicalSignal`, niveaux de marché certifiés et une enveloppe de file contenant priorité, `urgency_reason`, couverture, `as_of` et preuves.

Contrats de page à exposer par OpenAPI :

- `ReviewQueueItem` : identifiant stable, type, priorité canonique, raison d'urgence, échéance, statut, instrument éventuel et références de preuve ;
- `ThesisRevision` : auteur local, date, note, décision de suivi, snapshot lié, révision précédente et hash ;
- `EvidenceTimelineEntry` : type, date métier, date de réception, source, fraîcheur, résumé factuel et lien vers l'objet immuable ;
- `FollowUpCommand` : clé d'idempotence, action allowlistée, note, échéance éventuelle et version attendue.

Les actions autorisées sont limitées à `MARK_REVIEWED`, `SNOOZE`, `UPDATE_NOTE` et `ARCHIVE`. Elles ne sont pas des décisions financières. Le serveur calcule ordre, urgence et conflits ; le client affiche et filtre seulement. Toute révision est append-only, horodatée et liée aux snapshots exacts consultés.

## Livrables desktop

1. File de revues dominante avec urgence, raison, échéance, provenance et âge sur chaque ligne.
2. Fiche de la thèse sélectionnée, sans édition implicite, avec hypothèses, invalidation, horizon et dernière révision.
3. Timeline unifiée des révisions, événements, news, signaux et niveaux, avec filtres non destructifs.
4. Module d'hygiène des watchlists et alertes signalant doublons, éléments orphelins et alertes périmées sans suppression automatique.
5. Formulaire de revue avec note, action de suivi, échéance et récapitulatif du snapshot avant validation.
6. Navigation clavier complète entre file, fiche, timeline et formulaire, avec URL restaurable sans donnée sensible.

## Périmètre Vertex 1.0 Beta

- Phase 1 **DESKTOP ONLY** : `1280×800`, `1440×900` et `1600×1000`.
- `1024×768` est une dégradation laptop optionnelle, sans vue cartes téléphone.
- Détail plein écran mobile, feuilles basses, gestes de glissement, bottom nav,
  `MobileActionBar` et QA `390`/`360` sont `LATER`.
- Les contrats sémantiques conservent urgence, titre, raison, échéance, source,
  fraîcheur, sections Thèse/Changements/Réviser, brouillon et confirmation afin que
  la future UI mobile ne change ni action ni historique.

## États UI obligatoires

- `loading` : cartes ou lignes squelettes stables, sans fausse urgence ;
- `refreshing` : ordre précédent conservé jusqu'à réception atomique du nouveau snapshot ;
- `empty` : aucune revue due pour le périmètre affiché, avec prochaine échéance connue ;
- `partial` : familles de preuves et couverture manquantes explicitement listées ;
- `delayed` : délai exact sur l'information concernée, sans contaminer l'historique valide ;
- `stale` : niveaux de marché marqués et nouvelles actions dépendantes du live bloquées ;
- `offline` : historique lisible et notes en brouillon, sans prétendre enregistrer la révision ;
- `error` : dernière file valide conservée et panne isolée par source ou commande.

Un conflit d'édition affiche les deux versions et impose une nouvelle révision ; aucun « dernier écrit gagne » silencieux.

## Accessibilité

- WCAG 2.2 AA, focus visible et restauré après fermeture d'un détail ou validation d'une revue.
- Urgence communiquée par texte et symbole en plus de la couleur ; ordre visuel identique à l'ordre clavier.
- Timeline structurée en liste sémantique avec dates complètes, sources et types annoncés.
- Formulaire avec erreurs liées aux champs, résumé d'erreurs, confirmation non
  ambiguë et cibles interactives suffisantes.
- Zoom 200 %, textes longs, lecteur d'écran NVDA ou VoiceOver et navigation sans souris validés.
- Zéro violation axe critique ou sérieuse sur les états principaux.

## Performance

- Lecture d'un snapshot préparé : p95 API ≤ 250 ms et p99 ≤ 750 ms.
- Filtre, sélection ou ouverture locale : p95 ≤ 100 ms sur une fixture de 5 000 entrées de timeline.
- Virtualisation seulement au-delà d'un seuil mesuré et sans perte de focus ; aucun moteur graphique dans le chunk de route.
- Écriture idempotente avec retour utilisateur en ≤ 500 ms hors latence réseau ; traitement asynchrone visible au-delà.
- Aucun calcul financier, reclassement canonique ou fusion de preuves sur le thread UI.

## Tests obligatoires

- Unitaires : rendu de `urgency_reason`, tri reçu, brouillons, transitions d'action et conservation du snapshot lié.
- Contrats : rejet d'une action hors allowlist, d'une révision sans idempotence, d'un objet mutable ou d'une preuve non résolue.
- Propriétés : historique append-only, chaîne de révisions intacte, répétition d'une commande sans doublon.
- Storybook : huit états UI, échéances passées/futures, textes longs, contradictions et file volumineuse.
- E2E Playwright : révision, report, archivage, retour offline, conflit d'édition et nouvelle information contradictoire.
- Résilience : panne news ou TradingView sans perte des révisions et historique IBKR retardé sans faux live.
- Sécurité : contenu externe neutralisé, URL allowlistée, aucun identifiant de compte, secret ou payload brut dans DOM, logs et télémétrie.

## Critères de sortie mesurables

- 100 % des éléments de la file montrent une raison d'urgence, une échéance ou la mention « sans échéance », une source et un `as_of`.
- 100 % des révisions conservent auteur, timestamp, action, snapshot, hash et lien à la révision précédente.
- Zéro modification automatique de `Thesis` à l'ingestion d'une news, d'un événement ou d'un signal.
- Une même clé d'idempotence rejouée dix fois produit exactement une révision.
- Les huit états UI, les trois viewports desktop `1280×800`, `1440×900` et
  `1600×1000`, ainsi que les scénarios E2E sont verts ; `1024×768` est contrôlé
  seulement comme dégradation laptop utile et aucune QA mobile ne bloque la Beta.
- Aucune action d'ordre, aucun identifiant de compte et aucun calcul financier n'existent dans la route ou ses contrats.
- Revue humaine confirmant qu'une information contradictoire augmente au plus l'urgence et reste distincte de la thèse.
