# LOT-10 — Design system Black Glass et shell desktop

## Références et dépendances

- Références obligatoires : `docs/01-product/INFORMATION_ARCHITECTURE.md`,
  `docs/01-product/NAVIGATION.md`, `docs/01-product/ROUTES.md`,
  `docs/05-design/DESIGN_SYSTEM.md`, `docs/05-design/TOKENS.md`,
  `docs/05-design/CHART_STANDARD.md`, `docs/05-design/UI_STATES.md`,
  `docs/05-design/ACCESSIBILITY.md` et `docs/05-design/RESPONSIVE.md`.
- Décisions applicables : ADR-003, ADR-007, ADR-009 et ADR-010.
- Contrôles transversaux : `docs/06-quality/PERFORMANCE_BUDGETS.md` et
  `docs/06-quality/TEST_STRATEGY.md`.
- Dépendance bloquante : LOT-09 API, jobs, accès et observabilité.

Le lot commence uniquement avec une OpenAPI stable et un client TypeScript générable.
Il établit le vocabulaire visuel et interactif utilisé sans exception par les douze
pages des LOT-11 à LOT-22.

## Objectif

Livrer une application web installable React/TypeScript stricte, utilisée
exclusivement comme shell desktop pendant la Beta, un design system Black Glass
1.0 sobre et un `AppShell` pleinement accessible. Le shell doit rendre
la provenance, la fraîcheur, les droits et tous les états dégradés aussi visibles que
les valeurs, sans devenir une seconde autorité financière.

Vertex 1.0 Beta est **DESKTOP ONLY**. Les cibles de phase 1 sont `1280×800`,
`1440×900` et `1600×1000`. `1024×768` peut être vérifié comme dégradation
laptop si utile, sans devenir une cible mobile. Toute UI `390`/`360`, bottom nav,
`MobileActionBar`, feuille basse ou QA mobile est `LATER`. Les contrats
sémantiques, états, provenance, risque, hiérarchie du contenu et actions restent
conservés pour cette adaptation future.

## Non-objectifs

- construire le contenu métier des douze pages ou répliquer l'ancien dashboard ;
- calculer score, rang, P&L, Greeks, agrégation, fraîcheur ou verdict dans le client ;
- inventer des données démo lorsqu'une API manque ou convertir une erreur en état
  positif ;
- importer un thème générique, réintroduire les alias legacy ou ajouter des couleurs
  brutes dans les composants ;
- ajouter un troisième moteur graphique, D3 libre, Plotly, Chart.js ou une nouvelle
  bibliothèque UI sans ADR ;
- charger ECharts ou Lightweight Charts dans le bundle initial du shell ;
- dépendre du hover, de la couleur seule, d'un tooltip seul ou d'une animation pour
  transmettre une information essentielle.

## Livrables attendus

1. Application web installable desktop avec TypeScript strict, Vite et pnpm,
   routage des douze destinations et page explicite « lot non installé » sans
   fausse donnée pour les routes futures. Le manifeste et le service worker ne
   constituent ni une cible mobile ni une voie d'accès distante.
2. Client API généré depuis l'OpenAPI du LOT-09, TanStack Query pour l'état serveur et
   invalidation ciblée après les signaux SSE.
3. Source typée unique de tokens générant CSS et documentation : couleurs, espaces,
   rayons, ombres, typographie, mouvement, z-index et densité.
4. Fonts Geist Sans Variable et Geist Mono Variable auto-hébergées depuis la
   source Vercel vérifiée, notices OFL et
   chiffres tabulaires sur toutes les séries comparables.
5. `AppShell`, rail desktop rétractable, navigation desktop, recherche/commande et
   `ContextBar`, tous utilisables au clavier aux trois viewports de phase 1.
6. Primitives communes : `DataStateBoundary`, `FreshnessBadge`,
   `ProvenancePopover`, `EntitlementBadge`, `Metric`, `ChartFrame`,
   `AccessibleDataTable`, `EvidenceList`, `GateBadge`, `StatusBanner`, `SideSheet`,
   `NewsClusterRow` et `EventRow`.
7. Wrappers internes de Lightweight Charts et ECharts chargés par route ; attribution
   obligatoire, contrats d'axes/séries et aucune API brute accessible aux pages.
8. `ChartFrame` imposant titre, unité, période, `as_of`, source, fraîcheur, couverture,
   limites, résumé textuel et table accessible équivalente.
9. États standard `loading`, `refreshing`, `empty`, `partial`, `delayed`, `stale`,
   `offline` et `error`, avec copie française stable et comportement documenté.
10. Storybook complet pour tokens, primitives, états, textes longs, densités, focus,
    reduced-motion et trois viewports desktop de référence.
11. Tests unitaires, composants, contrats générés, visuels, accessibilité, mise en
    page desktop, sécurité du rendu et budgets de bundle.

## Règles d'interface et d'autorité

- Les nombres financiers sont reçus comme chaînes décimales et confiés uniquement à
  des formateurs typés ; aucun parse implicite ne devient un calcul métier.
- Le frontend peut trier, filtrer ou changer une représentation à la demande, mais ne
  modifie jamais valeur canonique, gate, priorité serveur ou conclusion financière.
- Une couleur a une seule signification. Tout état coloré comporte texte, icône,
  signe ou motif et respecte le contraste WCAG 2.2 AA.
- Réel, estimé, simulé, live, delayed, stale et offline gardent un libellé textuel
  permanent près de la donnée.
- Les anciennes données peuvent rester visibles pendant `refreshing`, avec âge exact ;
  `stale` ou `offline` interdit toute présentation comme live.
- Une page possède au maximum un bouton rempli ; le shell ne force aucune action
  financière et ne transforme aucun verdict en call-to-action d'ordre.
- Radix fournit le comportement accessible ; Vertex possède styles et tokens. Les
  APIs des moteurs graphiques sont isolées dans le package `charts`.
- Les événements SSE ne transportent pas la vérité affichée : ils invalident la
  query, puis REST fournit le nouveau snapshot canonique.

## Périmètre desktop et accessibilité

- `1600×1000` : rail 232 px rétractable à 68 px, grille 12 colonnes et largeur
  utile maximale 1600 px.
- `1440×900` : rail 232 px rétractable, grille 12 colonnes et densité de référence.
- `1280×800` : rail compact ou rétracté, grille desktop resserrée et modules
  secondaires réordonnés sans perdre action, unité, provenance ou état.
- `1024×768`, si le lot le justifie : dégradation laptop contrôlée avec rail compact
  et empilement possible ; ce profil n'ajoute aucune navigation mobile et ne
  remplace pas les trois captures de release.
- Aucun breakpoint de livraison `390`/`360`, bottom nav, `MobileActionBar`, feuille
  basse ou interaction tactile dédiée en phase 1 ; `Mobile UI = LATER`.
- Les composants répondent aussi à leur conteneur ; les breakpoints sont définis une
  seule fois.
- Focus visible et non masqué, ordre logique, restauration après fermeture, zoom
  200 %, cibles interactives suffisantes, landmarks et titres hiérarchiques
  obligatoires.
- Chaque graphique essentiel fournit conclusion et table équivalente.
- `prefers-reduced-motion` désactive les animations non essentielles ; transitions
  autorisées entre 140 et 220 ms.

## Tests obligatoires

- Génération : dérive OpenAPI/client détectée, types stricts sans `any` non justifié
  et erreurs d'enum rejetées.
- Tokens : CI refusant couleur hex/rgb hors source canonique, espacement arbitraire,
  z-index local et token non documenté.
- Storybook : chaque primitive dans les huit états, données longues/courtes,
  contraste, focus, thème et reduced-motion.
- Composants : clavier, focus piégé/restauré, live regions sobres, formatage unités,
  provenance, entitlement et absence de calcul financier.
- Visuels : captures déterministes en `1280×800`, `1440×900` et `1600×1000`, sans
  débordement, chevauchement ou texte tronqué essentiel ; `1024×768` seulement
  comme test de dégradation laptop si utile.
- Accessibilité : axe-core, navigation clavier complète, zoom 200 %, contraste,
  alternative tabulaire et revue NVDA ou VoiceOver des parcours shell/auth.
- Performance : analyse bundle, chargement différé des deux moteurs, Web Vitals et
  interactions ordinaires à 60 FPS sur fixtures synthétiques.
- Sécurité : échappement des libellés/URLs non fiables, CSP, aucun secret ou payload
  brut dans DOM, logs client ou télémétrie.
- E2E Playwright : login passkey simulé, navigation directe, expiration session,
  reconnexion SSE, offline puis retour réseau, et conservation visible du `as_of`.

## Critères de sortie mesurables

- Les douze routes sont accessibles directement et par navigation ; toute page non
  construite annonce son lot sans donnée fictive ni erreur console.
- 100 % des primitives listées ont types publics, documentation, story nominale et
  stories des états pertinents ; les huit états communs sont couverts au minimum une
  fois en E2E ou test de composant.
- Zéro couleur brute, espacement arbitraire ou z-index local hors sources autorisées ;
  100 % des couleurs d'état ont paire texte/fond AA et indice non colorimétrique.
- Zéro violation axe critique ou sérieuse, parcours shell complet au clavier et revue
  lecteur d'écran réussie.
- Les trois viewports desktop de référence passent les captures sans scroll
  horizontal ni perte d'action, provenance, unité ou état ; aucune QA mobile ne
  bloque la Beta.
- Bundle initial ≤ 300 Ko gzip recommandé ; ECharts et Lightweight Charts sont absents
  du chunk initial et chargés uniquement par les routes qui les utilisent.
- LCP ≤ 2,5 s, INP ≤ 200 ms et CLS ≤ 0,1 sur le scénario de référence ; navigation
  cached p95 ≤ 250 ms et interaction locale ordinaire ≤ 100 ms.
- Le client généré ne contient aucune modification manuelle et la CI détecte toute
  dérive avec l'OpenAPI.
- Une recherche statique et une revue humaine confirment zéro formule financière,
  zéro second gate/verdict et zéro terme d'ordre dans le frontend.
