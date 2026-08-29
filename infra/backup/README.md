# Sauvegarde et restauration

Deux scripts, une règle : **une copie n'est pas une sauvegarde ; seule une
restauration vérifiée en est une.**

| Script | Rôle | Ce qu'il prouve |
|---|---|---|
| `backup.sh` | `pg_dump` custom, chiffré AES-256, manifeste | rien — il produit un artefact, pas une preuve |
| `verify-restore.sh` | déchiffre, contrôle l'empreinte, restaure dans une base **vide et jetable**, vérifie les invariants, inscrit `verified_restore_at` | que cet artefact est restaurable et cohérent |

## Refus par défaut

`verify-restore.sh` s'arrête si la base cible ne porte pas un marqueur
`restore` / `verify` / `scratch` dans son nom, ou si elle contient déjà la
moindre table. Il ne peut donc pas écraser une base de production, même invoqué
avec la mauvaise variable.

## Invariants contrôlés après restauration

1. **Empreinte du clair** identique au manifeste — sinon la sauvegarde est
   corrompue et le script échoue (il ne « répare » rien).
2. **`alembic_version` présente** — sans elle la base restaurée ne peut pas
   être remise sous migrations.
3. **Déclencheurs append-only restaurés** — sans eux, la base restaurée
   accepterait une réécriture d'historique du ledger et des snapshots.
4. **Baux outbox relâchés** — un dump capture légitimement les baux en vol ;
   ils désignent après restauration des processus qui n'existent plus. Le
   script les relâche explicitement, puis vérifie qu'il n'en reste aucun. Ce
   n'est pas un invariant du dump, c'est une remise en état.

## Preuve d'exécution

Le cycle complet a été exécuté sur PostgreSQL réel (base de test, données
SYNTHETIC uniquement) : `pg_dump` → chiffrement → déchiffrement → contrôle
d'empreinte → `pg_restore --exit-on-error` dans une base vide → quatre
contrôles verts → `verified_restore_at` inscrit. La base de vérification a été
détruite ensuite ; aucun artefact n'est suivi par Git.

## Ce qui manque encore (ne pas croire couvert)

- **Archivage WAL / PITR** : absent. L'objectif RPO ≤ 5 min du runbook n'est
  donc **pas** atteint ; la perte maximale est l'intervalle entre deux dumps.
- **Troisième copie hors machine** : absente. La règle « trois copies, deux
  supports, une hors machine » n'est pas satisfaite.
- **Ordonnancement** : aucun planificateur n'appelle ces scripts. Ils
  s'exécutent à la main.
- **Rétention 7/4/12** : aucune purge n'est implémentée.
- `pg_verifybackup` et la restauration à un instant précis relèvent du base
  backup + WAL, donc de ce qui manque ci-dessus.

Ces manques appartiennent au LOT-24 (machine cible) et sont inscrits dans
`docs/99-status/DEBT.md`.
