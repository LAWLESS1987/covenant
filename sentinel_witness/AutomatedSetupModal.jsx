import { useState, useEffect, useRef, useMemo } from "react";
import { isValidLimit, computeMaxDailyExposure, computeExposurePctOfBalance } from "../lib/automatedLimits.js";

/**
 * AutomatedSetupModal.jsx
 *
 * Replaces the prompt()/alert() placeholder that used to sit inline in
 * Dashboard.jsx's handleTierChange. This is the one moment in the whole
 * app where a human hands off standing permission to trade without a
 * per-trade tap -- tradeGate.js already refuses to enable that tier
 * without finite, positive limits (no "unlimited" option, checked on
 * every signal, not just here); this form is the honest UI for setting
 * them, not just a barrier to get past.
 *
 * SIGNATURE ELEMENT: the two numbers a person types here (max per trade,
 * max trades per day) don't mean anything on their own -- their PRODUCT
 * is the real question ("how much could this commit in a single day if
 * every trade hit the cap"). That's computed live below the inputs, and
 * related to the actual USD balance when known, rather than left as an
 * exercise for the reader. Framed explicitly as a ceiling, not a loss
 * estimate -- each trade is a grid buy, not a guaranteed loss, and
 * overstating this as "money you will lose" would be its own kind of
 * dishonesty this project has consistently tried to avoid elsewhere
 * (see tradeGate.js and covenant_unified_v8.py's own HONESTY NOTEs).
 *
 * Validation lives in two places on purpose, not by accident: the fast
 * inline check here (so the submit button reflects reality as you type,
 * and you never even attempt a bad submission) AND tradeGate.js's own
 * enableAutomated() (the actual authority -- see its own comment: "no
 * unlimited option"). If those two ever disagreed, the gate wins; this
 * form's job is to never let that disagreement surface as a raw
 * exception, not to be a second source of truth.
 */

const FIELD_STYLE = {
  width: "100%", padding: "10px 12px", background: "#0d0f12",
  border: "1px solid #2a2d33", borderRadius: 8, color: "#e8e6e1",
  fontSize: 15, fontFamily: "ui-monospace, monospace",
};

function Field({ label, hint, value, onChange, inputRef, autoFocus, invalidMessage }) {
  const [touched, setTouched] = useState(false);
  const showError = touched && value !== "" && !isValidLimit(value);
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={{ fontSize: 12, color: "#8a8d93", letterSpacing: 0.5, display: "block", marginBottom: 6 }}>
        {label}
      </label>
      <input
        ref={inputRef}
        autoFocus={autoFocus}
        type="number"
        inputMode="decimal"
        min="0"
        step="any"
        placeholder="0"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={() => setTouched(true)}
        style={{
          ...FIELD_STYLE,
          borderColor: showError ? "#5a2626" : FIELD_STYLE.border,
        }}
      />
      <div style={{ fontSize: 11, color: showError ? "#e08a8a" : "#5a5d63", marginTop: 5, minHeight: 14 }}>
        {showError ? invalidMessage : hint}
      </div>
    </div>
  );
}

export default function AutomatedSetupModal({ open, onCancel, onConfirm, usdBalance }) {
  const [maxPerTradeUsd, setMaxPerTradeUsd] = useState("");
  const [maxDailyTradesCount, setMaxDailyTradesCount] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const firstFieldRef = useRef(null);

  // Reset to a blank form every time the modal is (re)opened -- stale
  // values from a cancelled attempt shouldn't reappear silently later.
  useEffect(() => {
    if (open) {
      setMaxPerTradeUsd("");
      setMaxDailyTradesCount("");
      setSubmitError(null);
      setSubmitting(false);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(e) {
      if (e.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onCancel]);

  const perTradeValid = isValidLimit(maxPerTradeUsd);
  const dailyCountValid = isValidLimit(maxDailyTradesCount);
  const bothValid = perTradeValid && dailyCountValid;

  const maxDailyExposure = useMemo(
    () => computeMaxDailyExposure(maxPerTradeUsd, maxDailyTradesCount),
    [maxPerTradeUsd, maxDailyTradesCount]
  );

  const exposurePctOfBalance = useMemo(
    () => computeExposurePctOfBalance(maxDailyExposure, usdBalance),
    [maxDailyExposure, usdBalance]
  );

  if (!open) return null;

  async function handleConfirm() {
    if (!bothValid || submitting) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await onConfirm({
        maxPerTradeUsd: Number(maxPerTradeUsd),
        maxDailyTradesCount: Number(maxDailyTradesCount),
      });
      // Success: the parent flips `open` to false via its own state once
      // gate.enableAutomated() has actually taken effect, so this modal
      // doesn't need (and shouldn't guess) its own success transition.
    } catch (e) {
      setSubmitError(e?.message || "Could not enable automated trading.");
      setSubmitting(false);
    }
  }

  return (
    <div
      role="presentation"
      onMouseDown={(e) => { if (e.target === e.currentTarget) onCancel(); }}
      style={{
        position: "fixed", inset: 0, background: "rgba(5,6,7,0.72)",
        display: "flex", alignItems: "flex-end", justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="automated-setup-title"
        style={{
          width: "100%", maxWidth: 480, background: "#16181c",
          borderTop: "1px solid #2a2d33", borderLeft: "1px solid #2a2d33", borderRight: "1px solid #2a2d33",
          borderRadius: "18px 18px 0 0", padding: "10px 20px 24px",
          boxShadow: "0 -8px 40px rgba(0,0,0,0.5)",
          animation: "sheet-rise 180ms ease-out",
        }}
      >
        <style>{`
          @keyframes sheet-rise { from { transform: translateY(24px); opacity: 0.4; } to { transform: translateY(0); opacity: 1; } }
          @media (prefers-reduced-motion: reduce) { * { animation-duration: 0.001ms !important; } }
        `}</style>

        <div style={{ width: 36, height: 4, borderRadius: 2, background: "#2a2d33", margin: "0 auto 16px" }} />

        <h2 id="automated-setup-title" style={{ fontSize: 16, fontWeight: 500, margin: "0 0 4px", color: "#e8e6e1" }}>
          Enable automated trading
        </h2>
        <p style={{ fontSize: 12.5, color: "#8a8d93", margin: "0 0 20px", lineHeight: 1.5 }}>
          The gate runs the strategy on a timer within the limits below. A Ledger
          confirmation is still required for every trade — this cannot be
          switched off at any tier.
        </p>

        <Field
          label="Max USD per trade"
          hint="A finite amount, required — there is no unlimited option."
          invalidMessage="Enter a number greater than 0."
          value={maxPerTradeUsd}
          onChange={setMaxPerTradeUsd}
          inputRef={firstFieldRef}
          autoFocus
        />
        <Field
          label="Max trades per day"
          hint="Resets at midnight UTC."
          invalidMessage="Enter a number greater than 0."
          value={maxDailyTradesCount}
          onChange={setMaxDailyTradesCount}
        />

        <div style={{
          background: "#0d0f12", border: "1px solid #21242a", borderRadius: 10,
          padding: "12px 14px", marginBottom: 20,
        }}>
          <div style={{ fontSize: 11, color: "#8a8d93", letterSpacing: 0.5, marginBottom: 6 }}>
            WORST-CASE DAILY DEPLOYMENT
          </div>
          <div style={{ fontFamily: "ui-monospace, monospace", fontSize: 20, color: bothValid ? "#c9a24b" : "#5a5d63" }}>
            {bothValid ? `$${maxDailyExposure.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : "—"}
          </div>
          <div style={{ fontSize: 11.5, color: "#5a5d63", marginTop: 4, lineHeight: 1.4 }}>
            {bothValid
              ? exposurePctOfBalance !== null
                ? `If every trade hits the per-trade cap, ${exposurePctOfBalance.toFixed(0)}% of your current $${usdBalance.toFixed(2)} balance in one day.`
                : "If every trade hits the per-trade cap. Not a loss estimate — each trade is a grid buy, not a guaranteed loss."
              : "Fill in both fields to see the ceiling this sets."}
          </div>
        </div>

        {submitError && (
          <div style={{ background: "#2a1616", border: "1px solid #5a2626", borderRadius: 8, padding: 10, marginBottom: 16, fontSize: 12, color: "#e08a8a" }}>
            {submitError}
          </div>
        )}

        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={onCancel}
            disabled={submitting}
            style={{
              flex: 1, padding: 12, borderRadius: 8, border: "1px solid #2a2d33",
              background: "transparent", color: "#a8abb1", fontSize: 14, fontWeight: 500,
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!bothValid || submitting}
            style={{
              flex: 2, padding: 12, borderRadius: 8, border: "1px solid #c9a24b",
              background: bothValid && !submitting ? "#20242b" : "#16181c",
              color: bothValid && !submitting ? "#c9a24b" : "#55585e",
              fontSize: 14, fontWeight: 500,
              cursor: bothValid && !submitting ? "pointer" : "default",
              opacity: bothValid ? 1 : 0.6,
            }}
          >
            {submitting ? "Enabling\u2026" : "Enable automated trading"}
          </button>
        </div>
      </div>
    </div>
  );
}
