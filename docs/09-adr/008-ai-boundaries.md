# ADR-008 — Frontières de Vertex AI

- Statut : Accepté
- Date : 2026-08-28
- Portée : IA, prompts, données, interface

## Contexte

Un modèle génératif peut expliquer et synthétiser, mais il est non déterministe, vulnérable aux instructions malveillantes et incapable de garantir seul une vérité financière. L’application doit rester pleinement utile lorsque le fournisseur IA est indisponible.

## Décision

Vertex AI est un adaptateur d’explication sans effet de bord.

- Il reçoit uniquement des DTO certifiés, minimisés et expurgés.
- Il ne se connecte ni à TWS, ni à PostgreSQL, ni à Cloudflare, ni à un outil d’ordre.
- Il ne calcule pas de prix, score, gate, probabilité ou verdict.
- Toute affirmation factuelle renvoie vers un evidence_id fourni par le cœur.
- La réponse est structurée, validée par schéma et affichée comme explication générée.
- Les contenus externes sont des données non fiables, jamais des instructions.
- Aucun identifiant de compte, position détaillée, secret ou donnée personnelle n’est transmis.
- Timeout, budget, modèle et version de prompt sont enregistrés ; le fallback déterministe reste disponible.

## Conséquences

### Positives

- Une erreur IA ne change pas le résultat financier.
- Les réponses sont auditables et reliées aux preuves.
- Le produit fonctionne sans fournisseur IA.

### Coûts et contraintes

- L’IA refuse certaines demandes qui nécessiteraient de nouveaux calculs.
- La qualité dépend des faits fournis par le cœur.
- Il faut tester schémas invalides, citations absentes et prompt injection.

## Options rejetées

| Option | Motif du rejet |
|---|---|
| LLM comme second analyste ou verdict | Autorité non déterministe |
| Accès direct à la base ou au broker | Exposition et effets de bord |
| Navigation Web libre | Sources et instructions non maîtrisées |
| Calcul financier en langage naturel | Non reproductible |
| Continuer après validation de schéma échouée | Risque d’afficher une réponse trompeuse |

## Critères de réexamen

De nouveaux usages IA restent soumis aux mêmes invariants. Une capacité à effet de bord nécessiterait un produit séparé et ne peut pas être ajoutée à Vertex One.
