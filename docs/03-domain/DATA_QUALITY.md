# Qualité, fraîcheur et couverture

## Validation en couches

1. Schéma et type.
2. Identité d'instrument.
3. Unité, devise et multiplicateur.
4. Timestamp, ordre temporel et dérive d'horloge.
5. Droit/entitlement et type live/delayed.
6. Bornes physiques et financières.
7. Cohérence bid/ask/OHLC/parité.
8. Couverture requise par l'usage.
9. Fraîcheur session-aware.
10. Conflit entre sources.

## TTL par usage

Le TTL n'est pas un nombre global. Le registre associe source, type de donnée, session et cas d'usage. Exemples : une quote utilisable pour un briefing de clôture peut être trop ancienne pour une analyse intraday ; une chaîne partielle peut suffire à inspecter un contrat mais pas à construire une surface.

Les politiques se nomment et se versionnent : `intraday_quote`, `selected_option_quote`, `option_surface`, `daily_bar`, `news_attention`, `corporate_event`, `fundamental_filing`, `portfolio_mark`.

## Couverture

Chaque collection publie : attendu, reçu, valide, retardé, périmé, manquant, taux de couverture et âge maximal. L'UI n'affiche jamais « chaîne complète » ou « marché complet » sans preuve.

## Conflits

- Le prix IBKR et le prix d'une alerte TradingView ne sont pas fusionnés : ils restent deux observations.
- Une date d'événement WSH, Pine ou SEC peut être révisée ; toutes les révisions sont conservées.
- Un fait fondamental est identifié par concept, période, unité, dimensions et filing.
- Aucun vote majoritaire automatique ne résout une contradiction financière.

## Fail-closed

Toute gate nécessitant du live bloque si le droit est absent, le type est delayed, l'epoch est ancien, la quote précède la demande ou l'horloge est douteuse. Le dernier snapshot reste consultable mais ne produit pas de nouveau `AdviceResult` exploitable.

