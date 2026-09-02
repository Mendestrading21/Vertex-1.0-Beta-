# Quarantaine de l'historique Git

## Déclencheur

Appliquer ce runbook lorsqu'un audit confirme qu'un secret, identifiant,
payload fournisseur, donnée personnelle, valeur de marché réelle ou capture
sensible a existé dans une référence Git publique, même si le fichier courant
a depuis été nettoyé.

## Actions immédiates non destructives

1. arrêter les merges et les nouvelles publications ;
2. ne pas recopier la donnée dans une issue, PR, log, test ou rapport ;
3. relever hors contenu les références, objets, chemins et dates concernés ;
4. révoquer ou faire tourner tout secret potentiellement exposé ;
5. décider humainement si le dépôt doit être rendu privé pendant l'incident ;
6. conserver le SHA actuel de `main` et la liste des branches avant action ;
7. préparer un miroir de sauvegarde chiffré et en tester la restauration.

Rendre un fichier propre ne purge pas son contenu historique. Fermer une PR ou
supprimer une branche ne prouve pas non plus que l'objet n'est plus accessible.

## Plan de remédiation contrôlée

La réécriture n'est autorisée qu'après une décision humaine distincte qui fixe :

- la catégorie exacte de donnée ;
- le périmètre complet des objets et références ;
- les obligations fournisseur, légales et contractuelles ;
- la fenêtre de maintenance et les personnes averties ;
- la sauvegarde restaurée avec succès ;
- la méthode (`git filter-repo` ou support GitHub) ;
- les branches et tags autorisés à être remplacés ;
- le plan de re-clonage des postes et d'invalidation des anciens clones ;
- la vérification distante après purge ;
- le rollback.

## Interdictions

- aucun `git push --force` improvisé ;
- aucune suppression en masse de branches ;
- aucun exemple utilisant la valeur sensible réelle ;
- aucune affirmation « purgé » fondée uniquement sur l'arbre courant ;
- aucune reprise fonctionnelle avant rotation des secrets applicables.

## Condition de sortie

L'incident peut être fermé seulement quand la visibilité est maîtrisée, les
secrets applicables sont tournés, chaque référence distante est recontrôlée,
les caches GitHub pertinents sont traités et un clone neuf ne retrouve plus le
contenu. Le compte rendu public reste abstrait ; la preuve détaillée demeure
dans le canal privé de sécurité.
