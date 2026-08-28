# Politique de migration depuis le Vertex actuel

## Position

Le dépôt actuel est un donneur épinglé en lecture seule. Le nouveau dépôt ne
partage ni son historique, ni ses dépendances runtime, ni ses autorités métier.
Il peut extraire ses capacités saines après preuve. Tout élément non inscrit
dans l'inventaire reste non migré ; il n'est pas copié implicitement.

## Classes

| Classe | Usage permis |
|---|---|
| `KEEP` | Code ou asset porté après preuve de propriété, licence, frontières et tests indépendants |
| `ADAPT` | Algorithme ou contrat sain porté vers les nouvelles interfaces et autorités |
| `REWRITE` | Besoin conservé, implémentation et tests entièrement nouveaux |
| `REFERENCE` | Consultation pour parcours, vocabulaire, capture ou cas limite ; aucune copie de code runtime |
| `DROP` | Élément exclu du nouveau produit |

Dans la matrice de réaudit du donneur, `KEEP_AS_REFERENCE` est un alias plus
explicite de `REFERENCE`. Les deux libellés ont exactement la même frontière :
consultation autorisée, copie de code runtime interdite.

## Classification de départ

- `KEEP/ADAPT` : contrats purs, tests d'invariants, validation hors échantillon,
  schémas de graphique, tokens, fonctions financières pures et adapters dont la
  frontière est prouvée.
- `REWRITE` : monolithe, composition des pages, autorités multiples, persistance
  ou connexions incompatibles avec les nouveaux contrats.
- `REFERENCE` : captures, historique des lots, scénarios et comportements dont
  le code ne doit pas migrer.
- `DROP` : capacité de trading, compte/positions IBKR automatiques, fail-open,
  mocks présentés comme réels, probabilités non calibrées, secrets, caches,
  builds et actifs sans provenance.

## Procédure par capacité

1. Inscrire la capacité et le SHA donneur avant extraction.
2. Établir propriétaire, licence, consommateurs et raison produit.
3. Identifier risques financier, sécurité, vie privée et données.
4. Choisir la classe et documenter les preuves.
5. Écrire d'abord les tests ou critères indépendants dans le nouveau dépôt.
6. Conserver dans la PR commit, chemins, blobs et adaptations.
7. Prouver parité, mutation, performance et rollback.
8. Marquer `accepted`, `rejected` ou `migrated` dans l'inventaire.

Les décisions sont groupées par vague cohérente et approuvées dans une PR
brouillon unique. Seuls changement financier, licence, coût, donnée personnelle
ou action irréversible imposent une décision humaine séparée.

Une ressemblance fonctionnelle n'autorise pas une copie. Un code appartenant au
projet peut migrer uniquement si sa provenance, sa frontière et sa justesse sont
prouvées. Une capture n'est jamais une preuve de calcul.

## Données

Aucune donnée de marché réelle, historique utilisateur, secret, identifiant de
compte ou export privé ne migre dans Git. Les données nécessaires aux tests sont
synthétiques, minimales et documentées. Les exports personnels restent hors
dépôt et chiffrés.

Le protocole complet est `DONOR_EXTRACTION_PROTOCOL.md`.
