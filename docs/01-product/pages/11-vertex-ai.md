# Page 11 — Vertex AI `/ai`

> **Statut depuis le LOT-12 : ce n'est plus une destination.** Le contenu
> ci-dessous reste le contrat du PANNEAU d'explication, désormais monté dans
> l'inspecteur des pages qui portent un dossier explicable — Analyse et
> Portefeuille (voir `docs/05-design/PAGE_ARBITRATION.md`). La question, les
> états, le bandeau B-05 et les critères d'acceptation sont inchangés ; seule
> la page hôte change. `/ai` redirige en permanence vers `/analysis`.

## Question

Comment expliquer, relier et résumer les données certifiées sans créer une seconde vérité ?

## Dominante et modules

Dominante : réponse structurée avec citations vers snapshots immuables.

1. Question et périmètre.
2. Réponse structurée.
3. Sources/citations.
4. Contradictions, données manquantes et limites.

Action principale : enregistrer la réponse comme note liée à un snapshot.

## Données et logique

Contrats typés, `AdviceResult`, news clusters, événements, faits et documents autorisés. Aucun accès brut à TWS, PostgreSQL, secrets ou portefeuille complet par défaut. Aucun calcul financier ni outil d'écriture.

## États et adaptation desktop

Indisponibilité IA ne bloque aucune autre page. Une ancienne réponse garde son `as_of`. Cible Vertex 1.0 Beta : 1280, 1440 et 1600 px. À 1024 px, la réponse structurée reste dominante et les citations, contradictions et limites passent sous celle-ci.

Mobile : **LATER**. Les contrats sémantiques de question, réponse, citations, états, limites et sauvegarde restent disponibles pour la phase ultérieure, sans interface Vertex pour téléphone.

## Acceptation

- chaque affirmation financière citée ou explicitement interprétative ;
- refus d'ordre et de recalcul ;
- sortie invalide rejetée par schéma ;
- E2E provider down, prompt injection dans une news et citation supprimée.
