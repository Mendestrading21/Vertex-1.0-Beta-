# Système d'objets et de widgets

## Principe

Une primitive mutualisée doit stabiliser un contrat visuel ou comportemental.
Elle ne doit pas effacer la personnalité de chaque page. Avant de créer un
composant, vérifier ses consommateurs, ses données, ses états et ses tests.

## Objets fondamentaux

### Ledger Frame

- Une seule dominante par écran.
- Contient question, période, provenance, état global et pied technique.
- Peut accueillir un graphique, une file ou un ledger, jamais un mélange sans
  hiérarchie.
- La tranche ambre identifie l'instrument actif, pas la réussite.

### Metric Block

- Libellé, valeur, unité, période, méthode et état accessibles.
- Tiret explicite pour absence ; raison visible pour valeur bloquée.
- Aucun calcul, arrondi métier ou conversion d'unité non fourni par le serveur.
- Variation positive/négative avec signe et texte, pas couleur seule.

### Evidence Row

- Identité et source à gauche, fait au centre, état et temps à droite.
- Ordre stable et navigation cohérente au clavier.
- Survol purement perceptif ; ne change ni rang ni importance.
- Une ligne cliquable est un vrai lien ou bouton, pas un `div` simulé.

### Ledger Table

- HTML `table` natif par défaut, `caption`, en-têtes associés et nombres alignés.
- Tri visible avec libellé accessible ; l'ordre initial vient du serveur ou est
  explicitement présenté comme tri d'affichage.
- Première colonne fixe seulement si cela améliore réellement la lecture.
- Virtualisation uniquement dans un lot mesuré, sans casser sémantique, focus,
  lecture d'écran ni copie.
- L'équivalent tabulaire d'un graphique contient les valeurs exactes utiles.

### Inspector Sheet

- Détail, provenance, thèse, contrat ou option ; aucune nouvelle vérité.
- Titre accessible, focus initial pertinent, boucle de tabulation et fermeture
  par Échap si modal.
- Retour du focus à l'élément déclencheur.
- Sous-couche inactive si modal ; préférer un panneau non modal si la comparaison
  avec le contenu principal doit rester possible.

### State Plate

- Libellé stable, icône ou forme, couleur sémantique et explication disponible.
- Ne jamais convertir `UNKNOWN` en neutre rassurant ni `PARTIAL` en succès.
- Les états inconnus du contrat doivent échouer de façon visible et sûre.

## Widgets spécialisés

| Widget | Usage | Contrat minimal |
|---|---|---|
| Snapshot Rail | état des sources et couverture | source, version, fraîcheur, population, raison |
| Attention Queue | priorités du jour | identité, raison serveur, urgence, preuve, état |
| Market Map | structure secteurs/tickers | valeur signée, unité, légende, sélection, table |
| Breadth Strip | avance/déclin/couverture | comptes exacts, population, seuils et méthode |
| Scenario Rail | faits haussiers/neutres/baissiers | scénario serveur, invalidation, preuves, limites |
| Option Chain | calls/puts par échéance | strike, échéance, cotations, droits, absences |
| Leg Composer | jambes du scénario | type, sens, quantité, strike, expiration, validation |
| Manual Ledger | lots et mouvements manuels | identité, quantité, prix, devise, date, provenance |
| Thesis Queue | suivi des thèses | état, raison, échéance, historique, action autorisée |
| Source Matrix | santé et droits | fournisseur, méthode, fraîcheur, entitlement, fallback |
| Ring Shares (ADR-017) | parts servies à chiffre central | parts `*_pct` en chaînes, chiffre central servi, légende chiffrée, table équivalente |
| Arc Gauge (ADR-017) | valeur bornée servie | valeur, bornes, seuils, position servie, méthode/version, `as_of`, raison si non calculable |
| Spark Figure (ADR-017) | mini-série servie en aire | points en chaînes, période nommée, `figcaption`, table |
| Day Bars (ADR-017) | comptes ou parts par jour sur rail | valeur servie ou `null`, nom de bande servi, unité, table |
| Cell Grid (ADR-017) | matrice de bandes nommées | nom de bande servi, texte servi, légende, `unknown` visible |
| Activity Feed (ADR-017) | liste groupée par jour | horodatages ISO servis, montants en chaînes signées, chips d'état |

## Matrice d'états obligatoire

Chaque objet de données doit définir et tester :

| État | Rendu attendu |
|---|---|
| loading | espace réservé, libellé de chargement, pas de fausse valeur |
| empty réel | explication contextualisée et prochaine action possible |
| partial | contenu disponible + bandeau + détails manquants |
| degraded | contenu prudent + cause + conséquence |
| error | échec identifiable, retry si idempotent et autorisé |
| stale | valeur visible avec horodatage et avertissement |
| not entitled | source ou champ masqué avec droit requis, sans contournement |
| unsupported | capacité explicitement non disponible |
| unknown | état sûr, visible, jamais converti silencieusement |
| success | contenu et provenance, sans décoration excessive |

## Formulaires et actions

- Utiliser `label`, `fieldset`, `legend`, messages d'aide et d'erreur associés.
- Une action financière manuelle récapitule les unités et la portée avant
  confirmation ; Vertex n'exécute aucun ordre broker.
- Les validations client améliorent la saisie mais ne deviennent pas autorité.
- Les actions destructives sont rares, explicites, ciblées et réversibles lorsque
  possible.
- Les menus, listes, combobox, grilles et dialogues suivent les interactions WAI
  APG pertinentes, sans ajouter ARIA quand le HTML natif suffit.

## Règle de création

Créer une nouvelle primitive seulement si :

1. au moins deux consommateurs partagent le même contrat ; ou
2. la sémantique/accessibilité serait sinon reproduite de façon risquée ;
3. tous les états peuvent être nommés et testés ;
4. la primitive n'impose pas une composition identique aux pages.

