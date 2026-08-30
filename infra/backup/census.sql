-- Recensement déterministe du contenu d'une base Vertex.
--
-- UNE SEULE DÉFINITION, DEUX APPELANTS : `backup.sh` l'exécute sur la SOURCE,
-- dans la transaction qui a exporté le snapshot lu par `pg_dump` — le
-- recensement porte donc exactement sur ce qui a été sauvegardé, sans fenêtre
-- de course. `verify-restore.sh` le rejoue sur la base RESTAURÉE et compare.
-- Sans cette comparaison, aucun des contrôles de restauration ne distinguait
-- une base rendue complète d'une base rendue vide.
--
-- DÉTERMINISME : le rendu textuel d'une ligne dépend de réglages de session.
-- Ils sont donc épinglés ici, des deux côtés. Ce qui n'est PAS garanti : deux
-- versions MAJEURES de PostgreSQL différentes entre source et cible peuvent
-- rendre certains types autrement — l'empreinte diverge alors sans que la
-- restauration soit fautive. Le nombre de lignes, lui, reste comparable.
SET TimeZone = 'UTC';
SET DateStyle = 'ISO, YMD';
SET IntervalStyle = 'postgres';
SET extra_float_digits = 3;
SET bytea_output = 'hex';

-- Sortie : une ligne « table|lignes|empreinte » par table de `public`.
-- `query_to_xml` permet de compter et d'empreindre une table dont le nom n'est
-- connu qu'à l'exécution, sans créer la moindre fonction dans la base
-- sauvegardée : la sauvegarde reste strictement en lecture.
-- L'agrégat est ordonné PAR LE TEXTE DE LA LIGNE, jamais par l'ordre physique :
-- un `pg_restore` réordonne les lignes, l'empreinte ne doit pas en dépendre.
--
-- La liste des tables vient de `pg_class`, PAS de `information_schema.tables` :
-- `information_schema` ne montre que les objets sur lesquels le rôle courant a
-- un droit. Une table sans GRANT y est INVISIBLE — un recensement fondé sur
-- elle déclarerait « rien à comparer » là où il manque une table entière. Avec
-- `pg_class`, une table illisible fait ÉCHOUER la requête au lieu de
-- disparaître silencieusement.
SELECT c.relname || '|'
       || (xpath('/row/c/text()',
             query_to_xml(format('SELECT count(*) AS c FROM %I.%I',
                                 n.nspname, c.relname),
                          false, true, '')))[1]::text
       || '|'
       || (xpath('/row/d/text()',
             query_to_xml(format(
               'SELECT md5(coalesce(string_agg(x.r, chr(10) ORDER BY x.r), '''')) AS d'
               || ' FROM (SELECT s::text AS r FROM %I.%I s) x',
               n.nspname, c.relname),
             false, true, '')))[1]::text
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
  AND NOT c.relispartition
ORDER BY c.relname;
