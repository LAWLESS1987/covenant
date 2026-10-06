#!/usr/bin/env python3
"""test_a269_model_one_slot.py -- A269: one request at a time against the model's whole context.

WHY. 2026-10-06, every ask through Tetsu's door failed with "the model did not answer: HTTPError:
HTTP Error 500". Asked directly, the server said why: "Context size has been exceeded." -- for a
2,521-token probe sent while other requests were in flight, in 34.5 s, while a five-word hello answered
in 5.7 s. The keeper starts llama-server with -c 8192 so that his conversation memory fits beside the
rules (its own comment, "8k for both", 2026-09-26), but this llama-server build defaults to 4 parallel
slots sharing that one pool, so concurrent requests overflow it together. The keeper never said how many
slots. (This docstring first said the slots divided -c; that is retracted as A269-SLOT-SPLIT-2026-10-06.)

WHAT IT PINS (the real start(); Popen is a recorder, nothing is launched).
  N1  start() passes -np 1, so a request is given the whole context
  N2  ... and -c 8192, the context the door's prompts were sized for
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_model as M  # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:300]), flush=True)


class _P:
    pid = 999999

    def poll(self):
        return None


def flag(args, name):
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else None


def main():
    print("A269 -- one request gets the model's whole context")
    seen = []
    up = [False]
    real = (M.STATE, M.LOG, M.BIN, M.pick_model, M.alive, M._watch_idle, M.subprocess.Popen)
    stub = os.environ.pop("COVENANT_MODEL_STUB", None)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            M.STATE = os.path.join(tmp, "model_server.json")
            M.LOG = os.path.join(tmp, "model_server.log")
            M.BIN = os.path.join(tmp, "llama-server.exe")
            open(M.BIN, "wb").close()
            M.pick_model = lambda: (os.path.join(tmp, "m.gguf"), "m.gguf", 2.0)
            M.alive = lambda: up[0]
            M._watch_idle = lambda: None

            def popen(args, **_kw):
                seen.append(list(args))
                up[0] = True
                return _P()
            M.subprocess.Popen = popen
            ok, why = M.start(say=lambda *_a: None)
        args = seen[0] if seen else []
        check("N1 start() asks for one slot (-np 1)", ok and flag(args, "-np") == "1", (ok, why, args))
        check("N2 start() gives that slot -c 8192", flag(args, "-c") == "8192", args)
    finally:
        M.STATE, M.LOG, M.BIN, M.pick_model, M.alive, M._watch_idle, M.subprocess.Popen = real
        if stub is not None:
            os.environ["COVENANT_MODEL_STUB"] = stub

    ok = sum(results)
    print("\nA269: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
