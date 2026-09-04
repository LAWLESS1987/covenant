#!/usr/bin/env python3
"""covenant_nightly.py -- one unattended pass of the covenant's own learning.

WHY (asked 2026-09-04: "begin having it recursive learning ... study all
philosophy and religious texts and teachings ... improve repeatedly keeping
green and synced ... but run most through covenant to be efficient")

  Three steps, in this order, because each one feeds the next:

    1. STUDY    turn a batch of unused precepts from the moral texts into
                transactions and judge them blind (covenant_study.py). Only
                agreements enter the ledger.
    2. DISTILL  write and blind-judge fresh cases, then train a candidate on
                the whole ledger and promote it ONLY if it clears nothing it
                should not, gets no vaguer and holds no legitimate transfer
                (covenant_distill.py).
    3. REPORT   append what happened to ops/NIGHTLY.md, including the exam
                line, so a person reading one file can see whether the judge
                is getting better or just getting bigger.

  It writes no code, changes no policy, restarts nothing and pushes nothing.
  A loop that could edit its own constraints would not have any
  (CONSTITUTION II.3), and a loop that could push could hide what it did.

RUN
  pythonw ops\\hidden_task.py covenant_nightly.py     (what the task does)
  python covenant_nightly.py --study 12 --cycle 4     (by hand)
EXIT  0 ran   1 a step failed (the report says which)
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPORT = os.path.join(HERE, "ops", "NIGHTLY.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", type=int, default=12, help="precepts to turn into cases")
    ap.add_argument("--cycle", type=int, default=4, help="generated cases per category")
    a = ap.parse_args()
    lines, rc = [], 0
    t0 = time.time()

    def say(s=""):
        print(s)
        lines.append(str(s))

    say("## %s  nightly pass" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    try:
        import covenant_study as S
        kept, rej = S.generate(a.study, say=say)
        say("study: +%d kept, %d rejected" % (kept, rej))
    except Exception as e:                                       # noqa: BLE001
        rc = 1
        say("study FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))

    try:
        import covenant_distill as X
        X.cycle(a.cycle, say=say)
        st = X.examine(__import__("covenant_judge_fallback").FallbackModel.load())
        say(X.thresholds_line(st))
        rows = X.load_verdicts()
        nv = sum(1 for r in rows if r.get("violates"))
        say("ledger: %d verdict(s), %d violates / %d clean (%.0f%% violates -- a corpus that "
            "drifts to one label makes the student vaguer, not safer)"
            % (len(rows), nv, len(rows) - nv, 100.0 * nv / max(1, len(rows))))
        say("exam: decides %d/%d, %d wrong, %d abstain, %d false clean, %d false hold"
            % (st["total"]["agree"], st["total"]["n"], st["total"]["wrong"],
               st["total"]["abstain"], st["total"]["false_clean"], st["total"]["false_hold"]))
    except Exception as e:                                       # noqa: BLE001
        rc = 1
        say("distill FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))

    say("took %.0f minutes" % ((time.time() - t0) / 60.0))
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    new = not os.path.exists(REPORT)
    with io.open(REPORT, "a", encoding="utf-8") as fh:
        if new:
            fh.write("# The covenant's nightly learning\n"
                     "# One block per pass: what it read, what it was taught, and what the\n"
                     "# exam said afterwards. Append-only, including the passes that failed.\n\n")
        fh.write("\n".join(lines) + "\n\n")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
