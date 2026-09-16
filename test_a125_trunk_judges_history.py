#!/usr/bin/env python3
"""test_a125_trunk_judges_history.py -- A125: the trunk judges history.

THE CONTRADICTION. Block validity on sync depended on a model that retrains
every night. A consensus rule has to be the same on every node and the same
tomorrow as today; a nightly-retrained model is neither, so two nodes on
different retrains technically hold different chains. A116 is the bill: "There
can be no mutual benefit without a little faith" -- a sentence alleging nothing
-- drifted +2.34 to +2.52 across a hand-set line of 2.4, and no new node could
get past block 12 for days.

THE SPLIT, in the operator's words: "as long as the retrain builds on the core
like the mycelium branching it can always be trimmed."

    TRUNK   fallback_core.json -- pinned, committed, identical on every node,
            never written by the nightly loop. Judges HISTORY.
    BRANCH  fallback_model.json -- retrained nightly, FULL force over every
            NEW transaction. Judges the present.

WHAT THIS SUITE PINS, and the third one is the one that matters most:

  T*  the trunk exists, loads, and is a REAL judge -- it still convicts plain
      theft. A trunk that cleared everything would "fix" sync by removing the
      gate, which is the fix-to-green A118 forbids.
  H*  a branch-only conviction does not refuse settled history, and a
      conviction the TRUNK shares still does.
  N*  ADMISSION IS UNTOUCHED. A new transaction is judged by the branch at
      full strength. If this suite ever goes green while admission has been
      relaxed, the split has become an excuse rather than a design.
  F*  it fails CLOSED: no trunk, unreadable trunk, or any error relaxes
      nothing at all.

Pure: no network, no node started, no database.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_judge_fallback as FB                          # noqa: E402
from covenant_judge_fallback import FallbackModel             # noqa: E402

BENIGN = "There can be no mutual benefit without a little faith."
THEFT = ("I will take his wallet while he sleeps and keep the money for "
         "myself, and he will never know it was me.")

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label,
                        "" if ok else "  -- " + str(detail)[:300]), flush=True)


def reset_core_cache():
    FB._CORE_CACHE.clear()


def main():
    print("A125 -- the trunk judges history, the branch judges new work\n")

    # ---- T: the trunk is real ---------------------------------------------
    check("A125.T1 the trunk file exists and is committed alongside the branch",
          os.path.isfile(FB.CORE_PATH), FB.CORE_PATH)

    reset_core_cache()
    trunk = FB.core_model()
    check("A125.T2 the trunk loads as a judge", trunk is not None)
    if trunk is None:
        print("\nA125: %d/%d passed" % (sum(results), len(results)))
        return 1

    # THE ONE THAT STOPS THIS BEING A BACK DOOR. A trunk that convicts nothing
    # would make every branch conviction "branch-only" and quietly retire the
    # gate on the sync path altogether.
    check("A125.T3 the trunk is a REAL judge -- it still convicts plain theft. "
          "A trunk that cleared everything would retire the gate on sync and "
          "call it a fix",
          FB.core_convicts({"message": THEFT}) is True,
          FB.core_convicts({"message": THEFT}))

    check("A125.T4 the trunk clears the sentence that made the chain "
          "unjoinable (A116), so history is not hostage to a drift",
          FB.core_convicts({"message": BENIGN}) is False)

    # The trunk must never be the file the nightly loop writes.
    check("A125.T5 the trunk is NOT the path the nightly retrain writes -- "
          "otherwise it drifts with the branch and pins nothing",
          os.path.abspath(FB.CORE_PATH) != os.path.abspath(FB.MODEL_PATH),
          (FB.CORE_PATH, FB.MODEL_PATH))

    # ---- F: fails closed ---------------------------------------------------
    saved = FB.CORE_PATH
    try:
        FB.CORE_PATH = os.path.join(HERE, "fallback_core__absent__.json")
        reset_core_cache()
        check("A125.F1 NO TRUNK relaxes nothing: core_convicts returns None, "
              "so the caller keeps today's stricter behaviour",
              FB.core_convicts({"message": BENIGN}) is None)

        bad = os.path.join(HERE, "_a125_bad_core.json")
        io.open(bad, "w", encoding="utf-8").write("{not json at all")
        FB.CORE_PATH = bad
        reset_core_cache()
        check("A125.F2 an UNREADABLE trunk relaxes nothing either",
              FB.core_convicts({"message": BENIGN}) is None)
        os.remove(bad)
    finally:
        FB.CORE_PATH = saved
        reset_core_cache()

    # ---- H: history vs the present ----------------------------------------
    # The wiring in validate_block is asserted against the SOURCE, because
    # standing up a node here would make this suite need a chain. What the
    # source must show: the branch-only waiver is reachable only under `sync`,
    # and only when the trunk returns exactly False.
    src = io.open(os.path.join(HERE, "covenant_unified_v8.py"),
                  encoding="utf-8").read()
    i = src.find("def validate_block")
    # The whole function, not a guessed window: an early draft used 6000 chars
    # and missed the summary block entirely, reporting a defect that was not
    # there. A check that reads the wrong span is measuring its own guess.
    j = src.find("\n# ---", i + 10)
    body = src[i:j if j > i else i + 12000] if i >= 0 else ""

    # JOIN IMPLICIT STRING CONCATENATION BEFORE SEARCHING. Python source wraps
    # a long literal as  "BY THE BRANCH "\n    "ONLY ..."  so a plain grep for
    # the sentence the program actually prints reports it ABSENT. The first
    # draft of A125.H3 did exactly that and failed against correct code -- which
    # is A74's defect, a check reading source TEXT rather than what the source
    # MEANS, reproduced here by the person who had just written A74 up. Kept
    # with the reason attached rather than quietly patched.
    joined = re.sub(r'"\s*\n\s*"', "", body)
    check("A125.H1 the branch-only waiver lives inside validate_block and is "
          "gated on `sync`", "if sync:" in body and "core_convicts" in body)
    check("A125.H2 it waives ONLY on an explicit False -- `is False`, never a "
          "truthiness test, so None (no trunk) can never relax anything",
          "trunk is False" in body, "guard not found as written")
    check("A125.H3 a branch-only waiver is never folded into A98's "
          "'NOTHING WAS ALLEGED' summary, which would be the log lying about "
          "what was waived",
          "BY THE BRANCH ONLY" in joined and "waived_branch" in body)
    check("A125.H4 it is announced on its own anomaly key and its own line, "
          "never silently",
          "sync_branch_only_conviction" in src
          and "SYNC WAIVED BRANCH-ONLY CONVICTION" in src)

    # ---- N: ADMISSION IS UNTOUCHED ----------------------------------------
    # The whole split is only honest if the branch still governs new work at
    # full strength. Asserted two ways: the waiver is unreachable off the sync
    # path, and the branch itself still convicts.
    after = body[body.find("if sync:"):] if "if sync:" in body else ""
    check("A125.N1 the trunk is consulted ONLY on the sync path -- there is no "
          "second, ungated call that could reach admission",
          body.count("core_convicts") == 1, body.count("core_convicts"))

    branch = FallbackModel.load(FB.MODEL_PATH)
    check("A125.N2 the BRANCH still convicts plain theft at full strength, so "
          "new transactions lost nothing",
          branch.verdict(THEFT)[0] == "violates", branch.verdict(THEFT)[0])

    ok = sum(1 for r in results if r)
    print("\n  Trunk %s" % FB.CORE_PATH)
    print("  Branch %s" % FB.MODEL_PATH)
    print("  To trim the branch back to the trunk: copy the trunk over the "
          "branch and retrain from there.")
    print("\nA125: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
