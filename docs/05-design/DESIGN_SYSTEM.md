# Design system — Black Glass 1.0

> Portée Beta : interface Vertex exclusivement bureau/laptop. Les largeurs cible
> sont 1280, 1440 et 1600 px ; 1024 px sert seulement de dégradation laptop.
> L'interface téléphone est `LATER`. Le téléphone pilote Claude Code via Remote
> Control et n'affiche pas Vertex.

## ADN conservé

Fond noir/graphite, surfaces très proches, bordures argent discrètes, chiffres tabulaires, violet réservé aux options, vert positif, corail négatif et ambre avertissement. Aucun bleu de marque.

## Palette canonique neuve

```css
:root {
  --vx-black: #040504;
  --vx-app: #08090b;
  --vx-surface-0: #0b0c0f;
  --vx-surface-1: #101216;
  --vx-surface-2: #15171c;
  --vx-surface-3: #1b1e23;
  --vx-hover: #232830;
  --vx-border-soft: rgba(222, 227, 237, 0.09);
  --vx-border: rgba(222, 227, 237, 0.14);
  --vx-border-strong: rgba(222, 227, 237, 0.22);
  --vx-text: #f3f5f8;
  --vx-text-secondary: #b7bcc4;
  --vx-text-muted: #828892;
  --vx-silver: #c9cdd4;
  --vx-positive: #36c889;
  --vx-negative: #ed655c;
  --vx-warning: #dda23b;
  --vx-option: #9c79d0;
  --vx-macro: #53b9ad;
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
- gradients réservés à sélection/action principale ;
- jauges uniquement linéaires/segmentées, nommées et sourcées ; aucun cadran décoratif ou score opaque ;
- animations 140–220 ms et désactivables ;
- un seul bouton rempli par page ;
- unités, devise, fuseau, source et fraîcheur proches de la donnée ;
- réel, estimé, simulé et delayed possèdent des labels textuels permanents.
