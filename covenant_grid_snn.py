#!/usr/bin/env python3
"""
covenant_grid_snn.py -- OPTIONAL, ALARM-ONLY spiking (SNN) temporal witness for
the grid guard.

WHAT IT IS, AND IS NOT. It is a *different-mechanism* second eye on the stream of
commands the deterministic gate already honored, looking for the one thing the
per-command checks C1..C7 structurally cannot see: an attack made of individually
in-bounds, individually-authorized commands (a slow shed ramp, breaker
oscillation under the cap, a setpoint walk, time-locked multi-zone events). It
can at most raise an ALARM / recommend a HOLD that an authority-holder (operator
or Tetsu) must SEE. It NEVER returns PERMIT/REFUSE, NEVER actuates, and is NEVER
imported by covenant_grid_guard.authorize() -- that boundary is a tested
invariant (test_gs1). On deterministic checks an SNN is strictly worse (memory
snn-not-a-judge-feature; gate-cannot-clear-conversation), so it is kept off the
gate by construction.

EARNS ITS PLACE ONLY BY MEASUREMENT. Until a training run (in the spiking lab
venv) produces weights that pass the SEALED pre-registered bar in
ops/GRID_SNN_PREREG_2026-10-30.md -- beating the trivial baselines B1..B4 at a
<=1% false-alarm operating point -- there are no weights, and this witness
returns UNKNOWN (never ABSENT: an unproven/absent witness must never read as
"all clear", covenant_highway P20). A redundant layer that merely duplicates an
EWMA is theater (memory spiking-witness-a375); if the net does not beat the
baseline we ship the baseline or park this UNPROVEN, and say so.

Deps are lazy (numpy inside functions, torch only in training) so importing this
module costs nothing and the guard runs on stdlib+cryptography alone.
"""
import json
import os

import covenant_grid_guard as gg

HERE = os.path.dirname(os.path.abspath(__file__))
WEIGHTS = os.path.join(HERE, "ops", "grid_snn_weights.npz")
PREREG = os.path.join(HERE, "ops", "GRID_SNN_PREREG_2026-10-30.md")
WINDOW_S = 3600          # matches covenant_grid_guard._window()
T_BINS = 60
MIN_ROWS = 8             # too few honored commands to judge a pattern -> UNKNOWN

PRESENT, ABSENT, UNKNOWN = gg.PRESENT, gg.ABSENT, gg.UNKNOWN


# --------------------------------------------------------------- honored stream
def _permit_rows(ledger=None, now=None, window_s=WINDOW_S):
    """The commands the gate ALREADY honored, within the window, in order. The
    witness sees exactly what passed C1..C7 -- never the raw proposals."""
    ledger = gg.LEDGER if ledger is None else ledger
    now = gg._now() if now is None else now
    out = []
    for r in gg._honored_rows(ledger):
        if r.get("decision") != PRESENT and r.get("decision") != gg.PERMIT:
            continue
        p = (r.get("command", {}) or {}).get("payload", {}) or {}
        if now - int(p.get("issued_utc", 0)) <= window_s:
            out.append(p)
    return out


# --------------------------------------------------------------- spike encoding
def encode_window(rows, now=None, window_s=WINDOW_S, t_bins=T_BINS):
    """Deterministic (no RNG) spike-channel encoding of a honored-command window.
    Returns a dict of numpy arrays [t_bins x n_zones] per channel. Derives the
    temporal/cross-zone structure a per-command sum cannot express:
      - breaker: impulse on each breaker_open/close
      - shed:    graded code of load_shed magnitude.pct
      - setpoint_delta: |value - last value in that zone| (trajectory contrast)
      - interval: inverse inter-command gap (burstiness)
      - zones_active: distinct zones touched in the bin (cross-zone coincidence)"""
    import numpy as np
    now = gg._now() if now is None else now
    zones = sorted({str(p.get("zone")) for p in rows}) or ["_"]
    zi = {z: i for i, z in enumerate(zones)}
    nz = len(zones)
    chans = {k: np.zeros((t_bins, nz), dtype=float)
             for k in ("breaker", "shed", "setpoint_delta", "interval", "zones_active")}
    if not rows:
        return {"zones": zones, **chans}
    t0 = min(int(p.get("issued_utc", now)) for p in rows)
    span = max(1, now - t0)
    last_sp = {}
    last_t = {}
    for p in rows:
        t = int(p.get("issued_utc", now))
        b = min(t_bins - 1, int((t - t0) / span * (t_bins - 1)))
        z = zi.get(str(p.get("zone")), 0)
        a = p.get("action")
        mag = p.get("magnitude") or {}
        if a in ("breaker_open", "breaker_close"):
            chans["breaker"][b, z] += 1.0
        elif a == "load_shed":
            chans["shed"][b, z] += float(mag.get("pct", 0))
        elif a == "setpoint":
            v = float(mag.get("value", 0))
            chans["setpoint_delta"][b, z] += abs(v - last_sp.get(z, v))
            last_sp[z] = v
        if z in last_t:
            gap = max(1, t - last_t[z])
            chans["interval"][b, z] += 1.0 / gap
        last_t[z] = t
        chans["zones_active"][b, z] = 1.0
    return {"zones": zones, **chans}


# --------------------------------------------------------------- pure-numpy LIF
def run_lif(enc, weights):
    """Pure-numpy leaky-integrate-and-fire forward pass. V[t+1]=beta*V[t]+I[t];
    spike when V>=thresh; subtractive reset. A small recurrent hidden layer + one
    'alarm' readout with cross-zone lateral inhibition (the coincidence detector).
    Score = alarm spike count. No torch at runtime, so inference is reproducible
    and auditable. `weights` is the frozen checkpoint dict."""
    import numpy as np
    chan_order = ("breaker", "shed", "setpoint_delta", "interval", "zones_active")
    # feature vector per time-bin: per-channel sum over zones + cross-zone coincidence
    t_bins = enc["breaker"].shape[0]
    feats = []
    for c in chan_order:
        feats.append(enc[c].sum(axis=1))
        feats.append((enc[c] > 0).sum(axis=1))   # how many zones active in this channel
    X = np.stack(feats, axis=1)                   # [t_bins, n_feat]
    scal = weights.get("scaler")
    if scal is not None:
        X = X / (np.asarray(scal) + 1e-9)
    W_in = np.asarray(weights["W_in"])            # [n_feat, hidden]
    W_rec = np.asarray(weights["W_rec"])          # [hidden, hidden]
    W_out = np.asarray(weights["W_out"])          # [hidden]
    beta = float(weights.get("beta", 0.9))
    th_h = float(weights.get("thresh_hidden", 1.0))
    th_a = float(weights.get("thresh_alarm", 1.0))
    H = W_in.shape[1]
    Vh = np.zeros(H); sh = np.zeros(H)
    Va = 0.0; alarm = 0
    for t in range(t_bins):
        I = X[t] @ W_in + sh @ W_rec
        Vh = beta * Vh + I
        sh = (Vh >= th_h).astype(float)
        Vh = Vh - sh * th_h
        Ia = sh @ W_out
        Va = beta * Va + Ia
        if Va >= th_a:
            alarm += 1
            Va -= th_a
    return float(alarm)


def load_weights(path=None):
    """Frozen checkpoint, or None if absent -> witness UNKNOWN (never a pass)."""
    if path is None:                 # resolve at call time, not def time
        path = WEIGHTS
    if not os.path.exists(path):
        return None
    try:
        import numpy as np
        z = np.load(path, allow_pickle=True)
        return {k: z[k] for k in z.files}
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------- trivial baselines
def ewma_baseline_score(rows, now=None, window_s=WINDOW_S):
    """The trivial baselines the SNN must BEAT before it may ship as a witness
    (sealed in the prereg). Shipped here so the honest fallback -- 'the baseline
    suffices' -- lives in the same place. No training, deterministic."""
    import numpy as np
    enc = encode_window(rows, now=now, window_s=window_s)
    shed = enc["shed"].sum(axis=1)
    breaker = enc["breaker"].sum(axis=1)
    # B1 EWMA of shed rate; B2 sustained fraction of window near cap; B3 setpoint slope;
    # B4 lagged cross-zone correlation of event trains (the family-D baseline).
    def ewma(x, a=0.3):
        y = 0.0; m = 0.0
        for v in x:
            y = a * v + (1 - a) * y
            m = max(m, y)
        return m
    sp = enc["setpoint_delta"].sum(axis=1)
    b3 = float(np.polyfit(np.arange(len(sp)), sp, 1)[0]) if len(sp) > 2 else 0.0
    # B3b: slope of the shed channel (a monotone ramp -> high slope; scatter -> ~0), the
    # right trivial detector for family A that B1's EWMA-max cannot see at matched marginals.
    b3b = float(np.polyfit(np.arange(len(shed)), shed, 1)[0]) if len(shed) > 2 else 0.0
    # B2: a proper CUSUM of shed above its own mean -- peaks for a sustained ramp, ~0 for
    # uncorrelated scatter even when the magnitude multiset is identical (matched marginal).
    c_acc, cusum = 0.0, 0.0
    ref = float(shed.mean())
    for v in shed:
        c_acc = max(0.0, c_acc + (v - ref))
        cusum = max(cusum, c_acc)
    ev = (enc["breaker"] + enc["shed"] + enc["setpoint_delta"])
    if ev.shape[1] >= 2:
        cc = np.corrcoef(ev.T)
        b4 = float(np.nanmax(cc[np.triu_indices(cc.shape[0], k=1)])) if cc.size > 1 else 0.0
    else:
        b4 = 0.0
    # B5: slope of the RAW setpoint value over time (family C monotone walk -> high |slope|;
    # mean-reverting -> ~0). The |delta| encoding cannot see this, so read the rows directly.
    spv = sorted((r.get("issued_utc", 0), float((r.get("magnitude") or {}).get("value", 0)))
                 for r in rows if r.get("action") == "setpoint")
    b5 = abs(float(np.polyfit(np.arange(len(spv)), [v for _, v in spv], 1)[0])) if len(spv) > 2 else 0.0
    # B6: breaker alternation (family B oscillation -> adjacent ops almost always differ;
    # a random benign mix -> ~0.5). Read the raw open/close sequence in time order.
    bseq = [1 if r.get("action") == "breaker_open" else 0
            for r in sorted(rows, key=lambda r: r.get("issued_utc", 0))
            if r.get("action") in ("breaker_open", "breaker_close")]
    b6 = float(np.mean([bseq[i] != bseq[i - 1] for i in range(1, len(bseq))])) if len(bseq) > 2 else 0.0
    return {"B1_ewma_shed": ewma(shed), "B2_cusum_shed": cusum,
            "B2_sustained_breaker": float(breaker.mean()),
            "B3_setpoint_slope": b3, "B3b_shed_slope": b3b, "B4_crosszone_corr": b4,
            "B5_setpoint_value_slope": b5, "B6_breaker_alternation": b6}


# --------------------------------------------------------------- the witness
def pattern_anomaly_state(envelope=None, now=None, ledger=None):
    """ALARM-only. {state, measured}. UNKNOWN when the witness cannot or has not
    earned a verdict (too few rows / no weights / any error) -- never ABSENT in
    those cases, so 'no witness' can never read as 'all clear' (P20). PRESENT with
    recommend=HOLD only when a FROZEN, pre-registered model scores above its
    frozen threshold. It recommends; it never decides."""
    try:
        rows = _permit_rows(ledger=ledger, now=now)
        if len(rows) < MIN_ROWS:
            return gg._st(UNKNOWN, note="too few honored commands to judge a pattern",
                          n_rows=len(rows), recommend=None, backend="none")
        w = load_weights()
        if w is None:
            return gg._st(UNKNOWN, note="no frozen SNN weights (unproven/not yet trained) -- "
                          "witness abstains; see ops/GRID_SNN_PREREG_2026-10-30.md",
                          n_rows=len(rows), recommend=None, backend="none")
        enc = encode_window(rows, now=now)
        score = run_lif(enc, w)
        thr = float(w.get("frozen_threshold", 1e9))
        if score >= thr:
            return gg._st(PRESENT, note="temporal pattern anomaly over honored commands",
                          score=score, thr=thr, recommend="HOLD", backend="numpy",
                          prereg_id=str(w.get("prereg_id", "")))
        return gg._st(ABSENT, score=score, thr=thr, recommend=None, backend="numpy")
    except Exception as e:  # noqa: BLE001
        return gg._st(UNKNOWN, note="snn witness error: %s" % type(e).__name__, recommend=None)


if __name__ == "__main__":
    import sys
    print(json.dumps(pattern_anomaly_state(), indent=2))
    sys.exit(0)
