#!/usr/bin/env python3
"""
GS2 -- invariants of the v2 grid-SNN measurement apparatus (sealed prereg
ops/GRID_SNN_PREREG_v2_2026-11-02.md) and a re-affirmation of the ALARM-only
boundary in the v2 context. Driven BOTH WAYS (CLAUDE.md rule 8). These pin the
apparatus properties the v1 review (A392) found missing, so a future edit that
re-breaks them turns GS2 red:

  * the generator is cumulative-window-respecting (an in-bounds stream all-PERMITs
    through the REAL gateway; a stream scaled over the cap is REFUSED at C5) --
    v1's A/D silently overran the window;
  * benign/attack pairs are matched-marginal EXACT (shift the magnitudes -> the
    check reads UNDETERMINED) -- v1 asserted this while pairing different seeds;
  * Holm-Bonferroni accepts when every zone agrees and rejects when one zone
    diverges (both ways);
  * the SEALED baseline list is exactly the keys ewma_baseline_score produces, so
    no baseline can be added post-hoc outside the seal;
  * authorize() still never references the witness, and a witness forced to scream
    PRESENT changes no gateway decision -- whether or not weights have shipped.

The "does a trained net beat the baselines" question is the SEALED benchmark
(tools/grid_snn_bench_v2.py + tools/grid_snn_train_v2.py); it is allowed to land
NO-GO/UNDETERMINED and say so -- it is NOT this file.

Run: python test_gs2_grid_snn_v2.py
"""
import inspect
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, "tools")
for p in (HERE, TOOLS):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    import numpy  # noqa: F401  -- the apparatus needs numpy; public CI may lack it
    _HAVE_NP = True
except ImportError:
    _HAVE_NP = False

import test_gg1_grid_guard as t
import covenant_grid_guard as gg
import covenant_grid_snn as snn

P = [0]; F = [0]


def check(name, ok):
    (P if ok else F)[0] += 1
    print("  %s %s" % ("ok  " if ok else "FAIL", name))


# --------------------------------------------------------------- boundary (no numpy)
def boundary_checks(keys, fpr, signers, interlocks, policy):
    """The LOAD-BEARING boundary in the v2 context -- needs no numpy, runs everywhere."""
    src = inspect.getsource(gg.authorize)
    check("authorize() source references no 'snn'/'pattern_anomaly' (gate stays deterministic)",
          "snn" not in src.lower() and "pattern_anomaly" not in src.lower())

    import tempfile as _tf
    fresh = os.path.join(_tf.mkdtemp(), "g.jsonl")
    orig = snn.pattern_anomaly_state
    snn.pattern_anomaly_state = lambda **k: gg._st(gg.PRESENT, recommend="HOLD", note="forced v2")
    try:
        gw = gg.GridEffectorGateway(ledger=fresh, chain=fresh + ".chain", heartbeat=gg.HEARTBEAT)
        t.fresh_heartbeat()
        good = gw.submit(t.actuation(keys, fpr, signers, policy, seq=0))
        bad = gw.submit(t.actuation(keys, fpr, signers, policy, seq=1, both=False))
        check("a PERMIT still PERMITs while the witness screams PRESENT (witness never clears/actuates)",
              good["decision"] == gg.PERMIT)
        check("a REFUSE still REFUSEs; a screaming witness cannot flip it to PERMIT",
              bad["decision"] == gg.REFUSE)
    finally:
        snn.pattern_anomaly_state = orig


# --------------------------------------------------------------- apparatus (numpy)
def apparatus_checks():
    import grid_snn_bench as B           # gateway replay (needs cryptography)
    import grid_snn_bench_v2 as B2

    # ---- SEALED baseline list == exactly what ewma_baseline_score produces
    one = B2.gen("A", 1, "benign")
    keys = set(snn.ewma_baseline_score(one, now=max(r["issued_utc"] for r in one) + 1))
    check("SEALED_BASELINES == the full set of ewma_baseline_score keys (nothing post-hoc, nothing dropped)",
          set(B2.SEALED_BASELINES) == keys)

    # ---- cumulative-window premise, BOTH WAYS, through the REAL gateway
    in_bounds = B2.gen("A", 7, "attack")                 # sum(shed) <= 80 by construction
    over_cap = [dict(r, magnitude={"pct": float(r["magnitude"]["pct"]) * 10.0}) for r in in_bounds]
    r_in, r_over = B.permits(in_bounds), B.permits(over_cap)
    check("v2 in-bounds stream: every command PERMITs through the real cumulative-C5 gateway",
          r_in["all_permit"] is True and r_in["n_permit"] == r_in["n"])
    check("v2 stream scaled 10x over the cap: REFUSED at C5 (the window really is cumulative)",
          r_over["all_permit"] is False and r_over["first_fail"]["check"] == "C5")

    # ---- matched marginals EXACT, BOTH WAYS
    ben = [B2.gen("A", 100 + i, "benign") for i in range(20)]
    att = [B2.gen("A", 100 + i, "attack") for i in range(20)]        # same (family,seed) -> same multiset
    shifted = [[dict(r, magnitude={"pct": r["magnitude"]["pct"] + 10}) for r in s] for s in att]
    check("benign/attack pair at the same seed reads MATCHED-EXACT (same multiset, only timing differs)",
          B2.marginal_check(ben, att)["status"] == "MATCHED-EXACT")
    check("a shifted attack magnitude reads UNDETERMINED (marginals measured, not assumed)",
          B2.marginal_check(ben, shifted)["status"] == "UNDETERMINED")

    # ---- Holm-Bonferroni BOTH WAYS
    ok_all, _ = B2._holm_ok([0.9, 0.8, 0.5])
    rej_one, _ = B2._holm_ok([0.9, 0.8, 0.0001])
    check("Holm accepts when every zone agrees; rejects when one zone diverges (both ways)",
          ok_all is True and rej_one is False)

    # ---- held-out family E is premise-valid and matched-marginal (bar #3 is runnable)
    e_ben = [B2.gen("E", 200 + i, "benign") for i in range(10)]
    e_att = [B2.gen("E", 200 + i, "attack") for i in range(10)]
    check("held-out family E: in-bounds through the real gateway AND matched-marginal (bar #3 valid)",
          B.permits(B2.gen("E", 7, "attack"))["all_permit"] is True
          and B2.marginal_check(e_ben, e_att)["status"] == "MATCHED-EXACT")


def weights_outcome_check():
    """Tie the shipped state to the verdict: no weights -> witness UNKNOWN (never a
    silent ABSENT). If weights ARE shipped they must carry the v2 prereg id (the
    evaluated model is the shipped model)."""
    w = snn.load_weights()
    if w is None:
        s = snn.pattern_anomaly_state(ledger=os.path.join(tempfile.mkdtemp(), "none.jsonl"))
        check("no shipped weights -> witness UNKNOWN (never ABSENT: absent witness is not 'all clear')",
              s["state"] == gg.UNKNOWN)
    else:
        check("shipped weights carry the v2 prereg id (evaluated model == shipped model)",
              "PREREG_v2" in str(w.get("prereg_id", "")) or "v2" in str(w.get("prereg_id", "")))


def main():
    d, keys, fpr, signers, interlocks, policy = t.setup()
    boundary_checks(keys, fpr, signers, interlocks, policy)
    weights_outcome_check()
    if not _HAVE_NP:
        print("\nGS2: apparatus checks NOT RUN -- numpy absent; the boundary checks above still ran.")
        print("GS2: %d passed, %d failed" % (P[0], F[0]))
        return 1 if F[0] else 0
    try:
        apparatus_checks()
    except ImportError as e:
        print("  .... apparatus gateway checks NOT RUN -- %s (needs cryptography)" % e)
    print("\nGS2: %d passed, %d failed" % (P[0], F[0]))
    return 1 if F[0] else 0


if __name__ == "__main__":
    sys.exit(main())
