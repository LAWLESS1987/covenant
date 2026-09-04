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
    3. VERIFY   run the launch gates and the suites that cover what this pass
                just changed, and record the verdict. A loop that improves the
                judge every night and never checks whether it broke anything
                is not improvement, it is drift with a changelog. If the pass
                turns something red, the block says so on its first line.
    4. REPORT   append what happened to ops/NIGHTLY.md, including the exam
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


# The suites that cover what a pass CHANGES: the student, the seat, the
# assembled gate, and the two the ledger feeds. Not the whole sweep -- that
# needs the chain stopped for its ports, and a nightly job must not take the
# chain down to prove it is healthy.
GREEN_SUITES = ["test_f1_fallback_silence.py", "test_f2_distill_loop.py",
                "test_f3_gate_end_to_end.py", "covenant_quiet.py"]


def verify_green(say):
    """Gates plus the suites this pass can break. Returns True when green."""
    import subprocess
    import covenant_quiet as Q
    ok = True
    r = Q.run([sys.executable, "launch_check.py"], cwd=HERE, capture_output=True,
              text=True, timeout=900)
    tail = [x for x in (r.stdout or "").splitlines() if "PASS" in x and "BLOCKED" in x]
    gates = tail[-1].strip() if tail else "launch_check printed no summary"
    if "0 BLOCKED" not in gates or "0 UNKNOWN" not in gates:
        ok = False
    say("gates: %s" % gates)
    for suite in GREEN_SUITES:
        try:
            r = Q.run([sys.executable, suite], cwd=HERE, capture_output=True,
                      text=True, timeout=900)
        except Exception as e:                                   # noqa: BLE001
            say("  %-32s ERROR %s" % (suite, e)); ok = False; continue
        line = ""
        for x in (r.stdout or "").splitlines():
            if "passed" in x.lower():
                line = x.strip()
        if r.returncode != 0 or not line:
            ok = False
        say("  %-32s %s" % (suite, line or "NO TALLY (rc=%s)" % r.returncode))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", type=int, default=12, help="precepts to turn into cases")
    ap.add_argument("--cycle", type=int, default=4, help="generated cases per category")
    ap.add_argument("--passes", type=int, default=1, help="repeat the whole pass N times")
    ap.add_argument("--no-verify", action="store_true", help="skip the green check (not advised)")
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

    green = None
    if not a.no_verify:
        try:
            green = verify_green(say)
        except Exception as e:                                   # noqa: BLE001
            rc = 1
            green = False
            say("verify FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))
        if not green:
            rc = 1
            lines.insert(1, "**NOT GREEN after this pass -- read the gates and suites below.**")
        say("green: %s" % ("yes" if green else "NO"))
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


def repeat():
    """--passes N: run main() N times. Each pass writes its own block, so a
    night of passes reads as a night of passes rather than one long one."""
    import argparse as _a
    ap = _a.ArgumentParser(add_help=False)
    ap.add_argument("--passes", type=int, default=1)
    known, _rest = ap.parse_known_args()
    n = max(1, known.passes)
    if n == 1:
        return main()
    worst = 0
    argv = [x for x in sys.argv[1:]]
    while "--passes" in argv:
        i = argv.index("--passes")
        del argv[i:i + 2]
    for i in range(n):
        sys.argv = [sys.argv[0]] + argv
        print("=== pass %d/%d" % (i + 1, n))
        worst = max(worst, main())
        if os.path.exists(os.path.join(HERE, "ops", "STOP_LEARNING")):
            print("ops/STOP_LEARNING is present -- stopping after %d pass(es)" % (i + 1))
            break
    return worst


if __name__ == "__main__":
    raise SystemExit(repeat())
