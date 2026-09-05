// tradeGate.js -- the gate the rest of Sentinel-Witness imports and never had.
//
// Written 2026-09-05 into covenant's sentinel-witness branch. Two duties:
//   1. TIERS and enableAutomated(): the tier ladder and the "no unlimited
//      option" rule that automatedLimits.js and AutomatedSetupModal.jsx say
//      they mirror. Limits must be finite and positive; there is no way to
//      express "unlimited".
//   2. gateTrade(): before ANY order executes, the decision is sealed through
//      covenant's ethics gate by way of the local seal service
//      (sentinel_witness/seal_service.py -> covenant_trader.seal_decision ->
//      the node's /transactions, judged by the sentinel). Only an answer of
//      {"ok": true, "admission": "admitted"} allows. Anything else -- a
//      refusal, a timeout, a network error, a malformed answer, a missing
//      service -- REFUSES. The gate fails closed, and executeIfAllowed() is
//      the only path that calls an executor.
//
// This file does not arm anything. It has no exchange client, no signer and
// no credential. Those the README promises still do not exist; see
// docs/SENTINEL_WITNESS.md.

export const TIERS = Object.freeze({
  DASHBOARD: "dashboard",
  MANUAL: "manual",
  AUTOMATED: "automated",
});

export const SEAL_URL = "http://127.0.0.1:8433/seal";
export const SEAL_TIMEOUT_MS = 20000;

function finitePositive(raw) {
  if (typeof raw === "number") return Number.isFinite(raw) && raw > 0;
  if (typeof raw !== "string" || raw.trim() === "") return false;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0;
}

// Returns the automated-tier state, or throws. Mirrors automatedLimits.js:
// a limit that is not a finite positive number is not a limit.
export function enableAutomated({ maxPerTradeUsd, maxDailyTradesCount } = {}) {
  if (!finitePositive(maxPerTradeUsd)) throw new Error("maxPerTradeUsd must be a finite positive number; there is no unlimited option");
  if (!finitePositive(maxDailyTradesCount)) throw new Error("maxDailyTradesCount must be a finite positive number; there is no unlimited option");
  const perTrade = Number(maxPerTradeUsd);
  const perDay = Math.floor(Number(maxDailyTradesCount));
  if (perDay < 1) throw new Error("maxDailyTradesCount must be at least 1");
  return Object.freeze({ tier: TIERS.AUTOMATED, maxPerTradeUsd: perTrade, maxDailyTradesCount: perDay, maxDailyExposureUsd: perTrade * perDay });
}

function refusal(reason, detail) {
  return Object.freeze({ allowed: false, reason, detail: detail == null ? "" : String(detail).slice(0, 300) });
}

// Seal one proposed order through covenant's gate. Never throws: every
// failure is a refusal with a reason.
export async function gateTrade(order, { sealUrl = SEAL_URL, fetchImpl = globalThis.fetch, timeoutMs = SEAL_TIMEOUT_MS } = {}) {
  if (!order || typeof order !== "object") return refusal("no order");
  const { venue, symbol, side, amountUsd } = order;
  if (!venue || !symbol || (side !== "buy" && side !== "sell")) return refusal("order is missing venue, symbol or side");
  if (!finitePositive(amountUsd)) return refusal("amountUsd must be a finite positive number");
  if (typeof fetchImpl !== "function") return refusal("no fetch available; nothing can be sealed, so nothing is allowed");

  const controller = typeof AbortController === "function" ? new AbortController() : null;
  const timer = controller ? setTimeout(() => controller.abort(), timeoutMs) : null;
  let response;
  try {
    response = await fetchImpl(sealUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ venue, symbol, side, amountUsd: Number(amountUsd), note: String(order.note || "").slice(0, 500) }),
      signal: controller ? controller.signal : undefined,
    });
  } catch (err) {
    return refusal("seal service unreachable or timed out", err && err.message);
  } finally {
    if (timer) clearTimeout(timer);
  }
  let body;
  try {
    body = await response.json();
  } catch (err) {
    return refusal("seal service answered without JSON", err && err.message);
  }
  if (!response.ok) return refusal("seal service answered HTTP " + response.status, body && body.detail);
  if (body && body.ok === true && body.admission === "admitted") {
    return Object.freeze({ allowed: true, reason: "admitted", detail: String(body.detail || "").slice(0, 300), txId: body.tx_id || null });
  }
  return refusal("not admitted", body && (body.detail || body.reason));
}

// The only path to an executor. If the gate does not allow, the executor is
// never called, and the refusal is returned as the result.
export async function executeIfAllowed(order, executor, opts) {
  const verdict = await gateTrade(order, opts);
  if (!verdict.allowed) return Object.freeze({ executed: false, verdict });
  if (typeof executor !== "function") return Object.freeze({ executed: false, verdict: refusal("no executor") });
  const result = await executor(order, verdict);
  return Object.freeze({ executed: true, verdict, result });
}
