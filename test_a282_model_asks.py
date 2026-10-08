#!/usr/bin/env python3
"""test_a282_model_asks.py -- A282: every real ask of Tetsu's model leaves one line, answered or not.

WHY. 2026-10-06, readiness() read PASS all morning while every ask through Tetsu's door came back 503 (A269);
the core's door returns that 503 and records nothing, so the road could not see it. covenant_model.ask now
writes one line per real ask to ops/model_asks.jsonl, which the highway's tetsu_asks_failing reads.

WHAT IT PINS (the real ask(); urlopen and start() are stand-ins, nothing reaches 8081).
  Q1  an ask the server does not answer is recorded ok False with the error, and still raises as before
  Q2  an ask that answers is recorded ok True with its time
  Q3  a test program never writes the LIVE ledger (A272's lesson); any other program does
"""
import io
import json
import os
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_model as M  # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:300]), flush=True)


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def rows(path):
    try:
        return [json.loads(x) for x in open(path, encoding="utf-8") if x.strip()]
    except FileNotFoundError:
        return []


def main():
    print("A282 -- every real ask leaves a line")
    stub = os.environ.pop("COVENANT_MODEL_STUB", None)
    real = (M.ASKS, M._REAL_ASKS, M.start, M._watch_idle, urllib.request.urlopen, sys.argv[0])
    tmp = tempfile.mkdtemp(prefix="a282_")
    try:
        M.start = lambda say=print: (True, "up")
        M._watch_idle = lambda: None
        M.ASKS = os.path.join(tmp, "asks.jsonl")

        def refuse(req, timeout=None):
            raise OSError("HTTP Error 500: Context size has been exceeded")
        urllib.request.urlopen = refuse
        raised = False
        try:
            M.ask([{"role": "user", "content": "hello"}])
        except OSError:
            raised = True
        r = rows(M.ASKS)
        check("Q1 an unanswered ask is recorded ok False with the error, and still raises",
              raised and len(r) == 1 and r[0]["ok"] is False and "Context size" in r[0]["error"], r)
        urllib.request.urlopen = lambda req, timeout=None: _Resp(b'{"choices":[{"message":{"content":"ok"}}],"usage":{}}')
        text, _meta = M.ask([{"role": "user", "content": "hello"}])
        r = rows(M.ASKS)
        check("Q2 an answered ask is recorded ok True with its time", text == "ok" and len(r) == 2 and r[1]["ok"] is True
              and isinstance(r[1]["ms"], int), r)
        live = os.path.join(tmp, "live.jsonl")
        M.ASKS = M._REAL_ASKS = live
        sys.argv[0] = "test_something.py"
        M.ask([{"role": "user", "content": "hello"}])
        n_test = len(rows(live))
        sys.argv[0] = "run_node.py"
        M.ask([{"role": "user", "content": "hello"}])
        check("Q3 a test program never writes the live ledger; a node does", n_test == 0 and len(rows(live)) == 1,
              (n_test, rows(live)))
    finally:
        M.ASKS, M._REAL_ASKS, M.start, M._watch_idle, urllib.request.urlopen, sys.argv[0] = real
        if stub is not None:
            os.environ["COVENANT_MODEL_STUB"] = stub

    ok = sum(results)
    print("\nA282: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
