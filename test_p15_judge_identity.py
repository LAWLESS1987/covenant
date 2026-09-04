#!/usr/bin/env python3
"""
test_p15_judge_identity.py -- the fourth long-lived process must be able to
answer for itself.

P15 (filed 2026-08-24, closed 2026-08-28): node A, node B and the watchdog all
report their own identity (P11, P14); ollama -- the process that IS the ethics
gate, inside consensus -- reported nothing, and nothing probed it. Re-pull or
re-tag the model and the gate's verdicts change with no surface saying so.

This suite is Linux-runnable with no ollama, no keys, no nodes (M13 shape):
the probe is tested against a canned local HTTP server and a refused port, and
the report logic is pure functions.

Run:  python3 test_p15_judge_identity.py     (imports covenant_watchdog from
                                              the same directory)
"""
import ast
import http.server
import json
import os
import socket
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_watchdog as wd                                    # noqa: E402

PASS = []
FAIL = []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not cond else ""))


# ---------------------------------------------------------------- fixtures --
TAGS = {"models": [
    {"name": "qwen3:8b", "digest": "a1b2c3d4e5f60718293a4b5c6d7e8f90", "size": 5},
    {"name": "llama3:8b", "digest": "ffeeddccbbaa99887766554433221100", "size": 5},
]}
PS = {"models": [{"name": "qwen3:8b",
                  "digest": "a1b2c3d4e5f60718293a4b5c6d7e8f90"}]}


class CannedOllama(http.server.BaseHTTPRequestHandler):
    """Serves canned /api/tags and /api/ps; records every method seen."""
    methods_seen = []
    tags_body = json.dumps(TAGS).encode()
    ps_body = json.dumps(PS).encode()

    def _send(self, body, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):                                             # noqa: N802
        CannedOllama.methods_seen.append(("GET", self.path))
        if self.path == "/api/tags":
            self._send(CannedOllama.tags_body)
        elif self.path == "/api/ps":
            self._send(CannedOllama.ps_body)
        else:
            self._send(b"{}", 404)

    def do_POST(self):                                            # noqa: N802
        CannedOllama.methods_seen.append(("POST", self.path))
        self._send(b"{}")

    def log_message(self, *a):                                    # silence
        pass


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), CannedOllama)
threading.Thread(target=srv.serve_forever, daemon=True).start()
ROOT = f"http://127.0.0.1:{srv.server_address[1]}"

# ------------------------------------------------------------------- probe --
print("== probe: judge_identity ==")

ident = wd.judge_identity(root=ROOT, timeout=5)
check("P1a probe reaches the canned endpoint", ident["reachable"] is True)
check("P1b served map carries the tag with a 12-hex digest",
      ident["served"].get("qwen3:8b") == "a1b2c3d4e5f6", str(ident))
check("P1c both served models parsed", len(ident["served"]) == 2)
check("P1d /api/ps parsed into loaded", ident["loaded"] == ["qwen3:8b"])
check("P1e probe never POSTs (a monitor must not make the judge work)",
      all(m == "GET" for m, _ in CannedOllama.methods_seen),
      str(CannedOllama.methods_seen))

dead = wd.judge_identity(root=f"http://127.0.0.1:{free_port()}", timeout=2)
check("P2a refused port -> reachable False, no raise", dead["reachable"] is False)
check("P2b refused port names the error type", bool(dead["error"]))

CannedOllama.tags_body = b"this is not json"
garbage = wd.judge_identity(root=ROOT, timeout=5)
check("P3  garbage /api/tags -> unreachable-with-error, no raise",
      garbage["reachable"] is False and bool(garbage["error"]))
CannedOllama.tags_body = json.dumps(TAGS).encode()

CannedOllama.ps_body = b"not json either"
psless = wd.judge_identity(root=ROOT, timeout=5)
check("P4  broken /api/ps does not take /api/tags identity with it",
      psless["reachable"] is True and psless["served"].get("qwen3:8b")
      == "a1b2c3d4e5f6" and psless["loaded"] == [])
CannedOllama.ps_body = json.dumps(PS).encode()

# ------------------------------------------------------------------ report --
print("== report: judge_identity_report (pure) ==")
R = "http://127.0.0.1:11434"
OK = {"reachable": True, "error": None,
      "served": {"qwen3:8b": "a1b2c3d4e5f6"}, "loaded": ["qwen3:8b"]}

a, i, st = wd.judge_identity_report(OK, {}, expected_model="qwen3:8b", root=R)
check("R1a first sight: no alert", a == [])
check("R1b first sight: identity named in full",
      len(i) == 1 and "qwen3:8b@a1b2c3d4e5f6" in i[0], str(i))
check("R1c baseline digest recorded", st.get("digest") == "a1b2c3d4e5f6")

a2, i2, st2 = wd.judge_identity_report(OK, st, expected_model="qwen3:8b",
                                       root=R)
check("R2a unchanged identity: still no alert", a2 == [])
check("R2b unchanged identity: line is stable (Adaptation can dedup)",
      i2 == i)
ad = wd.Adaptation()
check("R2c Adaptation says a stable line once",
      ad.observe("judge:identity", i[0]) == i[0]
      and ad.observe("judge:identity", i2[0]) is None)

CH = {"reachable": True, "error": None,
      "served": {"qwen3:8b": "0feedbeef012"}, "loaded": []}
a3, i3, st3 = wd.judge_identity_report(CH, st2, expected_model="qwen3:8b",
                                       root=R)
check("R3a digest change -> ALERT naming both digests",
      len(a3) == 1 and "a1b2c3d4e5f6" in a3[0] and "0feedbeef012" in a3[0]
      and "CHANGED" in a3[0], str(a3))
a4, _, st4 = wd.judge_identity_report(CH, st3, expected_model="qwen3:8b",
                                      root=R)
check("R3b baseline moves after being said once -- alert does not re-fire",
      a4 == [] and st4.get("digest") == "0feedbeef012")

# 2026-09-03: ops/quorum_policy.json can make the local seat DEFER (F2), and
# then "fails closed" would be a false alert. The fail-closed pins below run
# with NO policy (the core default); R4d/R5c pin the deferring wording.
import tempfile as _tf
os.environ["COVENANT_QUORUM_POLICY_PATH"] = os.path.join(_tf.mkdtemp(), "absent.json")
DOWN = {"reachable": False, "error": "URLError", "served": {}, "loaded": []}
a5, i5, st5 = wd.judge_identity_report(DOWN, st4, expected_model="qwen3:8b",
                                       root=R)
check("R4a unreachable -> ALERT naming fail-closed consequence",
      len(a5) == 1 and "UNREACHABLE" in a5[0] and "fails closed" in a5[0],
      str(a5))
check("R4b outage keeps the baseline (an unreachable judge is not a changed one)",
      st5.get("digest") == "0feedbeef012")
a5b, _, _ = wd.judge_identity_report(DOWN, st5, expected_model="qwen3:8b",
                                     root=R)
check("R4c outage alert text is STABLE across rounds (says once, then CLEARs)",
      a5b == a5)

GONE = {"reachable": True, "error": None,
        "served": {"llama3:8b": "ffeeddccbbaa"}, "loaded": []}
a6, i6, st6 = wd.judge_identity_report(GONE, st5, expected_model="qwen3:8b",
                                       root=R)
check("R5a expected tag missing -> ALERT", any("MISSING" in x for x in a6),
      str(a6))
check("R5b vanished tag keeps old digest as baseline",
      st6.get("digest") == "0feedbeef012")
_pol = os.path.join(_tf.mkdtemp(), "quorum_policy.json")
with open(_pol, "w", encoding="utf-8") as _fh:
    json.dump({"providers": "deferring,semantic", "silence_is_not_dissent": True}, _fh)
os.environ["COVENANT_QUORUM_POLICY_PATH"] = _pol
a5d, i5d, st5d = wd.judge_identity_report(DOWN, st4, expected_model="qwen3:8b", root=R)
check("R4d with a DEFERRING policy, unreachable is disclosed as INFO naming the deferral, never 'fails closed'",
      a5d == [] and any("DEFERS" in x and "quorum_policy" in x for x in i5d) and st5d.get("digest") == "0feedbeef012",
      str(a5d) + str(i5d))
a6c, i6c, _ = wd.judge_identity_report(GONE, st5, expected_model="qwen3:8b", root=R)
check("R5c with a DEFERRING policy, a missing tag is disclosed, not alerted",
      not any("MISSING" in x for x in a6c) and any("not among" in x for x in i6c), str(a6c) + str(i6c))
os.environ["COVENANT_QUORUM_POLICY_PATH"] = os.path.join(_tf.mkdtemp(), "absent.json")
BACK = {"reachable": True, "error": None,
        "served": {"qwen3:8b": "aaaa2222bbbb"}, "loaded": []}
a7, _, _ = wd.judge_identity_report(BACK, st6, expected_model="qwen3:8b",
                                    root=R)
check("R5c reappearance under a NEW digest reads as a change, not first sight",
      any("CHANGED" in x for x in a7), str(a7))

ok = True
for junk in (None, [], "x", {"served": 7}, {"reachable": True, "served": None},
             {"reachable": True, "served": {"qwen3:8b": None}}):
    try:
        wd.judge_identity_report(junk, None, expected_model="qwen3:8b", root=R)
    except Exception as e:                                # noqa: BLE001
        ok = False
        print(f"      raised on {junk!r}: {type(e).__name__}: {e}")
check("R6  report never raises on garbage input", ok)

# ------------------------------------------------------------------ wiring --
print("== wiring and boundary (AST, not prose -- M42) ==")
src = open(os.path.join(HERE, "covenant_watchdog.py"), encoding="utf-8").read()
tree = ast.parse(src)
funcs = {n.name: n for n in ast.walk(tree)
         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def calls_in(fn):
    out = set()
    for n in ast.walk(funcs[fn]):
        if isinstance(n, ast.Call):
            f = n.func
            out.add(f.id if isinstance(f, ast.Name) else
                    f.attr if isinstance(f, ast.Attribute) else "?")
    return out


check("W1a one_pass calls judge_identity", "judge_identity" in calls_in("one_pass"))
check("W1b one_pass feeds judge_identity_report",
      "judge_identity_report" in calls_in("one_pass"))
forbidden = {"start_node", "Popen", "run", "urlopen", "replace", "open",
             "remove", "unlink", "kill", "terminate"}
check("W2a judge_identity_report is disclosure-only (no process/file/net calls)",
      not (calls_in("judge_identity_report") & forbidden),
      str(calls_in("judge_identity_report") & forbidden))
check("W2b judge_identity issues no writes/process calls (urlopen GET is its job)",
      not (calls_in("judge_identity") & (forbidden - {"urlopen"})),
      str(calls_in("judge_identity") & (forbidden - {"urlopen"})))
# The probe must never be able to make the judge THINK: no generate/chat
# path among the probe's string CONSTANTS (its docstring may NAME them as
# forbidden -- prose is not a code path, and M42 says match code).
_fn = funcs["judge_identity"]
_docs = {n.body[0].value.value for n in ast.walk(_fn)
         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
         and n.body and isinstance(n.body[0], ast.Expr)
         and isinstance(n.body[0].value, ast.Constant)
         and isinstance(n.body[0].value.value, str)}
consts = [n.value for n in ast.walk(_fn)
          if isinstance(n, ast.Constant) and isinstance(n.value, str)
          and n.value not in _docs]
check("W2c no generate/chat endpoint in the probe's code",
      consts and not any(b in c for c in consts
                         for b in ("/api/generate", "/api/chat", "/v1/chat")),
      str([c for c in consts if "/" in c]))

srv.shutdown()

print(f"\n{len(PASS)} passed, {len(FAIL)} failed of {len(PASS) + len(FAIL)}")
if FAIL:
    print("FAILED:", ", ".join(FAIL))
sys.exit(1 if FAIL else 0)
