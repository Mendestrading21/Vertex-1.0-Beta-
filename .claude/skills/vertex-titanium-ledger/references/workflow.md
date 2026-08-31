# Workflow de reconstruction et de validation

## Étape 0 — Autorisation

- Vérifier le lot actif, la branche, le dirty state, le HEAD, la PR et la CI.
- Ne jamais démarrer la page suivante sans autorisation si le lot est borné.
- Préserver les modifications utilisateur non liées.
- Ne pas fusionner, publier ou changer une dépendance implicitement.

## Étape 1 — Audit de l'écran réel

Lire ensemble : route, page, vue pure, hooks, schémas générés, composants,
styles, tests, fixtures et spécifications. Relever :

- question actuelle et question souhaitée ;
- champs réellement disponibles ;
- états et raisons serveur ;
- éléments au-dessus de la ligne de flottaison ;
- actions, ordre de tabulation et focus ;
- densité, répétitions, surfaces inutiles et incohérences ;
- coût du code et du moteur graphique ;
- assertions qui protègent la vérité financière.

Rendre un verdict `KEEP / ADAPT / REWRITE / REMOVE` par zone, avec preuve.

## Étape 2 — Contrat de composition

Avant le JSX, écrire une fiche courte :

```text
Page / code Ledger :
Question :
Décision préparée :
Dominante :
Données serveur autorisées :
États :
Rail de preuve :
Action primaire :
Équivalent accessible :
Budget :
Interdits :
```

Une composition complète n'est pas un collage de références : traduire les
intentions visuelles avec les seules données et actions autorisées.

## Étape 3 — Architecture et vue pure

- Séparer adaptation de réponse, vue pure et rendu.
- Conserver l'autorité dans les contrats/moteur existants.
- Réutiliser les primitives Titanium Ledger quand leur contrat correspond.
- Créer un composant seulement après avoir nommé tous ses états.
- Préférer HTML natif ; ajouter ARIA seulement pour compléter une sémantique
  absente.
- Le texte visible explique source, heure, unité et dégradation au point d'usage.

## Étape 4 — CSS et tokens

- Modifier `tokens.ts`, générer `tokens.css`, ne jamais modifier le généré seul.
- Refuser les couleurs brutes, valeurs magiques répétées et `!important` de fuite.
- Tester focus, survol, sélection, disabled, partial, error et forced colors.
- Vérifier densité à 1280 avant d'agrandir à 1440/1600.
- Réserver l'espace des données asynchrones pour éviter les sauts.

## Étape 5 — Graphiques

Lire `charts.md`. Conserver les moteurs hors bundle initial, écrire la table
exacte, tester clavier et états. Ne pas installer de navigateur ou changer de
librairie pour obtenir une capture. Utiliser le Chromium déjà disponible ; sinon
documenter l'absence et laisser la CI exécuter la porte prévue.

## Étape 6 — Validation

Exécuter d'abord les contrôles ciblés, puis les portes du dépôt pertinentes :

```bash
python .claude/skills/vertex-titanium-ledger/scripts/audit_titanium_ledger.py
pnpm --dir apps/web tokens:css
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test
pnpm --dir apps/web build
```

Ajouter les tests ciblés de la page et les portes de sécurité/traceabilité du lot.
Ne jamais annoncer un E2E, une capture ou une mesure non exécutés.

### Revue visuelle

- `1280x800` : densité minimale et premier viewport ;
- `1440x900` : référence principale ;
- `1600x1000` : respiration et longueur de ligne ;
- `1024x768` : dégradation optionnelle, jamais promesse mobile ;
- zoom, focus, contraste, mouvement réduit et couleurs forcées selon composants ;
- données longues, valeurs négatives, unités, textes français et états absents.

Comparer d'abord le shell, le matériau, la densité et la hiérarchie à
`assets/vertex-dashboard-canonical.png`. La capture est une référence Vertex
choisie, pas une capture tierce à réinterpréter. Un diff de pixels assiste la
revue, mais la fidélité fonctionnelle, les états et la lisibilité restent jugés
humainement.

## Étape 7 — Performance

- Relever bundle initial gzip et chunks de graphiques.
- Vérifier lazy-loading par route et absence de mise en page instable.
- Mesurer TBT en laboratoire comme indicateur, sans le présenter comme INP réel.
- Les Core Web Vitals de terrain exigent des mesures réelles ; noter leur absence
  au lieu de les simuler.
- Toute hausse de budget doit être expliquée et acceptée, jamais masquée.

## Étape 8 — GitHub et handoff

- Une branche et une PR brouillon par lot ; commits atomiques et traçables.
- Mettre à jour `docs/99-status/NOW.md` avec résultats exacts.
- Le résumé final contient : page/lot, branche, fichiers, tests exacts, captures
  exactes, mesures, risque, rollback, blocage et une seule prochaine commande.
- Ne jamais fusionner automatiquement.

## Recherche de fraîcheur

Rouvrir `research-sources.md` et le web uniquement lorsqu'une règle, version,
API ou pratique a changé, lorsqu'une nouvelle dépendance est proposée, ou quand
le lot demande une recherche fraîche. Ajouter une source officielle et la
conséquence Vertex ; ne pas accumuler des liens sans décision.
