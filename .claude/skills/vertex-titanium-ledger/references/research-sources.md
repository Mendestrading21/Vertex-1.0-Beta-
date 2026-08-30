# Sources officielles et conséquences Vertex

Vérifiées le 30 août 2026. Ce registre synthétise les décisions ; il ne remplace
pas la lecture de la version courante lorsqu'un lot dépend d'un détail précis.

| Source officielle | Apport | Conséquence Titanium Ledger |
|---|---|---|
| [Claude Code — Skills](https://docs.anthropic.com/en/docs/claude-code/skills) | dossier de consignes et ressources découvert automatiquement | skill court comme routeur, détails dans `references/`, script déterministe séparé |
| [DTCG — Format 2025.10](https://www.designtokens.org/tr/drafts/format/) | types, références et structure de tokens | source typée unique, noms par rôle, alias explicites, génération contrôlée |
| [DTCG — Color](https://www.designtokens.org/tr/drafts/color/) | sémantique des couleurs et espaces colorimétriques | documenter espace/alpha, éviter les chaînes ambiguës |
| [CSS Color 4](https://www.w3.org/TR/css-color-4/) | Oklab/OKLCH et couleurs perceptuelles | utiliser OKLCH pour explorer des pas réguliers, puis tester la compatibilité et le contraste |
| [WCAG 2.2 — contraste](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum) | seuils de contraste du texte | 4,5:1 texte courant, 3:1 grand texte, contrôlé dans le contexte réel |
| [WCAG 2.2 — focus](https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html) | focus visible et suffisamment contrasté | anneau indépendant de la couleur de marque et visible sur toutes surfaces |
| [WCAG 2.2 — reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow) | lecture sans perte à zoom élevé | tester et documenter honnêtement la dette desktop existante |
| [WAI ARIA APG — patterns](https://www.w3.org/WAI/ARIA/apg/patterns/) | clavier et sémantique des widgets | utiliser table native ; réserver grid/dialog/combobox aux interactions complètes |
| [WAI APG — noms et descriptions](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/) | calcul des noms accessibles | préférer libellés visibles, captions et `aria-labelledby` à des labels redondants |
| [MDN — reduced motion](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/%40media/prefers-reduced-motion) | préférence de mouvement | annuler les animations non essentielles, sans effet de remplacement |
| [MDN — forced colors](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/%40media/forced-colors) | palette système à contraste forcé | préserver structure, état et focus sans imposer les couleurs Vertex |
| [MDN — reduced transparency](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/%40media/prefers-reduced-transparency) | réduction des effets translucides | fournir une surface opaque lorsque verre/scrim est utilisé |
| [IBM Carbon — dashboards](https://carbondesignsystem.com/data-visualization/dashboards/) | hiérarchie et nombre limité de métriques | une question, une dominante et peu d'indicateurs de soutien |
| [IBM Carbon — palettes dataviz](https://carbondesignsystem.com/data-visualization/color-palettes/) | attribution cohérente des séries | couleur stable entre vues, palette limitée, sémantique avant décoration |
| [IBM Carbon — statuts](https://carbondesignsystem.com/patterns/status-indicator-pattern/) | statut par plusieurs indices | forme, icône ou texte en plus de la couleur |
| [Apache ECharts — ARIA](https://echarts.apache.org/handbook/en/best-practices/aria/) | activation réelle de l'accessibilité ECharts | importer `AriaComponent`, tester le DOM ; `aria: {}` seul ne suffit pas |
| [Lightweight Charts — screen readers](https://tradingview.github.io/lightweight-charts/tutorials/a11y/screenreader) | figure, annonces et descriptions | fournir titre, description, valeur explorée et table contrôlée par Vertex |
| [Lightweight Charts — crosshair](https://tradingview.github.io/lightweight-charts/tutorials/customization/crosshair) | exploration précise | date/série/valeur exactes et interaction clavier équivalente |
| [React — lazy](https://react.dev/reference/react/lazy) | chargement différé de composants | maintenir les pages et moteurs lourds hors fermeture initiale |
| [Vite — features](https://vite.dev/guide/features) | dynamic imports et préchargement des dépendances communes | mesurer les chunks de route, ne pas supposer le découpage |
| [Web Vitals](https://web.dev/articles/vitals) | LCP, INP, CLS et distinction labo/terrain | budget laboratoire + vérité explicite sur l'absence de données terrain |

## Règles de veille

1. Sources normatives ou auteurs du produit d'abord.
2. Une source doit modifier une règle, un test ou une décision ; sinon ne pas
   l'ajouter.
3. Enregistrer la date, la version et la compatibilité avec les dépendances
   épinglées.
4. Les galeries visuelles servent au moodboard, jamais à définir la sémantique,
   les données ou le code.
5. Toute ressource externe copiée exige licence et provenance ; préférer une
   implémentation originale avec les primitives Vertex.

