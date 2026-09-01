# Page 09 — Suivi `/follow-up`

> **Statut depuis le LOT-10 : ce n'est plus une destination.** Le contenu
> ci-dessous reste le contrat du MODULE de revue, désormais rendu par
> `/catalysts` (voir `docs/05-design/PAGE_ARBITRATION.md`). La question, les
> états et les critères d'acceptation sont inchangés ; seule la page hôte
> change. `/follow-up` redirige en permanence vers `/catalysts`.

## Question

Quelles thèses, alertes et informations doivent être revues ?

## Dominante et modules

Dominante : file des revues.

1. Table thèses/revues.
2. Fiche de la thèse sélectionnée.
3. Timeline des changements, news, événements et signaux.
4. Hygiène des watchlists et alertes.

Action principale : marquer une revue avec note et décision de suivi.

## Données et logique

Thèses manuelles, anciens `AdviceResult`, clusters d'information, événements, alertes Pine et niveaux de marché. Une nouvelle information peut rendre une revue urgente, mais ne modifie pas la thèse automatiquement.

## États et adaptation desktop

Offline autorise les brouillons. Stale marque les niveaux mais conserve l'historique. Cible Vertex 1.0 Beta : 1280, 1440 et 1600 px. À 1024 px, la file des revues reste première et la fiche sélectionnée passe sous la table avec continuité de sélection et de focus.

Mobile : **LATER**. Les contrats sémantiques des thèses, urgences, états, historique et actions sont conservés, sans variante Vertex pour téléphone.

## Acceptation

- historique append-only des révisions ;
- raison d'urgence visible ;
- E2E révision, report, archivage et nouvelle contradictoire.
