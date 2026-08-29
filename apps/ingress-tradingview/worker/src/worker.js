/**
 * Vertex — TradingView ingress Worker (Cloudflare, ES module).
 *
 * STATUS: READY TO DEPLOY, NOT DEPLOYED. Human decision B-03 is pending; this
 * code is exercised locally with fakes only (node --test).
 *
 * Contract (ADR-005, docs/04-integrations/TRADINGVIEW.md):
 *  - POST only, JSON only, body <= 16 KiB;
 *  - secret route capability compared in CONSTANT TIME (never logged);
 *  - client IP taken from the CF-Connecting-IP header and checked against an
 *    allowlist provided by env binding (never hard-coded, fail-closed);
 *  - strict validation of vertex.tradingview.alert.v1 (manual, no deps);
 *  - `sent_at` must be within +/- SENT_AT_WINDOW_SECONDS of now;
 *  - deduplication key `alert_id + ":" + values.nonce` checked through the KV
 *    binding BEFORE enqueue; marker written only AFTER a successful enqueue;
 *  - simple per-IP rate limit through the same KV binding (best effort:
 *    Cloudflare KV is eventually consistent — documented in the README);
 *  - 202 is returned ONLY after queue.send() resolved; a queue failure is a
 *    5xx, never a 202 (fail-closed, no silent loss);
 *  - NO financial computation of any kind; the alert price is context only;
 *  - logs carry redacted reason codes only — never the secret, never the
 *    body, never a full payload.
 *
 * All bindings (queue, KV, vars, secret) arrive through `env`, which makes the
 * handler fully injectable for tests.
 */

import {
  MAX_BODY_BYTES,
  QUEUE_ENVELOPE_SCHEMA_ID,
  validateAlertPayload,
} from "./contract.js";
import { ipAllowed, parseAllowlist, timingSafeEqual } from "./security.js";

const DEFAULTS = Object.freeze({
  SENT_AT_WINDOW_SECONDS: 300,
  DEDUP_TTL_SECONDS: 86_400,
  RATE_LIMIT_MAX: 60,
  RATE_LIMIT_WINDOW_SECONDS: 60,
});

/** Cloudflare KV refuses TTLs below 60 seconds. */
const KV_MIN_TTL_SECONDS = 60;

function jsonResponse(status, body) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

/**
 * Structured, redacted log line. Only allowlisted fields ever reach the log:
 * outcome, reason, status and (post-validation only) alert_id. No secret, no
 * body, no IP, no capability.
 */
function logEvent(fields) {
  const allowed = {};
  for (const key of ["evt", "outcome", "reason", "status", "alert_id"]) {
    if (fields[key] !== undefined) allowed[key] = fields[key];
  }
  console.log(JSON.stringify(allowed));
}

function positiveIntFromEnv(raw, fallback) {
  if (raw === undefined || raw === null || raw === "") return fallback;
  const n = Number.parseInt(String(raw), 10);
  if (!Number.isFinite(n) || n <= 0) return null; // misconfigured -> fail closed
  return n;
}

/**
 * Read and validate the runtime configuration from env bindings.
 * Returns {ok:false, reason} when anything mandatory is missing or invalid —
 * the caller answers 503 without revealing details (fail-closed).
 */
function readConfig(env) {
  if (!env || typeof env !== "object") return { ok: false, reason: "missing_env" };
  if (typeof env.ROUTE_CAPABILITY !== "string" || env.ROUTE_CAPABILITY.length < 16) {
    return { ok: false, reason: "missing_route_capability" };
  }
  const allowlist = parseAllowlist(env.TV_ALLOWED_IPS);
  if (allowlist === null) return { ok: false, reason: "missing_ip_allowlist" };
  const queue = env.ALERT_QUEUE;
  if (!queue || typeof queue.send !== "function") {
    return { ok: false, reason: "missing_queue_binding" };
  }
  const kv = env.INGRESS_KV;
  if (!kv || typeof kv.get !== "function" || typeof kv.put !== "function") {
    return { ok: false, reason: "missing_kv_binding" };
  }
  const windowSeconds = positiveIntFromEnv(
    env.SENT_AT_WINDOW_SECONDS,
    DEFAULTS.SENT_AT_WINDOW_SECONDS,
  );
  const dedupTtlSeconds = positiveIntFromEnv(
    env.DEDUP_TTL_SECONDS,
    DEFAULTS.DEDUP_TTL_SECONDS,
  );
  const rateLimitMax = positiveIntFromEnv(env.RATE_LIMIT_MAX, DEFAULTS.RATE_LIMIT_MAX);
  const rateWindowSeconds = positiveIntFromEnv(
    env.RATE_LIMIT_WINDOW_SECONDS,
    DEFAULTS.RATE_LIMIT_WINDOW_SECONDS,
  );
  if (
    windowSeconds === null ||
    dedupTtlSeconds === null ||
    rateLimitMax === null ||
    rateWindowSeconds === null
  ) {
    return { ok: false, reason: "invalid_numeric_config" };
  }
  return {
    ok: true,
    routeCapability: env.ROUTE_CAPABILITY,
    allowlist,
    queue,
    kv,
    windowSeconds,
    dedupTtlSeconds,
    rateLimitMax,
    rateWindowSeconds,
  };
}

/**
 * Main handler. `now` (epoch ms) is injectable for deterministic tests.
 */
export async function handleRequest(request, env, { now = Date.now() } = {}) {
  // 1. Method: POST only.
  if (request.method !== "POST") {
    logEvent({ evt: "tv_ingress", outcome: "refused", reason: "method_not_allowed", status: 405 });
    return jsonResponse(405, { status: "method_not_allowed" });
  }

  // 2. Configuration: fail closed on any missing binding or invalid value.
  const config = readConfig(env);
  if (!config.ok) {
    logEvent({ evt: "tv_ingress", outcome: "refused", reason: config.reason, status: 503 });
    return jsonResponse(503, { status: "unavailable" });
  }

  // 3. Secret route capability, compared in constant time.
  //    Expected path shape: /hook/<capability>. A mismatch answers 404 and
  //    reveals neither the existence of the route nor the expected value.
  const segments = new URL(request.url).pathname.split("/").filter((s) => s.length > 0);
  const candidate = segments.length === 2 && segments[0] === "hook" ? segments[1] : "";
  const capabilityOk = await timingSafeEqual(candidate, config.routeCapability);
  if (!capabilityOk) {
    logEvent({ evt: "tv_ingress", outcome: "refused", reason: "unknown_route", status: 404 });
    return jsonResponse(404, { status: "not_found" });
  }

  // 4. IP allowlist from the Cloudflare header (fail-closed when absent).
  const clientIp = request.headers.get("CF-Connecting-IP");
  if (!clientIp || !ipAllowed(clientIp, config.allowlist)) {
    logEvent({ evt: "tv_ingress", outcome: "refused", reason: "ip_not_allowed", status: 403 });
    return jsonResponse(403, { status: "forbidden" });
  }

  // 5. Simple per-IP rate limit (KV, best effort). Refused before any body read.
  const windowIndex = Math.floor(now / 1000 / config.rateWindowSeconds);
  const rateKey = `rate:${clientIp}:${windowIndex}`;
  let rateCount = 0;
  try {
    const rawCount = await config.kv.get(rateKey);
    rateCount = rawCount === null ? 0 : Number.parseInt(rawCount, 10) || 0;
  } catch {
    // KV read failure: fail closed (temporarily unavailable, no enqueue).
    logEvent({ evt: "tv_ingress", outcome: "refused", reason: "rate_kv_unavailable", status: 503 });
    return jsonResponse(503, { status: "unavailable" });
  }
  if (rateCount >= config.rateLimitMax) {
    logEvent({ evt: "tv_ingress", outcome: "refused", reason: "rate_limited", status: 429 });
    return jsonResponse(429, { status: "rate_limited" });
  }
  try {
    await config.kv.put(rateKey, String(rateCount + 1), {
      expirationTtl: Math.max(KV_MIN_TTL_SECONDS, config.rateWindowSeconds * 2),
    });
  } catch {
    // Counting failure only weakens the limiter for this request; the request
    // itself still goes through the full validation pipeline.
    logEvent({ evt: "tv_ingress", outcome: "warn", reason: "rate_kv_put_failed" });
  }

  // 6. Content type: JSON only.
  const contentType = (request.headers.get("content-type") || "").toLowerCase();
  if (!contentType.startsWith("application/json")) {
    logEvent({ evt: "tv_ingress", outcome: "refused", reason: "unsupported_media_type", status: 415 });
    return jsonResponse(415, { status: "unsupported_media_type" });
  }

  // 7. Size: declared and actual body <= 16 KiB.
  const declaredLength = Number.parseInt(request.headers.get("content-length") || "", 10);
  if (Number.isFinite(declaredLength) && declaredLength > MAX_BODY_BYTES) {
    logEvent({ evt: "tv_ingress", outcome: "refused", reason: "payload_too_large", status: 413 });
    return jsonResponse(413, { status: "payload_too_large" });
  }
  let bodyBytes;
  try {
    bodyBytes = await request.arrayBuffer();
  } catch {
    logEvent({ evt: "tv_ingress", outcome: "refused", reason: "unreadable_body", status: 400 });
    return jsonResponse(400, { status: "invalid_body" });
  }
  if (bodyBytes.byteLength > MAX_BODY_BYTES) {
    logEvent({ evt: "tv_ingress", outcome: "refused", reason: "payload_too_large", status: 413 });
    return jsonResponse(413, { status: "payload_too_large" });
  }
  if (bodyBytes.byteLength === 0) {
    logEvent({ evt: "tv_ingress", outcome: "refused", reason: "empty_body", status: 400 });
    return jsonResponse(400, { status: "invalid_body" });
  }

  // 8. JSON decoding (strict UTF-8).
  let payload;
  try {
    const text = new TextDecoder("utf-8", { fatal: true }).decode(bodyBytes);
    payload = JSON.parse(text);
  } catch {
    logEvent({ evt: "tv_ingress", outcome: "refused", reason: "invalid_json", status: 400 });
    return jsonResponse(400, { status: "invalid_json" });
  }

  // 9. Strict contract validation (manual mirror of the JSON Schema).
  const validation = validateAlertPayload(payload);
  if (!validation.ok) {
    logEvent({ evt: "tv_ingress", outcome: "rejected", reason: validation.reason, status: 422 });
    return jsonResponse(422, { status: "rejected" });
  }

  // 10. Temporal window on sent_at (anti-replay / clock sanity).
  if (Math.abs(now - validation.sentAtMs) > config.windowSeconds * 1000) {
    logEvent({
      evt: "tv_ingress",
      outcome: "rejected",
      reason: "sent_at_out_of_window",
      status: 422,
      alert_id: validation.alert.alert_id,
    });
    return jsonResponse(422, { status: "rejected" });
  }

  // 11. Deduplication on alert_id + nonce, checked before enqueue.
  const dedupKey = `dedup:${validation.eventId}`;
  let existing;
  try {
    existing = await config.kv.get(dedupKey);
  } catch {
    logEvent({ evt: "tv_ingress", outcome: "refused", reason: "dedup_kv_unavailable", status: 503 });
    return jsonResponse(503, { status: "unavailable" });
  }
  if (existing !== null && existing !== undefined) {
    logEvent({
      evt: "tv_ingress",
      outcome: "duplicate",
      reason: "duplicate_event",
      status: 409,
      alert_id: validation.alert.alert_id,
    });
    return jsonResponse(409, { status: "duplicate" });
  }

  // 12. Durable enqueue. 202 ONLY after queue.send() resolved.
  const envelope = {
    schema: QUEUE_ENVELOPE_SCHEMA_ID,
    event_id: validation.eventId,
    received_at: new Date(now).toISOString(),
    alert: validation.alert,
  };
  try {
    await config.queue.send(envelope, { contentType: "json" });
  } catch {
    // Fail-closed: without durable write there is no acknowledgement.
    // The dedup marker is NOT written, so a retry can succeed later.
    logEvent({
      evt: "tv_ingress",
      outcome: "error",
      reason: "enqueue_failed",
      status: 503,
      alert_id: validation.alert.alert_id,
    });
    return jsonResponse(503, { status: "enqueue_failed" });
  }

  // 13. Dedup marker AFTER successful enqueue. A KV failure here must not turn
  // a durably enqueued alert into an error: the local consumer is idempotent
  // (at-least-once delivery), so we only log and still acknowledge.
  try {
    await config.kv.put(dedupKey, "1", { expirationTtl: config.dedupTtlSeconds });
  } catch {
    logEvent({ evt: "tv_ingress", outcome: "warn", reason: "dedup_kv_put_failed" });
  }

  logEvent({
    evt: "tv_ingress",
    outcome: "accepted",
    status: 202,
    alert_id: validation.alert.alert_id,
  });
  return jsonResponse(202, { status: "accepted" });
}

export default {
  /** Cloudflare module Worker entry point. */
  async fetch(request, env, _ctx) {
    return handleRequest(request, env);
  },
};
