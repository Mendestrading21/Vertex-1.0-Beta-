"""Vertex — ingestion locale des alertes TradingView (LOT-05, socle local).

Ce paquet valide le contrat ``vertex.tradingview.alert.v1`` (miroir Pydantic du
Worker Cloudflare), tient le registre des alertes autorisées et orchestre la
machine RECEIVED -> PERSISTED -> WAITING_FOR_IBKR -> REVALIDATED | BLOCKED |
EXPIRED.

Invariants :
- une alerte TradingView est un déclencheur, jamais une preuve de prix ;
- le prix transporté est du contexte non autoritaire ;
- ack uniquement après persistance confirmée ; fail-closed partout ;
- aucune donnée de marché réelle : les tests utilisent des fakes synthétiques.
"""
