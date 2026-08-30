# Vertex 1.0 Beta — direction visuelle « Obsidian Signal »

## Décision

Vertex devient un terminal de décision contemporain : fond graphite, hiérarchie
forte, grille bento régulière et signal lime rare. L'interface conserve sa
rigueur financière et sa traçabilité, mais cesse de présenter chaque donnée
comme un bloc technique de même importance.

Cette direction est une synthèse des références fournies, pas une copie d'un
écran Dribbble. Les effets spectaculaires restent subordonnés à la lisibilité,
à la provenance et à l'autorité des données publiées.

## Comparaison des trois propositions

| Proposition | Identité | Accent de marque | Logo proposé | Forces | Vigilance |
|---|---|---|---|---|---|
| A — Obsidian Signal | terminal institutionnel contemporain | lime acide rare | `V` dans un carré souple | distinctive, très lisible, énergique sans paraître crypto | ne jamais confondre le lime avec une performance positive |
| B — Prism Intelligence | laboratoire de données premium | violet prismatique + contrepoint turquoise | losange/prisme portant le `V` | exprime bien l'IA et l'analyse, plus éditorial | le violet doit rester distinct du langage sémantique des options |
| C — Titanium Ledger | outil patrimonial mature | métal chaud/ambre | monogramme angulaire `VX` | sobre, crédible, durable, excellente densité | risque d'être moins immédiatement différenciant |

La branche implémente A comme base de comparaison parce qu'elle répond le mieux
au besoin exprimé de contraste, de modernité et d'identité propre. B et C
restent des directions visuelles réversibles : aucune n'autorise un écart aux
contrats de données ou à la frontière sans exécution.

## Audit de l'interface avant refonte

### Ce qui fonctionne déjà

- modèle sombre cohérent et typographie Geist auto-hébergée ;
- contrats serveur stricts, états vide/erreur/hors ligne honnêtes ;
- navigation clavier, focus visible et ordre canonique des pages ;
- séparation explicite des populations réelles, retardées, théoriques,
  simulées et synthétiques ;
- moteurs graphiques chargés à la demande et budget initial respecté.

### Ce qui affaiblit la perception du produit

- mêmes rectangles, mêmes bordures et même poids visuel sur presque toutes les
  informations ;
- navigation repliée fondée sur des abréviations textuelles ;
- titres trop petits et peu de contraste entre dominante, preuve et détail ;
- listes perçues comme une pile de cartes administratives ;
- identifiants, versions et horodatages techniques trop proches de la lecture
  principale ;
- presque aucune profondeur entre fond, surface, rail et panneau latéral ;
- absence d'un langage de marque immédiatement reconnaissable.

## Lecture des références

| Famille de références | Ce qui est retenu | Ce qui est écarté |
|---|---|---|
| Terminaux de marché sombres | densité maîtrisée, rail latéral, grande dominante, tableaux compacts | surcharge de micro-données et ambiance Bloomberg illisible |
| Dashboards bento | modules de tailles différentes, respiration, rail secondaire | mosaïque décorative de KPI sans question métier |
| Formulaires de trading | regroupement clair, segments, résultat toujours visible | vocabulaire d'exécution, CTA d'achat ou promesse de trading automatique |
| Widgets financiers | données courtes, chiffres tabulaires, états très lisibles | cartes 3D, halos permanents et couleurs rouge/verte décoratives |
| Interfaces glass | profondeur ponctuelle pour barre sticky et panneau latéral | transparence généralisée, flou sur chaque carte et glow néon |
| Systèmes d'icônes | trait unique, pictogrammes simples et cohérents | mélange de styles, emojis et abréviations comme navigation principale |

## Grammaire visuelle

### Surfaces

Trois niveaux seulement au premier plan :

1. le canevas `--vx-app` ;
2. la dominante `--vx-surface-0` avec bordure discrète ;
3. les modules de support `--vx-surface-1` et les overlays élevés.

Une ombre traduit une superposition, jamais un effet lumineux. Le verre est
réservé à une barre sticky ou un `SideSheet`.

### Couleurs

- `--vx-signal` identifie la marque, la sélection ou l'action principale ;
- `--vx-positive` et `--vx-negative` restent exclusivement financiers ;
- `--vx-warning` signale prudence, retard ou population synthétique ;
- `--vx-option` reste attaché aux options et à leurs sélections ;
- aucune couleur n'est le seul porteur d'une information.

### Typographie et nombres

- titre de page à 28 px, question en texte secondaire ;
- titres de module courts, libellés décoratifs en capitale petite ;
- Geist Mono et chiffres tabulaires pour séries comparables ;
- identifiants complets et timestamps bruts relégués au détail/provenance.

### Formes et mouvement

- rayons de 10 px pour les contrôles, 18 px pour les grandes surfaces ;
- grille de 4 px et gaps principaux de 16 à 24 px ;
- transitions courtes, tokenisées et annulées en réduction de mouvement ;
- un seul bouton rempli par page, aucun mouvement décoratif permanent.

## Architecture de l'expérience

Le shell conserve douze destinations et quatre groupes. Le rail ouvert donne
le nom complet ; le rail compact conserve un pictogramme unique et un nom
accessible. La barre de contexte montre l'espace courant et l'état réel de la
session sans créer d'information de marché.

Chaque page suit la séquence :

1. question métier ;
2. nature et santé des données ;
3. une dominante ;
4. un rail de contexte ou de preuve ;
5. détail technique à la demande.

## Page de référence : Aujourd'hui

La route ne reçoit ni prix, ni P&L, ni score, ni probabilité. Elle ne doit donc
pas imiter un dashboard de courtage. Son premier écran devient un cockpit
opérationnel fondé exclusivement sur le DTO publié :

- bandeau de santé locale ;
- nature permanente de la population ;
- grande file d'attention, dans l'ordre exact du worker ;
- rail du snapshot : version, heure, population, items publiés et rejetés ;
- couverture : seuls les compteurs primitifs explicitement reçus sont rendus ;
- provenance complète dans le panneau latéral accessible.

La première ligne n'est jamais transformée en « meilleur signal ». L'ordre
serveur n'est ni recalculé, ni renommé score ou priorité par le navigateur.

## Application progressive aux autres pages

| Zone | Dominante prévue | Rail/support |
|---|---|---|
| Marchés | contexte et graphique de marché | breadth, couverture, benchmarks |
| Opportunités | candidats admissibles | gates, exclusions et preuves |
| Analyse | prix/volume certifié | avis, scénarios et provenance |
| Options | chaîne exploitable | sous-jacent, liquidité et inspecteur |
| Simulateur | payoff/scénarios | hypothèses et résumé déterministe |
| Portefeuille | ledger manuel | concentration et risques publiés |
| Vertex IA | réponse sourcée | citations, contradictions et limites |
| Système | matrice de santé | jobs, sauvegardes et audit |

## Interdits

- ordre d'achat, vente ou swap ;
- prix, KPI, score, P&L, sparkline ou tendance inventés ;
- rouge/vert comme couleurs de marque ;
- carte entière colorée pour une simple variation ;
- halo ou blur sur toutes les surfaces ;
- graphique sans source, période, unité et fraîcheur ;
- interface téléphone dans la Beta desktop ;
- masquage d'un état synthétique, périmé, partiel ou inconnu.

## Critères d'acceptation du thème 1.0 Beta

- shell reconnaissable à 1280, 1440 et 1600 px, dégradation contrôlée à 1024 ;
- une dominante immédiatement identifiable sur chaque page touchée ;
- navigation complète au clavier et noms accessibles en mode compact ;
- aucun token couleur brut hors de la source typée ;
- aucun contrat API ni calcul financier modifié ;
- tests unitaires, lint, typecheck et build de production verts ;
- revue visuelle humaine obligatoire avant fusion et publication.
