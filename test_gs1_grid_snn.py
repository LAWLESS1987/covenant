#!/usr/bin/env python3
"""
GS1 -- covenant_grid_snn ALARM-only witness invariants. These do NOT need a
trained model; they pin the LOAD-BEARING boundary (the witness can never touch a
decision) and the UNKNOWN-never-pass discipline, and drive the alarm mechanism
both ways with a synthetic frozen checkpoint. The "does a trained net beat the
baselines" question is the SEALED benchmark (ops/GRID_SNN_PREREG_2026-10-30.md),
which is allowed to land UNDETERMINED and say so -- it is NOT this file.

Run: python test_gs1_grid_snn.py
"""
import inspect
import json
import os
import sys

import numpy as np

import test_gg1_grid_guard as t
import covenant_grid_guard as gg
import covenant_grid_snn as snn

P = [0]; F = [0]


def check(name, ok):
    (P if ok else F)[0] += 1
    print("  %s %s" % ("ok  " if ok else "FAIL", name))


def honor_many(keys, fpr, signers, policy, n=10):
    gw = gg.GridEffectorGateway(ledger=gg.LEDGER, chain=gg.CHAIN, heartbeat=gg.HEARTBEAT)
    for i in range(n):
        e = t.actuation(keys, fpr, signers, policy, seq=i,
                        action="load_shed" if i % 2 else "breaker_open",
                        magnitude={"pct": 3} if i % 2 else {})
        gw.submit(e)
    return gw


def base_weights(frozen_threshold=0.0):
    n_feat, H = 10, 4            # 5 channels x 2 (sum, zones-active) -- see run_lif
    return {"W_in": np.full((n_feat, H), 5.0), "W_rec": np.zeros((H, H)),
            "W_out": np.ones(H), "beta": 0.5, "thresh_hidden": 0.1, "thresh_alarm": 0.1,
            "scaler": np.ones(n_feat), "frozen_threshold": float(frozen_threshold),
            "prereg_id": "GRID_SNN_PREREG_2026-10-30"}


def main():
    d, keys, fpr, signers, interlocks, policy = t.setup()
    # point the witness at a temp weights path (none yet -> UNKNOWN)
    snn.WEIGHTS = os.path.join(d, "grid_snn_weights.npz")
    gw = honor_many(keys, fpr, signers, policy, n=12)

    # ---- UNKNOWN, never ABSENT, when there are no weights (unproven witness)
    s = snn.pattern_anomaly_state(ledger=gg.LEDGER)
    check("no weights -> UNKNOWN (never ABSENT: absent witness is not 'all clear')",
          s["state"] == gg.UNKNOWN and "weights" in s["measured"].get("note", ""))

    # ---- too-few-rows -> UNKNOWN (fresh empty ledger)
    import tempfile
    empty = os.path.join(tempfile.mkdtemp(), "empty.jsonl")
    check("too few honored rows -> UNKNOWN",
          snn.pattern_anomaly_state(ledger=empty)["state"] == gg.UNKNOWN)

    # ---- alarm mechanism BOTH ways with a synthetic frozen checkpoint
    rows = snn._permit_rows(ledger=gg.LEDGER)
    enc = snn.encode_window(rows)
    hi = snn.run_lif(enc, base_weights(0.0))     # alarm-spike count for this window
    check("run_lif returns a positive float score for an active window", isinstance(hi, float) and hi > 0)

    def save(th):
        w = base_weights(th)
        np.savez(snn.WEIGHTS, W_in=w["W_in"], W_rec=w["W_rec"], W_out=w["W_out"],
                 beta=w["beta"], thresh_hidden=w["thresh_hidden"], thresh_alarm=w["thresh_alarm"],
                 scaler=w["scaler"], frozen_threshold=w["frozen_threshold"], prereg_id=w["prereg_id"])

    save(hi * 0.5)                                # threshold below the score -> fires PRESENT
    s_present = snn.pattern_anomaly_state(ledger=gg.LEDGER)
    save(hi + 100.0)                              # threshold above the score -> clears ABSENT
    s_absent = snn.pattern_anomaly_state(ledger=gg.LEDGER)
    check("witness fires PRESENT (recommend HOLD) above threshold",
          s_present["state"] == gg.PRESENT and s_present["measured"].get("recommend") == "HOLD")
    check("witness clears ABSENT below threshold (both ways on the mechanism)",
          s_absent["state"] == gg.ABSENT and s_absent["measured"].get("recommend") is None)

    # ---- determinism: identical score across repeated calls (no RNG at inference)
    check("encode+run_lif deterministic", snn.run_lif(enc, base_weights(0.0)) == hi)

    # ---- SOURCE INVARIANT: authorize() must never reference the witness (anti-smuggle)
    src = inspect.getsource(gg.authorize)
    check("authorize() source contains no 'snn' / 'pattern_anomaly' (gate stays deterministic)",
          "snn" not in src.lower() and "pattern_anomaly" not in src.lower())

    # ---- BOUNDARY PURITY: authorize() decision identical whether the witness imports or not
    env = t.actuation(keys, fpr, signers, policy, seq=100)
    dec_with = t.A(env, signers, interlocks, policy)
    saved = sys.modules.get("covenant_grid_snn")
    sys.modules["covenant_grid_snn"] = None      # force ImportError on deferred import
    try:
        dec_without = t.A(env, signers, interlocks, policy)
    finally:
        sys.modules["covenant_grid_snn"] = saved
    check("authorize() decision is byte-identical with the witness present vs absent",
          json.dumps(dec_with, sort_keys=True) == json.dumps(dec_without, sort_keys=True))

    # ---- NEVER AUTHORIZE: a screaming witness changes no gateway decision
    import tempfile as _tf
    fresh_led = os.path.join(_tf.mkdtemp(), "g.jsonl")
    fresh_ch = fresh_led + ".chain"
    orig = snn.pattern_anomaly_state
    snn.pattern_anomaly_state = lambda **k: gg._st(gg.PRESENT, recommend="HOLD", note="forced")
    try:
        gw2 = gg.GridEffectorGateway(ledger=fresh_led, chain=fresh_ch, heartbeat=gg.HEARTBEAT)
        t.fresh_heartbeat()
        ok_env = t.actuation(keys, fpr, signers, policy, seq=0)   # one breaker op in a fresh window
        dd = gw2.submit(ok_env)
        bad = t.actuation(keys, fpr, signers, policy, seq=1, both=False)   # missing authz
        db = gw2.submit(bad)
        check("a PERMIT still PERMITs even while the witness screams PRESENT",
              dd["decision"] == gg.PERMIT)
        check("a REFUSE still REFUSEs; the witness can alarm, never clear/actuate",
              db["decision"] == gg.REFUSE and db["failed_check"] == "C6")
    finally:
        snn.pattern_anomaly_state = orig

    # ---- the detector keys UNKNOWN in the guard snapshot when weights absent
    os.remove(snn.WEIGHTS)
    snap = gg.snapshot_detectors()
    check("guard snapshot keys grid_pattern_anomaly UNKNOWN when unproven",
          snap.get("grid_pattern_anomaly") == gg.UNKNOWN)

    print("\nGS1: %d passed, %d failed" % (P[0], F[0]))
    return 1 if F[0] else 0


if __name__ == "__main__":
    sys.exit(main())
