/**
 * Security primitives for the TradingView ingress Worker.
 *
 * - constant-time comparison of the secret route capability;
 * - IP allowlist parsing/matching from an env binding (never hard-coded).
 *
 * Nothing in this module logs; callers only log redacted reason codes.
 */

const encoder = new TextEncoder();

/**
 * Constant-time equality of two strings.
 *
 * Both inputs are first digested with SHA-256 (crypto.subtle), so:
 *  - both byte sequences compared have the same fixed length (32 bytes),
 *    which removes any length-dependent early exit;
 *  - the byte-by-byte comparison accumulates XOR differences without
 *    branching on content, so the time taken does not depend on WHERE the
 *    strings differ;
 *  - digest equality implies input equality (SHA-256 collision resistance).
 *
 * @param {string} a
 * @param {string} b
 * @returns {Promise<boolean>}
 */
export async function timingSafeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string") return false;
  const [da, db] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(a)),
    crypto.subtle.digest("SHA-256", encoder.encode(b)),
  ]);
  const va = new Uint8Array(da);
  const vb = new Uint8Array(db);
  let diff = 0;
  for (let i = 0; i < va.length; i += 1) {
    diff |= va[i] ^ vb[i];
  }
  return diff === 0;
}

const IPV4_RE = /^(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])(\.(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])){3}$/;

/**
 * Parse a comma-separated IPv4 allowlist coming from an env binding.
 *
 * Fail-closed: returns null when the binding is absent, empty or contains an
 * invalid entry — the caller must then refuse every request (the allowlist is
 * never guessed and never hard-coded).
 *
 * @param {unknown} raw
 * @returns {string[]|null}
 */
export function parseAllowlist(raw) {
  if (typeof raw !== "string") return null;
  const entries = raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
  if (entries.length === 0) return null;
  for (const entry of entries) {
    if (!IPV4_RE.test(entry)) return null;
  }
  return entries;
}

/**
 * Exact-match membership of a client IP in the parsed allowlist.
 * Fail-closed on any missing input.
 */
export function ipAllowed(ip, allowlist) {
  if (typeof ip !== "string" || !Array.isArray(allowlist)) return false;
  return allowlist.includes(ip.trim());
}
