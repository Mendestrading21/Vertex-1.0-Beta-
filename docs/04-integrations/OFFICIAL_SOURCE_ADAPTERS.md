# Adaptateurs de sources officielles

## Ce qui est livré

`apps/edge-official` fournit des clients strictement en lecture seule :

| Source | Client | Données | Configuration locale |
|---|---|---|---|
| SEC EDGAR | `SecEdgarClient` | submissions, Company Facts | `VERTEX_SEC_USER_AGENT` avec contact |
| FRED/ALFRED | `FredClient` | observations et périodes de vérité | `VERTEX_FRED_API_KEY` |
| OpenFIGI | `OpenFigiClient` | candidats de correspondance d'identifiants | clé facultative `VERTEX_OPENFIGI_API_KEY` |
| BCE | `EcbDataClient` | séries CSV de la Data API | flow et clé de série en allowlist |
| BNS | `SnbDataClient` | cubes CSV du portail de données | identifiant de cube en allowlist |

Chaque client utilise un hôte officiel codé en dur, HTTPS, sans redirection,
avec timeout, réponse bornée et `DataEnvelope`. Il n'existe aucun endpoint de
compte, ordre, position, P&L ou exécution.

## Où obtenir les accès

- SEC EDGAR : aucune clé. Déclarer seulement le nom de l'application et un
  contact conformément à la politique SEC.
- FRED : créer une clé dans le compte FRED, puis la placer uniquement dans le
  `.env` local ou le gestionnaire de secrets.
- OpenFIGI : l'API publique accepte les requêtes sans clé à quota réduit ; la
  clé du compte OpenFIGI augmente les limites.
- BCE et BNS : aucune clé. Sélectionner explicitement les séries/cubes utiles ;
  aucun téléchargement global n'est activé par défaut.
- Wall Street Horizon : abonnement séparé dans IBKR Account Management, puis
  sonde réelle avec l'adaptateur IBKR déjà présent.

Ne jamais coller une clé dans Git, une issue, une PR, un log ou une capture.

## Ce qui reste volontairement désactivé

FMP et ORATS ne sont pas implémentés. Avant activation, une personne doit
valider le prix, les endpoints réellement inclus dans le plan, les droits de
stockage/affichage/export, les quotas et la procédure de résiliation. Une clé
absente produit `NOT_ENTITLED` ou une capacité désactivée, jamais de faux
fallback.

## Prochaine frontière d'intégration

Ces adaptateurs retournent les réponses brutes autorisées. Un prochain lot doit
choisir une seule famille — par exemple les faits SEC — puis écrire le
normaliseur typé, les règles `available_at`, la persistance PostgreSQL, les
corrections, le rejeu, le snapshot consommateur et les tests de panne. Aucun
payload de ce lot n'alimente encore un verdict ou une page.
