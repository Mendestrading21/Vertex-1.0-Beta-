# Mouvement et micro-interactions

## Intention

Le mouvement confirme une action, révèle une relation spatiale ou signale qu'une donnée se rafraîchit. Il ne dramatise jamais une variation financière et ne transforme pas Black Glass en interface de jeu.

## Tokens

| Token | Durée | Usage |
|---|---:|---|
| `--vx-motion-instant` | 90 ms | hover/focus visuel, sans déplacement |
| `--vx-motion-fast` | 140 ms | sélection, badge, bouton |
| `--vx-motion-base` | 180 ms | accordéon court, contenu conditionnel |
| `--vx-motion-slow` | 220 ms | sheet, dialog, changement de panneau |
| `--vx-motion-data` (généré : `--vx-motion-600`) | 600 ms max | surbrillance unique d'une valeur mise à jour (ADR-017) |

Courbes :

```css
--vx-ease-standard: cubic-bezier(.2, 0, 0, 1);
--vx-ease-enter: cubic-bezier(0, 0, .2, 1);
--vx-ease-exit: cubic-bezier(.4, 0, 1, 1);
```

Une transition ne dépasse pas 220 ms, sauf la surbrillance non répétée d'une mise à jour. Aucun `spring`, rebond, overshoot ou inertie décorative.

## Micro-interactions autorisées

| Interaction | Comportement | Reduced motion |
|---|---|---|
| Bouton | fond/bordure 90–140 ms ; déplacement ≤ 1 px au press | couleur/bordure immédiate |
| Ligne de table | surface de hover ; focus ring séparé ; sélection persistante | identique sans transition |
| Tooltip | délai d'ouverture cohérent ; fermeture immédiate au blur/Escape | identique |
| Accordion | hauteur/opacité 180 ms via états Radix | ouverture instantanée |
| SideSheet/Dialog | opacité + translation 8–12 px, 220 ms ; focus géré par Radix | opacité 90 ms, aucune translation |
| Navigation | indicateur de sélection 140 ms, sans glissement entre pages | indicateur immédiat |
| Refresh | petit indicateur tournant, ancien snapshot conservé | texte « Actualisation » sans rotation |
| Valeur mise à jour | fond argent discret une fois, 600 ms ; `aria-live` regroupé | contour statique 1 s |
| Stale/delayed | badge stable, heure exacte ; aucune pulsation | identique |
| Graphique | crosshair et tooltip répondent directement ; pan/zoom au pointeur et au clavier | animations de séries désactivées |
| Toast | entrée 180 ms, temporisation suffisante, pause au focus/hover | apparition immédiate |

Aucun son ni feedback haptique n'entre dans la Beta bureau.

## Radix et état

Utiliser les attributs `data-state`, `data-side` et `data-disabled` exposés par Radix au lieu de maintenir une seconde machine d'état visuelle. Un composant passé via `asChild` propage toutes les props, événements et refs ; le wrapper Vertex ne neutralise jamais la gestion du clavier ou du focus.

Le focus est déplacé seulement lorsqu'un pattern WAI-ARIA l'exige. Après fermeture d'un dialog/sheet, il retourne au déclencheur ou à un successeur explicite si ce déclencheur a disparu.

## Données et graphiques

- une nouvelle quote ne fait pas rouler tous les chiffres ; seule la cellule changée peut recevoir une surbrillance unique ;
- positif/négatif n'utilise jamais une direction de mouvement comme signification ;
- un changement de rang canonique arrive depuis le serveur et ne s'anime pas comme une victoire/défaite ;
- `refreshing` garde la donnée précédente et son `as_of` ; aucun skeleton flash ;
- Lightweight Charts reçoit des mises à jour incrémentales ; une réinitialisation complète de série n'est pas une animation ;
- ECharts désactive les animations initiales pour les gros datasets et toute vue comparant précisément des positions ;
- les transitions entre deux snapshots ne doivent pas interpoler des valeurs qui n'ont jamais existé ;
- aucune interpolation, agrégation ou physique financière n'est exécutée en JavaScript pour produire une animation.

## Chargement

Premier chargement : squelette fidèle à la géométrie, sans fausse donnée ni shimmer agressif. Refresh : conserver le contenu. Job long : étapes textuelles reçues du serveur, temps écoulé et possibilité d'annuler lorsque le contrat le permet.

Les placeholders ne simulent ni chandeliers, ni P&L, ni courbe de payoff. Une zone graphique vide montre son cadre, titre et état.

## Erreurs et actions sensibles

- validation inline après blur ou submit, jamais tremblement du champ ;
- erreur serveur annoncée dans la région concernée, focus sur le résumé seulement après submit ;
- diagnostic système et import CSV montrent progression réelle, jamais barre fictive ;
- une action irréversible exige `AlertDialog`, formulation précise et focus initial sur l'action sûre ;
- Vertex n'exécute aucun ordre : aucune micro-interaction ne doit imiter confirmation, remplissage ou succès de trading.

## Préférence reduced motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
  }
}
```

Cette règle globale est un filet de sécurité. Chaque composant doit aussi proposer un état final correct sans dépendre d'un événement `animationend`.

## Interdictions

- parallaxe, particules, blobs, reflets mouvants, halos pulsants et fond animé ;
- cartes flottantes en perspective, tilt, 3D, WebGL décoratif ou ECharts GL ;
- compteur roulant pour prix/P&L ;
- confettis, succès sonore, tremblement d'erreur ;
- animation infinie hors indicateur de tâche réellement active ;
- auto-scroll d'une file, carrousel ou ticker d'actualités ;
- transition qui masque provenance, fraîcheur, contradiction ou gate.

## Tests

- captures visuelles au début, milieu et fin des transitions critiques ;
- Playwright avec `reducedMotion: 'reduce'` sur navigation, sheet, dialog, refresh et graphiques ;
- test clavier/Escape/retour focus de chaque wrapper Radix ;
- test d'une rafale de 20 mises à jour : pas de clignotement continu, INP ≤ 200 ms et 60 FPS ordinaire ;
- aucune animation au chargement d'un dataset dense ;
- audit épilepsie : zéro flash à plus de trois occurrences/seconde ;
- test architectural : aucune fonction de calcul financier appelée depuis une animation.
