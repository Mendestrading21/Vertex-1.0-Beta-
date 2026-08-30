# Sauvegarde et restauration

Deux scripts, une règle : **une copie n'est pas une sauvegarde ; seule une
restauration vérifiée en est une.**

| Script | Rôle | Ce qu'il prouve |
|---|---|---|
| `backup.sh` | `pg_dump` custom + recensement du contenu sous le MÊME snapshot, chiffré AES-256, manifeste | rien — il produit un artefact et la description de ce que cet artefact doit rendre |
| `verify-restore.sh` | déchiffre, contrôle l'empreinte, restaure dans une base **vide et jetable**, vérifie schéma, déclencheurs **et contenu**, inscrit `verified_restore_at` | que cet artefact est restaurable, cohérent **et complet** |
| `census.sql` | recensement déterministe : lignes + empreinte par table | définition unique, partagée par les deux scripts |

Le rôle à utiliser est celui des **migrations** (`VERTEX_MIGRATION_DATABASE_URL`,
propriétaire des tables), pas celui du runtime.

## Refus par défaut

`verify-restore.sh` s'arrête si :

- la base cible ne porte pas un marqueur `restore` / `verify` / `scratch` dans
  son nom ;
- elle contient déjà le moindre objet — le décompte passe par `pg_class`, **pas**
  par `information_schema` : ce dernier ne montre que les objets sur lesquels le
  rôle courant a un droit, si bien qu'une base pleine de tables appartenant à un
  autre rôle y apparaissait **vide** ;
- le manifeste ne porte pas de recensement. Un artefact produit par une version
  antérieure de `backup.sh` est **refusé**, pas estampillé faute de mieux.

## Invariants contrôlés après restauration

1. **Empreinte du clair** identique au manifeste — sinon la sauvegarde est
   corrompue et le script échoue (il ne « répare » rien).
2. **`alembic_version` égale à celle de la source** — la VALEUR, pas seulement
   la présence : un `count(*) = 1` passait sur une base restaurée à une
   révision antérieure.
3. **Les huit déclencheurs append-only, nommés un par un, présents ET ACTIFS**
   — `observations`, `ledger_transactions`, `snapshots`, `thesis_revisions`,
   chacun avec son `_append_only` et son `_no_truncate`. Plus un contrôle que
   la base n'en porte pas une neuvième hors liste : une future table
   append-only fait échouer ce contrôle et impose de mettre la liste à jour,
   au lieu de passer au vert sur une couverture partielle.
4. **Ensemble des déclencheurs identique à la source**, activation comprise.
5. **Contenu restitué** — nombre de lignes ET empreinte, table par table,
   comparés au recensement pris pendant la sauvegarde. Le recensement est fait
   **avant** la remise en état de l'outbox, qui modifie `outbox`.
6. **Baux outbox relâchés** — un dump capture légitimement les baux en vol ;
   ils désignent après restauration des processus qui n'existent plus. Ce
   n'est pas un invariant du dump, c'est une remise en état.

`verified_restore_at` n'est écrit **que** si les six passent.

## Ce que le 8e audit avait trouvé, et qui est corrigé

- Le contrôle des déclencheurs était `count(*) > 0 … tgname LIKE '%append_only%'`.
  **Un seul suffisait** ; il y en a huit. Une base amputée de
  `snapshots_append_only` recevait « RESTAURATION VÉRIFIÉE ». Un déclencheur
  simplement **désactivé** était compté lui aussi — `pg_dump` le restaure
  désactivé, et il ne protège rien.
- **Aucun** des contrôles ne comparait les données à la source. Les quatre
  rendaient un verdict identique sur une base de 25 lignes et sur une base de
  0 ligne : ils ne portaient aucune information sur la restitution.

## Preuve d'exécution

Cycle complet exécuté sur PostgreSQL 16 réel, base jetable, données `SYNTHETIC`
uniquement, détruite ensuite. Aucun artefact n'est suivi par Git.

Cas verts : sauvegarde → chiffrement → déchiffrement → empreinte →
`pg_restore --exit-on-error` dans une base vide → contrôles 1 à 6 → tampon écrit.

Cas rouges, tous vérifiés comme échouant **sans** écrire le tampon :

| Cas | Ancien comportement | Nouveau |
|---|---|---|
| `snapshots_append_only` supprimé | « RESTAURATION VÉRIFIÉE » | `ÉCHEC … attendu O, obtenu ABSENT` |
| `snapshots_append_only` désactivé | non détecté (`count(*)` le comptait) | `ÉCHEC … attendu O, obtenu D` |
| restitution schéma seul | les 4 contrôles passaient | diff de recensement, `ÉCHEC` |
| manifeste hérité sans recensement | — | `REFUS`, base cible laissée intacte |

## Ce qui manque encore (ne pas croire couvert)

- **Archivage WAL / PITR** : absent. L'objectif RPO ≤ 5 min du runbook n'est
  donc **pas** atteint ; la perte maximale est l'intervalle entre deux dumps.
- **Troisième copie hors machine** : absente. La règle « trois copies, deux
  supports, une hors machine » n'est pas satisfaite.
- **Ordonnancement** : aucun planificateur n'appelle ces scripts. Ils
  s'exécutent à la main.
- **Rétention 7/4/12** : aucune purge n'est implémentée.
- **Restitution des droits** : `pg_restore` tourne `--no-privileges` et
  `--no-owner`. Les rôles et les `GRANT` ne sont **pas** rendus par la
  sauvegarde ; ils sont reposés par `infra/compose/initdb/` puis
  `alembic upgrade head`. Une restauration réussie ne prouve donc **rien**
  sur le moindre privilège — c'est `infra/compose/check-least-privilege.sh`
  qui le prouve.
- **Empreinte entre versions majeures de PostgreSQL** : le rendu textuel de
  certains types peut différer entre PostgreSQL 16 et 18. Les réglages de
  session sont épinglés dans `census.sql`, mais une comparaison
  source-16/cible-18 peut faire diverger l'empreinte sans faute de la
  restauration. Le nombre de lignes, lui, reste comparable.
- `pg_verifybackup` et la restauration à un instant précis relèvent du base
  backup + WAL, donc de ce qui manque ci-dessus.

Ces manques appartiennent au LOT-24 (machine cible) et sont inscrits dans
`docs/99-status/DEBT.md`.
