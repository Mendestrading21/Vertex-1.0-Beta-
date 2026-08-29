import { test } from "node:test";
import assert from "node:assert/strict";

import workerDefault, { handleRequest } from "../src/worker.js";
import {
  ALLOWED_IP,
  FakeKV,
  FakeQueue,
  FORBIDDEN_IP,
  makeAlert,
  makeEnv,
  makeRequest,
  NOW_MS,
  TEST_CAPABILITY,
} from "./helpers.mjs";

const OPTS = { now: NOW_MS };

async function call(env, requestOptions = {}, opts = OPTS) {
  const request = makeRequest(requestOptions);
  const response = await handleRequest(request, env, opts);
  const body = await response.json();
  return { response, body };
}

// ---------------------------------------------------------------------------
// Happy path
// ---------------------------------------------------------------------------

test("valid alert -> 202 ONLY after successful enqueue, with dedup marker", async () => {
  const env = makeEnv();
  const { response, body } = await call(env, { body: makeAlert() });
  assert.equal(response.status, 202);
  assert.equal(body.status, "accepted");

  // Message durably enqueued exactly once, wrapped in the queue envelope.
  assert.equal(env.ALERT_QUEUE.sent.length, 1);
  const { message, options } = env.ALERT_QUEUE.sent[0];
  assert.equal(options.contentType, "json");
  assert.equal(message.schema, "vertex.tradingview.queue-envelope.v1");
  assert.equal(message.event_id, "syn-market-regime-v1:1787999700000");
  assert.equal(message.received_at, new Date(NOW_MS).toISOString());
  assert.deepEqual(message.alert, makeAlert());

  // Dedup marker written AFTER enqueue, keyed on alert_id + nonce.
  const marker = await env.INGRESS_KV.get("dedup:syn-market-regime-v1:1787999700000");
  assert.equal(marker, "1");
});

test("default export fetch delegates to the handler (405 on GET)", async () => {
  const response = await workerDefault.fetch(makeRequest({ method: "GET" }), makeEnv(), {});
  assert.equal(response.status, 405);
});

// ---------------------------------------------------------------------------
// Method / media / size guards
// ---------------------------------------------------------------------------

test("non-POST methods -> 405, nothing enqueued", async () => {
  for (const method of ["GET", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]) {
    const env = makeEnv();
    const request = makeRequest({ method, body: method === "GET" || method === "HEAD" ? undefined : makeAlert() });
    const response = await handleRequest(request, env, OPTS);
    assert.equal(response.status, 405, method);
    assert.equal(env.ALERT_QUEUE.sent.length, 0);
  }
});

test("wrong content-type -> 415, nothing enqueued", async () => {
  const env = makeEnv();
  const { response } = await call(env, { body: makeAlert(), contentType: "text/plain" });
  assert.equal(response.status, 415);
  assert.equal(env.ALERT_QUEUE.sent.length, 0);
});

test("oversize body (>16 KiB) -> 413, nothing enqueued", async () => {
  const env = makeEnv();
  const oversize = makeAlert({ values: { nonce: "1787999700000", pad: "x".repeat(17000) } });
  const { response } = await call(env, { body: oversize });
  assert.equal(response.status, 413);
  assert.equal(env.ALERT_QUEUE.sent.length, 0);
});

test("empty body -> 400, malformed JSON -> 400", async () => {
  let env = makeEnv();
  let result = await call(env, { body: "" });
  assert.equal(result.response.status, 400);
  env = makeEnv();
  result = await call(env, { body: "{not json" });
  assert.equal(result.response.status, 400);
  assert.equal(env.ALERT_QUEUE.sent.length, 0);
});

// ---------------------------------------------------------------------------
// Secret route capability (constant-time comparison, functional behaviour)
// ---------------------------------------------------------------------------

test("wrong capability -> 404 without enqueue and without content echo", async () => {
  const env = makeEnv();
  const { response, body } = await call(env, {
    capability: "cap-synthetic-WRONG-0123456789",
    body: makeAlert(),
  });
  assert.equal(response.status, 404);
  assert.deepEqual(body, { status: "not_found" });
  assert.equal(env.ALERT_QUEUE.sent.length, 0);
});

test("capability differing only by its last character -> 404", async () => {
  const env = makeEnv();
  const nearMiss = TEST_CAPABILITY.slice(0, -1) + "X";
  const { response } = await call(env, { capability: nearMiss, body: makeAlert() });
  assert.equal(response.status, 404);
  assert.equal(env.ALERT_QUEUE.sent.length, 0);
});

test("unexpected path shape -> 404", async () => {
  const env = makeEnv();
  for (const path of ["/", "/hook", `/other/${TEST_CAPABILITY}`, `/hook/${TEST_CAPABILITY}/x`]) {
    const { response } = await call(env, { path, body: makeAlert() });
    assert.equal(response.status, 404, path);
  }
  assert.equal(env.ALERT_QUEUE.sent.length, 0);
});

// ---------------------------------------------------------------------------
// IP allowlist (env binding, fail-closed)
// ---------------------------------------------------------------------------

test("IP outside the allowlist -> 403, nothing enqueued", async () => {
  const env = makeEnv();
  const { response } = await call(env, { ip: FORBIDDEN_IP, body: makeAlert() });
  assert.equal(response.status, 403);
  assert.equal(env.ALERT_QUEUE.sent.length, 0);
});

test("missing CF-Connecting-IP header -> 403 (fail-closed)", async () => {
  const env = makeEnv();
  const { response } = await call(env, { ip: null, body: makeAlert() });
  assert.equal(response.status, 403);
  assert.equal(env.ALERT_QUEUE.sent.length, 0);
});

test("absent or invalid allowlist binding -> 503 (fail-closed, config error)", async () => {
  for (const badList of [undefined, "", "not-an-ip"]) {
    const env = makeEnv({ TV_ALLOWED_IPS: badList });
    const { response } = await call(env, { body: makeAlert() });
    assert.equal(response.status, 503);
    assert.equal(env.ALERT_QUEUE.sent.length, 0);
  }
});

test("missing queue, KV or secret binding -> 503 (fail-closed)", async () => {
  for (const overrides of [
    { ALERT_QUEUE: undefined },
    { INGRESS_KV: undefined },
    { ROUTE_CAPABILITY: undefined },
    { ROUTE_CAPABILITY: "tooshort" },
    { SENT_AT_WINDOW_SECONDS: "-5" },
  ]) {
    const env = makeEnv(overrides);
    const { response } = await call(env, { body: makeAlert() });
    assert.equal(response.status, 503);
  }
});

// ---------------------------------------------------------------------------
// Contract validation & temporal window
// ---------------------------------------------------------------------------

test("schema-invalid alert -> 422, nothing enqueued", async () => {
  const env = makeEnv();
  const { response, body } = await call(env, { body: makeAlert({ signal: "BUY_NOW" }) });
  assert.equal(response.status, 422);
  assert.deepEqual(body, { status: "rejected" });
  assert.equal(env.ALERT_QUEUE.sent.length, 0);
});

test("alert without nonce -> 422, nothing enqueued", async () => {
  const env = makeEnv();
  const { response } = await call(env, { body: makeAlert({ values: { volume: "1" } }) });
  assert.equal(response.status, 422);
  assert.equal(env.ALERT_QUEUE.sent.length, 0);
});

test("sent_at too old -> 422 ; too far in the future -> 422", async () => {
  const env = makeEnv();
  const old = await call(env, { body: makeAlert({ sent_at: "2026-08-29T11:54:59Z" }) });
  assert.equal(old.response.status, 422); // 301 s in the past, window 300 s
  const future = await call(env, { body: makeAlert({ sent_at: "2026-08-29T12:05:01Z" }) });
  assert.equal(future.response.status, 422);
  assert.equal(env.ALERT_QUEUE.sent.length, 0);

  // Boundary: exactly at the window edge stays accepted.
  const edge = await call(env, { body: makeAlert({ sent_at: "2026-08-29T11:55:00Z" }) });
  assert.equal(edge.response.status, 202);
});

// ---------------------------------------------------------------------------
// Deduplication (alert_id + nonce via KV)
// ---------------------------------------------------------------------------

test("duplicate alert_id+nonce -> 409, second delivery NOT enqueued", async () => {
  const env = makeEnv();
  const first = await call(env, { body: makeAlert() });
  assert.equal(first.response.status, 202);
  const second = await call(env, { body: makeAlert() });
  assert.equal(second.response.status, 409);
  assert.equal(second.body.status, "duplicate");
  assert.equal(env.ALERT_QUEUE.sent.length, 1);
});

test("same alert_id with a different nonce is a distinct event -> 202", async () => {
  const env = makeEnv();
  await call(env, { body: makeAlert() });
  const other = await call(env, {
    body: makeAlert({ values: { nonce: "1788000000000" } }),
  });
  assert.equal(other.response.status, 202);
  assert.equal(env.ALERT_QUEUE.sent.length, 2);
});

test("KV dedup read failure -> 503, nothing enqueued (fail-closed)", async () => {
  const env = makeEnv();
  // Let the rate-limit read succeed, then fail the dedup read.
  let reads = 0;
  const kv = env.INGRESS_KV;
  const originalGet = kv.get.bind(kv);
  kv.get = async (key) => {
    reads += 1;
    if (key.startsWith("dedup:")) throw new Error("synthetic KV outage");
    return originalGet(key);
  };
  const { response } = await call(env, { body: makeAlert() });
  assert.equal(response.status, 503);
  assert.equal(env.ALERT_QUEUE.sent.length, 0);
  assert.ok(reads >= 2);
});

// ---------------------------------------------------------------------------
// Queue failure: never 202, no dedup marker, retry can succeed
// ---------------------------------------------------------------------------

test("queue.send failure -> 503 (never 202) and NO dedup marker written", async () => {
  const env = makeEnv();
  env.ALERT_QUEUE.failWith = new Error("synthetic queue outage");
  const { response, body } = await call(env, { body: makeAlert() });
  assert.equal(response.status, 503);
  assert.equal(body.status, "enqueue_failed");
  assert.equal(env.ALERT_QUEUE.sent.length, 0);
  assert.equal(await env.INGRESS_KV.get("dedup:syn-market-regime-v1:1787999700000"), null);

  // Once the queue heals, the retry of the SAME event succeeds (not a dup).
  env.ALERT_QUEUE.failWith = null;
  const retry = await call(env, { body: makeAlert() });
  assert.equal(retry.response.status, 202);
  assert.equal(env.ALERT_QUEUE.sent.length, 1);
});

test("dedup marker write failure after enqueue still answers 202 (documented)", async () => {
  const env = makeEnv();
  const kv = env.INGRESS_KV;
  const originalPut = kv.put.bind(kv);
  kv.put = async (key, value, options) => {
    if (key.startsWith("dedup:")) throw new Error("synthetic KV outage");
    return originalPut(key, value, options);
  };
  const { response } = await call(env, { body: makeAlert() });
  // The message IS durable in the queue; the local consumer dedupes anyway.
  assert.equal(response.status, 202);
  assert.equal(env.ALERT_QUEUE.sent.length, 1);
});

// ---------------------------------------------------------------------------
// Rate limit (per IP, KV)
// ---------------------------------------------------------------------------

test("rate limit: request beyond RATE_LIMIT_MAX in the window -> 429", async () => {
  const env = makeEnv({ RATE_LIMIT_MAX: "3" });
  for (let i = 0; i < 3; i += 1) {
    const { response } = await call(env, {
      body: makeAlert({ values: { nonce: `17879997000${10 + i}` } }),
    });
    assert.equal(response.status, 202, `request ${i}`);
  }
  const { response } = await call(env, {
    body: makeAlert({ values: { nonce: "1787999700099" } }),
  });
  assert.equal(response.status, 429);
  assert.equal(env.ALERT_QUEUE.sent.length, 3);
});

test("rate limit counters are per IP", async () => {
  const env = makeEnv({ RATE_LIMIT_MAX: "1" });
  const first = await call(env, { body: makeAlert() });
  assert.equal(first.response.status, 202);
  const blocked = await call(env, {
    ip: ALLOWED_IP,
    body: makeAlert({ values: { nonce: "1788000000001" } }),
  });
  assert.equal(blocked.response.status, 429);
  const otherIp = await call(env, {
    ip: "192.0.2.11",
    body: makeAlert({ values: { nonce: "1788000000002" } }),
  });
  assert.equal(otherIp.response.status, 202);
});

test("rate limit window rolls over with time", async () => {
  const env = makeEnv({ RATE_LIMIT_MAX: "1", RATE_LIMIT_WINDOW_SECONDS: "60" });
  const first = await call(env, { body: makeAlert() });
  assert.equal(first.response.status, 202);
  const blocked = await call(env, {
    body: makeAlert({ values: { nonce: "1788000000003" } }),
  });
  assert.equal(blocked.response.status, 429);
  // Next window (now + 60 s): counter starts again. sent_at stays in window.
  const nextWindow = await call(
    env,
    { body: makeAlert({ values: { nonce: "1788000000004" } }) },
    { now: NOW_MS + 60_000 },
  );
  assert.equal(nextWindow.response.status, 202);
});

// ---------------------------------------------------------------------------
// Redacted logging: no secret, no body in log output
// ---------------------------------------------------------------------------

test("logs never contain the capability, the body or the nonce", async (t) => {
  const lines = [];
  const original = console.log;
  console.log = (line) => lines.push(String(line));
  t.after(() => {
    console.log = original;
  });

  const env = makeEnv();
  await call(env, { body: makeAlert() });
  await call(env, { capability: "cap-synthetic-WRONG-0123456789", body: makeAlert() });

  assert.ok(lines.length >= 2);
  for (const line of lines) {
    assert.ok(!line.includes(TEST_CAPABILITY), "capability leaked in logs");
    assert.ok(!line.includes("1787999700000"), "nonce leaked in logs");
    assert.ok(!line.includes("123.45"), "price/body leaked in logs");
    assert.ok(!line.includes(ALLOWED_IP), "client IP leaked in logs");
  }
});
