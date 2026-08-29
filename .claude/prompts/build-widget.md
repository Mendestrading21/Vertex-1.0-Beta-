# Prompt — construire un widget canonique

Travaille sur `WIDGET_ID` dans le lot indiqué, sans élargir la page.

1. Valide sa définition contre `widget-definition-v1.schema.json`.
2. Écris la question, l'action analytique et l'équivalent texte.
3. Utilise l'icône du catalogue ; aucune nouvelle famille visuelle locale.
4. Consomme un contrat API généré ; aucun calcul financier TypeScript.
5. Implémente loading, live, delayed, partial, stale, offline, empty, error,
   not-entitled et unsupported selon le catalogue.
6. Respecte clavier, focus, contraste et reduced motion aux viewports desktop
   `1280×800`, `1440×900` et `1600×1000` ; contrôle `1024×768` comme
   dégradation laptop seulement si utile.
7. Respecte payload, rendu, virtualisation et downsampling.
8. Livre Storybook, tests composants, axe, captures et benchmark réel.

Vertex 1.0 Beta est **DESKTOP ONLY** : n'implémente ni `390`/`360`, bottom nav,
`MobileActionBar`, feuille basse, geste mobile dédié ou QA mobile.
`Mobile UI = LATER` ; préserve toutefois les contrats sémantiques et la hiérarchie
du contenu.
