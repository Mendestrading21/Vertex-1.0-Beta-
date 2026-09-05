# Arbitrage des destinations — actuel → cible → décision

## Pourquoi ce document existe

`.claude/skills/vertex-titanium-ledger/SKILL.md` fixe **douze destinations
cibles** et impose, quand les routes courantes diffèrent : « établir une table
`actuel -> cible -> décision` **avant** de proposer renommage, fusion ou
retrait ».

Le script d'inventaire du skill mesurait l'écart :

```text
destinations cibles sans équivalent détecté: catalysts
routes historiques à arbitrer: follow-up, performance, ai, system
```

Quatre pages livrées, fonctionnelles et couvertes par les 405 tests Playwright
n'apparaissent pas dans la cible. Quatre destinations cibles n'existent pas.
Supprimer les premières détruirait des capacités prouvées ; les garder toutes
donnerait seize entrées de rail là où la capture canonique en montre douze.

**Décision humaine du 2026-08-31 : absorber.** Aucune capacité n'est perdue,
la cible des douze est respectée.

## Table d'arbitrage

| Actuel | Cible | Décision | Ce qui doit être préservé |
|---|---|---|---|
| `today` | Aujourd'hui | `CONSERVER` | — |
| `markets` | Marchés | `CONSERVER` | — |
| `opportunities` | Opportunités | `CONSERVER` | — |
| `analysis` | Analyse | `CONSERVER` | — |
| `options` | Options | `CONSERVER` | — |
| `simulator` | Simulateur | `CONSERVER` | — |
| `portfolio` | Portefeuille | `CONSERVER` | — |
| `calendar` | Calendrier | `CONSERVER` | — |
| `system` | **Sources & Rapports** | `RENOMMER + ÉTENDRE` | `SourceHealthMatrix` (14 capacités), santé base/migrations/horloge/sauvegarde, états `NEVER_TESTED`. La page porte déjà la santé des sources : la cible ajoute lignage, incidents et rapports. |
| `performance` | Portefeuille | `ABSORBER` | TWR, XIRR, drawdown, heatmap mensuelle, export CSV + manifeste, bandeau `SYNTHETIC_MARKS_REAL_LEDGER`. Les deux pages lisent le même portefeuille manuel. |
| `follow-up` | Catalyseurs | `ABSORBER` | File de revues, thèses avec invalidation obligatoire, badge « nouvelle information ». Une thèse est suivie **parce qu'un catalyseur l'affecte** : la fusion est sémantique, pas cosmétique. |
| `ai` | inspecteur contextuel | `ABSORBER` | Explication déterministe versionnée, séparation faits / extraits externes, bandeau B-05. L'IA n'est pas une destination : elle explique le dossier ouvert, donc elle vit dans l'inspecteur de droite présent sur les douze pages. |
| `auth` | — | `HORS RAIL` | Route de session, jamais une destination de navigation. Inchangée. |
| — | **Graphiques** | `CRÉER` | — |
| — | **Risques** | `CRÉER` | — |

## Une contradiction du skill, tranchée par son propre contrat

Le script d'inventaire `scripts/audit_titanium_ledger.py` normalisait
`performance -> charts` et `follow-up -> risks`. Ces deux correspondances
contredisent `references/pages.md`, dont le titre est *Contrats des douze pages
Vertex* et qui définit chaque destination :

- **Graphiques** (§8) est « un espace graphique configurable avec séries
  autorisées », pour explorer un instrument — pas la mesure d'un registre. Le
  contrat range l'« historique » du registre dans les widgets de
  **Portefeuille** (§7).
- **Risques** (§9) est « la matrice des risques avec exposition, horizon,
  sévérité et preuve ». La file de revue de thèses répond à la question de
  **Catalyseurs** (§10) : « quels événements vérifiés peuvent modifier LA THÈSE
  et quand ? »

Le contrat l'emporte sur le script, qui n'est qu'une heuristique d'inventaire et
dont la sortie porte elle-même la mention « les candidats exigent une revue
humaine ». Le script a donc été corrigé pour s'accorder avec le document qu'il
mesure. Aucune définition de page n'a été modifiée.

## Règles d'exécution de l'absorption

1. **Aucune capacité ne disparaît avant que sa remplaçante soit prouvée.** Une
   absorption se fait en deux temps : la cible reçoit la capacité et ses tests
   passent, *puis seulement* l'ancienne route est retirée. Jamais l'inverse.
2. **Les contrats API ne bougent pas.** `/api/v1/performance/{id}`,
   `/api/v1/follow-up/queue` et `/api/v1/ai/explain` restent servis : c'est la
   composition d'interface qui change, pas l'autorité des données.
   `.claude/rules/architecture.md` interdit de déplacer une responsabilité entre
   modules sans ADR — ici rien ne se déplace côté serveur.
3. **Les tests E2E existants sont déplacés, pas supprimés.** Les 405 assertions
   actuelles restent la preuve que la capacité survit à la fusion. Un test
   retiré au lieu d'être déplacé serait un affaiblissement, interdit par
   `.claude/rules/testing.md`.
4. **Une page absorbée garde sa question.** « Quelles thèses doivent être
   revues ? » doit rester lisible dans Catalyseurs, sinon la fusion a détruit
   du sens au lieu d'en regrouper.
5. **Une redirection permanente remplace chaque route retirée**, pour ne pas
   casser un signet ou un lien profond existant.

## Graphiques et Risques — de « pas créées » à créées

**Mise à jour du 2026-09-02.** Les deux destinations existent désormais ; le
raisonnement du 2026-09-01 qui suit est conservé comme trace, parce qu'il dit
pourquoi elles n'ont PAS été créées en façade.

- **Risques (§9)** a été installée le 2026-09-01 en CRÉANT son contrat :
  `risk.correlation` au registre des calculs, snapshot `risk_matrix/global`,
  relais `GET /api/v1/risk/matrix`.
- **Graphiques (§8)** a été installée le 2026-09-02 (LOT-A2, `TL / 08`) SANS
  nouveau contrat, et sans façade : la planche est rendue en entier, module
  par module, et chaque module y est soit **servi**, soit **déclaré absent**
  avec un motif du vocabulaire fermé d'`AbsentModule` (article 17 de la
  Constitution). Sa dominante — l'espace graphique, chandeliers + volume + table
  OHLCV équivalente — lit le **même DTO, par le même client, avec le même
  composant** que `/analysis`. Ce n'est pas un second propriétaire de donnée :
  le propriétaire est le contrat `GET /api/v1/analysis/{instrument}`, et la
  page ne recalcule rien. Ce que `/analysis` porte en propre (verdict, gates,
  preuves, scénarios, explication) n'y est pas repris.

  Les neuf modules sans source au 2026-09-02, et leur motif mesuré (état
  serveur mis à jour le 2026-09-03 pour les overlays et oscillateurs) :

  | Module | Motif | Ce qui manque exactement |
  |---|---|---|
  | Comparaison base 100 | `CONTRAT SERVEUR ABSENT` | `market.rebased_series` est approuvé au registre et implémenté dans `vertex_core`, mais **aucun snapshot ni aucune route ne le relaie** |
  | Graphiques synchronisés | `CONTRAT SERVEUR ABSENT` | aucun contrat d'alignement de plusieurs séries sur un calendrier commun |
  | Overlays (moyennes mobiles), RSI, MACD | `AUCUNE SOURCE` côté page → **source serveur depuis le lot S6 (2026-09-03)** | `market.sma`, `market.ema`, `market.bollinger_bands`, `market.rsi`, `market.macd` sont approuvés au registre, implémentés dans `vertex_core` et publiés par le worker dans `indicators.overlays` / `indicators.oscillators` du snapshot `analysis/{instrument}` (chaînes rendues alignées sur leurs jours de bourse, fenêtres déclarées, noms des bandes et des lignes, `INSUFFICIENT_SAMPLE` nommé avec le compte réel), relayés tels quels par `GET /api/v1/analysis/{instrument}` ; la page les déclare encore absents — les brancher est un lot d'interface, sans calcul |
  | Objet sélectionné, Alertes liées, Agencement, Études sauvegardées | `DÉCISION EN ATTENTE` | données ou préférences **utilisateur** persistées ; propriétaire et contrat non tranchés (« Alertes » est une capacité globale, pas un module de page) |

  Brancher la comparaison est donc un lot **serveur** — producteur et relais de
  `market.rebased_series` — et non un lot d'interface. Le calculer dans le
  navigateur reste interdit (`.claude/rules/frontend.md`).

Le contrat OpenAPI compte trente-deux routes au 2026-09-02, dont
`/api/v1/risk/matrix` ; aucune ne se nomme `charts`, et c'est cohérent : la
page n'a pas de contrat propre, elle affiche celui d'Analyse sous sa question.

### Trace du 2026-09-01 — pourquoi ni l'une ni l'autre n'a été créée en façade

Mesuré le 2026-09-01, pas supposé. Catalyseurs a montré qu'une destination
« sans contrat » pouvait en fait être constructible depuis des contrats déjà
servis ; la même vérification a donc été refaite pour les deux dernières.

Les trente routes du contrat OpenAPI d'alors ne comportaient **ni `charts` ni
`risks`**. La question était : ces pages sont-elles assemblables depuis
l'existant, comme Catalyseurs l'était ?

**Graphiques (§8) — pas sans déclarer ses absences.** Sa dominante est « un
espace graphique configurable avec séries autorisées » et son widget
distinctif est la **comparaison**. Comparer deux séries de prix suppose de les
rebaser, c'est-à-dire de calculer un rendement dans le navigateur — ce que
`.claude/rules/frontend.md` interdit explicitement. L'alternative, un double
axe, est interdite au même endroit. Sans overlays ni comparaison servis par le
serveur, il ne resterait qu'un graphique d'un seul instrument : ce que
`/analysis` fait déjà. C'est la voie de l'`AbsentModule` (LOT-A0) qui a levé
l'objection : la composition complète avec absences nommées n'est pas une
façade, et l'affichage du même contrat sous une autre question n'en fait pas
un second propriétaire.

**Risques (§9) — non.** Sa dominante est « la matrice des risques avec
exposition, horizon, sévérité et preuve ». Les morceaux existent bien
(concentration dans `/v1/portfolio`, gates bloquantes dans `/v1/analysis`,
santé des sources dans `/v1/system/capabilities`), mais **aucune source ne
publie de sévérité ni d'horizon par risque**. Les attribuer côté navigateur
serait fabriquer un score, ce que `.claude/rules/architecture.md` réserve à
`AdviceEngine` et que le §9 lui-même interdit (« aucun score global vert
dérivé de mesures partielles »).

Les deux pages attendent donc un **contrat serveur**, pas une décision
d'interface. Les inventer maintenant produirait exactement la façade que
l'article 17 de la Constitution interdit.

## Le motif d'inspecteur, tranché et appliqué (LOT-13)

Décision : **l'inspecteur persistant du shell est le motif unique.** Le
dialogue modal a disparu des deux pages qui en portaient un — Aujourd'hui et
Options. Il ne reste plus aucun `role="dialog"` ni `aria-modal` dans
l'application.

**Le piège de focus a été retiré, et c'est la correction, pas un
affaiblissement.** Un piège n'est correct que pour un dialogue modal, où le
reste de la page est justement inerte. Sur un panneau NON modal, piéger le
clavier enfermerait l'utilisateur hors de sa propre page : ce serait un défaut
d'accessibilité. Les assertions qui l'exigeaient sont remplacées par leur
contrepartie correcte — depuis le dernier élément du panneau, la tabulation
CONTINUE vers le reste de la page. C'est une propriété plus forte : elle
prouve que la page reste opérable.

Conservé à l'identique, parce que ces propriétés valent pour les deux motifs :
le focus entre dans le panneau à l'ouverture, `Échap` referme, le focus revient
au déclencheur. Axe reste à zéro violation critique/sérieuse.

Deux défauts introduits par la conversion, trouvés et corrigés :

1. **le focus n'entrait plus dans le panneau.** Le panneau est monté par
   PORTAIL : au premier rendu, le nœud d'accueil n'est pas encore résolu, donc
   un `useEffect([])` ne trouve aucun bouton à focaliser. Remplacé par une ref
   de rappel, qui se déclenche à l'attachement réel du nœud ;
2. **le panneau chevauchait la zone de travail.** `.vx-sheet` restait une
   surcouche `position: fixed` pleine hauteur, avec ombre portée et flou —
   toute la chrome du modal. Elle coule désormais dans la colonne, et
   l'encadrement visuel est celui de `.vx-inspector-panel`, commun à tous les
   panneaux.

Options a suivi exactement la même recette, et sans surprise : les deux
défauts trouvés sur Aujourd'hui (focus perdu par le portail, surcouche
`position: fixed`) étaient déjà corrigés à la racine — la ref de rappel dans
le composant, la règle `.vx-sheet` dans la feuille de style. La conversion s'y
est donc réduite au composant et à ses assertions.

## Ancienne section — deux motifs coexistaient

Constat du LOT-12, non corrigé, à traiter avant la refonte des pages.

L'anatomie canonique décrit un inspecteur **persistant à droite**, et c'est
celui que le LOT-11 a livré. Mais deux pages en avaient déjà un, livré comme
**dialogue modal** : le panneau latéral d'Aujourd'hui et `OptionInspector`
d'Options — tous deux `role="dialog"`, avec piège de focus, `Échap` et
restauration du focus, et tous deux utilisant les mêmes noms de classes
`.vx-inspector-*`.

Les convertir n'est pas mécanique : passer d'un modal à une colonne
persistante **retire le piège de focus et la touche Échap**, propriétés
aujourd'hui asserées par des tests d'accessibilité. Une conversion faite sans
soin dégraderait l'accessibilité de deux pages livrées. Ce lot doit donc être
explicite sur ce qu'il remplace, page par page, et prouver l'accessibilité
après conversion — pas seulement avant.

Vérifié au passage : les classes `.vx-inspector-hash`, `-note`, `-value`,
`-unit`, `-absent` sont des utilitaires génériques non scopés (taille, couleur,
césure). Les panneaux du LOT-11 et du LOT-12 les réutilisent sans conflit.

## Ce que ce document ne décide pas

Le **contenu** des deux pages à créer. Graphiques et Risques n'ont aujourd'hui
ni contrat, ni endpoint, ni donnée : leur composition se décide à leur lot, à
partir de leur planche canonique et des données réellement disponibles — jamais
en remplissant une maquette avec ce qui n'existe pas.

## Journal d'exécution

| Date | Ligne arbitrée | Ce qui a été fait | Preuve |
|---|---|---|---|
| 2026-08-31 | `system` → **Sources & Rapports** | Renommage de la destination : clé de page, `navPath`, `routePath`, glyphe du rail, sélecteurs CSS, composant (`SystemPage` → `SourcesReportsPage`), spec e2e (`system.spec.ts` → `sources-reports.spec.ts`) et libellés produit dans `docs/`. Redirection permanente `/system` → `/sources-reports` ajoutée. La route API `/v1/system/capabilities` n'a **pas** bougé (règle 2). | `vitest run` 398 passed ; `playwright test` 405 passed ; `tools/run_checks.sh` TOUT VERT. Redirection falsifiée : en retirant `replace`, `routes.test.tsx` passe à `expected 'PUSH' to be 'REPLACE'`. |

| 2026-08-31 | `performance` → **Portefeuille** | Le module Performance entier (courbe, métriques brut\|net, heatmap + table mensuelle, série quotidienne, jours exclus, export CSV + manifeste, conventions) déplacé sous `src/pages/portfolio/performance/`, rendu dans `PortfolioPage`. `/performance` retirée du rail et redirigée vers `/portfolio`. La route API `/v1/performance/{id}` n'a **pas** bougé (règle 2). | `vitest run` 399 passed ; `playwright test` 399 passed ; `tools/run_checks.sh` TOUT VERT. Décompte e2e 405 → 399 intégralement expliqué ci-dessous. |

| 2026-09-01 | `follow-up` → **Catalyseurs** | Création de la douzième destination et absorption du module de revue. Aucun endpoint ajouté : la page CROISE `calendar/global` (dont chaque événement porte déjà son `event_context`) et `review_queue/global`. `/follow-up` retirée du rail et redirigée vers `/catalysts`. Les routes API ne bougent pas (règle 2). | vitest 415 ; playwright 432 ; `run_checks.sh` TOUT VERT ; l'audit du skill ne liste plus `follow-up` |

| 2026-09-01 | (shell) **inspecteur contextuel** | Point 6 de l'anatomie canonique livré comme EMPLACEMENT du shell, rempli par la page. Premier remplissage : Catalyseurs (§10). Débloque la ligne `ai`, qui attendait cet emplacement. | vitest 420 ; playwright 435 ; largeur mesurée dans 300–340 px ; « aucune colonne morte » vérifiée sur `/today` et `/catalysts` |

| 2026-09-01 | `ai` → **inspecteur contextuel** | Dernière ligne d'absorption. Le module d'explication passe sous `src/components/ai/` et est monté par les pages qui portent un dossier explicable : Analyse (`analysis`) et Portefeuille (`portfolio_valuation`, `performance`). Le sélecteur de sujet disparaît au profit des dossiers RÉELLEMENT ouverts sur la page hôte. `/ai` quitte le rail et redirige vers `/analysis`. Routes API inchangées (règle 2). | vitest 423 ; playwright 429 ; `run_checks.sh` TOUT VERT ; l'audit ne liste plus aucune route à arbitrer |

| 2026-09-01 | (shell) **ticker horizontal** | Point 4 de l'anatomie canonique. Aucune ligne d'arbitrage : c'est une capacité de shell, pas une destination. Livré parce que la raison écrite pour ne PAS le livrer s'est révélée fausse — voir ci-dessous. | vitest 434 ; playwright 435 ; `run_checks.sh` TOUT VERT |

### Le ticker : une dette fondée sur une vérification jamais faite (LOT-14)

`docs/99-status/DEBT.md` déclarait le point 4 ouvert parce qu'il « exige une
source d'indices servie au shell sur chaque page, donc une décision de charge
réseau **et un contrat** ». La seconde moitié était fausse.

`/api/v1/markets/overview` publie `MarketsTicker` depuis la première vague :
`ticker`, `last_close`, `return_1d_pct`, `currency`, `quality`, `synthetic`,
`trading_day` — **tous calculés et formatés par le worker**. Il n'y avait rien
à obtenir du serveur.

C'est **exactement l'erreur de Catalyseurs au LOT-10** : une capacité déclarée
« sans contrat » l'était par défaut de vérification. La leçon avait été écrite ;
elle n'avait pas été appliquée aux deux points d'anatomie restants. Elle l'est
maintenant, et la règle est plus dure : *une entrée de dette qui affirme « le
contrat manque » doit **nommer la route absente**. Sans nom, ce n'est pas un
constat, c'est une supposition.*

Ce qui restait réellement — la charge réseau — est une décision, et elle est
bornée : la clé de requête est `markets_overview/global`, **exactement** celle
de la page Marchés, donc react-query dédoublonne sur `/markets` ; et
`staleTime: Infinity` interdit tout re-fetch périodique. Le ticker ne « bat »
pas.

### Ce que le ticker n'affiche pas, et pourquoi

- **Aucun chiffre qu'il ne peut pas qualifier.** Hors ligne, sans session, sans
  instantané ou en erreur, la bande affiche un message et **aucun cours**.
  Garder les derniers cours pendant une coupure présenterait un cache comme du
  courant, ce que `.claude/rules/financial-safety.md` interdit.
- **Aucun tri.** L'ordre est celui du worker, secteur par secteur. Reclasser
  produirait un classement financier côté navigateur.
- **Aucun mouvement.** « Aucun ticker animé faisant croire à une donnée live » :
  le défilement est celui de l'utilisateur, et un test e2e vérifie qu'aucune
  animation n'est déclarée.
- **Aucune portée applicative.** La population et la fraîcheur sont portées par
  la bande, pas par le coin haut-droit (point 5). `population` est un champ
  **par instantané** : le poser en haut à droite lui donnerait une portée
  « Vertex » qu'aucune source ne publie. Le point 5 reste donc vide — et c'est
  désormais une décision argumentée, plus un simple constat d'absence.

### Le défaut que l'absorption de `/ai` a révélé

En montant le panneau dans une page hôte, celle-ci lui a servi — via son mock
de test — le corps d'une AUTRE ressource. `ClaimsBlock` a échoué sur
`catalog is not iterable`, et l'erreur est remontée jusqu'à la frontière de
route : **c'est la page entière qui disparaissait** — analyse, avis, barres —
à cause d'un panneau accessoire.

Le défaut préexistait l'absorption ; il était simplement invisible tant que
l'explication vivait seule sur sa propre page, où elle n'avait qu'elle-même à
emporter. Corrigé par une garde de forme (`isWellFormedAnswer`) : une réponse
hors contrat se dégrade en état `error` visible et **le dossier de la page
hôte reste intact**. Falsifié — neutraliser la garde fait réapparaître
`catalog is not iterable`.

C'est la leçon générale de ce lot : un composant déplacé dans un hôte hérite
de la responsabilité de ne jamais le faire tomber.

### Ce que Catalyseurs n'invente pas

La page ne crée aucune donnée en croisant deux snapshots publiés :

- une thèse **citée par un événement** mais absente de la file de revue est
  affichée comme absente, avec son titre d'origine — jamais complétée par une
  échéance ou un état qu'aucun snapshot ne publie ;
- les événements que le snapshot ne relie à rien sont **comptés et annoncés**,
  jamais silencieusement filtrés ;
- les deux requêtes restent **indépendantes** : hors ligne, chacune affiche son
  propre état avec un message distinct. Un bandeau partagé laisserait croire à
  une source unique et masquerait le cas — le plus fréquent — où une seule des
  deux tombe ;
- le widget « **consensus fourni** » que le contrat §10 nomme n'a aucun champ
  correspondant dans le contrat d'agenda publié. Il est déclaré **absent** à
  l'écran, pas approximé.

Distinction avec Calendrier (§11) : Calendrier sert **tout** l'agenda dans une
fenêtre et son fuseau ; Catalyseurs n'en sert que la part reliée à une thèse ou
une position. Un seul propriétaire de donnée, deux questions — jamais deux
vérités. Un test e2e vérifie que les deux nombres (reliés + non reliés)
s'additionnent exactement à l'agenda servi par l'API : un événement perdu
serait pire qu'un événement de trop.

### Pourquoi le total Playwright passe de 405 à 399

Un total qui baisse doit s'expliquer, sinon il cache une suppression.

- **−12** : `/performance` sort de la liste `ROUTES` d'`accessibility.spec.ts`,
  qui exécute **4** contrôles par route (axe WCAG, focus au `Tab`, débordement à
  200 %, `prefers-reduced-motion`) sur **3** viewports. Ces 4 contrôles ne
  disparaissent pas : le module Performance est désormais dans le DOM de
  `/portfolio`, donc balayé par l'entrée `/portfolio` de la même liste. Y
  laisser `/performance` n'aurait plus mesuré qu'une redirection.
- **+6** : deux tests de redirection permanente (`/performance` → `/portfolio`
  et `/system` → `/sources-reports`, retour arrière compris) sur 3 viewports.

405 − 12 + 6 = **399**. Les 7 tests de l'ancien `performance.spec.ts` sont
**tous** conservés : le fichier a été renommé `portfolio-performance.spec.ts` et
seule la route visitée change.

### Note de composition, non résolue

`.claude/rules/frontend.md` impose « un visuel dominant » et « trois à cinq
modules » par page. Portefeuille en compte cinq après absorption (valorisation,
performance, journal, saisie, import CSV) — dans la limite. En revanche la
courbe de performance est un **second** visuel fort à côté du tableau de
valorisation. Cette tension se tranche à la refonte Titanium Ledger, contre la
planche `pages-07-08-portfolio-charts.png`, pas ici : la règle 1 (aucune
capacité perdue) prime sur la composition tant que la page n'est pas recomposée.

L'`ÉTENDRE` de la ligne `system` — lignage, incidents et rapports — n'est **pas**
livré. Il n'est pas non plus simulé : la page affiche exactement les capacités
qu'elle sait prouver, conformément à l'article 17 de la Constitution.
