#!/usr/bin/env python3
"""test_a265_model_stop.py -- A265: the model keeper's stop is a stop only when the server stops answering.

WHY. 2026-10-04T23:10:12 the idle stop logged "stop pid 5524", deleted the keeper's state and
returned True, while taskkill had answered "Access is denied" (exit 128). The server kept answering
on 8081 for a day: start() reused it as "already up", nothing could put it away, readiness() read
PASS, and on 2026-10-05 the first private batch ask through Tetsu's door timed out against it (503).
No suite had ever run the real stop(): MK1 replaces it with a stub. These checks run it.

WHAT IT PINS.
  S1  a kill that is refused (the server still answers): False with taskkill's words, state KEPT,
      the log says STOP FAILED and never "stop pid"
  S2  a kill that works: True, state removed, the log says "stop pid" as before
  S3  a server already gone: True, state removed (nothing to wait for)
  S4  no state: "not started by this keeper", and no kill is attempted
  R1  readiness(): a server answers and the keeper recorded nothing -> UNDETERMINED, managed False
  R2  readiness(): a server answers and the keeper started it -> PASS, as before

Every kill is a recorder (subprocess.run and os.kill are replaced) and the pid is one that does not
exist: nothing real is stopped, here or on a CI runner. State and log paths are temporary.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_model as M  # noqa: E402

results = []
FAKE_PID = 999999


class _Run:
    def __init__(self, code, err):
        self.returncode, self.stderr, self.stdout = code, err, ""


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:300]), flush=True)


def main():
    tmp = tempfile.mkdtemp(prefix="a265_")
    real = (M.STATE, M.LOG, M.alive, M.subprocess.run, os.kill, M.STOP_VERIFY_S, M._read_state, M.free_gb)
    kills = []

    def write_state(d):
        with open(M.STATE, "w", encoding="utf-8") as fh:
            json.dump(d, fh)

    def log_text():
        try:
            return open(M.LOG, encoding="utf-8").read()
        except OSError:
            return ""

    try:
        M.STATE = os.path.join(tmp, "model_server.json")
        M.LOG = os.path.join(tmp, "model_server.log")
        M.STOP_VERIFY_S = 1
        os.kill = lambda pid, sig: kills.append(("kill", pid))
        state = {"pid": FAKE_PID, "model": "qwen2.5-3b-instruct-q4_k_m.gguf", "started": 0}

        # S1: refused -- the server goes on answering
        write_state(state)
        M.subprocess.run = lambda args, **k: (kills.append(tuple(args)) or
                                              _Run(128, "ERROR: The process with PID %d could not be terminated. Reason: Access is denied." % FAKE_PID))
        M.alive = lambda: True
        ok, why = M.stop(say=lambda *_a: None)
        log = log_text()
        check("S1 a refused kill returns False and says why%s" % (" (taskkill's words)" if os.name == "nt" else ""),
              ok is False and "still answers" in why and (os.name != "nt" or "Access is denied" in why), (ok, why))
        check("S1 ...the state is KEPT, so the keeper still knows what it runs",
              os.path.isfile(M.STATE) and json.load(open(M.STATE, encoding="utf-8")).get("pid") == FAKE_PID)
        check("S1 ...the log says STOP FAILED and never claims a stop",
              "STOP FAILED pid %d" % FAKE_PID in log and " stop pid " not in log, log)
        check("S1 ...a kill was attempted", len(kills) == 1, kills)

        # S2: the kill works -- the server stops answering after it
        kills.clear()
        open(M.LOG, "w").close()
        write_state(state)
        gone = []
        M.subprocess.run = lambda args, **k: (kills.append(tuple(args)) or gone.append(1) or _Run(0, ""))
        os.kill = lambda pid, sig: (kills.append(("kill", pid)) or gone.append(1))
        M.alive = lambda: not gone
        ok, why = M.stop(say=lambda *_a: None)
        log = log_text()
        check("S2 a kill that works returns True, removes the state and logs 'stop pid' as before",
              ok is True and why == "stopped" and not os.path.isfile(M.STATE)
              and " stop pid %d " % FAKE_PID in log and "STOP FAILED" not in log, (ok, why, log))

        # S3: already gone
        write_state(state)
        M.alive = lambda: False
        ok, _why = M.stop(say=lambda *_a: None)
        check("S3 a server already gone: True and the state removed", ok is True and not os.path.isfile(M.STATE))

        # S4: no state
        kills.clear()
        M.alive = lambda: True
        ok, why = M.stop(say=lambda *_a: None)
        check("S4 no state: 'not started by this keeper' and no kill attempted",
              ok is False and why == "not started by this keeper" and kills == [], (ok, why, kills))

        # R1/R2: readiness
        M.alive = lambda: True
        M.free_gb = lambda: 0.52
        M._read_state = lambda: {}
        r1 = M.readiness()
        check("R1 readiness: a server answers and the keeper recorded nothing -> UNDETERMINED, managed False, A265 named",
              r1.get("verdict") == "UNDETERMINED" and r1.get("managed") is False and "A265" in r1.get("why", ""), r1)
        M._read_state = lambda: {"pid": FAKE_PID, "model": "qwen2.5-3b-instruct-q4_k_m.gguf"}
        r2 = M.readiness()
        check("R2 readiness: a server the keeper started -> PASS naming its model, as before",
              r2.get("verdict") == "PASS" and "qwen2.5-3b" in r2.get("why", ""), r2)
    finally:
        M.STATE, M.LOG, M.alive, M.subprocess.run, os.kill, M.STOP_VERIFY_S, M._read_state, M.free_gb = real

    ok = sum(results)
    print("\nA265: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
