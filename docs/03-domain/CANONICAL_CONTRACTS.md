# Contrats canoniques

Tous les modèles sont Pydantic stricts, immuables et versionnés. Les timestamps sont UTC et timezone-aware. Les prix, montants et ratios sensibles traversent l'API sous forme de chaînes décimales.

## Identités

### `InstrumentId`

```text
instrument_id, asset_class, canonical_symbol, exchange, currency,
ibkr_con_id, tradingview_ticker_id, isin?, cusip?, cik?, issuer_id?,
valid_from, valid_to?, identity_status
```

Un symbole seul n'est jamais une identité. Toute collision reste `UNRESOLVED` jusqu'à résolution explicite.

### `OptionContractId`

```text
underlying_id, ibkr_con_id, expiry, strike, right, exercise_style,
settlement, multiplier, currency, exchange, trading_class,
adjustment_code?, deliverable?
```

L'expiration ne peut pas être identifiée par sa date seule : plusieurs `trading_class` peuvent coexister.

## Enveloppe source

### `DataEnvelope[T]`

```text
event_id, schema_version, source, source_event_id?, entitlement_id?,
instrument_id?, observed_at?, published_at?, received_at, as_of,
stale_after, quality_status, delay_status, connection_epoch?,
rights, payload_hash, payload
```

États de qualité : `VALID`, `PARTIAL`, `STALE`, `INVALID`, `CONFLICT`, `INSUFFICIENT_DATA`.

États de délai : `LIVE`, `FROZEN`, `DELAYED`, `DELAYED_FROZEN`, `UNKNOWN`.

## Marché

- `QuoteSnapshot` : bid/ask/last, tailles, type de marché, timestamps, spread et source.
- `Bar` : OHLCV, timeframe, session, ajustement, timezone et complétude.
- `OptionQuote` : contrat exact, bid/ask/last, OI, volume, Greeks fournisseur et sous-jacent associé.
- `OptionChainSnapshot` : expirations, contrats, couverture, budget de lignes et âge maximum.
- `ScannerResult` : définition versionnée du scan, rang, instrument, heure et données enrichies séparément.
- `MarketRegimeSnapshot` : méthode, features, état, confiance descriptive et limites.

## Information fusionnée

- `NewsItem` : provider, article ID, headline, dates, entités, URL/droit, langue et corps autorisé.
- `NewsCluster` : items reliés, fait principal, conflits, sources et raisons de pertinence.
- `CorporateEvent` : type, instrument, date/heure, statut estimé/confirmé, source et révisions.
- `MacroEvent` : zone, série, publication, période, consensus?, précédent?, réel?, vintage.
- `Filing` : autorité, accession, type, période, date de dépôt et document.
- `FundamentalFact` : taxonomie, concept, valeur, unité, période, filing et dimensions.
- `EtfProfile` : émetteur, benchmark, devise, domicile, structure et date.
- `TechnicalSignal` : script/version, symbole, timeframe, condition, valeur, bar time et état de repaint.
- `SourceEntitlement` : capacité, identifiant d'utilisateur technique, statut, délai, testé à et erreur.
- `SourceCoverage` : univers, champs disponibles, taux de couverture, âge et limites.

## Portefeuille manuel

- `Portfolio`, `PortfolioBaseCurrency`, `CashLedgerEntry`.
- `PositionLot` : instrument, quantité, coût, date, frais, source manuelle/import et révision.
- `Transaction` : entrée, sortie, dividende, frais, taxe, transfert, FX ou ajustement manuel.
- `Thesis` : horizon, hypothèses, invalidation, objectifs, échéance de revue et snapshots liés.

Aucun champ `ibkr_account_id` n'est autorisé dans ces contrats.

## Calcul

### `CalculationRecord`

```text
calculation_id, calculation_type, engine_version, code_sha,
input_hash, source_event_ids, assumptions, method, parameters,
random_seed?, started_at, completed_at, status, warnings,
result_hash, result
```

### `GateResult`

```text
gate_id, version, status(PASS|DEGRADE|BLOCK), reason_code,
message, evidence_ids, observed_values, thresholds
```

### `AdviceResult`

```text
advice_id, instrument_id, as_of, valid_until, input_snapshot_id,
engine_version, status, direction, horizon, gates[], evidence_ids[],
risk_summary, scenario_ids[], probability_evidence?, limitations[],
explanation_facts[], supersedes?
```

`status` : `BLOCKED`, `INSUFFICIENT_DATA`, `OBSERVE`, `REVIEW`, `QUALIFIED`. `direction` : `BULLISH`, `BEARISH`, `NEUTRAL`, `MIXED`, `UNKNOWN`. Aucun champ n'ordonne d'acheter ou vendre.
