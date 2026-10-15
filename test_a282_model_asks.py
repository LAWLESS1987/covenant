#!/usr/bin/env python3
"""test_a282_model_asks.py -- A282: every real ask of Tetsu's model leaves one line, answered or not.

WHY. 2026-10-06, readiness() read PASS all morning while every ask through Tetsu's door came back 503 (A269);
the core's door returns that 503 and records nothing, so the road could not see it. covenant_model.ask now
writes one line per real ask to ops/model_asks.jsonl, which the highway's tetsu_asks_failing reads.

WHAT IT PINS (the real ask(); urlopen and start() are stand-ins, nothing reaches 8081).
  Q1  an ask the server does not answer is recorded ok False with the error, and still raises as before
  Q2  an ask that answers is recorded ok True with its time
  Q3  a test program never writes the LIVE ledger (A272's lesson); any other program does
  Q4-Q7 (A351, 2026-10-14) an answer's own timings ride its line after the four fields it always had; an answer
      without them is the line it always was; measured_rate is the median over answered rows that carry the
      speed, past the short ones, or None under three
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
    real_used = M.USED
    tmp = tempfile.mkdtemp(prefix="a282_")
    try:
        M.start = lambda say=print: (True, "up")
        M._watch_idle = lambda: None
        M.ASKS = os.path.join(tmp, "asks.jsonl")
        # A348b (2026-10-14): ask() also marks the shared last-use stamp, and Q3 asks as run_node.py -- measured,
        # that touched the tree's ops/model_last_use.stamp. Never the live one: it would hold the model up.
        M.USED = os.path.join(tmp, "last_use.stamp")

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
        # A351: the server's own speeds ride the line. The timings below carry llama-server's field names; the writing
        # speed is the 6.27 a second measured 2026-10-14, the reading numbers A273's cold read (2,902 in 49.6 s).
        M.ASKS = os.path.join(tmp, "asks_a351.jsonl")
        timed = {"choices": [{"message": {"content": "ok"}}], "usage": {"completion_tokens": 400},
                 "timings": {"prompt_n": 2902, "prompt_ms": 49600.0, "prompt_per_second": 58.5,
                             "predicted_n": 400, "predicted_ms": 63796.0, "predicted_per_second": 6.27}}
        urllib.request.urlopen = lambda req, timeout=None: _Resp(json.dumps(timed).encode("utf-8"))
        M.ask([{"role": "user", "content": "hello"}])
        r4 = rows(M.ASKS)
        check("Q4 an answer's own timings ride its line, after the four fields it always had",
              len(r4) == 1 and list(r4[0])[:4] == ["at", "ok", "ms", "error"] and r4[0]["ok"] is True
              and {k: r4[0].get(k) for k in ("gen_n", "gen_tps", "prompt_n", "prompt_tps")}
              == {"gen_n": 400, "gen_tps": 6.27, "prompt_n": 2902, "prompt_tps": 58.5}, r4)
        urllib.request.urlopen = lambda req, timeout=None: _Resp(b'{"choices":[{"message":{"content":"ok"}}],"usage":{}}')
        M.ask([{"role": "user", "content": "hello"}])
        partial = {"choices": [{"message": {"content": "ok"}}], "timings": {"predicted_n": 500, "predicted_ms": 100000.0}}
        urllib.request.urlopen = lambda req, timeout=None: _Resp(json.dumps(partial).encode("utf-8"))
        M.ask([{"role": "user", "content": "hello"}])
        no_n = {"choices": [{"message": {"content": "ok"}}], "usage": {"completion_tokens": 120},
                "timings": {"predicted_per_second": 6.0}}
        urllib.request.urlopen = lambda req, timeout=None: _Resp(json.dumps(no_n).encode("utf-8"))
        M.ask([{"role": "user", "content": "hello"}])
        r5 = rows(M.ASKS)
        extra = [{k: v for k, v in x.items() if k not in ("at", "ok", "ms", "error")} for x in r5]
        check("Q5 an answer without timings is the line it always was; a rate left out beside its count and time is "
              "worked from them, a part left out stays out, and without predicted_n the tokens written are usage's count",
              len(r5) == 4 and list(r5[1]) == ["at", "ok", "ms", "error"]
              and extra[2:] == [{"gen_n": 500, "gen_tps": 5.0}, {"gen_n": 120, "gen_tps": 6.0}], r5)
        led = os.path.join(tmp, "ledger_a351.jsonl")
        with open(led, "w", encoding="utf-8") as fh:
            for tps in (9.0, 6.0, 7.0, 5.0):
                fh.write(json.dumps({"at": 1, "ok": True, "ms": 1, "error": "", "gen_n": 200, "gen_tps": tps,
                                     "prompt_n": 3000, "prompt_tps": tps * 10}) + "\n")
            fh.write(json.dumps({"at": 1, "ok": False, "ms": 1, "error": "x", "gen_n": 200, "gen_tps": 0.5}) + "\n")
            fh.write(json.dumps({"at": 1, "ok": True, "ms": 1, "error": "", "gen_n": 5, "gen_tps": 90.0,
                                 "prompt_n": 40, "prompt_tps": 1.0}) + "\n")
            fh.write(json.dumps({"at": 1, "ok": True, "ms": 1, "error": ""}) + "\n")
            fh.write("not json\n")
        check("Q6 measured_rate is the median over answered rows that carry the speed; a failed row, a short answer, "
              "a row without it and a broken line are not counted",
              M.measured_rate(path=led) == 6.5 and M.measured_rate(which="prompt", path=led) == 65.0
              and M.measured_rate(window=3, path=led) == 6.0,
              (M.measured_rate(path=led), M.measured_rate(which="prompt", path=led), M.measured_rate(window=3, path=led)))
        two = os.path.join(tmp, "two_rows.jsonl")
        with open(two, "w", encoding="utf-8") as fh:
            fh.writelines(json.dumps(x) + "\n" for x in r5[:3])          # two answers that carry a speed, one that does not
        check("Q7 ...it reads what ask() wrote (6.0, the median of the three answers above that carry a speed), and is "
              "None with fewer than three such rows, or no ledger at all",
              M.measured_rate(path=M.ASKS) == 6.0 and M.measured_rate(path=two) is None
              and M.measured_rate(path=os.path.join(tmp, "absent.jsonl")) is None,
              (M.measured_rate(path=M.ASKS), rows(M.ASKS)))
    finally:
        M.ASKS, M._REAL_ASKS, M.start, M._watch_idle, urllib.request.urlopen, sys.argv[0] = real
        M.USED = real_used
        if stub is not None:
            os.environ["COVENANT_MODEL_STUB"] = stub

    ok = sum(results)
    print("\nA282: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
