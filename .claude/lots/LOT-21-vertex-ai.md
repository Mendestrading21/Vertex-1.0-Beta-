# LOT-21 — Page Vertex AI

## Références et dépendances

- Fiche produit obligatoire : `docs/01-product/pages/11-vertex-ai.md`.
- Références transversales : `docs/03-domain/CANONICAL_CONTRACTS.md`, `docs/03-domain/DECISION_ENGINE.md`, `docs/03-domain/DATA_QUALITY.md`, `docs/04-integrations/DATA_FUSION.md`, `docs/05-design/UI_STATES.md`, `docs/05-design/ACCESSIBILITY.md`, `docs/06-quality/SECURITY_CONTROLS.md` et `docs/06-quality/OBSERVABILITY.md`.
- Dépendances bloquantes : LOT-02 Contrats canoniques, LOT-03 Stockage et qualité, LOT-06 Data Fusion, LOT-08 Décision, LOT-09 API/jobs, LOT-10 Design shell et les DTO certifiés des pages 11 à 20.

Le lot ne commence qu'après définition d'une passerelle IA à outils allowlistés, d'un schéma de sortie strict et d'un jeu d'évaluation hostile. L'indisponibilité du fournisseur IA ne doit bloquer aucune autre route.

## Question à résoudre

Comment expliquer, relier et résumer les données certifiées, avec leurs contradictions et limites, sans créer une seconde vérité ?

## Objectif

Livrer `/ai`, une interface d'explication sourcée sur des snapshots immuables. Vertex AI reformule des faits structurés, relie des preuves autorisées et signale les données manquantes. Il ne calcule aucune valeur financière, ne produit aucun verdict et n'exécute aucune écriture ou opération.

## Non-objectifs

- accéder directement à TWS, PostgreSQL, aux secrets, au système de fichiers ou au portefeuille complet par défaut ;
- recalculer prix, Greeks, probabilité, score, performance, risque, scénario ou agrégat ;
- créer, modifier ou arbitrer un `AdviceResult`, une `GateResult`, une thèse, une alerte ou un ordre ;
- traiter le texte d'une news, d'un document ou d'un utilisateur comme instruction système ;
- masquer une contradiction, combler une donnée absente ou citer une source non consultée ;
- conserver un prompt ou une réponse contenant des données sensibles non nécessaires.

## Contrats et autorité

Entrées autorisées : contrats typés, `AdviceResult.explanation_facts`, `NewsCluster`, événements, faits, documents autorisés et métadonnées de snapshots immuables. Aucun payload brut de fournisseur n'est transmis par défaut.

Contrats de page à exposer par OpenAPI :

- `AiQuestionRequest` : question, périmètre explicite, identifiants de snapshots, langue et clé d'idempotence ;
- `EvidenceExcerpt` : identifiant immuable, source, droit d'accès, `as_of`, extrait autorisé, hash et URL sûre éventuelle ;
- `AiAnswer` : sections structurées, affirmations, citations, contradictions, données manquantes, limites, modèle, politique et `as_of` ;
- `CitedClaim` : texte, type `FACT|INTERPRETATION`, identifiants de preuves et niveau de support ;
- `SavedAiNote` : réponse validée, snapshots, citations, politique, modèle, date et hash.

La passerelle refuse tout outil hors lecture allowlistée. Les calculs et décisions viennent exclusivement des moteurs certifiés ; l'IA peut les expliquer et les citer, jamais les remplacer, les recomposer ou en inventer. Toute sortie est validée par schéma avant affichage ou sauvegarde. Une citation devenue inaccessible reste un tombstone explicite et n'est pas supprimée silencieusement.

## Livrables desktop

1. Zone de question avec périmètre visible et sélection explicite des snapshots accessibles.
2. Réponse structurée séparant faits, interprétations, contradictions, données manquantes et limites.
3. Citations ouvrables vers un panneau de preuve montrant source, date, droit, extrait autorisé et snapshot exact.
4. Bandeau permanent rappelant le périmètre, le `as_of`, le modèle et l'absence d'autorité de calcul/décision.
5. Enregistrement volontaire comme note immuable liée aux mêmes snapshots et hashes.
6. Explication déterministe de l'`AdviceResult` disponible même si l'IA est en panne.

## Périmètre Vertex 1.0 Beta

- Phase 1 **DESKTOP ONLY** : `1280×800`, `1440×900` et `1600×1000`.
- `1024×768` peut servir de dégradation laptop, sans conversation plein écran
  téléphone.
- Feuilles basses, sections conçues spécifiquement pour mobile, bottom nav,
  `MobileActionBar`, gestes tactiles et QA `390`/`360` sont `LATER`.
- Les contrats sémantiques conservent périmètre, ancienneté, citations,
  contradictions, limites, focus et séparation envoi/enregistrement afin que la
  future UI mobile ne change ni preuve ni politique.

## États UI obligatoires

- `loading` : structure de réponse sans faux texte ni citation ;
- `refreshing` : ancienne réponse conservée avec son `as_of`, jamais présentée comme actualisée ;
- `empty` : aucune question ou aucun snapshot sélectionné, avec aide de périmètre ;
- `partial` : réponse affichée seulement si les affirmations restantes sont valides, preuves manquantes listées ;
- `delayed` : sources retardées annotées dans les affirmations concernées ;
- `stale` : ancienne réponse lisible avec watermark et proposition de nouvelle requête, sans réécriture ;
- `offline` : notes enregistrées disponibles en lecture seule ; aucune génération simulée ;
- `error` : provider down, schéma invalide, citation inaccessible et refus de politique distingués.

Une sortie invalide n'est jamais rendue partiellement comme une réponse sûre. Le fallback est une erreur structurée et, lorsqu'il existe, le gabarit déterministe des faits.

## Accessibilité

- Réponse structurée avec titres sémantiques, liens de citations descriptifs et ordre de lecture stable.
- Les citations indiquent verbalement source, date et état ; aucun lien n'est identifié seulement par un numéro ou une couleur.
- Le streaming n'interrompt pas le lecteur d'écran : annonces regroupées et fin de réponse signalée une seule fois.
- Focus restauré après fermeture d'une preuve ; raccourcis facultatifs et aucune interaction hover-only.
- WCAG 2.2 AA, zoom 200 %, textes longs, reduced motion et validation NVDA ou VoiceOver.
- Zéro violation axe critique ou sérieuse.

## Performance

- Création de contexte interne p95 ≤ 250 ms hors appel fournisseur ; aucune requête directe aux sources live depuis le modèle.
- Premier état utile affiché en ≤ 500 ms ; timeout fournisseur explicite et annulable, avec budget configurable.
- Chargement paresseux de l'interface et des citations ; aucune dépendance IA dans le bundle ou le chemin critique des autres pages.
- Taille du contexte, nombre de preuves, tokens, latence et coût journalisés sans contenu sensible.
- Cache uniquement par hash de question, politique, modèle, droits et snapshots ; aucune réponse réutilisée entre périmètres incompatibles.

## Tests obligatoires

- Schéma : rejet de champ inconnu, citation orpheline, claim factuel non cité et snapshot mutable.
- Politique : refus d'ordre, de recalcul, de conseil transactionnel, d'écriture et de lecture hors périmètre.
- Sécurité : prompt injection dans une news, document hostile, URL malveillante, exfiltration de secret et tentative d'appel d'outil interdit.
- Grounding : chaque affirmation financière factuelle pointe vers au moins une preuve réellement fournie ; les interprétations sont étiquetées.
- E2E : provider down, timeout, réponse invalide, citation supprimée/inaccessible, source delayed, ancienne réponse et sauvegarde de note.
- Résilience : la panne IA laisse toutes les autres pages et l'explication déterministe opérationnelles.
- Accessibilité : streaming, navigation dans les citations et erreurs au clavier/lecteur d'écran.

## Critères de sortie mesurables

- 100 % des affirmations financières factuelles affichées possèdent au moins une citation valide vers un snapshot réellement fourni.
- 100 % des interprétations visibles portent explicitement le libellé « Interprétation ».
- 100 % des demandes de calcul, décision, ordre ou écriture du corpus hostile sont refusées sans appel d'outil non autorisé.
- Zéro accès direct à TWS, PostgreSQL, secrets, portefeuille complet ou endpoint d'ordre dans code, configuration et traces de la page.
- 100 % des sorties affichées et notes sauvegardées passent le schéma strict et conservent modèle, politique, `as_of`, snapshots et hashes.
- Les huit états UI, les trois viewports desktop, corpus de prompt injection et
  scénarios E2E passent en CI ; `1024×768` est une dégradation laptop optionnelle
  et aucune QA mobile ne bloque la Beta.
- Revue sécurité et métier confirmant que l'IA explique et cite, mais ne calcule ni ne décide.
