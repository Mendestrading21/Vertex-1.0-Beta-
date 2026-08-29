# AI Gateway — explication sourcée uniquement

## Rôle

L'IA rend les résultats Vertex plus lisibles. Elle reformule des faits déjà calculés et certifiés, résume un corpus autorisé, compare des scénarios fournis et répond sur la base des preuves reçues. Elle ne collecte pas les données de marché, ne calcule pas une valeur financière faisant autorité, ne prédit pas, ne décide pas et n'agit pas.

L'application reste intégralement compréhensible sans fournisseur IA grâce à des gabarits déterministes construits depuis les mêmes DTO.

## Autorité et frontières

Entrées autorisées, sur allowlist et versionnées :

- `AdviceResult` déjà produit par l'unique `AdviceEngine` ;
- `GateResult`, `CalculationRecord` et scénarios certifiés en lecture ;
- `NewsCluster` déterministe et extraits dont `ArticleAccess` autorise le traitement ;
- événements, faits fondamentaux, profils ETF, signaux et états de qualité canoniques ;
- thèse ou portefeuille manuel seulement si le cas d'usage est activé explicitement et après minimisation.

Sorties autorisées : `Explanation`, `ClusterSummary`, `ScenarioNarrative` et `EvidenceAnswer`, sous schéma JSON strict. Une sortie contient au minimum langue, texte structuré, `evidence_ids`, limites, `as_of`, fournisseur/modèle, version de prompt et statut de validation.

L'IA ne possède jamais :

- accès direct IBKR, TradingView, PostgreSQL, fichiers, navigateur, shell, URL arbitraire ou Internet ;
- outil d'écriture, notification externe, modification de thèse/portefeuille, création d'alerte ou effet de bord ;
- méthode d'ordre, de compte, position, P&L ou exécution ;
- droit de créer/modifier un `GateResult`, `CalculationRecord`, `AdviceResult`, rang, couverture, entitlement ou identité ;
- capacité à transformer `BLOCKED`, `INSUFFICIENT_DATA`, `OBSERVE` ou `REVIEW` en `QUALIFIED` ;
- droit de compléter un fait, prix, date, probabilité, unité, source ou citation absent.

## Cas d'usage permis

1. Expliquer un `AdviceResult` dans un langage simple en conservant statut, direction, horizon, gates et limites.
2. Résumer un `NewsCluster` déjà dédupliqué sans décider quels items appartiennent au cluster.
3. Décrire les différences entre scénarios calculés, sans recalculer leurs valeurs.
4. Répondre à une question sur les données canoniques fournies, avec preuve pour chaque affirmation factuelle.
5. Reformuler une alerte, un événement ou une anomalie de données en distinguant observation, calcul, interprétation et inconnue.

Ne sont pas permis : recommandations d'achat/vente, prix cible inventé, taille de position, probabilité non fournie, sélection automatique d'une stratégie, résumé d'un contenu non licencié, recherche web autonome et conseil présenté comme vérité certaine.

## Contrat d'entrée

Le `AiExplanationRequest` contient :

```text
request_id, use_case, locale, requested_at, as_of,
subject_ids, certified_facts[], evidence_catalog[],
required_limitations[], rights[], data_quality,
prompt_version, output_schema_version, privacy_mode
```

- `certified_facts` utilise des champs structurés, unités explicites et décimales sous forme de chaînes.
- `evidence_catalog` mappe chaque `evidence_id` vers un titre sûr, sa source, son heure, son droit et une cible d'ouverture autorisée ; le modèle ne compose pas d'URL.
- Le gateway supprime tout champ hors allowlist. Les objets complets, secrets, identifiants techniques de compte et données inutiles ne sont jamais envoyés.
- Les textes issus des sources sont marqués comme contenu non fiable et délimités séparément des instructions système.
- Un droit insuffisant, une qualité invalide ou un corpus vide renvoie un refus structuré avant appel fournisseur.

## Contrat de sortie et validation

La sortie du fournisseur passe successivement par :

1. parsing JSON sans coercition ;
2. validation de schéma/version/taille/langue ;
3. vérification que chaque `evidence_id` existe dans la requête et est autorisé ;
4. vérification de couverture : toute phrase factuelle doit référencer au moins une preuve ;
5. comparaison des nombres, unités, dates, statuts et directions avec les faits fournis ;
6. détection de langage interdit : ordre, promesse, certitude non justifiée ou élévation de statut ;
7. ajout déterministe des limites obligatoires ;
8. décision `VALID`, `RETRYABLE_INVALID`, `REJECTED` ou `FALLBACK`.

Une citation n'est jamais une URL produite par le modèle. L'interface résout les `evidence_ids` via le catalogue serveur après contrôle d'autorisation.

Une réponse invalide n'est pas affichée partiellement. Le gateway effectue au maximum une réparation structurée, sans nouvel apport de faits, puis utilise le gabarit déterministe.

## Défense contre l'injection

- Système, contrat, faits structurés et contenu externe utilisent quatre canaux/délimiteurs distincts.
- Headline, article, filing, thèse, note et texte d'alerte sont toujours des données non fiables, jamais des instructions.
- Les chaînes « ignore les règles », faux JSON, liens, code, balises et demandes d'outil restent citées ou neutralisées comme contenu.
- Aucun contenu source ne peut modifier modèle, prompt, schéma, outils, droits, politique de confidentialité ou liste de preuves.
- Le gateway refuse les URLs non cataloguées, les références à une preuve absente et toute tentative de révéler prompt, secret ou donnée d'un autre utilisateur.
- Les tests utilisent un corpus multilingue d'injections directes, indirectes, encodées et imbriquées.

## Droits, confidentialité et rétention

- `ArticleAccess` est vérifié avant préparation, appel, cache et affichage. Un droit headline-only n'autorise pas l'envoi du corps.
- Par défaut, les quantités, coûts, notes libres et identifiants du portefeuille manuel sont exclus. Un cas d'usage activé n'envoie que les agrégats strictement nécessaires.
- Aucun secret, token, capacité de webhook, prompt complet sensible ni payload fournisseur brut ne figure dans les logs.
- Les traces conservent hashes, IDs, versions, latence, compte de tokens, validation et coût ; le texte n'est conservé que selon la politique explicite de rétention.
- Les caches sont cloisonnés par utilisateur, droits, locale, modèle, prompt, schéma et hash exact des faits. Une révocation de droit invalide les entrées concernées.
- Le choix du fournisseur, la région, la conservation et l'utilisation des données pour entraînement nécessitent validation humaine et ADR.

## Reproductibilité, coût et résilience

- Chaque appel enregistre fournisseur, modèle exact, paramètres, prompt SHA, schéma, hash d'entrée et horodatage.
- Température basse et paramètres bornés pour l'explication ; aucune valeur pseudo-déterministe n'est promise si le fournisseur ne la garantit pas.
- Quotas par utilisateur/cas d'usage, limites de tokens, timeout, concurrence bornée, circuit breaker et budget mensuel configurable.
- Les appels ne bloquent jamais la collecte, les calculs, les gates ou l'affichage déterministe.
- En panne, quota dépassé, timeout, schéma invalide ou refus de droits : gabarit déterministe, statut visible et aucune répétition illimitée.
- Un changement de modèle ou prompt est évalué hors ligne sur le corpus golden avant activation progressive et retour arrière possible.

## Interface fournisseur

Le domaine dépend d'un port minimal, pas du SDK d'un vendeur :

```text
explain(request: AiExplanationRequest) -> AiExplanationResponse
health() -> AiProviderHealth
estimate(request_metadata) -> AiCostEstimate
```

Le port n'accepte ni URL, ni outil, ni callback, ni instruction libre non typée. Les adaptateurs fournisseurs vivent dans `adapters/ai`; validation, droits, fallback et journal d'audit restent dans `ai`/`application`.

## Tests obligatoires

- Schéma : sorties valides, JSON cassé, champs inconnus, texte trop long, langue incorrecte et version incompatible.
- Grounding : preuve absente, citation inventée, nombre/date/unité/statut modifié, contradiction et affirmation sans preuve.
- Sécurité : injections dans news, filing, alerte, note et thèse ; exfiltration de prompt/secret ; URL et outil inventés.
- Autorité : tentatives de modifier gate/verdict/rang, recommandation d'ordre, calcul de taille ou probabilité inventée.
- Droits/confidentialité : headline-only, droit révoqué, cache inter-utilisateur, données manuelles non nécessaires et logs.
- Résilience : timeout, 429, 5xx, flux interrompu, réponse vide, réparation invalide, circuit ouvert et fournisseur absent.
- Golden set : explications en français pour chaque statut/direction, données partial/delayed/stale/conflict et scénarios actions/options/ETF.
- Évaluations : fidélité aux faits, couverture des preuves, conservation des limites, absence de recommandation et lisibilité, avec reviewers humains aveugles aux variantes.

## Critères d'acceptation

- 100 % des affirmations factuelles du corpus golden portent un `evidence_id` présent et autorisé ; zéro citation ou URL inventée.
- 100 % des nombres, dates, unités, statuts et directions affichés correspondent exactement aux faits certifiés ou sont omis.
- Zéro élévation de statut, création de verdict, ordre, taille, prix cible ou probabilité dans les tests normaux et adversariaux.
- 100 % des sorties invalides sont rejetées avant UI ; après une réparation maximum, le fallback déterministe s'affiche.
- Les tests d'injection directe/indirecte atteignent 100 % de blocage des effets interdits et zéro appel d'outil, puisqu'aucun outil n'est exposé.
- Aucun corps non autorisé ni champ portefeuille exclu n'apparaît dans requête fournisseur, cache, logs ou réponse.
- Une panne totale du fournisseur conserve 100 % des pages fonctionnelles avec explication déterministe et état honnête.
- Chaque réponse est retraçable par `request_id`, hashes, modèle, prompt, schéma, preuves, validation, latence et coût, sans contenu sensible.
- Tout changement de modèle/prompt passe le corpus golden, la revue sécurité/droits et un canary réversible avant généralisation.
