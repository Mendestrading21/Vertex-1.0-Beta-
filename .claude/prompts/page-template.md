# Prompt — Planification ou construction d'une page

Remplace les champs entre accolades avant utilisation.

- **Commande :** `{PLAN|EXÉCUTE} LOT {NN}`
- **Lot :** `.claude/lots/LOT-{NN}-{slug}.md`
- **Spécification :** `docs/01-product/pages/{page-file}.md`
- **Route :** `{route}`

## Mode et périmètre

Applique les règles de `.claude/prompts/lot-template.md`. Une demande ambiguë reste un
plan en lecture seule. En exécution, ne construis que la page, ses composants
partagés strictement nécessaires, ses contrats déjà prévus et ses tests. Ne
retouche pas une autre page pour harmonisation opportuniste.

## Lecture obligatoire

Lis complètement :

1. `CLAUDE.md` et la constitution ;
2. `docs/99-status/NOW.md` ;
3. le lot et la spécification de page ;
4. `docs/01-product/INFORMATION_ARCHITECTURE.md` ;
5. `.claude/skills/vertex-titanium-ledger/SKILL.md` et les références qu'il
   route pour la page ;
6. `docs/05-design/DESIGN_SYSTEM.md` ;
7. `docs/05-design/CHART_STANDARD.md` ;
8. `docs/05-design/RESPONSIVE.md` ;
9. `docs/05-design/ACCESSIBILITY.md` ;
10. `docs/05-design/UI_STATES.md` ;
11. les contrats, ADR et budgets cités par la page.

## Contrat de page

Avant de proposer ou écrire du code, établis une fiche courte :

- question utilisateur principale ;
- action principale unique ;
- visuel dominant unique ;
- trois modules secondaires au maximum hors navigation ;
- rythme et composition propres à cet écran, sans recopier le bento d'une autre
  page ;
- contrats backend consommés ;
- unités, devise, timezone, source et fraîcheur affichées ;
- ce que la page ne fait explicitement pas.

Si la spécification ne permet pas de répondre à ces points, reste en mode Plan et
signale le manque. N'invente pas de donnée ou de calcul pour remplir l'écran.

## Invariants d'interface financière

- TypeScript met en forme et affiche ; il ne calcule aucun prix, Greek, IV,
  rendement, risque, R:R, score, probabilité ou verdict faisant autorité.
- La page rend le `AdviceResult` canonique reçu du serveur sans le recomposer.
- Source, horodatage, unité et état de qualité restent visibles jusqu'au détail.
- Réel, retardé, estimé, simulé, théorique, historique et démonstration ne partagent
  jamais un libellé ou un style ambigu.
- Une donnée requise absente ou invalide ne produit ni zéro, ni feu vert, ni valeur
  inventée.
- Aucun ordre, achat, vente, validation d'ordre ou liaison au compte IBKR.

## États obligatoires

Implémente et teste, selon le contrat backend :

- `loading` ;
- `refreshing` ;
- `empty` ;
- `partial` ;
- `delayed` ;
- `stale` ;
- `offline` ;
- `error`.

Le navigateur ne déduit pas lui-même la fraîcheur. Un snapshot hors ligne reste
daté, en lecture seule, et ne déclenche aucun nouveau verdict.

## Périmètre desktop et accessibilité

Vertex 1.0 Beta est **DESKTOP ONLY**. Valide `1280×800`, `1440×900` et
`1600×1000`. `1024×768` peut servir de contrôle de dégradation laptop si la page
le justifie, sans devenir une cible mobile. Préserve :

- ordre de lecture logique et navigation clavier complète ;
- focus visible et restauré après fermeture d'un tiroir ou dialogue ;
- contraste WCAG 2.2 AA ;
- noms accessibles et annonces d'état utiles ;
- tableau ou résumé textuel équivalent pour chaque graphique essentiel ;
- tri, provenance, état, risque et actions lors de toute dégradation de densité.

N'implémente ni ne teste en phase 1 de viewport `390`/`360`, disposition
téléphone, bottom nav, `MobileActionBar`, feuille basse ou geste mobile dédié.
`Mobile UI = LATER` : conserver la sémantique des contrats et la hiérarchie du
contenu pour l'adaptation future, sans créer aujourd'hui de branche mobile.

## Graphiques

Chaque graphique affiche ou expose : titre, métrique, unité, devise éventuelle,
timezone, période, source, observation et fraîcheur. Limite les overlays à ceux
prévus par la spécification. Charge les bibliothèques lourdes à la demande et
mesure le budget défini dans `PERFORMANCE_BUDGETS.md`.

## Plan attendu

En mode `PLAN LOT {NN}`, rends :

1. disposition aux trois viewports desktop et, si utile, dégradation laptop
   `1024×768` ;
2. arbre des composants ;
3. contrats et requêtes consommés ;
4. matrice des huit états ;
5. interactions clavier et alternatives aux graphiques ;
6. tests unitaires, composants, visuels et E2E ;
7. budget de performance ;
8. fichiers à toucher ;
9. critères d'acceptation binaires ;
10. une seule prochaine commande.

## Exécution et sortie

Avec `EXÉCUTE LOT {NN}` seulement, implémente le plan approuvé, exécute les gates
du lot, mets `NOW.md` à jour et termine au format compact de pilotage Claude de
`.claude/prompts/lot-template.md`. Ne commence aucune autre page.
