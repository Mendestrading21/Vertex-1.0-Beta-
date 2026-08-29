# ADR-014 — Énumérations canoniques du verdict, de la direction et des gates

- Statut : Accepté
- Date : 2026-08-28
- Propriétaire : contrats (`contracts`), moteur de décision (`decision`)

## Contexte

Le blueprint contenait deux vocabulaires concurrents pour le même concept :

- `docs/03-domain/CANONICAL_CONTRACTS.md` et `DECISION_ENGINE.md` :
  statut `BLOCKED | INSUFFICIENT_DATA | OBSERVE | REVIEW | QUALIFIED`,
  direction `BULLISH | BEARISH | NEUTRAL | MIXED | UNKNOWN`,
  gate `PASS | DEGRADE | BLOCK` ;
- `contracts/json-schema/decision-snapshot-v1.schema.json`,
  `manifests/strategy-profiles.yaml` et `STRATEGY_PROFILES.md` :
  statut `REJECT | WATCH | RESEARCH | QUALIFIED | INSUFFICIENT_DATA`,
  direction `UP | DOWN | VOLATILITY | MIXED | UNKNOWN`,
  gate `PASS | WARN | BLOCK | UNKNOWN`.

Deux énumérations concurrentes pour une même vérité violent la Constitution
(« Un seul `AdviceResult` constitue le verdict canonique ») et créeraient une
double autorité dès le premier code.

## Décision

Une seule famille canonique, implémentée dans
`packages/python/vertex_core/contracts` et reprise par tous les schémas :

- `AdviceStatus` = `BLOCKED | INSUFFICIENT_DATA | OBSERVE | REVIEW | QUALIFIED`.
  Correspondance depuis l'ancien vocabulaire : `REJECT → BLOCKED`,
  `WATCH → OBSERVE`, `RESEARCH → REVIEW`.
- `Direction` = `BULLISH | BEARISH | NEUTRAL | MIXED | UNKNOWN`.
- `GateStatus` = `PASS | DEGRADE | BLOCK`. `WARN → DEGRADE`. Une gate qui ne
  peut pas être évaluée est `BLOCK` avec `reason_code = "UNEVALUABLE"`
  (fail-closed) ; l'état `UNKNOWN` de gate est supprimé.
- `DirectionHypothesis` (flux options uniquement) reste une énumération
  distincte : `UP | DOWN | VOLATILITY | HEDGE_LIKELY | MIXED | UNKNOWN`.
  Elle qualifie une hypothèse d'anomalie, jamais un verdict.
- Les qualités restent deux espaces de noms distincts et assumés :
  `EnvelopeQuality` = `VALID | PARTIAL | STALE | INVALID | CONFLICT |
  INSUFFICIENT_DATA` (par observation) et `SnapshotQuality` =
  `GOOD | PARTIAL | DEGRADED | MISSING | CONTRADICTORY` (par snapshot de
  preuves). Aucun des deux ne convertit l'autre implicitement.

`contracts/json-schema/decision-snapshot-v1.schema.json`, son exemple,
`manifests/strategy-profiles.yaml` et `docs/03-domain/STRATEGY_PROFILES.md`
sont alignés dans le même lot. Le schéma reste `1.0.0` : aucun consommateur
n'existe avant ce lot, il s'agit d'une correction pré-release, pas d'une
rupture de compatibilité.

## Conséquences

- Le code Python définit ces énumérations une seule fois ; API, UI, tests et
  documents les consomment sans les redéclarer.
- Tout document historique employant `REJECT/WATCH/RESEARCH` se lit via la
  table de correspondance ci-dessus ; il ne crée pas une seconde autorité.
- La CI (gate `contracts`) échoue si une énumération concurrente réapparaît.

## Options rejetées

- Conserver les deux vocabulaires avec une table de conversion runtime :
  double autorité déguisée, source de divergence silencieuse.
- Adopter `REJECT/WATCH/RESEARCH` comme canonique : perd la distinction
  explicite `BLOCKED` (gate fermée) vs `OBSERVE` (données valides mais
  insuffisantes pour étude), déjà utilisée par la Constitution et les gates.

## Réexamen

Réexaminer si un consommateur externe impose un vocabulaire différent, via un
schéma v2 versionné — jamais par divergence silencieuse.
