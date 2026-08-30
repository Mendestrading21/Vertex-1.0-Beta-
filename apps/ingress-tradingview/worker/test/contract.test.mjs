import { test } from "node:test";
import assert from "node:assert/strict";

import {
  MAX_BODY_BYTES,
  parseUtcTimestampMs,
  SIGNALS,
  validateAlertPayload,
} from "../src/contract.js";
import { makeAlert } from "./helpers.mjs";

test("valid synthetic alert passes and yields the alert_id+nonce event id", () => {
  const result = validateAlertPayload(makeAlert());
  assert.equal(result.ok, true);
  assert.equal(result.eventId, "syn-market-regime-v1:1787999700000");
  assert.equal(result.nonce, "1787999700000");
  assert.equal(result.sentAtMs, Date.parse("2026-08-29T11:59:30Z"));
});

test("every declared signal enum value is accepted", () => {
  for (const signal of SIGNALS) {
    const result = validateAlertPayload(makeAlert({ signal }));
    assert.equal(result.ok, true, `signal ${signal} should be valid`);
  }
});

test("null and absent price are accepted (optional field)", () => {
  assert.equal(validateAlertPayload(makeAlert({ price: null })).ok, true);
  const noPrice = makeAlert();
  delete noPrice.price;
  assert.equal(validateAlertPayload(noPrice).ok, true);
});

test("non-object payloads are rejected", () => {
  for (const bad of [null, [], "str", 42, true]) {
    const result = validateAlertPayload(bad);
    assert.equal(result.ok, false);
    assert.equal(result.reason, "not_an_object");
  }
});

test("unknown top-level field is rejected (additionalProperties: false)", () => {
  const result = validateAlertPayload(makeAlert({ extra_field: "x" }));
  assert.deepEqual(result, { ok: false, reason: "unknown_field" });
});

test("each required field missing is rejected", () => {
  const required = [
    "schema",
    "alert_id",
    "script_version",
    "sent_at",
    "bar_time",
    "exchange",
    "ticker",
    "interval",
    "signal",
  ];
  for (const field of required) {
    const payload = makeAlert();
    delete payload[field];
    const result = validateAlertPayload(payload);
    assert.equal(result.ok, false, `missing ${field} must be rejected`);
    assert.equal(result.reason, "missing_field");
  }
});

test("wrong schema constant is rejected", () => {
  const result = validateAlertPayload(makeAlert({ schema: "vertex.tradingview.alert.v2" }));
  assert.deepEqual(result, { ok: false, reason: "schema_mismatch" });
});

test("alert_id bounds are enforced", () => {
  assert.equal(validateAlertPayload(makeAlert({ alert_id: "" })).reason, "invalid_alert_id");
  assert.equal(
    validateAlertPayload(makeAlert({ alert_id: "a".repeat(121) })).reason,
    "invalid_alert_id",
  );
  assert.equal(validateAlertPayload(makeAlert({ alert_id: "a".repeat(120) })).ok, true);
});

test("script_version pattern is enforced", () => {
  for (const bad of ["v1", "2026-08-29", "2026-08-29.", "26-08-29.1", "2026-08-29.1x"]) {
    const result = validateAlertPayload(makeAlert({ script_version: bad }));
    assert.equal(result.reason, "invalid_script_version", `should reject ${bad}`);
  }
});

test("naive or malformed timestamps are rejected (timezone mandatory)", () => {
  for (const bad of ["2026-08-29T11:59:30", "2026-08-29 11:59:30Z", "not-a-date", ""]) {
    assert.equal(validateAlertPayload(makeAlert({ sent_at: bad })).reason, "invalid_sent_at");
    assert.equal(validateAlertPayload(makeAlert({ bar_time: bad })).reason, "invalid_bar_time");
  }
  // Explicit offsets are accepted and interpreted as absolute instants.
  const withOffset = validateAlertPayload(makeAlert({ sent_at: "2026-08-29T13:59:30+02:00" }));
  assert.equal(withOffset.ok, true);
  assert.equal(withOffset.sentAtMs, Date.parse("2026-08-29T11:59:30Z"));
});

test("parseUtcTimestampMs is fail-closed", () => {
  assert.equal(parseUtcTimestampMs("2026-08-29T11:59:30"), null);
  assert.equal(parseUtcTimestampMs(1234), null);
  assert.equal(parseUtcTimestampMs("x".repeat(65)), null);
  assert.equal(parseUtcTimestampMs("2026-13-45T99:99:99Z"), null);
});

test("string length bounds on exchange, ticker and interval", () => {
  assert.equal(validateAlertPayload(makeAlert({ exchange: "" })).reason, "invalid_exchange");
  assert.equal(
    validateAlertPayload(makeAlert({ exchange: "E".repeat(33) })).reason,
    "invalid_exchange",
  );
  assert.equal(
    validateAlertPayload(makeAlert({ ticker: "T".repeat(49) })).reason,
    "invalid_ticker",
  );
  assert.equal(
    validateAlertPayload(makeAlert({ interval: "1".repeat(17) })).reason,
    "invalid_interval",
  );
});

test("unknown signal enum value is rejected", () => {
  const result = validateAlertPayload(makeAlert({ signal: "BUY_NOW" }));
  assert.deepEqual(result, { ok: false, reason: "invalid_signal" });
});

test("price pattern is enforced when present", () => {
  for (const bad of ["", "12.", ".5", "1,5", "1e3", "NaN", 123.45]) {
    const result = validateAlertPayload(makeAlert({ price: bad }));
    assert.equal(result.reason, "invalid_price", `should reject ${JSON.stringify(bad)}`);
  }
  assert.equal(validateAlertPayload(makeAlert({ price: "-0.5" })).ok, true);
});

test("values map: nesting, non-finite numbers and >40 properties rejected", () => {
  assert.equal(
    validateAlertPayload(makeAlert({ values: { nonce: "1787999700000", nested: {} } })).reason,
    "invalid_values",
  );
  assert.equal(
    validateAlertPayload(makeAlert({ values: { nonce: "1787999700000", arr: [1] } })).reason,
    "invalid_values",
  );
  assert.equal(
    validateAlertPayload(makeAlert({ values: { nonce: "1787999700000", bad: Infinity } })).reason,
    "invalid_values",
  );
  const tooMany = { nonce: "1787999700000" };
  for (let i = 0; i < 40; i += 1) tooMany[`k${i}`] = i;
  assert.equal(validateAlertPayload(makeAlert({ values: tooMany })).reason, "invalid_values");
  // Exactly 40 properties (nonce included) stays valid.
  const exactly40 = { nonce: "1787999700000" };
  for (let i = 0; i < 39; i += 1) exactly40[`k${i}`] = i;
  assert.equal(validateAlertPayload(makeAlert({ values: exactly40 })).ok, true);
});

test("missing or invalid nonce is rejected (ingress policy)", () => {
  const noValues = makeAlert();
  delete noValues.values;
  assert.equal(validateAlertPayload(noValues).reason, "missing_nonce");
  assert.equal(
    validateAlertPayload(makeAlert({ values: { volume: "1" } })).reason,
    "missing_nonce",
  );
  assert.equal(
    validateAlertPayload(makeAlert({ values: { nonce: "short" } })).reason,
    "invalid_nonce",
  );
  assert.equal(
    validateAlertPayload(makeAlert({ values: { nonce: 1787999700000 } })).reason,
    "invalid_nonce",
  );
});

test("MAX_BODY_BYTES is exactly 16 KiB", () => {
  assert.equal(MAX_BODY_BYTES, 16384);
});

test("bar_time far after sent_at is rejected (a bar cannot close after its alert)", () => {
  const result = validateAlertPayload(
    makeAlert({ sent_at: "2026-08-29T11:59:30Z", bar_time: "2126-08-29T11:55:00Z" }),
  );
  assert.equal(result.ok, false);
  assert.equal(result.reason, "bar_time_after_sent_at");
});

test("bar_time before sent_at stays valid (a weekly bar opened long before)", () => {
  const result = validateAlertPayload(
    makeAlert({ sent_at: "2026-08-29T11:59:30Z", bar_time: "2026-08-24T00:00:00Z" }),
  );
  assert.equal(result.ok, true);
});

test("a small provider clock skew on bar_time is tolerated", () => {
  const result = validateAlertPayload(
    makeAlert({ sent_at: "2026-08-29T11:59:30Z", bar_time: "2026-08-29T11:59:31Z" }),
  );
  assert.equal(result.ok, true);
});
