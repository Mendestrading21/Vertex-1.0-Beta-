import { test } from "node:test";
import assert from "node:assert/strict";

import { ipAllowed, parseAllowlist, timingSafeEqual } from "../src/security.js";

// ---------------------------------------------------------------------------
// Functional tests of the constant-time comparison. Timing itself cannot be
// asserted reliably in a unit test; what is proven here is the functional
// contract of the primitive (correct equality semantics on every input shape)
// plus, by construction (see security.js), the fixed-length digest comparison
// without early exit.
// ---------------------------------------------------------------------------

test("timingSafeEqual: equal strings compare equal", async () => {
  assert.equal(await timingSafeEqual("cap-0123456789abcdef", "cap-0123456789abcdef"), true);
  assert.equal(await timingSafeEqual("", ""), true);
});

test("timingSafeEqual: difference at ANY position yields false", async () => {
  const secret = "cap-0123456789abcdef";
  for (let i = 0; i < secret.length; i += 1) {
    const forged =
      secret.slice(0, i) + (secret[i] === "x" ? "y" : "x") + secret.slice(i + 1);
    assert.equal(await timingSafeEqual(forged, secret), false, `pos ${i}`);
  }
});

test("timingSafeEqual: different lengths, prefixes and suffixes are unequal", async () => {
  assert.equal(await timingSafeEqual("cap", "cap-0123456789abcdef"), false);
  assert.equal(await timingSafeEqual("cap-0123456789abcdef", "cap"), false);
  assert.equal(await timingSafeEqual("cap-0123456789abcdefX", "cap-0123456789abcdef"), false);
  assert.equal(await timingSafeEqual("", "cap"), false);
});

test("timingSafeEqual: non-string input is refused (fail-closed)", async () => {
  assert.equal(await timingSafeEqual(null, "cap"), false);
  assert.equal(await timingSafeEqual("cap", undefined), false);
  assert.equal(await timingSafeEqual(123, 123), false);
});

test("timingSafeEqual: unicode strings are compared by exact bytes", async () => {
  assert.equal(await timingSafeEqual("clé-é", "clé-é"), true);
  assert.equal(await timingSafeEqual("clé-é", "cle-e"), false);
});

// ---------------------------------------------------------------------------
// Allowlist parsing/matching (env-provided, fail-closed, never hard-coded).
// ---------------------------------------------------------------------------

test("parseAllowlist: valid comma-separated IPv4 list is parsed", () => {
  assert.deepEqual(parseAllowlist("192.0.2.10, 192.0.2.11 ,192.0.2.12"), [
    "192.0.2.10",
    "192.0.2.11",
    "192.0.2.12",
  ]);
});

test("parseAllowlist: absent, empty or invalid input fails closed", () => {
  assert.equal(parseAllowlist(undefined), null);
  assert.equal(parseAllowlist(null), null);
  assert.equal(parseAllowlist(""), null);
  assert.equal(parseAllowlist("   ,  "), null);
  assert.equal(parseAllowlist("192.0.2.10, not-an-ip"), null);
  assert.equal(parseAllowlist("999.0.2.10"), null);
  assert.equal(parseAllowlist(42), null);
});

test("ipAllowed: exact membership only, fail-closed on missing input", () => {
  const list = ["192.0.2.10"];
  assert.equal(ipAllowed("192.0.2.10", list), true);
  assert.equal(ipAllowed(" 192.0.2.10 ", list), true);
  assert.equal(ipAllowed("192.0.2.11", list), false);
  assert.equal(ipAllowed(null, list), false);
  assert.equal(ipAllowed("192.0.2.10", null), false);
});
