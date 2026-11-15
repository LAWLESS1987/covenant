#!/usr/bin/env python3
"""tools/hands_content_measure.py -- what this tree's own quorum does to Tetsu's practice when the judge of his hands is
given one sentence about each act, and when it is given the content. (A428, 2026-11-14)

WHY. covenant_tetsu_hands.JUDGE_SEES_CONTENT is built and off, and the reason is a measurement. A number copied into
prose rots, and the students are retrained, so this is the measurement, re-runnable: the day it prints "passed 10" on
both lines is the day the reason is gone.

WHAT IT DOES. The practice curriculum's ten reference solutions (read from test_pp1_tetsu_practice.py, the part above
its first check) go through covenant_tetsu_practice.attempt -- his hands' WRITE and RUN -- with the REAL gate
(covenant_gate_proxy.default_sentinel, as this tree builds it: its policy file if it has one, else the seats a clone
has), once with the switch off and once with it on. A scratch workshop and a scratch hands ledger; the judges' own
ledgers are rebound to a scratch folder for the run, so nothing measured here reaches ops/judged_by_student.jsonl or a
training ledger.

WHAT IT CANNOT TELL YOU. What a real model's own files would get: these are ten reference files, not his. Another
node's quorum: it measures the tree it is run in. Whether a conviction is right: it counts them.

    python tools/hands_content_measure.py

Exit 0 when it measured, 2 when it could not. LICENCE: public domain.
"""
import collections
import contextlib
import io
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
MARK = 'check("PP1.1a'


def main():
    for k in ("COVENANT_SILENCE_IS_NOT_DISSENT", "COVENANT_RELAX_VALUELESS_FOR"):
        os.environ.pop(k, None)
    import covenant_tetsu_hands as HANDS
    import covenant_tetsu_practice as PR
    import covenant_gate_proxy as GP
    import covenant_judge_defer as JD
    with open(os.path.join(HERE, "test_pp1_tetsu_practice.py"), encoding="utf-8") as fh:
        src = fh.read()
    if MARK not in src:
        print("cannot measure: test_pp1_tetsu_practice.py no longer has %r, above which its reference solutions are" % MARK)
        return 2
    ns = {"__name__": "pp1_reference_solutions", "__file__": os.path.join(HERE, "test_pp1_tetsu_practice.py")}
    with contextlib.redirect_stdout(io.StringIO()):          # the suite's own banner line is not this tool's output
        exec(compile(src.split(MARK, 1)[0], "test_pp1_tetsu_practice.py (above its first check)", "exec"), ns)
    ref = ns["REF"]
    scratch = tempfile.mkdtemp(prefix="hands_content_measure_")
    JD.AUDIT_PATH, JD.VERDICTS, JD.LIVE_VERDICTS = (os.path.join(scratch, n) for n in
                                                   ("judged_by_student.jsonl", "verdicts.jsonl", "verdicts_live.jsonl"))
    judge = GP.default_sentinel().judge
    print("the gate measured: %s" % getattr(judge, "judge_id", "?"))
    print("providers: %s" % (os.environ.get("COVENANT_JUDGE_PROVIDERS") or GP.NODE_NO_POLICY_PROVIDERS + " (no policy file, nothing exported)"))
    shipped = HANDS.JUDGE_SEES_CONTENT
    try:
        for on in (False, True):
            HANDS.JUDGE_SEES_CONTENT = on
            ws = tempfile.mkdtemp(prefix="ws_", dir=scratch)
            hled = os.path.join(tempfile.mkdtemp(prefix="hl_", dir=scratch), "hands.jsonl")
            passed, stopped = 0, []
            for t in PR.CURRICULUM:
                res, stop = PR.attempt(t, ref[t["id"]].strip() + "\n", gate=None, workshop=ws, hands_ledger=hled)
                passed += bool(res["passed"] is not None and res["passed"] == res["total"])
                if stop:
                    stopped.append("%s (%s)" % (t["id"], "write" if "refused the write" in stop else "run"))
            states = collections.Counter("%s %s" % (r.get("kind"), (r.get("gate") or {}).get("state")) for r in HANDS._rows(hled))
            print("\nJUDGE_SEES_CONTENT = %s%s" % (on, "   (as shipped)" if on == shipped else ""))
            print("  tasks: %d   passed %d   stopped by the gate %d%s"
                  % (len(PR.CURRICULUM), passed, len(stopped), (": " + ", ".join(stopped)) if stopped else ""))
            print("  acts put to the gate: %s" % ", ".join("%s x%d" % kv for kv in sorted(states.items())))
    finally:
        HANDS.JUDGE_SEES_CONTENT = shipped
    return 0


if __name__ == "__main__":
    sys.exit(main())
