/**
 * Manual validation of the vertex.tradingview.alert.v1 contract.
 *
 * Mirror of contracts/json-schema/tradingview-alert-v1.schema.json, implemented
 * by hand (no runtime dependency): required fields, patterns, enums, bounds,
 * additionalProperties: false.
 *
 * Ingress policy overlay (stricter than schema v1, never looser):
 *  - `sent_at` / `bar_time` must be ISO-8601 WITH an explicit timezone
 *    (naive timestamps are ambiguous -> rejected, fail-closed);
 *  - `values.nonce` is REQUIRED: schema v1 has no top-level nonce field and
 *    forbids additional properties, so the nonce travels inside `values`
 *    (allowed string map). The deduplication key is `alert_id + ":" + nonce`.
 *
 * The alert `price` is TradingView context only. It is NEVER authoritative:
 * no financial computation happens here or downstream of this module.
 */

export const SCHEMA_ID = "vertex.tradingview.alert.v1";
export const QUEUE_ENVELOPE_SCHEMA_ID = "vertex.tradingview.queue-envelope.v1";

/** Hard byte limit for the request body (16 KiB). */
export const MAX_BODY_BYTES = 16 * 1024;

/** Signal enum, verbatim from the JSON Schema. */
export const SIGNALS = Object.freeze([
  "SETUP",
  "BREAKOUT",
  "BREAKDOWN",
  "REGIME_CHANGE",
  "EVENT",
  "FUNDAMENTAL_UPDATE",
  "HEARTBEAT",
]);

const REQUIRED_FIELDS = Object.freeze([
  "schema",
  "alert_id",
  "script_version",
  "sent_at",
  "bar_time",
  "exchange",
  "ticker",
  "interval",
  "signal",
]);

const ALLOWED_FIELDS = new Set([...REQUIRED_FIELDS, "price", "values"]);

const SCRIPT_VERSION_RE = /^[0-9]{4}-[0-9]{2}-[0-9]{2}\.[0-9]+$/;
const PRICE_RE = /^-?[0-9]+(?:\.[0-9]+)?$/;
export const NONCE_RE = /^[A-Za-z0-9._-]{8,64}$/;
// ISO-8601 with mandatory explicit timezone (Z or +hh:mm / -hh:mm).
const TIMESTAMP_RE =
  /^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,9})?(?:Z|[+-][0-9]{2}:[0-9]{2})$/;

const MAX_VALUES_PROPERTIES = 40;

function isPlainString(value, minLen, maxLen) {
  return (
    typeof value === "string" && value.length >= minLen && value.length <= maxLen
  );
}

/**
 * Parse an ISO-8601 timestamp with explicit timezone.
 * Returns the epoch milliseconds, or null when invalid (fail-closed).
 */
export function parseUtcTimestampMs(value) {
  if (!isPlainString(value, 1, 64)) return null;
  if (!TIMESTAMP_RE.test(value)) return null;
  const ms = Date.parse(value);
  return Number.isFinite(ms) ? ms : null;
}

/**
 * Validate one decoded JSON payload against the v1 contract + ingress policy.
 *
 * @returns {{ok: true, alert: object, sentAtMs: number, nonce: string, eventId: string}
 *          |{ok: false, reason: string}}
 * The reason code never contains payload content (safe to log).
 */
export function validateAlertPayload(payload) {
  if (typeof payload !== "object" || payload === null || Array.isArray(payload)) {
    return { ok: false, reason: "not_an_object" };
  }
  for (const key of Object.keys(payload)) {
    if (!ALLOWED_FIELDS.has(key)) return { ok: false, reason: "unknown_field" };
  }
  for (const key of REQUIRED_FIELDS) {
    if (!(key in payload)) return { ok: false, reason: "missing_field" };
  }

  if (payload.schema !== SCHEMA_ID) return { ok: false, reason: "schema_mismatch" };
  if (!isPlainString(payload.alert_id, 1, 120)) {
    return { ok: false, reason: "invalid_alert_id" };
  }
  if (
    typeof payload.script_version !== "string" ||
    !SCRIPT_VERSION_RE.test(payload.script_version)
  ) {
    return { ok: false, reason: "invalid_script_version" };
  }

  const sentAtMs = parseUtcTimestampMs(payload.sent_at);
  if (sentAtMs === null) return { ok: false, reason: "invalid_sent_at" };
  const barTimeMs = parseUtcTimestampMs(payload.bar_time);
  if (barTimeMs === null) return { ok: false, reason: "invalid_bar_time" };

  if (!isPlainString(payload.exchange, 1, 32)) {
    return { ok: false, reason: "invalid_exchange" };
  }
  if (!isPlainString(payload.ticker, 1, 48)) {
    return { ok: false, reason: "invalid_ticker" };
  }
  if (!isPlainString(payload.interval, 1, 16)) {
    return { ok: false, reason: "invalid_interval" };
  }
  if (typeof payload.signal !== "string" || !SIGNALS.includes(payload.signal)) {
    return { ok: false, reason: "invalid_signal" };
  }

  // price: optional, string matching the decimal pattern, or null.
  if ("price" in payload && payload.price !== null) {
    if (typeof payload.price !== "string" || !PRICE_RE.test(payload.price)) {
      return { ok: false, reason: "invalid_price" };
    }
  }

  // values: optional string->scalar map, <= 40 properties, no nesting.
  let values;
  if ("values" in payload) {
    values = payload.values;
    if (typeof values !== "object" || values === null || Array.isArray(values)) {
      return { ok: false, reason: "invalid_values" };
    }
    const entries = Object.entries(values);
    if (entries.length > MAX_VALUES_PROPERTIES) {
      return { ok: false, reason: "invalid_values" };
    }
    for (const [, v] of entries) {
      const t = typeof v;
      if (v === null || t === "string" || t === "boolean") continue;
      if (t === "number") {
        if (!Number.isFinite(v)) return { ok: false, reason: "invalid_values" };
        continue;
      }
      return { ok: false, reason: "invalid_values" };
    }
  }

  // Ingress policy: nonce required inside values (see module docstring).
  if (values === undefined || !("nonce" in values)) {
    return { ok: false, reason: "missing_nonce" };
  }
  const nonce = values.nonce;
  if (typeof nonce !== "string" || !NONCE_RE.test(nonce)) {
    return { ok: false, reason: "invalid_nonce" };
  }

  return {
    ok: true,
    alert: payload,
    sentAtMs,
    nonce,
    eventId: `${payload.alert_id}:${nonce}`,
  };
}
