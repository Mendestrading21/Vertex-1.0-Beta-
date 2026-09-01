# ADR-016 — SEC EDGAR point-in-time

- Statut : Accepté
- Date : 2026-09-01
- Portée : normalisation SEC, observations, outbox, snapshots et API

## Contexte

ADR-015 livre le transport officiel mais interdit de confondre une réponse
brute avec un fait utilisable. Company Facts contient plusieurs périodes,
unités, dépôts et corrections ; une sélection par ordre de tableau ou par date
de période créerait du look-ahead et pourrait masquer un amendement.

## Décision

- Associer CIK et instrument uniquement par argument explicite.
- Produire un contrat par version de dépôt et par fait XBRL, avec accession,
  unité, période, formulaire et provenance des deux réponses source.
- Fixer `available_at` à `acceptanceDateTime`; si elle manque, utiliser le
  lendemain UTC de `filed`, jamais le début du jour déclaré.
- Persister chaque version comme observation append-only idempotente.
- Publier un snapshot par instrument depuis les seules observations dont
  `available_at <= now`.
- Pour une même clé de fait, retenir la dernière disponibilité prouvée. Si
  deux valeurs divergent au même instant, n'en retenir aucune et publier le
  conflit.
- Refuser toute valeur métier lorsque plusieurs identités CIK/nom coexistent
  pour la même clé d'instrument.
- Ne pas persister les corps bruts sans mécanisme de purge 24 h. Conserver
  dans chaque contrat normalisé les identifiants et hash des réponses sources.
- Exposer un relais API en lecture seule. Aucun branchement automatique vers
  l'analyse, les opportunités ou `AdviceEngine`.

## Conséquences

Le replay est déterministe et un audit peut retrouver la réponse source qui a
produit chaque valeur. Une correction devient une nouvelle observation et ne
réécrit pas le passé. Le snapshot est borné et publie sa troncature. La page
Analyse ne consomme pas encore ces faits : ce choix évite de transformer une
présence réglementaire en preuve suffisante pour une recommandation.

## Options rejetées

| Option | Motif |
|---|---|
| Dernière entrée du tableau SEC | ordre fournisseur non constitutif d'une vérité |
| `filed` à minuit comme disponibilité | look-ahead intrajournalier |
| Élection lexicographique d'un conflit | invente une valeur métier |
| Persistance durable du JSON brut | rétention 24 h sans reaper disponible |
| Calcul de ratios dans le connecteur | seconde autorité financière |
| Déclenchement direct d'Opportunités | un dépôt n'est pas un avis |
