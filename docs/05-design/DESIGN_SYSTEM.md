# Design system — Black Glass 1.2 « Titanium Ledger »

> Portée Beta : interface Vertex exclusivement bureau/laptop. Les largeurs cible
> sont 1280, 1440 et 1600 px ; 1024 px sert seulement de dégradation laptop.
> L'interface téléphone est `LATER`. Le téléphone pilote Claude Code via Remote
> Control et n'affiche pas Vertex.

## ADN conservé

Fond noir/graphite chaud, surfaces hiérarchisées, bordures titane discrètes,
chiffres tabulaires, violet réservé aux options, vert positif et corail négatif.
Un signal ambre métallique, rare et non financier, identifie la sélection, le
focus de marque et l'action principale. Aucun bleu de marque.

## Palette canonique neuve

```css
:root {
  --vx-black: #030302;
  --vx-app: #080806;
  --vx-surface-0: #0d0d0b;
  --vx-surface-1: #141310;
  --vx-surface-2: #1b1915;
  --vx-surface-3: #242119;
  --vx-text: #f6f2e8;
  --vx-text-secondary: #b8b0a0;
  --vx-text-muted: #948c7d;
  --vx-silver: #d8d3c7;
  --vx-titanium: #aaa497;
  --vx-signal: #d7a94a;
  --vx-signal-bright: #f2c76b;
  --vx-positive: #50c992;
  --vx-negative: #ef6f6c;
  --vx-warning: #f0c36a;
  --vx-option: #a88ae8;
  --vx-macro: #6bc5bc;
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
- rail desktop 248 px rétractable à 68 px ;
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
- le signal ambre n'exprime jamais une hausse, un score ou une validation ;
- gradients : sélection/action principale, variation de matériau et — depuis ADR-017 — l'aire sous une série servie (dégradé vertical d'une teinte sémantique vers sa transparence, tokens `<famille>-gradient-start/-end`) ; jamais un fond plein de carte ;
- jauges nommées et sourcées uniquement : barre linéaire, bullet, bande segmentée et, sur une valeur bornée servie avec seuils et position servie (ADR-017), arc gradué ; anneau à chiffre central sur des parts servies ; aucun cadran décoratif, aiguille animée ou score opaque ;
- une teinte sémantique secondaire par page, déclarée dans le catalogue parmi `macro`, `option`, `warning` (ADR-017) — jamais `positive` ni `negative`, réservés au signe financier servi ; l'ambre reste la seule lumière de la dominante ;
- animations 140–220 ms et désactivables ;
- un seul bouton rempli par page ;
- unités, devise, fuseau, source et fraîcheur proches de la donnée ;
- réel, estimé, simulé et delayed possèdent des labels textuels permanents.
