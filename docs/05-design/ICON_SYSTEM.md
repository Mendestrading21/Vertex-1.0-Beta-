# Système d'icônes — Vertex Black Glass

## Décision

Lucide est l'unique bibliothèque d'icônes généralistes. Les vingt SVG Vertex de `design-assets/icons/custom/` ne couvrent que des concepts financiers ou de qualité de données qui n'existent pas clairement dans Lucide. Aucun mélange avec Radix Icons, Heroicons, Font Awesome, emojis, logos de fournisseurs ou pictogrammes dessinés au fil des pages.

Cette décision garde une silhouette homogène, réduit le bundle grâce aux imports nommés et empêche qu'une couleur ou une illustration remplace un libellé métier.

## Sources officielles vérifiées

- [Guide Lucide](https://lucide.dev/guide/) : géométrie cohérente, SVG optimisés et architecture compatible tree-shaking.
- [Lucide React](https://lucide.dev/guide/react/) : composants SVG typés, réglage de la taille/couleur/épaisseur et imports unitaires.
- [Accessibilité Radix Primitives](https://www.radix-ui.com/primitives/docs/overview/accessibility) : rôles ARIA, clavier et gestion du focus pour les primitives interactives.
- [Radix Accessible Icon](https://www.radix-ui.com/primitives/docs/utilities/accessible-icon) : ajout d'un nom accessible lorsqu'une icône porte seule le sens.
- [Licence Lucide](https://github.com/lucide-icons/lucide/blob/main/LICENSE) : conserver les notices ISC et celles des icônes Feather incorporées.

Les versions restent épinglées par le registre de dépendances ; ces liens servent de référence de conception, pas de demande d'installation implicite.

## Grammaire géométrique

| Propriété | Règle Vertex |
|---|---|
| Canevas | `viewBox="0 0 24 24"` |
| Trait | `currentColor`, `1.75`, bouts et jonctions arrondis |
| Remplissage | `none`, sauf petite surface d'état documentée ; aucun pictogramme custom actuel n'en utilise |
| Tailles | 16 px métadonnée, 18 px contrôle compact, 20 px navigation, 24 px état vide ou fiche |
| Zone interactive | 32×32 px minimum même si le glyphe mesure 18–20 px |
| Alignement | boîte optique 24 px ; ne pas corriger chaque page avec des marges locales |
| Couleur | héritée du texte ; jamais de couleur codée dans le fichier SVG |
| Animation | conteneur seulement ; ne pas déformer les chemins |

À 16, 18 ou 20 px, le composant commun fixe `strokeWidth={1.75}`. Une dérogation doit être mesurée sur écrans 1× et 2× et approuvée dans ce document, jamais injectée par une page.

## Règles d'usage accessibles

1. Une icône décorative est `aria-hidden="true"` et `focusable="false"`. Les SVG custom sont livrés ainsi par défaut.
2. Un bouton icône seule porte un `aria-label` sur le bouton et un `Tooltip` accessible ; l'icône reste masquée au lecteur d'écran.
3. Une icône informative sans texte visible est enveloppée par `AccessibleIcon` avec un libellé issu de `manifests/icon-catalog.yaml`.
4. Un état comporte toujours icône + libellé (`Bloqué`, `Retardé`, `Partiel`, etc.) ; vert, corail ou ambre ne suffisent jamais.
5. Les icônes ne sont jamais focusables séparément du contrôle qui les contient.
6. Le texte de remplacement décrit l'état ou l'action, pas la forme : « Données périmées », pas « cylindre avec sablier ».
7. Une icône répétée dans une table est décorative lorsque l'en-tête ou la cellule contient déjà le même libellé.

## Imports et performance

Autorisé :

```tsx
import { CalendarDays, Settings2 } from 'lucide-react';
```

Interdit dans le runtime : import global, sprite contenant toute la bibliothèque, nom d'icône construit depuis une chaîne ou `DynamicIcon` pour un cas statique. La table nom→composant de navigation est statique, typée et limitée aux icônes du catalogue.

Les SVG Vertex sont convertis en composants au build avec une chaîne auditée. Aucun SVG non fiable ne traverse `dangerouslySetInnerHTML`.

## Navigation des douze pages

| Page | Icône Lucide principale | Icône custom éventuelle | Libellé permanent |
|---|---|---|---|
| Aujourd'hui | `Sun` | `attention-queue` dans la dominante | Aujourd'hui |
| Calendrier | `CalendarDays` | `History` pour une révision | Calendrier |
| Marchés | `ChartLine` | `market-regime` | Marchés |
| Opportunités | `ScanSearch` | `gate-pass`, `gate-degrade`, `gate-block` | Opportunités |
| Analyse | `ChartCandlestick` | `evidence-rail`, `snapshot-sealed` | Analyse |
| Options | `Rows3` | `option-chain`, `volatility-smile`, `term-structure` | Options |
| Simulateur | `FlaskConical` | `payoff-curve`, `greeks-basket` | Simulateur |
| Portefeuille | `BriefcaseBusiness` | `manual-ledger` | Portefeuille |
| Suivi | `ClipboardCheck` | `thesis-active`, `History` | Suivi |
| Performance | `ChartSpline` | aucun | Performance |
| Vertex AI | `Bot` | `evidence-rail` pour les citations | Vertex AI |
| Système | `Settings2` | `source-coverage`, `audit-trace` | Système |

Le rail desktop rétracté affiche les icônes, mais un tooltip et le nom accessible
restent obligatoires. Les douze pages restent accessibles dans le rail bureau à
1280, 1440 et 1600 px. Une navigation mobile est `LATER` et n'entre ni dans les
composants ni dans la QA de la Beta.

## Couleur et statut

- neutre : `--vx-text-secondary` ;
- sélection : `--vx-text` avec surface/contour, jamais accent seul ;
- positif confirmé : `--vx-positive` + texte ;
- négatif confirmé : `--vx-negative` + texte ;
- avertissement/retard : `--vx-warning` + texte ;
- options : `--vx-option` uniquement pour identifier la classe d'actif, pas un résultat positif ;
- macro : `--vx-macro` uniquement pour catégoriser la source ;
- teinte secondaire de page (ADR-017, `docs/09-adr/017-titanium-ledger-v2-formes-widgets.md`) : les deux règles ci-dessus régissent la couleur d'une icône ; la famille déclarée par une page (`macro`, `option` ou `warning`) colore, par `--vx-page-accent*`, les formes de widgets sur données servies (anneaux, arcs, aires, rails) et jamais un statut d'icône — une icône `--vx-macro` continue de catégoriser une source, une icône `--vx-option` d'identifier la classe d'actif.

Une direction haussière ou baissière n'est pas un statut de sécurité. `scenario-bull` et `scenario-bear` héritent de la couleur du contexte et restent nommés textuellement.

## Icônes custom et gouvernance

Le catalogue YAML est l'autorité pour l'identifiant, le fichier, le sens et les contextes autorisés. Avant d'ajouter un glyphe :

1. chercher le concept dans Lucide ;
2. vérifier qu'un libellé sans icône ne suffit pas ;
3. prouver un usage sur au moins deux composants ou une dominante irremplaçable ;
4. dessiner sur la même grille 24 px ;
5. vérifier XML, rendu 16/20/24 px, contraste, nom accessible et absence de duplication ;
6. ajouter tests visuels clair/sombre — Black Glass reste le thème produit, le fond clair sert seulement au contrôle des traits.

Les logos IBKR, TradingView, SEC ou autres fournisseurs ne sont pas recréés. Leur nom textuel et leur provenance suffisent ; tout logo futur exige une source officielle, une licence et une règle de marque.

## Critères d'acceptation

- une seule dépendance d'icônes généralistes dans le bundle ;
- imports Lucide nommés et arbre mort éliminé ;
- vingt SVG custom exactement, XML valides et conformes aux six attributs géométriques ;
- zéro couleur fixe dans les SVG custom ;
- chaque contrôle icône seule possède nom accessible et tooltip ;
- chaque statut reste compréhensible sans couleur et sans icône ;
- aucune icône ne déclenche, calcule ou suggère une action financière.
