/**
 * automatedLimits.js
 *
 * Pure logic behind AutomatedSetupModal.jsx, pulled out of the component
 * for the same reason gridMath.js and strategyGuide.js already live here
 * rather than inside a .jsx file: this project's test runner only
 * executes plain .js under src/lib/__tests__/ (no JSX transform in that
 * path, by design -- see package.json's "test" script), so logic left
 * inline in a component is logic that never gets a regression test.
 * That gap is exactly how Dashboard.jsx's dead dashboard-tier button
 * shipped unnoticed -- see tierNavigation.js for the other half of that
 * fix.
 *
 * isValidLimit() intentionally mirrors tradeGate.js's own enableAutomated()
 * check (finite, > 0, nothing stricter) rather than inventing a separate
 * rule -- if this ever drifted from the gate's actual check, the UI could
 * either block something the gate would allow, or (worse) look valid
 * here and still throw at the gate. Kept identical on purpose.
 */

export function isValidLimit(raw) {
  if (typeof raw !== "string" || raw.trim() === "") return false;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0;
}

/** Worst-case, not expected-case: what it would mean if every single
 * trade, every day, hit the per-trade cap. Returns null rather than NaN
 * or 0 when inputs aren't both valid yet, so a caller can't accidentally
 * render "$0" and have it read as a real answer. */
export function computeMaxDailyExposure(maxPerTradeUsd, maxDailyTradesCount) {
  if (!isValidLimit(String(maxPerTradeUsd)) || !isValidLimit(String(maxDailyTradesCount))) return null;
  return Number(maxPerTradeUsd) * Number(maxDailyTradesCount);
}

/** null when there's no balance to relate the exposure to yet (still
 * loading, or a zero/missing USD balance) -- distinguished from 0 for
 * the same "don't render a fake-looking real number" reason as above. */
export function computeExposurePctOfBalance(maxDailyExposure, usdBalance) {
  if (maxDailyExposure === null || !Number.isFinite(usdBalance) || usdBalance <= 0) return null;
  return (maxDailyExposure / usdBalance) * 100;
}
