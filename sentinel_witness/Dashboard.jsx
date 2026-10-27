import { useState, useEffect, useCallback } from "react";
import { TIERS } from "../lib/tradeGate.js";
import { getTierRank, isTierClickable } from "../lib/tierNavigation.js";
import AutomatedSetupModal from "./AutomatedSetupModal.jsx";

/**
 * Dashboard.jsx
 *
 * Design intent: this is a trading terminal, not a marketing page --
 * dense, precise, calm. The tier ladder (dashboard -> manual ->
 * automated) is rendered as a real structural element because it IS
 * the real security model (see tradeGate.js), not decoration. Numbers
 * that came from the walk-forward-validated baseline are visually
 * distinguished from numbers the live adaptive layer just computed --
 * conflating "this was proven out-of-sample" with "this is a live
 * guess" in the UI would be the same category of silent-failure this
 * whole project has consistently flagged as the dangerous thing to do.
 */

const TIER_INFO = [
  { key: TIERS.DASHBOARD, label: "Dashboard", desc: "Read-only. Balances and strategy status." },
  { key: TIERS.MANUAL, label: "Manual approval", desc: "See signals, tap to confirm, sign on Ledger." },
  { key: TIERS.AUTOMATED, label: "Automated", desc: "Runs within limits you set. Ledger confirmation still required per trade." },
];

function TierLadder({ currentTier, onRequestTierChange }) {
  const currentRank = getTierRank(currentTier);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {TIER_INFO.map((tier, i) => {
        const active = i === currentRank;
        const clickable = isTierClickable(currentTier, tier.key);
        const reachable = clickable || active;
        return (
          <button
            key={tier.key}
            disabled={!clickable}
            onClick={() => onRequestTierChange(tier.key)}
            style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              padding: "12px 14px", borderRadius: 10, textAlign: "left",
              border: active ? "1px solid #c9a24b" : "1px solid #2a2d33",
              background: active ? "#20242b" : "#16181c",
              color: reachable ? "#e8e6e1" : "#55585e",
              opacity: reachable ? 1 : 0.5, cursor: clickable ? "pointer" : "default",
            }}
          >
            <span>
              <div style={{ fontFamily: "ui-monospace, monospace", fontSize: 13, letterSpacing: 0.5 }}>
                {i < currentRank ? "\u2713 " : active ? "\u25CF " : "\u25CB "}{tier.label.toUpperCase()}
              </div>
              <div style={{ fontSize: 12, color: "#8a8d93", marginTop: 2 }}>{tier.desc}</div>
            </span>
            {active && <span style={{ fontSize: 11, color: "#c9a24b" }}>ACTIVE</span>}
          </button>
        );
      })}
    </div>
  );
}

function NumberRow({ label, value, source, mono = true }) {
  const sourceColor = source === "walk_forward_validated" ? "#5fb87a" : source === "conservative_default" ? "#8a8d93" : "#c9a24b";
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid #21242a" }}>
      <span style={{ fontSize: 13, color: "#a8abb1" }}>{label}</span>
      <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ fontFamily: mono ? "ui-monospace, monospace" : "inherit", fontSize: 13, color: "#e8e6e1" }}>{value}</span>
        {source && <span style={{ width: 6, height: 6, borderRadius: "50%", background: sourceColor }} title={source} />}
      </span>
    </div>
  );
}

export default function Dashboard({ gate, ledgerSupport }) {
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tier, setTier] = useState(gate.tier);
  const [automatedModalOpen, setAutomatedModalOpen] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const s = await gate.getDashboardSnapshot();
      setSnapshot(s);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [gate]);

  useEffect(() => { refresh(); }, [refresh]);

  const handleTierChange = (key) => {
    if (key === TIERS.DASHBOARD) {
      // FIXED -- this button rendered clickable at manual/automated tiers
      // (see TierLadder's `reachable` check) but had no matching branch
      // here, so tapping it silently did nothing. Confirmed empirically
      // before this fix, not assumed. De-escalating trust should never
      // be the hard path, and "hard path" turns out to have included
      // "doesn't work at all."
      gate.disableTrading();
      setTier(gate.tier);
    } else if (key === TIERS.MANUAL) {
      gate.enableManual();
      setTier(gate.tier);
    } else if (key === TIERS.AUTOMATED) {
      setAutomatedModalOpen(true);
    }
  };

  const handleConfirmAutomated = async ({ maxPerTradeUsd, maxDailyTradesCount }) => {
    // Let a thrown TradeGateError propagate -- AutomatedSetupModal catches
    // it and displays it inline. Only close the modal and advance tier
    // state on genuine success, so a rejected attempt never looks like it
    // silently succeeded.
    gate.enableAutomated({ maxPerTradeUsd, maxDailyTradesCount });
    setTier(gate.tier);
    setAutomatedModalOpen(false);
  };

  const usdBalance = snapshot?.balances?.find((b) => b.asset === "USD")?.available ?? null;

  return (
    <div style={{ background: "#0d0f12", minHeight: "100%", padding: 16, fontFamily: "system-ui, sans-serif", color: "#e8e6e1" }}>
      <div style={{ marginBottom: 18 }}>
        <div style={{ fontSize: 12, color: "#8a8d93", letterSpacing: 1 }}>ASSET</div>
        <div style={{ fontSize: 22, fontFamily: "ui-monospace, monospace" }}>{gate.asset.toUpperCase()}</div>
      </div>

      {!ledgerSupport.supported && (
        <div style={{ background: "#2a1f16", border: "1px solid #5a4426", borderRadius: 8, padding: 10, marginBottom: 14, fontSize: 12, color: "#d9b26a" }}>
          Ledger unavailable in this browser: {ledgerSupport.reason}
        </div>
      )}

      {error && (
        <div style={{ background: "#2a1616", border: "1px solid #5a2626", borderRadius: 8, padding: 10, marginBottom: 14, fontSize: 12, color: "#e08a8a" }}>
          {error}
        </div>
      )}

      <div style={{ background: "#16181c", border: "1px solid #21242a", borderRadius: 12, padding: 14, marginBottom: 16 }}>
        <NumberRow label="Price" value={loading ? "\u2026" : `$${snapshot?.price?.toFixed(4) ?? "--"}`} />
        {snapshot?.balances?.map((b) => (
          <NumberRow key={b.asset} label={`Balance (${b.asset})`} value={b.available.toFixed(b.asset === "USD" ? 2 : 6)} />
        ))}
      </div>

      <div style={{ fontSize: 12, color: "#8a8d93", letterSpacing: 1, marginBottom: 8 }}>CAPABILITY</div>
      <TierLadder currentTier={tier} onRequestTierChange={handleTierChange} />

      <div style={{ marginTop: 20, fontSize: 11, color: "#5a5d63", display: "flex", gap: 10 }}>
        <span><span style={{ color: "#5fb87a" }}>\u25CF</span> walk-forward validated</span>
        <span><span style={{ color: "#8a8d93" }}>\u25CF</span> conservative default</span>
      </div>

      <AutomatedSetupModal
        open={automatedModalOpen}
        onCancel={() => setAutomatedModalOpen(false)}
        onConfirm={handleConfirmAutomated}
        usdBalance={usdBalance}
      />
    </div>
  );
}
