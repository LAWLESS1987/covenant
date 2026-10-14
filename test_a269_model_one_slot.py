#!/usr/bin/env python3
"""test_a269_model_one_slot.py -- A269: one request at a time against the model's whole context.

WHY. 2026-10-06, every ask through Tetsu's door failed with "the model did not answer: HTTPError:
HTTP Error 500". Asked directly, the server said why: "Context size has been exceeded." -- for a
2,521-token probe sent while other requests were in flight, in 34.5 s, while a five-word hello answered
in 5.7 s. The keeper starts llama-server with -c 8192 so that his conversation memory fits beside the
rules (its own comment, "8k for both", 2026-09-26), but this llama-server build defaults to 4 parallel
slots sharing that one pool, so concurrent requests overflow it together. The keeper never said how many
slots. (This docstring first said the slots divided -c; that is retracted as A269-SLOT-SPLIT-2026-10-06.)

WHAT IT PINS (the real start(); for N1-N3 Popen is a recorder, nothing is launched).
  N1  start() passes -np 1, so a request is given the whole context
  N2  ... and -c 8192, the context the door's prompts were sized for
  N3  (A348b) the runtime's output goes to its own file, never through the keeper log's handle
  N4  (A348b) ... so a stop line another process appends while the runtime runs survives whole. The one
      check that launches something: a python child in llama-server's place, which prints one line on the
      suite's go and exits. On Windows the inherited handle carried no append and the child wrote over
      that line; elsewhere an inherited handle appends anyway, so only N3 can go red there.
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
    kws = []
    up = [False]
    real = (M.STATE, M.LOG, M.BIN, M.pick_model, M.alive, M._watch_idle, M.subprocess.Popen)
    real_a348b = (M.RUNTIME_LOG, M.USED)
    real_popen = M.subprocess.Popen
    stub = os.environ.pop("COVENANT_MODEL_STUB", None)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            M.STATE = os.path.join(tmp, "model_server.json")
            M.LOG = os.path.join(tmp, "model_server.log")
            M.RUNTIME_LOG = os.path.join(tmp, "model_server.runtime.log")     # A348b: never the live logs/
            M.USED = os.path.join(tmp, "last_use.stamp")                     # A348b: never the live ops/ stamp
            M.BIN = os.path.join(tmp, "llama-server.exe")
            open(M.BIN, "wb").close()
            M.pick_model = lambda: (os.path.join(tmp, "m.gguf"), "m.gguf", 2.0)
            M.alive = lambda: up[0]
            M._watch_idle = lambda: None

            def popen(args, **_kw):
                seen.append(list(args))
                kws.append(dict(_kw))
                up[0] = True
                return _P()
            M.subprocess.Popen = popen
            ok, why = M.start(say=lambda *_a: None)
            out = kws[0].get("stdout") if kws else None
            out_name = os.path.abspath(str(getattr(out, "name", out)))
            with open(M.LOG, encoding="utf-8") as fh:
                keeper = fh.read()
            check("N3 (A348b) the runtime's output goes to its own file, never through the keeper log's handle",
                  out_name == os.path.abspath(M.RUNTIME_LOG) and out_name != os.path.abspath(M.LOG)
                  and " start m.gguf " in keeper, (out_name, keeper))

            # N4 (A348b): the overwrite itself, end to end -- the review found two stop lines in the live log
            # headless this way, and a scratch run reproduced it on this PC.
            go = os.path.join(tmp, "go")
            code = ("import os, time\n"
                    "t = time.time()\n"
                    "while not os.path.exists(%r) and time.time() - t < 20:\n"
                    "    time.sleep(0.05)\n"
                    "print('RUNTIME-FIRST-LINE')\n" % go)
            kids = []

            def popen_child(args, **kw):
                p = real_popen([sys.executable, "-I", "-c", code], **kw)
                kids.append(p)
                up[0] = True
                return p
            up[0] = False
            M.subprocess.Popen = popen_child
            ok4, why4 = M.start(say=lambda *_a: None)
            stop_line = "2026-10-14T00:00:00 stop pid 4242 (m.gguf) -- reason=idle by pid 1 (covenant_watchdog.py)"
            with open(M.LOG, "a", encoding="utf-8") as other:             # another process's stop(), its own handle
                other.write(stop_line + "\n")
            open(go, "w").close()
            for p in kids:
                try:
                    p.wait(timeout=30)
                except Exception:                                         # noqa: BLE001 -- never leave the child behind
                    p.kill()
                    p.wait(timeout=10)
            with open(M.LOG, encoding="utf-8") as fh:
                keeper = fh.read()
            runtime = open(M.RUNTIME_LOG, encoding="utf-8").read() if os.path.exists(M.RUNTIME_LOG) else ""
            check("N4 (A348b) a stop line appended while the runtime runs survives whole; the runtime's line is kept, "
                  "in its own file", ok4 and len(kids) == 1 and stop_line + "\n" in keeper
                  and "RUNTIME-FIRST-LINE" in runtime, (ok4, why4, keeper[-400:], runtime[-200:]))
        args = seen[0] if seen else []
        check("N1 start() asks for one slot (-np 1)", ok and flag(args, "-np") == "1", (ok, why, args))
        check("N2 start() gives that slot -c 8192", flag(args, "-c") == "8192", args)
    finally:
        M.STATE, M.LOG, M.BIN, M.pick_model, M.alive, M._watch_idle, M.subprocess.Popen = real
        M.RUNTIME_LOG, M.USED = real_a348b
        if stub is not None:
            os.environ["COVENANT_MODEL_STUB"] = stub

    ok = sum(results)
    print("\nA269: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
