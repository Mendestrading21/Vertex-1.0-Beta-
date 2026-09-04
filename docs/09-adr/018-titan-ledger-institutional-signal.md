# ADR-018 — Titan Ledger / Institutional Signal : direction visuelle canonique

- Statut : Accepté
- Date : 2026-09-04
- Décideurs : propriétaire produit (brief écrit du 2026-09-04, « MISSION MAÎTRE — REFONTE VISUELLE COMPLÈTE DE VERTEX », qui déclare : « cette direction est désormais la référence canonique »), responsable du design system
- Portée : `apps/web/src/design/tokens.ts` et le `tokens.css` généré ; le shell (`apps/web/src/shell/`) ; les primitives (`apps/web/src/components/`) ; la composition des douze destinations ; `docs/05-design/*` ; `.claude/skills/vertex-titanium-ledger/references/*` ; `manifests/widget-catalog.yaml`
- Remplace : **la palette, le matériau et la référence de style d'ADR-017**. Ne remplace **aucune** de ses règles d'autorité : les dix formes admises restent admises, les treize interdits restent interdits, et la règle cardinale — « une forme est admise si et seulement si chaque grandeur qu'elle dessine est servie » — est reconduite mot pour mot.

## Contexte

Faits vérifiables, établis par l'audit du 2026-09-04.

### 1. La vérité des données est la contrainte qui décide

Le brief demande d'afficher vingt-six familles d'information. Mesuré contre le
contrat OpenAPI généré (`apps/web/src/api/schema.d.ts`), les routes FastAPI et
les douze catalogues de modules :

| Statut | Nombre | Exemples |
|---|---:|---|
| Servis | 6 | breadth (`MarketsBreadth`), heatmap sectorielle (`MarketsSector` × `MarketsTicker`), drawdown (`performance.drawdown`), matrice de scénarios (`SimulationPreviewResponse.scenario_grid`), couverture des symboles (`MarketsCoverage`), provenance et fraîcheur partout |
| Partiellement servis | 6 | structure par terme (par groupe, jamais agrégée), skew (géométrie IV × strike, aucune pente publiée), open interest (par contrat, aucune agrégation par strike), Greeks (par contrat, `THEORETICAL`, jamais agrégés), scénarios (grille spot × temps, aucune probabilité), disponibilité (statut typé, jamais un pourcentage) |
| **Non servis** | **14** | sentiment 0–100, régime de marché, rotation sectorielle, courbe de taux, IV Rank, put/call ratio, max pain, activité inhabituelle, score décomposé à huit facteurs, benchmark, taux de réussite, expectancy, attribution, backtest, latence |

Le registre de calculs autorisés
(`packages/python/vertex_core/src/vertex_core/calculations/`) contient
vingt-cinq identifiants. Aucun ne produit l'un des quatorze éléments non
servis. `.claude/rules/frontend.md` interdit de les dériver en TypeScript.

Sur les cent quatre-vingt-trois modules des douze catalogues, **soixante-dix-sept
sont déjà déclarés absents** avec leur motif typé (`NO_SOURCE`,
`SUBSCRIPTION_REQUIRED`, `SERVER_CONTRACT_MISSING`, `DECISION_PENDING`).

Le brief l'écrit lui-même : « Une métrique indisponible doit être masquée,
désactivée ou explicitement signalée comme indisponible. Ne jamais fabriquer une
valeur. » Les deux textes concordent. Cette décision ne crée donc aucune
capacité : elle habille ce qui est servi et laisse dire ce qui ne l'est pas.

### 2. La référence de style change de nature : elle devient écrite

ADR-017 et `references/canonical-visual.md` verrouillent l'autorité de style sur
une **capture PNG** et son empreinte SHA-256
`eb2eb0fc2105a98203e571381aec7765775d80aacec3513def10e99c9fdc7ace`, avec la
règle : « Toute différence d'empreinte exige une nouvelle validation explicite de
l'utilisateur ; elle ne constitue jamais une "amélioration" automatique. »

Le brief fournit cette validation explicite. Mais il fonde la nouvelle direction
sur quinze images de référence **qui ne sont pas jointes au dépôt** : elles ont
été décrites, image par image, dans le texte du brief, et non versionnées.

Fabriquer une empreinte pour une image que le dépôt ne possède pas serait une
preuve inventée. La nouvelle autorité de style est donc **un contrat écrit**,
versionné dans le dépôt et hachable comme tel :
`.claude/skills/vertex-titanium-ledger/references/titan-ledger.md`.

La capture `vertex-dashboard-canonical.png` reste dans le dépôt comme **témoin
historique** de la direction Black Glass. Son empreinte reste vérifiée, pour que
sa modification silencieuse reste impossible ; elle n'a plus autorité.

### 3. Les dix-neuf invariants verrouillés restent tous vrais

`apps/web/src/design/canon-v2-docs.test.ts` verrouille dix-neuf formulations
dans quinze documents : « une couleur = une signification », « jamais couleur
seule : texte, icône ou motif », « le signal ambre n'exprime jamais une hausse,
un score ou une validation », « aucune pulsation », « aucun halo néon
permanent », « Réserver vert/rouge au signe financier », `"animated_needle"`,
`"opaque_composite_score"`, et les autres.

Le brief exige **exactement** les mêmes disciplines : « la couleur n'est jamais
le seul vecteur d'information », « aucune animation permanente », « pas de glow
constant », « Le vert sert uniquement à … », « aucun score sans expliquer sa
composition ». **Aucun invariant n'est levé par cette décision.**

### 4. L'écart de navigation

Le brief nomme douze espaces dont quatre n'existent plus comme destinations :
Suivi, Performance, Vertex IA et Système. Ils ont été absorbés par une décision
humaine du 2026-08-31, consignée dans `docs/05-design/PAGE_ARBITRATION.md`.
Symétriquement, le brief ne nomme ni Graphiques ni Risques, qui sont deux
destinations servies.

Le brief interdit par ailleurs de « supprimer une fonctionnalité existante
uniquement parce qu'elle est difficile à intégrer visuellement », et prévoit que
« les anciennes routes doivent être redirigées proprement lorsque la nouvelle
navigation l'exige ».

### 5. Une grammaire de table par page

Vingt-et-une familles de classes CSS de table pour vingt-quatre fichiers ;
aucun composant `DataTable` partagé n'existe. `vx-matrix-table` est la seule
classe employée par plus de cinq fichiers.

## Décision

### A. Palette — rôles sémantiques, contrastes mesurés

Les valeurs du brief §4 sont adoptées **avec deux corrections mesurées**, la
source typée `apps/web/src/design/tokens.ts` restant l'unique endroit où une
couleur est écrite.

Contrastes calculés sur les cinq fonds du produit (`bg-root` `#06080B`,
`bg-canvas` `#090C11`, `surface-2` `#111722`, `surface-3` `#151C27`,
`surface-hover` `#19212D`) :

| Rôle | Valeur | Pire contraste | Verdict |
|---|---|---:|---|
| `text-primary` | `#F4F7FA` | 15,06 | AA large |
| `text-secondary` | `#A8B0BD` | 7,41 | AA |
| **`text-muted`** | **`#7E8897`** | **4,52** | **corrigé** |
| `text-disabled` | `#4C5562` | 2,15 | exempté, voir ci-dessous |
| `accent-ember` | `#FF7A45` | 6,26 | AA |
| `accent-amber` | `#F4B84A` | 9,10 | AA |
| positif | `#2ED49B` | 8,49 | AA |
| négatif | `#FF6577` | 5,69 | AA |
| avertissement | `#F3BE55` | 9,49 | AA |
| technique (cyan) | `#31CED7` | 8,44 | AA |
| options (violet) | `#9A82FF` | 5,41 | AA |
| neutre | `#8791A0` | 5,08 | AA |

**Correction 1 — `text-muted`.** La valeur `#707A89` proposée par le brief tient
4,62:1 sur le fond le plus sombre mais tombe à **3,73:1 sur `surface-hover`**,
sous le seuil AA. Or ce rôle porte les métadonnées *à l'intérieur des cartes*,
c'est-à-dire précisément sur les surfaces claires. Corrigée en `#7E8897` : même
teinte, quatorze crans de clarté par canal, **4,52:1 au pire**. Le brief demande
d'« ajuster uniquement pour garantir WCAG 2.2 AA » ; c'est cet ajustement.

**Correction 2 — `text-disabled`.** `#4C5562` tient 2,15:1 au pire. WCAG 2.2
exempte explicitement le texte des composants **inactifs** (1.4.3, « Incidental
… inactive user interface components »). La valeur est conservée, et son emploi
est restreint par cette décision : **jamais sur une donnée lisible**, seulement
sur un contrôle désactivé dont l'état est aussi dit par un texte ou un attribut.

### B. Emploi des couleurs — vocabulaire fermé, inchangé dans son esprit

- **Ember / amber** : identité, action principale, sélection active, point focal.
  Ils n'expriment **jamais** une hausse, un score ni une validation — invariant
  d'ADR-017 reconduit.
- **Vert** : progression positive, gain, amélioration, état disponible, hausse.
  **Rouge** : perte, détérioration, état critique, invalidation, risque élevé.
  Réservés au **signe financier servi**, doublés d'un signe et d'un texte.
- **Violet** : options, scénarios, distributions.
- **Cyan** : données techniques, Calls, flux, comparaison, données live.
- Aucune carte n'est colorée en entier parce qu'elle contient une variation.

Dans la visualisation d'open interest, **Calls en cyan et Puts en violet** : le
brief refuse explicitement l'assignation automatique vert = Call / rouge = Put,
qui volerait au signe financier ses deux seules couleurs. **ATM en ambre** — c'est
un repère de sélection, pas une performance, donc conforme à l'invariant.

### C. Deux formes ajoutées aux dix d'ADR-017

Elles obéissent à la même règle cardinale : chaque grandeur dessinée est servie.

| Forme | Donnée servie exigée | Refus (état nommé, jamais 0) |
|---|---|---|
| **Barres miroir d'open interest** | `open_interest` et `volume` publiés **par contrat** (`OptionChainContract`), avec `open_interest_status` ; strike servi ; l'axe central est la liste des strikes servis | statut non `OK` → aucune barre, cellule qui dit le statut servi. **La notion de « mur » n'est pas servie** : aucune agrégation par strike n'est publiée, et l'interface n'en dérive aucune |
| **Matrice de P&L de scénarios** | `scenario_grid` (`string[][][]`), `scenario_spot_grid`, `scenario_time_grid_years` de `SimulationPreviewResponse`, relayés verbatim ; la couleur encode le signe servi, la valeur exacte reste lisible en texte | grille absente → « aucun calcul effectué », jamais une matrice vide colorée |

### D. Formes toujours interdites

La liste d'ADR-017 est reconduite **intégralement** :

- halos ou néons permanents, glow de sélection ;
- noir pur comme fond ou surface ;
- cartes translucides floues (le blur reste réservé au rail ou à la fiche superposée) ;
- couleur seule sans texte, signe ou motif ;
- compte à rebours, horloge client, ou toute fraîcheur déduite de `Date.now()` ;
- radar ou nuage de points sans dimension multiple servie ;
- dégradé de fond plein sur une carte ;
- pulsation, aiguille animée, compteur roulant ;
- valeur abrégée côté client (« 12.4K ») ;
- score composite opaque, cadran décoratif, 3D ;
- toute forme sur une valeur non servie.

S'y ajoutent, sur demande explicite du brief : aucun bouton nommé Acheter,
Vendre, Trader, Exécuter, Placer un ordre ou Swap — interdiction déjà tenue par
la porte `no-raw-colors.test.ts`, qui refuse ce vocabulaire dans tout le code.

### E. Navigation cible

Le brief nomme douze espaces. La règle d'exécution d'ADR-017 et de
`PAGE_ARBITRATION.md` — « aucune capacité ne disparaît avant que sa remplaçante
soit prouvée » — impose d'**absorber, jamais de supprimer**.

| Actuel | Cible | Décision |
|---|---|---|
| `today`, `calendar`, `markets`, `opportunities`, `analysis`, `options`, `simulator`, `portfolio` | idem | `CONSERVER` |
| `catalysts` | Suivi | `RENOMMER + RECENTRER` |
| module `portfolio/performance/*` | Performance | `EXTRAIRE` |
| `components/ai/*` | Vertex IA | `EXTRAIRE` |
| `sources-reports` | Système | `RENOMMER` |
| `charts` | sous-vue d'Analyse | `ABSORBER` |
| `risks` | sous-vue de Performance | `ABSORBER` |

Les cinq règles d'exécution de `PAGE_ARBITRATION.md` s'appliquent au mouvement
inverse, verbatim. Aucune route API ne bouge. Chaque route retirée reçoit une
redirection permanente.

### F. Un composant de table partagé

`DataTable` devient la primitive unique des tables financières : en-tête
persistant, nombres alignés à droite en chasse fixe tabulaire, tri visible et
nommé, hauteur de ligne 42–46 px, virtualisation seulement sur mesure et sans
casser la sémantique, le focus ni la copie. Les vingt-et-une grammaires
existantes y migrent progressivement, une page par lot.

## Conséquences

### Attendues

- Une seule direction visuelle sur les douze destinations, vérifiable par les
  portes existantes.
- La discipline de vérité des données est renforcée, pas relâchée : les
  soixante-dix-sept absences restent absentes, avec leur motif.
- `text-muted` devient conforme AA là où il était en défaut — un gain
  d'accessibilité qui n'était pas demandé mais que la mesure a révélé.

### Coûts et contraintes

- **La référence de style n'est plus une image.** Tant que les quinze images ne
  sont pas versionnées, la fidélité se juge sur le contrat écrit et sur les
  captures produites à chaque lot, pas sur une comparaison pixel.
- Ré-extraire Vertex IA rouvre le défaut fermé au LOT-12 : un sélecteur de sujet
  proposant des sujets qu'aucune page n'affiche. La page ne listera que les
  trois sujets explicables par le contrat, et l'inspecteur des pages hôtes est
  conservé.
- Portefeuille porte douze modules depuis l'absorption de Performance ; son
  extraction ramène la page dans la limite « trois à cinq modules » de
  `.claude/rules/frontend.md`. C'est un effet de bord favorable, mesuré.

### Preuves d'application

- `apps/web/src/design/tokens-css.test.ts` : valeurs canoniques et cohérence
  clé ↔ valeur des rayons.
- `apps/web/src/design/canon-v2-docs.test.ts` : cohérence documentaire, étendue
  à cette décision.
- `apps/web/src/design/no-raw-colors.test.ts`, `no-fabricated-values.test.ts`,
  `no-authoritative-calculation.test.ts`, `no-ambiguous-dash.test.ts`,
  `one-dominant-per-page.test.ts` : inchangées, toujours applicables.
- `apps/web/src/components/widgets/catalog.test.ts` : douze catalogues, une
  dominante par page, teinte de page dans le vocabulaire typé.
