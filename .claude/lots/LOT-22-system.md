# LOT-22 — Page Système

## Références et dépendances

- Fiche produit obligatoire : `docs/01-product/pages/12-system.md`.
- Références transversales : `docs/03-domain/CANONICAL_CONTRACTS.md`, `docs/03-domain/DATA_QUALITY.md`, `docs/04-integrations/SOURCE_CAPABILITY_MATRIX.md`, `docs/04-integrations/IBKR.md`, `docs/04-integrations/TRADINGVIEW.md`, `docs/06-quality/SECURITY_CONTROLS.md`, `docs/06-quality/OBSERVABILITY.md`, `docs/08-runbooks/BACKUP_RESTORE.md` et `docs/08-runbooks/INCIDENT.md`.
- Dépendances bloquantes : LOT-01 Toolchain/CI, LOT-02 Contrats canoniques, LOT-03 Stockage et qualité, LOT-04 IBKR, LOT-05 TradingView, LOT-06 Data Fusion, LOT-09 API/jobs et LOT-10 Design shell.

Le lot ne commence qu'avec un manifeste exhaustif et versionné des capacités attendues. Le shell de santé utilise un chemin de diagnostic minimal séparé afin de rester lisible lorsque l'API principale est dégradée.

## Question à résoudre

Puis-je faire confiance, maintenant, à chaque source, droit, fraîcheur, traitement, file, sauvegarde et version dont Vertex dépend ?

## Objectif

Livrer `/system`, une matrice exhaustive sources × capacités × état. Elle expose séparément droits commerciaux visibles, droits API effectivement sondés, couverture, délai, fraîcheur et dernier test pour IBKR, TradingView et chaque source primaire, puis relie ces états aux jobs, files, sauvegardes, incidents et diagnostics.

## Non-objectifs

- afficher un statut global vert qui masque une capacité indisponible, retardée ou non testée ;
- déduire un droit API du seul fait qu'un abonnement apparaît dans TWS ou TradingView ;
- exposer secret, token, identifiant de compte, payload complet, chemin sensible ou donnée financière privée ;
- corriger automatiquement une panne, rejouer une DLQ, restaurer une sauvegarde ou redémarrer TWS depuis un diagnostic ;
- aspirer l'interface TradingView ou contourner un entitlement ;
- transformer un manque de données en fallback silencieux.

## Contrats et autorité

Entrées minimales : `SourceEntitlement`, `SourceCoverage`, santé TWS, budgets de pacing, alertes et imports TradingView, Queue/DLQ, base, jobs, dérive d'horloge, sauvegardes/restaurations, versions, journal d'audit et incidents.

Contrats de page à exposer par OpenAPI :

- `CapabilityManifest` : identifiant, source, famille, description, mode `API|WEBHOOK|MANUAL_EXPORT`, criticité, fréquence de sonde et dépendances ;
- `CapabilityStatus` : état canonique, droit déclaré, droit testé, délai, couverture, `tested_at`, `as_of`, `stale_after`, erreur neutralisée et trace ;
- `ComponentHealth` : composant, version, build SHA, disponibilité, dernière activité, backlog, latence et limites ;
- `BackupStatus` : dernier succès, âge, cible logique neutralisée, chiffrement, dernier test de restauration et objectif RPO/RTO ;
- `DiagnosticRun` : identifiant, version, début/fin, checks, résultats, remédiations documentées et hash.

Les seuls états de capacité sont `AVAILABLE`, `DELAYED`, `MANUAL_EXPORT`, `NOT_ENTITLED`, `UNSUPPORTED` et `ERROR`. Chaque capacité du manifeste possède exactement un état, même si elle n'a jamais été testée : ce cas est `ERROR` avec raison explicite, pas une cellule vide. Les droits visibles dans le fournisseur et les droits API sondés occupent deux champs et deux colonnes distincts.

## Livrables desktop

1. Matrice dominante sources × capacités affichant état, droit déclaré, droit testé, fraîcheur, délai, couverture et dernier test.
2. Filtres par source, famille, criticité et état, avec compteur correspondant au manifeste total.
3. Modules secondaires pour composants/jobs, Queue/DLQ, sauvegardes/restaurations, sécurité/versions et incidents.
4. Détail d'une capacité montrant la chaîne de dépendances, les dernières transitions, les limites et le runbook approprié.
5. Diagnostic global idempotent et non destructif, avec progression, résultats structurés et possibilité de retester une capacité.
6. Export neutralisé du diagnostic pour support, excluant secrets et payloads complets.

## Périmètre Vertex 1.0 Beta

- Phase 1 **DESKTOP ONLY** : `1280×800`, `1440×900` et `1600×1000`.
- `1024×768` peut servir de dégradation laptop avec matrice resserrée ou modules
  empilés, sans créer une version cartes téléphone.
- Cartes mobiles, filtres en feuille basse, gestes de glissement, bottom nav,
  `MobileActionBar` et QA `390`/`360` sont `LATER`.
- Les contrats sémantiques conservent criticité, source, compteurs, droit, état,
  fraîcheur, dernier test et progression du diagnostic afin de garantir la parité
  d'une future UI mobile.

## États UI obligatoires

- `loading` : manifeste connu affiché avec cellules « vérification en cours », jamais vide ;
- `refreshing` : derniers résultats datés conservés jusqu'au remplacement atomique ;
- `empty` : uniquement pour un filtre sans résultat, jamais pour le manifeste global ;
- `partial` : certaines sondes manquantes avec compte exact et capacités nommées ;
- `delayed` : capacité `DELAYED` avec durée, source et impact ;
- `stale` : résultat de sonde dépassant `stale_after`, âge exact et nouveau diagnostic proposé ;
- `offline` : dernier diagnostic signé/daté consultable, état réseau distinct ;
- `error` : shell minimal actif, composant fautif isolé et runbook accessible.

Les états `NOT_ENTITLED`, `UNSUPPORTED` et `MANUAL_EXPORT` sont des résultats métier durables, non des erreurs génériques ni des cellules vides.

## Accessibilité

- Matrice disponible comme table HTML sémantique avec en-têtes de lignes/colonnes, caption et filtres annoncés.
- Chaque état possède libellé, symbole et explication ; aucune information n'est portée uniquement par rouge, ambre ou vert.
- Changements d'état annoncés sans rafale ; progression du diagnostic accessible et focus préservé.
- WCAG 2.2 AA, zoom 200 %, navigation clavier, reduced motion et cibles
  interactives suffisantes.
- La table desktop expose tous les champs critiques ; les mêmes contrats seront
  réutilisés par la version mobile `LATER`.
- Zéro violation axe critique ou sérieuse et parcours NVDA ou VoiceOver validé.

## Performance

- Lecture du dernier diagnostic : p95 API ≤ 250 ms et p99 ≤ 750 ms, même si un connecteur externe est en panne.
- Premier shell de santé utilisable selon les budgets Web Vitals ; aucun moteur graphique dans le chunk de route.
- Diagnostic asynchrone, borné par check et parallélisé sans dépasser les budgets de pacing IBKR ou les limites fournisseur.
- Rafraîchissement d'une ligne ou application d'un filtre : p95 ≤ 100 ms pour 2 000 capacités synthétiques.
- Aucun secret, payload complet ou donnée de compte dans cache navigateur, logs, traces, métriques ou export.

## Tests obligatoires

- Contrats : exhaustivité du manifeste, unicité capacité/source, état canonique obligatoire, timestamps et distinction droit déclaré/droit testé.
- Unitaires : calcul d'âge d'affichage non financier, regroupements, filtres, compteurs et neutralisation des erreurs.
- Intégration : TWS down, WSH absent, droit news manquant, quote delayed, pacing saturé, webhook rejeté, import manuel ancien, Queue en retard et DLQ non vide.
- Sauvegarde : alerte de sauvegarde trop vieille et preuve d'un test de restauration selon le runbook.
- E2E : API principale dégradée avec shell accessible, diagnostic répété idempotent, capacité stale et export support neutralisé.
- Sécurité : snapshots garantissant l'absence de secrets, tokens, identifiants de compte, en-têtes d'authentification et payloads complets.
- Accessibilité et mise en page desktop : table, filtres, diagnostic et incidents
  sur les trois viewports de phase 1 ; `1024×768` seulement si utile comme
  dégradation laptop.

## Critères de sortie mesurables

- Le nombre de lignes rendues avant filtre égale exactement le nombre de capacités du manifeste versionné.
- 100 % des capacités montrent source, mode, état canonique, droit déclaré, droit API testé, couverture, fraîcheur, `tested_at` et limite ou raison.
- Zéro cellule d'état vide et zéro substitution silencieuse lorsqu'un droit est absent ou une source échoue.
- Les six états `AVAILABLE`, `DELAYED`, `MANUAL_EXPORT`, `NOT_ENTITLED`, `UNSUPPORTED` et `ERROR` possèdent fixture, story et scénario automatisé.
- Le shell et le dernier diagnostic restent accessibles pendant les scénarios API principale down et TWS down.
- Le test de restauration est enregistré, l'âge de sauvegarde déclenche l'alerte au seuil configuré et l'export ne contient aucun secret selon scan automatisé.
- Les huit états UI, les trois viewports desktop, budgets performance et scénarios
  E2E passent en CI ; aucune QA mobile ne bloque la Beta.
- Revue humaine confirmant que toutes les capacités, droits et fraîcheurs sont explicites et qu'aucune action destructive n'est disponible.
