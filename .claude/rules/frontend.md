---
paths:
  - "apps/web/**"
  - "packages/typescript/ui/**"
  - "packages/typescript/charts/**"
---

# Frontend — règles obligatoires

## Rôle

- Le frontend présente les DTO de l’API et collecte des intentions utilisateur ; il n’est jamais une autorité financière.
- Ne calculer en TypeScript aucun prix, IV, Greek, rendement, risque, ratio, score, probabilité, gate, classement financier ou verdict faisant autorité.
- Ne pas reconstruire un statut depuis des champs partiels. Afficher le statut canonique et sa version reçus de l’API.
- Utiliser le client TypeScript généré depuis OpenAPI. Aucun type réseau critique dupliqué manuellement.

## États de données

Chaque vue et composant connecté couvre explicitement `loading`, `refreshing`, `empty`, `partial`, `delayed`, `stale`, `offline` et `error`.

- Ne jamais remplacer une donnée absente par `0`, `—` ambigu, une fixture ou une ancienne valeur non datée.
- Afficher source, `as_of`, fraîcheur, droit et nature réelle/retardée/théorique/simulée lorsque la décision en dépend.
- En `stale` ou `offline`, figer les actions dépendantes du live et afficher un watermark explicite.
- Les fixtures et mocks ne sont activés qu’en test/Storybook avec un badge `DÉMONSTRATION` impossible à masquer.

## Sobriété et cohérence

- Une page répond à une question, possède un visuel dominant, trois à cinq modules et une seule action principale au maximum.
- Réutiliser les tokens et primitives du design system ; aucune couleur, ombre, typographie ou statut codé en dur hors tokens.
- Charger ECharts et Lightweight Charts uniquement sur les routes qui les utilisent.
- Ne pas ajouter de tableau, bouton ou métrique sans décision utilisateur précise et critère d’acceptation.
- Aucun graphique décoratif, 3D, jauge ambiguë, double axe non justifié ou animation qui altère la lecture.

## Accessibilité et périmètre desktop

- Cibler WCAG 2.2 AA et zéro violation axe critique ou sérieuse.
- Tout parcours fonctionne au clavier avec ordre logique, focus visible et restauration du focus après dialogue ou panneau.
- La couleur n’est jamais le seul vecteur d’information ; utiliser texte, forme ou motif en complément.
- Tout graphique essentiel comporte titre, unité, timezone, source, fraîcheur, légende et alternative textuelle ou tabulaire équivalente.
- Respecter `prefers-reduced-motion`, zoom 200 %, contraste et lecteurs d’écran.
- Vertex 1.0 Beta est **DESKTOP ONLY**. Les viewports de phase 1 sont
  `1280×800`, `1440×900` et `1600×1000`.
- `1024×768` peut servir de contrôle de dégradation laptop si le lot le justifie ;
  ce n’est ni un breakpoint mobile ni une quatrième cible de release.
- Ne pas implémenter ni exiger en phase 1 de viewport `390`/`360`, bottom nav,
  `MobileActionBar`, feuille basse, geste tactile dédié ou QA mobile.
- `Mobile UI = LATER`. Conserver dans les contrats et composants la sémantique des
  états, l’ordre du contenu, la provenance, le risque et les actions afin de ne pas
  compromettre une adaptation future, sans livrer de branche mobile maintenant.

## Qualité

- TypeScript strict, aucune assertion non vérifiée, aucun `any` non isolé et documenté.
- Gérer erreurs et annulations réseau ; ne pas lancer de requête concurrente illimitée.
- Tester composants, états, clavier, visuels et parcours Playwright avant de déclarer la page terminée.
- Respecter les budgets de `docs/06-quality/PERFORMANCE_BUDGETS.md` ; toute exception exige mesure et ADR.
