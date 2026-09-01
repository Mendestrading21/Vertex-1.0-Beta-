# Identité Titanium Ledger

## Thèse perceptive

Titanium Ledger n'est ni un thème crypto néon, ni un clone de terminal. C'est un
instrument de lecture Black Glass : noir pétrole très discret pour le silence,
verre graphite gris-vert pour les plans, titane pour la structure, argent pour
les valeurs et ambre rare pour l'intention. La densité vient de la précision des
alignements et non de l'accumulation d'effets. `canonical-visual.md` et sa capture
priment sur toute formulation plus ancienne de cette référence.

À la première seconde, l'utilisateur doit percevoir :

1. où il se trouve ;
2. quelle question l'écran traite ;
3. quel objet contient la preuve principale ;
4. si les données sont complètes, fraîches et autorisées ;
5. quelle action est possible sans confondre analyse et exécution.

## Palette et rôles

La source unique est `apps/web/src/design/tokens.ts`. Le CSS généré ne se modifie
pas à la main. Aucune couleur brute ailleurs que dans les fichiers autorisés par
la porte `no-raw-colors`.

| Famille | Rôle | Règle |
|---|---|---|
| noir / app | profondeur et canevas | jamais du noir pur partout ; conserver des plans lisibles |
| surface 0–3 | hiérarchie de panneaux | une marche par niveau, pas une carte dans une carte sans raison |
| argent / titane | valeur, structure, microcopie | argent pour le premier plan, titane pour le contexte |
| signal ambre | marque, actif, action | rare, jamais synonyme de gain |
| positif / négatif | sens financier | texte ou symbole obligatoire en plus de la couleur |
| option | domaine options | ne remplace pas l'état positif/négatif |
| macro | série contextuelle | secondaire, jamais verdict |

### Protocole de nuance

- Créer un token seulement si son rôle se répète sur au moins deux objets ou si
  une exigence d'accessibilité l'impose.
- Nommer le rôle, pas la couleur : `surface-2`, `signal-soft`, `text-muted`.
- Vérifier le contraste dans le contexte réel, y compris sur gradient ou overlay.
- Pour une nouvelle famille, définir au maximum : valeur principale, valeur
  atténuée, fond faible. Éviter les gammes décoratives de dix tons.
- Lorsque le navigateur ciblé le permet, OKLCH peut servir à explorer des pas de
  luminosité perceptuellement réguliers ; commiter ensuite une valeur compatible
  et testée dans la source typée.
- Une différence subtile de surface ne porte jamais seule une information.

## Surfaces et lumière

- Le canevas reste presque mat ; les gradients sont des variations de matériau,
  pas des projecteurs.
- Un seul Ledger Frame domine la page. Les panneaux voisins sont plus calmes.
- Liseré, angle métallique et grille doivent rester sous le contenu.
- Les ombres donnent un plan, jamais un halo lumineux permanent.
- La transparence ne doit pas diminuer la lisibilité. Prévoir une variante opaque
  avec `prefers-reduced-transparency` lorsqu'un effet translucide est introduit.
- Sous `forced-colors`, préserver structure, focus et signification avec les
  couleurs système ; ne pas forcer la palette de marque.

## Logo et signature

- Symbole facetté argent/titane, géométrie hexagonale/polyédrique conforme à la
  capture canonique ; aucun `VX`, symbole de hausse ou baisse.
- Le rail n'ajoute pas de mot-symbole à côté du symbole.
- `VERTEX 1.0 BETA` est un cartouche de version indépendant, en bas à gauche.
- Pas d'ombre néon, chandelier, pièce, flèche, vert ou rouge dans la marque.
- Toute variante doit rester lisible monochrome et à petite taille.

## Typographie

- Sans-serif sobre pour titres et lecture continue ; mono pour codes, unités,
  provenance, statuts et nombres tabulaires.
- Employer `font-variant-numeric: tabular-nums` pour séries et tableaux.
- Une valeur principale peut être grande ; son unité, sa période et son état ne
  doivent jamais disparaître.
- Limiter les capitales aux micro-libellés et en-têtes courts.
- Préserver un interlignage lisible ; ne pas compenser la densité par une police
  trop petite ou trop grise.

## Composition

- Grille conceptuelle de 12 colonnes, espace courant de 16 à 24 px.
- Dominante de 7 à 9 colonnes, rail de preuve de 3 à 5 colonnes.
- Le premier viewport porte la question et le principal outil décisionnel.
- Un seul bouton rempli par page ; les autres actions sont secondaires.
- Les alignements verticaux des valeurs priment sur la symétrie décorative.
- Les pages ont des rythmes différents : file, carte, graphique, chaîne, ledger,
  calendrier ou conversation. Ne pas les réduire à un même bento.

## Mouvement et réponse

- 90 ms ligne, 140 ms contrôle, 180 ms rail/panneau ; pas d'animation financière
  continue.
- Respecter `prefers-reduced-motion: reduce` sans animation de substitution.
- Les squelettes réservent l'espace final pour limiter les déplacements de mise
  en page.
- Aucun mouvement ne doit faire croire qu'une donnée est plus fraîche qu'elle ne
  l'est.

## Critères de qualité

- contraste texte normal au moins 4,5:1, grand texte 3:1 ;
- focus clairement perceptible avec contraste suffisant et surface visible ;
- cibles d'interaction conformes à WCAG 2.2 ou espacées de façon équivalente ;
- zoom et reflow vérifiés dans le périmètre desktop déclaré ;
- modes mouvement réduit, contraste renforcé, couleurs forcées et transparence
  réduite considérés dès qu'un composant les sollicite ;
- aucune information portée uniquement par teinte, opacité ou mouvement.
