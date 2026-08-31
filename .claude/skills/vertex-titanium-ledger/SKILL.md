---
name: vertex-titanium-ledger
description: Concevoir, auditer, développer et valider l'identité Titanium Ledger de Vertex 1.0 Beta, écran par écran, pour le shell, les composants, widgets, tableaux et graphiques, sans modifier les contrats ni la vérité financière. Utiliser pour toute refonte visuelle Vertex, composition de page, palette, logo, objet UI, visualisation, accessibilité ou QA visuelle.
---

# Vertex — Titanium Ledger

## Mission

Faire de Vertex un registre décisionnel premium, dense et calme : précision d'un
terminal de marché, lisibilité d'un outil patrimonial et traçabilité d'un poste
d'analyse. Chaque écran doit avoir sa propre composition et répondre à une
question réelle. Le thème ne doit jamais masquer, inventer ou recalculer une
information financière.

## Autorités et périmètre

Lire dans cet ordre avant toute action :

1. `CLAUDE.md` ;
2. `docs/00-foundation/CONSTITUTION.md` ;
3. `docs/99-status/NOW.md` ;
4. le lot autorisé et ses ADR ;
5. `docs/05-design/TITANIUM_LEDGER_VISUAL_SYSTEM.md` ;
6. les contrats, composants, tests et données réellement présents ;
7. ce skill et uniquement ses références utiles.

Ce skill gouverne l'affichage. Il n'autorise ni un nouveau calcul métier, ni une
nouvelle source de données, ni un changement de contrat API, ni une dépendance,
ni une publication. Toute extension de ce type exige son propre lot ou ADR.

## Invariants absolus

- Le serveur Python reste l'unique autorité des calculs, états et verdicts.
- Le navigateur ne dérive ni score, rendement, probabilité, recommandation,
  breakeven, P&L, grecque, classement ou statut canonique.
- Une valeur absente n'est jamais remplacée par zéro, un exemple ou une donnée
  décorative.
- `PARTIAL`, `DEGRADED`, `MISSING`, `NOT_ENTITLED`, `UNSUPPORTED`,
  `INSUFFICIENT_DATA` et `UNKNOWN` restent visibles et explicables.
- L'ambre signifie marque, sélection ou action ; jamais performance positive.
- Le vert et le rouge restent strictement financiers et sont toujours doublés
  par un libellé, une forme, un signe ou une icône.
- Aucun graphique sans question, unité, période, source, fraîcheur, état et
  équivalent exact accessible.
- Desktop uniquement : vérifier `1280x800`, `1440x900`, `1600x1000` ;
  `1024x768` sert de dégradation facultative. Ne pas créer de navigation mobile.
- Aucun secret, donnée personnelle, identifiant broker ou capture sensible.

## Sélection du mode

- `audit` : constater l'écran réel, les contrats, états, tests et écarts ; aucune
  écriture.
- `research` : vérifier une pratique instable ou manquante dans des sources
  officielles et documenter sa conséquence locale.
- `identity` : palette, typographie, logo, surfaces, densité, lumière et mouvement.
- `component` : créer ou consolider un objet réutilisable et sa matrice d'états.
- `chart` : construire une visualisation exacte, accessible et chargée par route.
- `page` : reconstruire une composition entière à partir de sa question métier.
- `qa` : contrôler fidélité, responsive desktop, clavier, états, performance et
  non-régression financière.

Charger seulement les références du mode :

- identité : `references/visual-identity.md` ;
- composants : `references/component-system.md` ;
- graphiques : `references/charts.md` ;
- pages : `references/pages.md` ;
- exécution et QA : `references/workflow.md` ;
- recherche : `references/research-sources.md`.

## Ordre de reconstruction par défaut

Pour une passe complète, traiter un écran à la fois :

1. Aujourd'hui ;
2. Marchés ;
3. Analyse ;
4. Options ;
5. Simulateur ;
6. Portefeuille ;
7. Calendrier ;
8. Opportunités ;
9. Suivi ;
10. Performance ;
11. Vertex IA ;
12. Système.

Ne pas homogénéiser ces pages en répétant une grille de cartes. Mutualiser les
primitives, pas les compositions.

## Baseline obligatoire

Avant d'écrire :

1. relever dépôt, branche, HEAD, dirty state, PR, CI et lot actif ;
2. lire la page, sa vue pure, ses hooks, ses schémas, ses tests et son CSS ;
3. inventorier uniquement les champs serveur disponibles et leurs états ;
4. formuler la question de l'écran et la décision qu'il aide à préparer ;
5. désigner un seul objet dominant, les preuves secondaires et l'action primaire ;
6. écrire les critères d'acceptation, viewports, rollback et validations ;
7. arrêter si la proposition exige de fabriquer une donnée ou de déplacer une
   autorité financière côté client.

## Recherche web contrôlée

En mode `research`, chercher d'abord les normes, documentations officielles et
dépôts maintenus par les auteurs. Préférer W3C/WAI, DTCG, documentation du moteur
de graphique, React/Vite et systèmes de design établis. Pour chaque apport noter :

- URL et organisme ;
- date de vérification ;
- problème Vertex résolu ;
- règle locale proposée ;
- coût, compatibilité, licence et risque ;
- preuve à ajouter.

Ne jamais copier une galerie Dribbble, une maquette ou un dépôt tiers comme
implémentation. Les références visuelles donnent une intention ; les contrats et
tests Vertex déterminent le produit.

## Cycle d'exécution

1. **Observer** — capture ou rendu réel, densité, hiérarchie, états, clavier.
2. **Contracter** — question, données autorisées, dominante, actions, états.
3. **Composer** — structure spécifique à l'écran avant les détails décoratifs.
4. **Systématiser** — réutiliser tokens et objets ; justifier tout nouveau token.
5. **Implémenter** — vue pure, sémantique native, calculs absents du navigateur.
6. **Prouver** — tests de vue, états, accessibilité, tokens, typecheck et build.
7. **Comparer** — trois viewports desktop et référence Titanium Ledger.
8. **Livrer** — diff borné, faits exacts, risques, rollback et PR brouillon.

Le protocole détaillé est dans `references/workflow.md`.

## Contrôle automatique du socle

Depuis la racine du dépôt :

```bash
python .claude/skills/vertex-titanium-ledger/scripts/audit_titanium_ledger.py
```

Ce contrôle vérifie des invariants mesurables du socle visuel ; il ne remplace ni
les tests applicatifs, ni la revue humaine des douze compositions.

## Condition de sortie

Un écran n'est terminé que si sa question, sa dominante et sa hiérarchie sont
évidentes ; les données restent exactes et sourcées ; tous les états sont
présents ; le clavier, le focus et l'équivalent textuel fonctionnent ; les trois
viewports sont revus ; les budgets et tests sont verts ; le lot, `NOW.md` et la
PR décrivent exactement ce qui a été fait et ce qui reste à vérifier.

