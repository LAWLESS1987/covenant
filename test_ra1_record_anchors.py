#!/usr/bin/env python3
"""RA1 -- the travelling record anchors, measured on every sweep (A477, 2026-11-23).

WHY. ops/RECORD_ANCHORS.json anchors the first 200 lines of five ledgers so a stranger can check that their history was
not rewritten. On 2026-11-23 all five had drifted and nothing had said so: the sweep ran only the sentinels' offline
self-test, test_g6 handed the sentinel an empty anchor dict, and nothing scheduled the live check. This suite runs
tools/anchor_drift.py against the tree and holds every drift to ops/ANCHOR_DRIFT_ACK.json: a drift is RECORDED there,
never ACCEPTED (accepting is the operator re-anchoring). Driven both ways.

    python test_ra1_record_anchors.py
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import anchor_drift as AD  # noqa: E402

n_fail = n_total = 0


def check(name, ok, detail=""):
    global n_fail, n_total
    n_total += 1
    print(("ok   " if ok else "FAIL ") + name + (("  -- %s" % (detail,)) if detail else ""))
    if not ok:
        n_fail += 1


# A ledger whose head CANNOT hold an anchor, by how it is written (measured 2026-11-23: ops/SELF_EVAL.md puts each new
# round at the top and drops old ones, so its first 200 lines change every round on a node that runs it). Its row may
# say head_anchor_cannot_hold, and then RA1 does not compare its head; no other ledger may say so. This narrows RA1 only:
# covenant_sentinels still alerts on it, and a retention rule that fits it is the operator's decision.
PREPENDING = {"ops/SELF_EVAL.md"}


def problems(measured, ack):
    """Every way MEASURED disagrees with ACK. Empty means the record is honest about the drift."""
    out = []
    for rel, r in measured.items():
        a = ack.get(rel)
        if a and a.get("head_anchor_cannot_hold"):
            if rel not in PREPENDING:
                out.append("%s: only a ledger measured as prepending may say its head anchor cannot hold" % rel)
                continue
            if r["state"] == "MISSING":
                out.append("%s: anchored ledger is missing" % rel)
            if a.get("accepted") is not False:
                out.append("%s: a drift row cannot accept a drift (accepted must be false)" % rel)
            continue
        if r["state"] == "MISSING":
            out.append("%s: anchored ledger is missing" % rel)
        elif r["state"] == "MATCH":
            if a:
                out.append("%s: matches its anchor again; its drift row is stale" % rel)
        elif not a:
            out.append("%s: drifted (%s) and no row in ops/ANCHOR_DRIFT_ACK.json names it" % (rel, r["state"]))
        else:
            if a.get("current_prefix_sha256") != r["current_prefix_sha256"]:
                out.append("%s: its head moved again since the row was written" % rel)
            if a.get("accepted") is not False:
                out.append("%s: a drift row cannot accept a drift (accepted must be false; re-anchoring is the "
                           "operator's act)" % rel)
            if not r["state"].startswith("DRIFTED") and a.get("class") != r["state"]:
                out.append("%s: row says %s, measured %s" % (rel, a.get("class"), r["state"]))
    for rel in ack:
        if rel not in measured:
            out.append("%s: a drift row for a ledger that is not anchored" % rel)
    return out


with open(os.path.join(HERE, "ops", "RECORD_ANCHORS.json"), encoding="utf-8") as fh:
    anchors = json.load(fh)
ack = AD.load_ack()
measured = AD.measure(anchors=anchors, hint={k: v.get("anchored_from_commit") for k, v in ack.items()})
for rel, r in measured.items():
    print("     %-22s %s" % (rel, r["state"]))

# RA1.1 the real tree: every drift is recorded, exactly.
bad = problems(measured, ack)
check("RA1.1 every anchored ledger matches its anchor or its drift is recorded exactly (not accepted)", not bad, bad)

# RA1.2 every ledger the sentinel guards is anchored (a ledger dropped from the anchors would escape RA1).
import covenant_sentinels as S  # noqa: E402
missing = [l for l in S.GUARDED_LEDGERS if l not in (anchors.get("ledgers") or {})]
check("RA1.2 every guarded ledger has an anchor", not missing, missing)

# ---- both ways, on copies of the real measurement (nothing on disk is touched)
some = next((k for k, v in measured.items() if v["state"] != "MATCH"), None)
if some:
    a2 = copy.deepcopy(ack)
    a2.pop(some, None)
    check("RA1.3 a drift with no row is caught", any("no row" in p for p in problems(measured, a2)), some)
    m2 = copy.deepcopy(measured)
    m2[some]["current_prefix_sha256"] = "0" * 64
    check("RA1.4 a head that moved again (new hash) is caught", any("moved again" in p for p in problems(m2, ack)))
    a3 = copy.deepcopy(ack)
    a3.setdefault(some, {})["accepted"] = True
    check("RA1.5 a row that tries to accept the drift is caught", any("cannot accept" in p for p in problems(measured, a3)))
    m3 = copy.deepcopy(measured)
    # A class different from the ROW's (not from the measurement's: in a copy without git, as the sweep stages it, the
    # measured state is "DRIFTED (no git here)" and a class taken from it would equal the row's -- found 2026-11-23).
    m3[some]["state"] = "REWRITTEN" if ack.get(some, {}).get("class") != "REWRITTEN" else "INSERTION"
    check("RA1.6 a row whose class no longer matches the measurement is caught",
          any("measured" in p for p in problems(m3, ack)))
    m4 = copy.deepcopy(measured)
    m4[some]["state"] = "MATCH"
    check("RA1.7 a row for a ledger that matches again is stale and caught", any("stale" in p for p in problems(m4, ack)))
else:
    check("RA1.3-7 not driven: no ledger drifts today (drive them against a fixture before relying on this)", True)

# RA1.9 the prepending exemption, both ways: it holds for the measured ledger, and only for it.
pre = next(iter(PREPENDING))
if pre in measured and pre in ack:
    m5 = copy.deepcopy(measured)
    m5[pre]["current_prefix_sha256"] = "1" * 64                  # a new round on top
    check("RA1.9 the prepending ledger's head moving is not a failure while its row says the anchor cannot hold",
          not [p for p in problems(m5, ack) if p.startswith(pre)], pre)
    other = next(k for k in ack if k != pre)
    a6 = copy.deepcopy(ack)
    a6[other]["head_anchor_cannot_hold"] = True
    check("RA1.9b any other ledger claiming that exemption is caught",
          any("only a ledger measured as prepending" in p for p in problems(measured, a6)), other)

# RA1.8 the classifier itself, both ways, on bytes (no git needed).
old = [b"%d" % i for i in range(10)]
check("RA1.8 insertion keeps every anchored line in order",
      AD.kept_in_order(old, old[:4] + [b"new"] + old[4:]) == len(old))
check("RA1.8b one anchored line changed is not insertion",
      AD.kept_in_order(old, old[:4] + [b"4 rewritten"] + old[5:]) < len(old))

print("\nRA1: %d/%d passed" % (n_total - n_fail, n_total))
sys.exit(1 if n_fail else 0)
