/**
 * Test fakes and builders for the ingress Worker (SYNTHETIC data only).
 *
 * No network, no real Cloudflare binding, no real market data: every value is
 * fabricated for tests and never crosses a production boundary.
 */

export const TEST_CAPABILITY = "cap-synthetic-0123456789abcdef";
export const ALLOWED_IP = "192.0.2.10"; // TEST-NET-1, synthetic
export const OTHER_ALLOWED_IP = "192.0.2.11";
export const FORBIDDEN_IP = "203.0.113.99"; // TEST-NET-3, synthetic
export const NOW_MS = Date.parse("2026-08-29T12:00:00Z");

/** Fake Cloudflare Queue producer binding. */
export class FakeQueue {
  constructor() {
    this.sent = [];
    this.failWith = null;
  }

  async send(message, options) {
    if (this.failWith) throw this.failWith;
    this.sent.push({ message, options });
  }
}

/** Fake Cloudflare KV namespace binding (strongly consistent, unlike real KV). */
export class FakeKV {
  constructor() {
    this.data = new Map();
    this.puts = [];
    this.failGetWith = null;
    this.failPutWith = null;
  }

  async get(key) {
    if (this.failGetWith) throw this.failGetWith;
    return this.data.has(key) ? this.data.get(key) : null;
  }

  async put(key, value, options) {
    if (this.failPutWith) throw this.failPutWith;
    this.data.set(key, value);
    this.puts.push({ key, value, options });
  }
}

/** Build a complete, contract-valid synthetic alert payload. */
export function makeAlert(overrides = {}) {
  const base = {
    schema: "vertex.tradingview.alert.v1",
    alert_id: "syn-market-regime-v1",
    script_version: "2026-08-29.1",
    sent_at: "2026-08-29T11:59:30Z",
    bar_time: "2026-08-29T11:55:00Z",
    exchange: "SYNTH",
    ticker: "FAKE",
    interval: "5",
    signal: "REGIME_CHANGE",
    price: "123.45",
    values: { nonce: "1787999700000", volume: "1000" },
  };
  const merged = { ...base, ...overrides };
  if (overrides.values !== undefined) merged.values = overrides.values;
  return merged;
}

/** Build the env bindings object consumed by the Worker (all injected). */
export function makeEnv(overrides = {}) {
  return {
    ROUTE_CAPABILITY: TEST_CAPABILITY,
    TV_ALLOWED_IPS: `${ALLOWED_IP}, ${OTHER_ALLOWED_IP}`,
    SENT_AT_WINDOW_SECONDS: "300",
    DEDUP_TTL_SECONDS: "86400",
    RATE_LIMIT_MAX: "60",
    RATE_LIMIT_WINDOW_SECONDS: "60",
    ALERT_QUEUE: new FakeQueue(),
    INGRESS_KV: new FakeKV(),
    ...overrides,
  };
}

/** Build an HTTP Request the way Cloudflare would hand it to the Worker. */
export function makeRequest({
  method = "POST",
  capability = TEST_CAPABILITY,
  path,
  ip = ALLOWED_IP,
  body,
  contentType = "application/json",
  extraHeaders = {},
} = {}) {
  const headers = { ...extraHeaders };
  if (contentType !== null) headers["content-type"] = contentType;
  if (ip !== null) headers["CF-Connecting-IP"] = ip;
  const url = `https://ingress.invalid${path ?? `/hook/${capability}`}`;
  const init = { method, headers };
  if (body !== undefined && method !== "GET" && method !== "HEAD") {
    init.body = typeof body === "string" ? body : JSON.stringify(body);
  }
  return new Request(url, init);
}
