# Droits, finalités et rétention des sources d’information

Revue documentaire : 28 août 2026. Cette politique applique le principe de minimisation ; elle ne remplace pas l’analyse des contrats réellement acceptés. Si un contrat, une loi ou une demande de suppression est plus strict, la règle la plus stricte l’emporte.

## Porte de déploiement

Une source reste désactivée tant que les éléments suivants ne sont pas renseignés et approuvés humainement :

- propriétaire opérationnel et contact ;
- finalité précise et écrite ;
- API/interface officielle et version ;
- statut `ACTIVE`, `OPTIONAL` ou `UNSUPPORTED` ;
- type d’authentification et emplacement du secret ;
- entitlement, contrat, plan tarifaire et plafond de coût ;
- territoires/utilisateurs autorisés et droit d’affichage ;
- droit ou interdiction de stockage, dérivation, export et usage IA ;
- TTL brut, TTL normalisé, suppression, modification et fin de contrat ;
- procédure 401/403/429, révocation, incident et audit.

Claude ne peut pas accepter une condition, acheter un plan, demander une entitlement ou changer une finalité au nom de l’utilisateur.

## Classes de données

| Classe | Contenu | Stockage par défaut | Export/IA |
|---|---|---|---|
| `R0_REFERENCE` | identifiant natif, URL, source, timestamps, droit | selon source, minimisé | export seulement si autorisé ; pas de secret |
| `R1_PUBLIC_FACT` | fait réglementaire ou macro dont les droits sont validés | durable avec vintage et provenance | selon attribution et droit de la série |
| `R2_LICENSED_METADATA` | titre, événement ou métadonnée sous abonnement | TTL contractuel, chiffré | aucune redistribution par défaut |
| `R3_COPYRIGHT_CONTENT` | corps d’article, image, PDF éditeur | mémoire/cache ≤ 24 h ou aucun stockage | jamais vers IA/export sans droit écrit |
| `R4_SOCIAL_CONTENT` | post, commentaire, auteur public | 24 h par défaut, suppression réversible | aucun entraînement, profilage ou export corpus |
| `R5_SECRET` | token, clé, cookie, mot de passe | gestionnaire de secrets seulement | jamais log, base métier, capture ou sauvegarde applicative |

Une donnée dérivée hérite des restrictions de sa source si elle permet de reconstruire le contenu, d’identifier une personne ou de contourner une limite. « Dérivée » ne signifie pas « libre ».

## Matrice de rétention par défaut

| Source | Brut/contenu | Métadonnées normalisées | Dérivés | Suppression/correction |
|---|---|---|---|---|
| IBKR News | corps et titre ≤ 24 h, corps non persisté de préférence | identifiants/horodatage/empreinte 30 j | cluster non reconstructible 90 j seulement si permis | purge à la fin du droit ou selon fournisseur |
| IBKR WSH | payload ≤ 24 h | jusqu’à 30 j après événement | révisions/preuves ≤ 1 an si permis | appliquer révisions, purge à fin d’entitlement |
| SEC EDGAR | réponse API ≤ 24 h ; pas de miroir complet par défaut | accession, CIK, formulaires et faits durables | durable avec accession/version | contrôle hebdomadaire des corrections/suppressions |
| FRED/ALFRED | réponse API ≤ 24 h | durable seulement pour série autorisée | même droit que la série, vintage obligatoire | appliquer révisions ; désactiver si droit change |
| GDELT | réponse API ≤ 24 h ; aucun texte d’éditeur | métadonnées GDELT ≤ 1 an | agrégats non personnels ≤ 5 ans | rectifier le lien/source ; respecter retrait éditeur |
| Bluesky | texte ≤ 24 h, aucun média | URI/CID/DID utiles ≤ 7 j | agrégats réversibles ≤ 30 j | purge suppression/désactivation/takedown ≤ 24 h |
| Reddit | texte/auteur/métadonnées ≤ 24 h | aucune conservation au-delà de 48 h | fenêtre courte et réversible, sinon aucune | contenu/auteur supprimé dès détection ; purge globale < 48 h |
| X | contenu ≤ 24 h | IDs ≤ 30 j si cas d’usage approuvé | agrégats réversibles ≤ 30 j si permis | supprimer/modifier dès que possible, au plus tard 24 h après demande |
| Stocktwits | aucun | aucun | aucun | source `UNSUPPORTED` |

Ces durées sont des maxima Vertex, pas une extension de licence. Une règle contractuelle plus courte remplace le tableau sans ADR ; une durée plus longue exige revue juridique/contractuelle, justification et ADR.

## Règles communes de conservation

### Minimisation

- Stocker un identifiant et un lien plutôt qu’une copie du contenu.
- Ne jamais archiver images, vidéos, pièces jointes ou PDF d’éditeur depuis une source sociale/news.
- N’ingérer que les instruments, entités, séries et communautés en allowlist.
- Ne jamais stocker message privé, email, IP, géolocalisation précise ou identifiant hors finalité.
- Les auteurs sociaux sont pseudonymisés seulement si nécessaire au calcul de diversité ; aucun rapprochement entre plateformes.

### Backups

- Les contenus `R3` et `R4` à TTL court sont exclus des sauvegardes longues.
- Chaque ligne persistée porte `source_id`, `retention_class`, `delete_by` et `rights_version`.
- Une restauration réapplique immédiatement le journal des suppressions avant d’ouvrir l’API.
- Les sauvegardes expirées sont détruites ; elles ne servent jamais d’archive cachée d’un contenu supprimé.
- Une fin de licence inclut base primaire, caches, index de recherche, objets, exports, files, DLQ et sauvegardes récupérables.

### IA

- Aucun corpus IBKR, éditeur, Bluesky, Reddit, X ou Stocktwits n’est utilisé pour entraînement, fine-tuning, embeddings persistants ou évaluation externe.
- Un résumé IA n’est permis que si la transmission au fournisseur est autorisée ; sinon le résumé reste désactivé ou utilise un traitement local approuvé.
- Les prompts et traces ne contiennent pas le corps sous licence. Les citations pointent vers les identifiants encore accessibles.
- La suppression d’une observation supprime aussi résumé, embedding, cache et index associés.

### Affichage et redistribution

- L’interface privée n’accorde aucun droit de redistribution.
- Afficher provenance, éditeur, nature live/delayed, entitlement et lien officiel selon les exigences de la source.
- Ne jamais exporter un corpus d’articles/posts, fournir une API de revente ou exposer une source souscrite à un autre utilisateur.
- Le partage d’une capture masque tout contenu sous licence au-delà de ce que le fournisseur autorise.

## Conditions par source

### IBKR News

La capacité dépend du fournisseur effectivement souscrit pour l’API. `reqNewsProviders` est la seule découverte autorisée ; une source absente donne `NOT_ENTITLED`. Les abonnements sont attachés à l’utilisateur TWS et peuvent avoir des frais distincts de l’affichage TWS.

Règles Vertex :

- usage local privé et informationnel uniquement ;
- conditions de chaque fournisseur enregistrées séparément ;
- aucune redistribution, republication, constitution de dataset ou entraînement IA ;
- corps non persisté par défaut, titres en cache au plus 24 h ;
- à la fin de l’abonnement : couper l’ingestion, invalider l’affichage, purger le contenu licencié et conserver seulement la preuve technique minimale permise ;
- si les conditions de rétention ne sont pas accessibles ou ambiguës, aucun corps/titre n’est stocké.

Références officielles : [TWS API](https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/), [News API](https://interactivebrokers.github.io/tws-api/news.html), [abonnements](https://www.interactivebrokers.com/campus/trading-lessons/subscribing-to-data/), [tarification données](https://www.interactivebrokers.com/en/pricing/market-data-pricing.php).

### IBKR Wall Street Horizon

WSH est une donnée tierce distribuée par IBKR. La présence de méthodes API ne prouve ni entitlement ni droit d’archivage.

Règles Vertex :

- sonder la capacité et afficher `NOT_ENTITLED` si absente ;
- interdire `fillPortfolio` et toute lecture de compte/positions ;
- conserver la révision et la certitude, pas seulement la dernière date ;
- pas de redistribution du calendrier ;
- TTL brut 24 h et normalisé limité à la fenêtre opérationnelle, sauf droit documenté plus large ;
- purge du contenu licencié à la fin de l’abonnement.

Références officielles : [documentation TWS API](https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/), [WSH corporate events](https://interactivebrokers.github.io/tws-api/fundamentals.html), [filtres WSH](https://interactivebrokers.github.io/tws-api/wshe_filters.html).

### SEC EDGAR

EDGAR est accessible gratuitement sans clé, mais l’accès automatisé reste soumis au Fair Access. Le plafond officiel actuel est 10 requêtes/s, avec `User-Agent` déclaré. Les API `data.sec.gov` fournissent submissions et XBRL ; les corrections post-acceptation doivent être absorbées.

Règles Vertex :

- plafond interne inférieur au maximum SEC, cache conditionnel et téléchargement bulk pour le volume ;
- ne pas utiliser les résultats HTML comme source automatisée ;
- conserver CIK, accession, formulaire, unité, période, amendement et date de dépôt ;
- vérifier chaque semaine les indexes reconstruits pour suppressions/corrections ;
- minimiser les noms/identifiants de personnes physiques et ne jamais constituer un profil individuel ;
- l’interface lie vers le dépôt officiel au lieu d’en republier une copie complète.

Références officielles : [API EDGAR](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [Fair Access et corrections](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data), [ressources développeurs](https://www.sec.gov/about/developer-resources).

### FRED/ALFRED

L’accès API requiert une clé selon la version. Les séries peuvent appartenir à des tiers ; leur disponibilité dans FRED n’annule pas leur copyright. Les notes d’une série et sa source sont donc une contrainte exécutable.

Règles Vertex :

- allowlist par `series_id` avec propriétaire, attribution, copyright, finalité et droit de stockage/affichage ;
- exclure par défaut toute série marquée `Copyright` d’un export ou usage dépassant le personnel ;
- associer chaque observation à son vintage ALFRED pour audit et backtest ;
- conserver les séries autorisées aussi longtemps que nécessaire, mais appliquer les mêmes droits aux dérivés ;
- afficher FRED et la source d’origine sans suggérer d’affiliation ou d’endossement ;
- si les droits changent, désactiver la série et appliquer la procédure de purge prévue par le propriétaire.

Références officielles : [API](https://fred.stlouisfed.org/docs/api/fred/), [conditions API](https://fred.stlouisfed.org/docs/api/terms_of_use.html), [mentions légales](https://fred.stlouisfed.org/legal/), [ALFRED](https://fred.stlouisfed.org/docs/api/fred/alfred.html), [clés API](https://fred.stlouisfed.org/docs/api/fred/v2/api_key.html).

### GDELT

GDELT déclare ses datasets disponibles sans frais pour usages académiques, commerciaux et gouvernementaux, avec citation et lien vers GDELT lors de l’usage ou redistribution. Cette ouverture concerne les données GDELT, pas le copyright des articles et images d’éditeurs référencés.

Règles Vertex :

- inclure attribution « GDELT Project » et lien ;
- stocker métadonnées, thèmes, scores GDELT et URL, jamais le texte/image des éditeurs ;
- ne pas franchir paywall ni récupérer l’article cible ;
- conserver le nom de l’éditeur et distinguer GDELT de la source primaire ;
- utiliser cadence 15 minutes comme fréquence annoncée, pas comme SLA ;
- un score de tonalité GDELT reste un champ fournisseur et ne devient pas sentiment investisseur.

Références officielles : [conditions GDELT](https://www.gdeltproject.org/about.html), [données](https://www.gdeltproject.org/data.html), [DOC 2.0](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/), [cadence GDELT 2.0](https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/).

### Bluesky / AT Protocol

Les repositories AT Protocol contiennent des données publiques et vérifiables, mais les utilisateurs gardent la propriété de leur contenu. Les suppressions de record et les états supprimé, désactivé, suspendu ou takedown doivent être propagés.

Règles Vertex :

- endpoints AppView publics officiels, sans compte utilisateur et sans écriture ;
- allowlist de requêtes, aucun miroir complet ni archive de média ;
- respecter limites du service et labels de modération ;
- texte 24 h, métadonnées sept jours, agrégats réversibles 30 jours ;
- purge contenu/dérivés au plus tard 24 h après événement de suppression/état inactif ;
- aucun graphe social, rapprochement d’identité, caractéristique sensible ou entraînement IA.

Références officielles : [API et auth](https://docs.bsky.app/docs/advanced-guides/api-directory), [rate limits](https://docs.bsky.app/docs/advanced-guides/rate-limits), [firehose](https://docs.bsky.app/docs/advanced-guides/firehose), [accounts](https://atproto.com/specs/account), [repositories](https://atproto.com/specs/repository), [conditions Bluesky](https://bsky.social/about/support/tos).

### Reddit Data API

Reddit impose une approbation explicite, OAuth et un `User-Agent` descriptif. L’usage commercial exige permission et contrat ; l’accès gratuit éligible est actuellement limité à 100 QPM par client OAuth, moyenné sur dix minutes. Reddit exige la suppression du contenu supprimé et recommande de supprimer régulièrement toute donnée/contenu stocké sous 48 h.

Règles Vertex :

- source désactivée jusqu’à approbation du cas d’usage exact ;
- texte, auteur et métadonnées 24 h, purge dure avant 48 h ;
- suppression d’un post/comment : supprimer titre, corps, URL et dérivés associés ;
- suppression d’un compte : supprimer ID, nom, profil, avatar, flair et toute référence auteur ;
- agrégats courts avec provenance permettant de soustraire une observation supprimée ;
- aucune recherche académique hors programme officiel, commercialisation sans contrat, publicité ciblée, entraînement IA, ré-identification ou inférence sensible ;
- respecter en-têtes de rate limit sans multiplier les applications.

Références officielles : [Data API Wiki](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki), [accès et commercial](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data), [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy), [Data API Terms](https://redditinc.com/policies/data-api-terms), [Developer Terms](https://redditinc.com/policies/developer-terms).

### X API

L’accès nécessite un compte développeur, un cas d’usage déclaré et des clés d’application. Le modèle actuel est pay-per-use par crédits. La Developer Policy oblige à tenir le contenu stocké à jour et à supprimer/modifier le contenu dès que raisonnablement possible, au plus tard 24 h après demande de X ou du titulaire concerné.

Règles Vertex :

- OAuth 2.0 App-Only, lecture publique uniquement ;
- plafond de crédits mensuel humain et arrêt automatique avant dépassement ;
- contenu 24 h, IDs/agrégats jusqu’à 30 jours seulement si le cas approuvé le permet ;
- relecture de la version courante avant affichage et traitement des flux de conformité si disponibles ;
- aucune donnée protégée/privée, DM, écriture, ciblage, profilage ou entraînement IA ;
- ne pas qualifier publiquement comptes/contenus de bots, spam ou violation sans permission écrite spécifique ;
- ne pas masquer les marques/attributions ni modifier substantiellement le cas d’usage sans nouvelle approbation.

Références officielles : [Developer Policy](https://docs.x.com/developer-terms/policy), [Developer Agreement](https://docs.x.com/developer-terms/agreement), [prix](https://docs.x.com/x-api/getting-started/pricing), [rate limits](https://docs.x.com/x-api/fundamentals/rate-limits), [Search Posts](https://docs.x.com/x-api/posts/search/introduction), [flux de conformité](https://docs.x.com/x-api/stream/stream-posts-compliance-data).

### Stocktwits

La page officielle de création d’application indique que Stocktwits révise ses API, documentation et conditions et n’accepte pas de nouvelles inscriptions. Firestream documente des endpoints protégés par les identifiants d’un compte autorisé, mais aucun droit public ne peut en être déduit.

Règles Vertex :

- statut `UNSUPPORTED`, zéro collecte et zéro rétention ;
- aucun scraping du site ou de l’application ;
- aucun endpoint découvert par inspection réseau ;
- réouverture seulement après autorisation/contrat écrit, coût, limites, droits dérivés et suppression approuvés par ADR.

Références officielles : [statut développeur](https://api.stocktwits.com/developers), [Firestream](https://firestream-portal.stocktwits.com/), [documentation API](https://api-docs.stocktwits.com/).

## Suppression et rectification

### Contrat technique

Chaque observation persistée doit fournir :

- `source_id`, `native_id`, `rights_version`, `retention_class` ;
- `collected_for`, `collected_at`, `delete_by` ;
- `parent_ids` pour tous les dérivés ;
- `content_state = ACTIVE | MODIFIED | DELETED | TAKEDOWN | EXPIRED` ;
- `purged_at`, `purge_reason` et hash de preuve non reconstructible.

### Pipeline

1. Recevoir ou détecter suppression, modification, fin d’entitlement ou expiration TTL.
2. Marquer immédiatement l’observation non affichable.
3. Invalider cache, index, résumé, embedding, cluster et agrégat réversible.
4. Purger base, objet, file et DLQ ; inscrire une preuve minimale sans contenu.
5. Propager le tombstone vers les vues et snapshots.
6. Empêcher une sauvegarde restaurée de ressusciter la donnée.
7. Mesurer le délai et alerter avant le SLA de la source.

## Revue périodique

- À chaque démarrage : entitlement IBKR et état des credentials, sans lire compte/positions.
- Chaque jour : quotas/coûts, erreurs de suppression et lignes échues.
- Chaque semaine : corrections SEC et échantillon de conformité d’affichage.
- Chaque mois : coût X/IBKR, pertinence, minimisation et taux de faux rapprochement.
- Chaque trimestre et avant release : relire toutes les conditions officielles, vérifier les liens et dater `rights_version`.
- À tout changement de prix, politique, finalité ou propriétaire : couper la source jusqu’à revue humaine.

## Décision fail-closed

Une source dont le droit, la fraîcheur, l’identité, la suppression ou le coût est inconnu publie `UNSUPPORTED`, `NOT_ENTITLED`, `STALE` ou `ERROR`. Vertex n’affiche pas le contenu, ne le remplace pas par une autre source et ne conserve pas un ancien signal comme s’il était actuel.

Le manifeste `manifests/news-social-sources.yaml` matérialise ces règles. Un contrat signé plus strict doit y être traduit avant activation.
