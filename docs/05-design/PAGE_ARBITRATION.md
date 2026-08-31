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
