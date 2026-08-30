# Rapport d'accessibilité — Vertex 1.0 Beta

**Cible déclarée** : WCAG 2.2 niveau AA, périmètre desktop
(`.claude/rules/frontend.md`).
**État global** : **PARTIELLEMENT CONFORME**. Un critère AA est mesuré non
conforme, et une vérification indispensable n'a pas été faite. Les deux sont
nommés ci-dessous ; ce document ne revendique aucune conformité qu'il ne
prouve pas.

Toutes les mesures ci-dessous proviennent d'exécutions réelles de
`apps/web/e2e/accessibility.spec.ts` sur le pipeline complet (PostgreSQL réel,
worker réel, API réelle, build de production servi par `vite preview`), sur
une population **SYNTHETIC**. Aucune n'est estimée.

## Périmètre mesuré

12 routes authentifiées : `/today`, `/calendar`, `/markets`,
`/opportunities`, `/analysis`, `/options`, `/simulator`, `/portfolio`,
`/follow-up`, `/performance`, `/ai`, `/system`.
La 13ᵉ route, `/auth`, est couverte par `e2e/auth.spec.ts`.

Trois viewports de release : 1280×800, 1440×900, 1600×1000.
`1024×768` sert de contrôle de dégradation laptop (`e2e/smoke.spec.ts`) ; ce
n'est ni un breakpoint mobile ni une quatrième cible.

## Résultats

| Vérification | Critères visés | Résultat mesuré |
|---|---|---|
| axe restreint aux étiquettes WCAG (`wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`), **tous impacts** | l'ensemble des critères A/AA couverts par axe, contraste (1.4.3) inclus | **0 violation** sur 12 routes × 3 viewports |
| Traversée clavier et focus visible | 2.1.1, 2.4.3, 2.4.7, 2.4.11 | la première tabulation atteint un élément interactif portant un indicateur de focus visible sur **12/12** routes × 3 viewports |
| `prefers-reduced-motion` | 2.3.3 | **0 animation ou transition > 100 ms** sur 12 routes × 3 viewports |
| Redimensionnement 200 % (reflow) | 1.4.10 | **NON CONFORME** — voir ci-dessous |
| Revue lecteur d'écran par une personne | 1.3.1, 4.1.2 en usage réel | **NON FAITE** — voir ci-dessous |

Total : **144 assertions vertes** (48 par viewport, 3 viewports).

Les specs de page exécutent en outre axe avec un seuil de zéro violation
critique ou sérieuse sur chaque parcours ; cette campagne les complète, elle ne
les remplace pas.

## Écart 1 — WCAG 1.4.10 (Reflow) : non conforme, mesuré

L'enveloppe applicative porte `min-width: 1024px`
(`apps/web/src/styles/global.css`), plancher « desktop only » de la phase 1.

À 200 % de zoom sur une fenêtre de 1280 px, la largeur CSS disponible tombe à
640 px, sous ce plancher. La page défile alors horizontalement, ce que le
critère 1.4.10 interdit.

**Mesure** : largeur défilable de **1024 px exactement** sur les 12 routes,
soit un débordement de **384 px** à 640 px de large. La valeur est identique
partout : le débordement vient du seul plancher déclaré, aucun composant n'y
ajoute sa propre largeur minimale.

**Aucun contenu n'est perdu** : le défilement horizontal atteint le bord droit
du contenu sur les 12 routes ; l'information reste accessible, au prix d'un
défilement bidimensionnel.

Les tests correspondants épinglent cette réalité au lieu de la masquer : ils
échouent si la largeur défilable s'éloigne du plancher déclaré, c'est-à-dire si
la situation empire.

**Ce que lever cet écart suppose** : retirer le plancher et refondre les mises
en page larges (matrices, chaînes d'options, tables de 10 000 lignes) pour
qu'elles se réorganisent sous 1024 px. C'est un chantier d'interface entier, et
il entre en tension directe avec la décision « desktop only, mobile UI =
LATER » de la phase 1. Inscrit à `docs/99-status/DEBT.md`.

## Écart 2 — revue lecteur d'écran : non faite

Aucune revue par un lecteur d'écran réel (NVDA, VoiceOver, Orca), conduite par
une personne, n'a eu lieu. `.claude/rules/testing.md` l'exige pour les parcours
critiques.

Aucun outil automatique ne la remplace : axe vérifie des règles sur le DOM, il
n'écoute pas ce qu'un utilisateur entend, ne juge pas si l'ordre de lecture a
du sens, et ne dit pas si un libellé est compréhensible. Trois défauts de
libellé corrigés pendant la session — des `aria-label` posés sur des éléments
sans rôle, où un lecteur d'écran annonçait « tiret » au lieu de « bid absent »,
« strike illisible », « as_of absent » — avaient été trouvés par le lint, pas
par axe.

Cette revue reste une **décision et une action humaines**, préalable à toute
revendication de conformité AA.

## Ce que ce rapport ne prouve pas

- axe ne couvre qu'une partie des critères WCAG ; « 0 violation axe » ne vaut
  pas « conforme AA ».
- La traversée clavier vérifiée est la **première** tabulation, pas le parcours
  complet ni la restauration du focus après un panneau ou une boîte de dialogue.
- Le seuil de 100 ms pour `prefers-reduced-motion` est un choix écrit dans le
  test, pas une valeur normative.
- Les mesures viennent de Chromium uniquement. Firefox et WebKit sont exécutés
  par `.github/workflows/nightly.yml`, qui **n'a jamais tourné** à ce jour
  (`docs/99-status/DEBT.md`).
- La population est SYNTHETIC : aucune donnée réelle n'a encore été observée.

## Comment reproduire

```bash
export VERTEX_TEST_DATABASE_URL='postgresql+psycopg://<user>:<password>@127.0.0.1:5432/<base_jetable>'
cd apps/web
pnpm exec playwright test e2e/accessibility.spec.ts
```
