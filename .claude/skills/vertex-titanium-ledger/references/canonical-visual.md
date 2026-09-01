# Contrat visuel canonique — Vertex 1.0 Beta

## Source unique

La seule référence de style est :

`../assets/vertex-dashboard-canonical.png`

Empreinte SHA-256 verrouillée :
`eb2eb0fc2105a98203e571381aec7765775d80aacec3513def10e99c9fdc7ace`.
Toute différence d'empreinte exige une nouvelle validation explicite de
l'utilisateur ; elle ne constitue jamais une « amélioration » automatique.

Elle fixe le shell, le matériau, le logo, la densité, la palette, les rayons,
les bordures, la lumière, la navigation et la hiérarchie. Les six planches de
pages dans `assets/` ne servent qu'à montrer comment varier le contenu central.
En cas de contradiction, revenir à la capture canonique.

## Anatomie immuable du shell

1. monogramme facetté argent/titane en haut à gauche, sans texte adjacent ;
2. rail gauche fin et intégré au fond, sans grande plaque flottante ;
3. seul l'item actif reçoit une capsule ambre translucide et son icône ambre ;
4. ticker horizontal compact en haut, dans une surface vitrée continue ;
5. badge de mode, cloche et fraîcheur en haut à droite ;
6. zone de travail dense avec une dominante centrale et un inspecteur contextuel
   à droite ;
7. cartouche `VERTEX 1.0 BETA` discret en bas à gauche ;
8. fond presque noir à nuance pétrole très faible, avec arcs orbitaux subtils.

Le shell reste identique sur les douze destinations. Seuls l'item actif, le
titre, la dominante, les modules secondaires et l'inspecteur changent.

## Matériau Black Glass

- Fond : noir bleuté/pétrole très sombre, jamais bleu lumineux ni noir plat.
- Panneaux : verre graphite gris-vert, translucide mais parfaitement lisible.
- Bordures : titane froid d'un pixel, plus clair au bord supérieur.
- Ombres : profondeur courte et mate ; aucun halo néon permanent.
- Reflets : un reflet interne très faible, jamais une bande décorative.
- Rayon : moyen et constant ; les cartes ne doivent pas devenir des bulles.
- Arrière-plan : décor presque invisible, sous le niveau de contraste du texte.

Les valeurs de départ ci-dessous sont des ancres à calibrer par comparaison
rendue, pas des couleurs à répéter directement dans les composants :

| Rôle | Ancre |
|---|---:|
| canevas profond | `#061016` |
| verre principal | `rgba(22, 34, 39, 0.76)` |
| verre élevé | `rgba(27, 40, 45, 0.86)` |
| bord titane | `rgba(164, 177, 176, 0.42)` |
| texte principal | `#F1F0EB` |
| texte secondaire | `#9AA3A2` |
| ambre interface | `#D58B17` |
| turquoise analytique | `#36B9AD` |
| positif financier | `#66BE72` |
| négatif financier | `#E4573C` |

Centraliser ces rôles dans la source typée de tokens. Une différence de nuance
doit répondre à un rôle, un contraste ou une profondeur mesurée.

## Densité et géométrie

- Référence de composition : capture `1536x1024`.
- Navigation visuelle : environ 120 px ; icônes 17–19 px, trait fin cohérent.
- Ticker : hauteur compacte, valeurs tabulaires, séparateurs à peine visibles.
- Gouttières principales : 12–16 px ; espace interne courant : 14–18 px.
- Grande dominante : environ la moitié de la largeur de travail.
- Inspecteur : 300–340 px selon viewport.
- Titres de carte courts ; microcopie et provenance proches de la donnée.
- Alignement des chiffres, axes et colonnes prioritaire sur la symétrie.

La densité ne vient ni de polices minuscules ni d'une accumulation de cartes :
elle vient d'une hiérarchie stable, d'alignements nets et d'espaces courts.

## Typographie, icônes et logo

- Sans-serif neutre et compacte ; mono/tabular pour prix, dates, unités et codes.
- Titre de page clair, jamais spectaculaire.
- Capitales limitées aux micro-libellés et statuts.
- Une seule famille d'icônes linéaires, même épaisseur et même boîte optique.
- Icônes d'état accompagnées d'un mot, signe ou motif.
- Logo : polyèdre/hexagone facetté argent, lisible à petite taille et en
  monochrome. Ne pas réintroduire le monogramme `VX`, une flèche, une pièce, un
  chandelier ou un symbole de hausse.

## Comportements

- Survol : hausse très légère de surface ou de bordure, sans déplacement.
- Sélection : ambre uniquement pour l'intention et le focus de navigation.
- Vert/rouge : sens financier uniquement, doublé par signe et texte.
- Panneau sélectionné : bord plus précis, pas de glow.
- Mouvement : 90 ms ligne, 140 ms contrôle, 180 ms panneau ; aucun ticker animé
  faisant croire à une donnée live.
- Prévoir surfaces opaques sous `prefers-reduced-transparency` et supprimer les
  mouvements non essentiels sous `prefers-reduced-motion`.

## Comparaison obligatoire

Pour chaque page :

1. capturer `1280x800`, `1440x900`, `1600x1000` ;
2. comparer d'abord shell, proportions, densité, matériau et hiérarchie ;
3. superposer ou utiliser un diff visuel lorsque possible ;
4. vérifier textes français longs, valeurs extrêmes et tous les états ;
5. documenter tout écart intentionnel ;
6. faire valider humainement, car un score de pixels ne mesure pas la clarté.

## Dérives interdites

- rail gauche large, flottant ou très arrondi ;
- fond bleu saturé, noir pur uniforme ou dominante violette ;
- cartes opaques grises, verre blanc, gradients arc-en-ciel ou néon ;
- capsules partout, rayons exagérés ou ombres molles de style mobile ;
- nouveau logo, mot-symbole envahissant ou logo `VX` ;
- bento générique identique sur chaque page ;
- décoration Apple, crypto ou science-fiction ajoutée au modèle ;
- valeurs fictives non étiquetées dans le produit réel.
