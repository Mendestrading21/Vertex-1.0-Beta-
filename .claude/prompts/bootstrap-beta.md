# Prompt — bootstrap des deux dépôts

Travaille uniquement en mode Plan.

Le donneur est `Mendestrading21/Vertex-` et la cible est
`Mendestrading21/Vertex-1.0-Beta-`. Ils peuvent avoir la même branche locale.

1. Lis le skill `/vertex-one`, `manifests/repositories.yaml` et
   `BETA_REPOSITORY_BOOTSTRAP.md`.
2. Vérifie `pwd`, `origin`, branche, HEAD et dirty state des deux dépôts.
3. Interdis toute écriture dans le donneur.
4. Compare le HEAD donneur à `c683c944f93f61d5fd22303df726fac6e79820fe`.
5. Inventorie le README existant de Beta et le diff exact d'installation du
   blueprint.
6. Ne copie, n'installe, ne commit et ne push rien dans cette session.
7. Rends verdict, fichiers prévus, contrôles, rollback et une seule commande :
   `EXÉCUTE BOOTSTRAP BETA` si tout est sûr.

