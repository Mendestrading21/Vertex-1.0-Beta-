# Page 02 — Calendrier `/calendar`

## Question

Quels événements peuvent affecter mes instruments et mon portefeuille ?

## Dominante et modules

Dominante : agenda chronologique jour/semaine.

1. Agenda macro, résultats, dividendes, expirations, splits, IPO, conférences et filings.
2. Barre de filtres compacte et vues enregistrées.
3. Croisement position/watchlist/thèse.
4. Fiche événement et historique de révision.

Action principale : créer une note ou alerte locale sur l'événement.

## Données et logique

Événements WSH lorsque souscrit, Pine ciblé, FRED releases, SEC filings et saisies manuelles. L'importance vient de la source ou d'une règle versionnée ; l'IA ne l'invente pas. Les dates estimées et confirmées restent distinctes.

## États et adaptation desktop

Erreur isolée par source. Une absence WSH affiche le droit manquant, pas un agenda vide trompeur. Cible Vertex 1.0 Beta : 1280, 1440 et 1600 px. À 1024 px, l'agenda chronologique reste dominant et la fiche événement passe sous l'agenda, sans substitution par une vue téléphone.

Mobile : **LATER**. Les contrats sémantiques des événements, filtres, états, dates et actions sont conservés pour la phase ultérieure ; aucun rendu Vertex pour téléphone n'est spécifié.

## Acceptation

- timezone source, exchange et utilisateur testées ;
- révisions et conflits visibles ;
- filtres persistants et accessibles ;
- E2E earnings, événement macro, expiration et abonnement absent.
