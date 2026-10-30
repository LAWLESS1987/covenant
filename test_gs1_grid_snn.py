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


HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, "tools")


def _load_tool(name, path=None):
    """Import tools/<name>.py (or a given copy of it) as a fresh module."""
    import importlib.util
    path = path or os.path.join(TOOLS, name + ".py")
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    spec = importlib.util.spec_from_file_location("%s_%d" % (name, abs(hash(path))), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The bench checks below are functions of a bench module so the SAME check can be
# driven against a pre-fix copy (rule 8: show it red on the old code).
def bench_cumulative_c5(B):
    """F17: the in-bounds premise must be judged by the REAL gateway over the whole
    stream. 30 load-sheds of 5% each are individually in bounds (5 <= 100) but sum to
    150% in one window -> the real C5 refuses; 10 of them (50%) all PERMIT."""
    base = B.gen("benignA", 7)
    over = [dict(r, magnitude={"pct": 5.0}) for r in base[:30]]
    under = [dict(r, magnitude={"pct": 5.0}) for r in base[:10]]
    r_over, r_under = B.permits(over), B.permits(under)
    return (isinstance(r_over, dict) and r_over["all_permit"] is False
            and r_over["first_fail"]["check"] == "C5" and r_over["n_permit"] == 20
            and isinstance(r_under, dict) and r_under["all_permit"] is True
            and r_under["n_permit"] == 10)


def bench_marginals_measured(B):
    """F19: matched marginals are MEASURED -- a permuted identical multiset reads
    MATCHED-EXACT, a shifted magnitude distribution reads UNDETERMINED."""
    ben = [B.gen("benignA", 100 + i) for i in range(20)]
    same = [list(reversed(s)) for s in ben]
    shifted = [[dict(r, magnitude={"pct": r["magnitude"]["pct"] + 10}) for r in s] for s in ben]
    return (B.marginal_check(ben, same)["status"] == "MATCHED-EXACT"
            and B.marginal_check(ben, shifted)["status"] == "UNDETERMINED")


def bench_header_true(B):
    """F20: the header names the post-hoc baselines and no longer says no SNN exists."""
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        B.main(["--families", "C", "--n", "10", "--no-validate"])
    out = buf.getvalue()
    return ("POST-HOC" in out and "no trained SNN yet" not in out
            and "B1-B4 only" not in out and "premise NOT MEASURED" in out)


def train_paths_relative(path):
    """F9: the trainer carries no absolute machine path, resolves the repo from its
    own location, and writes to an --out under logs/ (gitignored) by default."""
    import ast
    import re
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    absolute = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
                and isinstance(n.value, str) and re.match(r"^([A-Za-z]:[\\/]|/(home|Users)/)", n.value)]
    if absolute:
        return False
    T = _load_tool("grid_snn_train", path)
    root = os.path.dirname(os.path.dirname(os.path.abspath(path)))
    return (os.path.normcase(T.ROOT) == os.path.normcase(root)
            and os.path.normcase(T.DEFAULT_OUT) == os.path.normcase(
                os.path.join(root, "logs", "grid_snn_train_result.json")))


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

    # ---- the benchmark harness measures its premises (F9/F17/F19/F20, 2026-10-30)
    g_names = ("LEDGER", "CHAIN", "SIGNERS", "INTERLOCKS", "POLICY", "HEARTBEAT", "SAFE_STATE",
               "snapshot_detectors")
    saved_g = {k: getattr(gg, k) for k in g_names}
    B = _load_tool("grid_snn_bench")
    # A latched safe-state at the module default must NOT reach the replay (it used to:
    # every command came back LATCHED and the premise read FAIL for the wrong reason).
    with open(gg.SAFE_STATE, "w") as fh:
        json.dump({"latched": True, "latch_id": "gs1-planted"}, fh)
    try:
        check("bench permits(): REAL gateway + cumulative C5 over the whole stream "
              "(30 x 5pct refused at #21, 10 x 5pct all PERMIT) -- with the default latch planted",
              bench_cumulative_c5(B))
    finally:
        os.remove(gg.SAFE_STATE)
    check("bench permits() restores EVERY guard module global it touches",
          all(getattr(gg, k) is saved_g[k] for k in g_names))
    check("bench marginal_check(): identical multiset MATCHED-EXACT, shifted UNDETERMINED",
          bench_marginals_measured(B))
    check("bench header labels POST-HOC baselines; no 'B1-B4 only / no trained SNN yet'",
          bench_header_true(B))
    check("grid_snn_train: no absolute path; root from its own location; --out under logs/",
          train_paths_relative(os.path.join(TOOLS, "grid_snn_train.py")))

    print("\nGS1: %d passed, %d failed" % (P[0], F[0]))
    return 1 if F[0] else 0


if __name__ == "__main__":
    sys.exit(main())
