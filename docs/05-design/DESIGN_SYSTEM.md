# Design system — Black Glass 1.1 « Obsidian Signal »

> Portée Beta : interface Vertex exclusivement bureau/laptop. Les largeurs cible
> sont 1280, 1440 et 1600 px ; 1024 px sert seulement de dégradation laptop.
> L'interface téléphone est `LATER`. Le téléphone pilote Claude Code via Remote
> Control et n'affiche pas Vertex.

## ADN conservé

Fond noir/graphite, surfaces hiérarchisées, bordures argent discrètes, chiffres
tabulaires, violet réservé aux options, vert positif, corail négatif et ambre
avertissement. Un signal lime acide, rare et non financier, identifie la
sélection, le focus de marque et l'action principale. Aucun bleu de marque.

## Palette canonique neuve

```css
:root {
  --vx-black: #020304;
  --vx-app: #06080d;
  --vx-surface-0: #090c12;
  --vx-surface-1: #0e1219;
  --vx-surface-2: #141923;
  --vx-surface-3: #1a202b;
  --vx-hover: #202835;
  --vx-border-soft: rgba(232, 239, 249, 0.07);
  --vx-border: rgba(232, 239, 249, 0.11);
  --vx-border-strong: rgba(232, 239, 249, 0.18);
  --vx-text: #f5f7fb;
  --vx-text-secondary: #a8b0bf;
  --vx-text-muted: #747e8e;
  --vx-silver: #d4dae3;
  --vx-signal: #d4ff45;
  --vx-positive: #2bd99b;
  --vx-negative: #ff6070;
  --vx-warning: #f2b94b;
  --vx-option: #a87cf7;
  --vx-macro: #5bd2c2;
}
```

Le gris plus faible que `--vx-text-muted` n'est autorisé que pour décorations non textuelles après vérification de contraste. Aucun alias legacy `orange`, `blue`, `signal-green` ou surcharge en cascade.

## Typographie

- Geist Sans Variable pour l'interface, acquis depuis la source Vercel vérifiée
  et auto-hébergé sous OFL-1.1.
- Geist Mono Variable pour symboles, nombres et code, acquis depuis la même
  source vérifiée et auto-hébergé sous OFL-1.1.
- Chiffres tabulaires pour toutes les séries comparables.
- Corps 14 px par défaut, 13 px uniquement pour métadonnées conformes AA.

## Mise en page

- largeur utile maximale 1600 px ;
- rail desktop 232 px rétractable à 68 px ;
- grille 12 colonnes, gap 16–20 px ;
- un visuel dominant occupe 6 à 8 colonnes ;
- trois à cinq modules par page ;
- une carte seulement lorsqu'elle matérialise un groupe sémantique ;
- les détails secondaires vivent dans un `SideSheet`, pas dans une deuxième rangée de tuiles.

## Primitives communes

`AppShell`, `ContextBar`, `DataStateBoundary`, `FreshnessBadge`, `ProvenancePopover`, `EntitlementBadge`, `Metric`, `ChartFrame`, `AccessibleDataTable`, `EvidenceList`, `GateBadge`, `StatusBanner`, `SideSheet`, `NewsClusterRow`, `EventRow`.

Radix Primitives apporte le comportement accessible ; Vertex fournit tous les styles. Aucun thème générique prêt à l'emploi ne définit l'identité.

## Règles visuelles

- une couleur = une signification ;
- jamais couleur seule : texte, icône ou motif ;
- verre discret, pas de blur généralisé ;
- le signal lime n'exprime jamais une hausse, un score ou une validation ;
- gradients réservés à sélection/action principale ;
- jauges uniquement linéaires/segmentées, nommées et sourcées ; aucun cadran décoratif ou score opaque ;
- animations 140–220 ms et désactivables ;
- un seul bouton rempli par page ;
- unités, devise, fuseau, source et fraîcheur proches de la donnée ;
- réel, estimé, simulé et delayed possèdent des labels textuels permanents.
