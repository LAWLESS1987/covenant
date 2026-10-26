#!/usr/bin/env python3
"""RN1 -- record-non-executions, from HF thread 180541 (u/neo_konsi: "a log holding only successful executions
lies"), adopted 2026-10-26. Pins that the HANDS act executor records a REFUSED act as a row, not only the
successes, driven BOTH ways (rule 8): a gate-refused WRITE leaves a `refused` row and writes nothing; a cleared
WRITE leaves a success row beside it -- so the ledger carries the non-executions too, and a regression that
dropped them would turn this red.

Scope (named, rule 9): this pins HANDS, the highest-stakes act executor (writes/runs). The other doors already
record their non-executions and are covered elsewhere -- the reasoning leg's rejected consult by LG1.35; the
Moltbook door's NOT-sent sends by M6; the node gate's holds in ops/verdicts.jsonl. Offline, stub gate, temp
dirs; no node. Stdlib only."""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_tetsu_hands as H

fails = []


def ok(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -- " + str(detail)[:160]))
    if not cond:
        fails.append(name)


d = tempfile.mkdtemp()
ws, led = os.path.join(d, "ws"), os.path.join(d, "hands.jsonl")
os.makedirs(ws, exist_ok=True)

# --- a gate-refused WRITE: recorded as refused, and NOTHING written (a non-execution that still leaves a record)
h1, data1, _r1 = H.act("HANDS WRITE probe.py\nprint('x')\n",
                       gate=lambda line: ("violates", "denied by test"), workshop=ws, ledger=led, say=lambda *a: None)
rows1 = [json.loads(x) for x in open(led, encoding="utf-8")] if os.path.exists(led) else []
ok("RN1.1 a gate-refused WRITE is RECORDED (refused=True, with the reason), not dropped",
   h1 and any(r.get("refused") and r.get("kind") == "write" and r.get("gate") for r in rows1), (data1, rows1))
ok("RN1.2 ...and the refused WRITE wrote nothing (a non-execution that still left a record)",
   not os.path.exists(os.path.join(ws, "probe.py")), os.listdir(ws))

# --- a cleared WRITE: recorded as a success (no 'refused'), beside the refusal -- the log carries BOTH
n_before = len(rows1)
h2, _data2, _r2 = H.act("HANDS WRITE ok.py\nprint('y')\n",
                        gate=lambda line: ("clean", ""), workshop=ws, ledger=led, say=lambda *a: None)
rows2 = [json.loads(x) for x in open(led, encoding="utf-8")]
ok("RN1.3 a cleared WRITE is recorded as a success (no 'refused') beside the refusal -- both are in the log",
   h2 and len(rows2) == n_before + 1 and any(r.get("kind") == "write" and not r.get("refused") for r in rows2)
   and os.path.exists(os.path.join(ws, "ok.py")), rows2)

# --- a RUN the screen refuses (a disallowed import) is recorded too, as a non-execution
h3, data3, _r3 = H.act("HANDS WRITE bad.py\nimport socket\nsocket.socket()\n",
                       gate=lambda line: ("clean", ""), workshop=ws, ledger=led, say=lambda *a: None)
h4, data4, _r4 = H.act("HANDS RUN bad.py",
                       gate=lambda line: ("clean", ""), workshop=ws, ledger=led, say=lambda *a: None)
rows3 = [json.loads(x) for x in open(led, encoding="utf-8")]
ran_row = [r for r in rows3 if r.get("kind") == "run" and r.get("target") == "bad.py"]
ok("RN1.4 a RUN the screen refuses is recorded (its outcome is in the log, not dropped)",
   h4 and bool(ran_row) and ran_row[-1].get("ok") is False, (data4, ran_row[-1] if ran_row else None))

print("\nRN1: %d/4 passed" % (4 - len(fails)))
raise SystemExit(1 if fails else 0)
