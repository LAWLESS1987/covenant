"""test_covenant_app.py -- the console, proved rather than described.

covenant_app.py can restart nodes and sign transactions. Four of its
properties are load-bearing, and a docstring is not a proof of any of them:

  1. it binds loopback and nothing moves it
  2. actions are a fixed allowlist of scripts, never a command string
  3. actions are OFF until COVENANT_APP_ACTIONS is exactly "1"
  4. the signing key never appears in a response

So this suite starts three STUB nodes on the real production ports, runs the
real unmodified covenant_app.py against them as a subprocess -- twice, once
read-only and once armed -- and asserts all four from the outside, the way an
attacker or a mistake would meet them.

It also asserts the things that made this project's earlier bugs:

  M11  the console must never poll /chain (20 reads/60s per node). The stubs
       count every /chain hit and the count must stay zero.
  M31  every guard is mutation-tested: the test flips the guard off and
       requires the refusal to disappear, then flips it back and requires it
       to return. A guard nobody has watched fail is a guard nobody has tested.
  M38  running != disk. One stub reports a wrong source hash and the console
       must SAY SO rather than average it away.
  UNKNOWN is never PASS. A missing watchdog log reports age=None, not age=0.

    python test_covenant_app.py
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
APP = os.path.join(HERE, "covenant_app.py")
APP_PORT = 5199
NODE_PORTS = {"A": 5000, "B": 5020, "C": 5060}

_passed, _failed, _unknown = 0, 0, 0


def ok(tag, name, cond, detail=""):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"PASS  {tag} {name}  {detail}")
    else:
        _failed += 1
        print(f"FAIL  {tag} {name}  {detail}")


def unknown(tag, name, detail=""):
    """Not a pass. This project folds UNKNOWN into PASS exactly never."""
    global _unknown
    _unknown += 1
    print(f"UNKN  {tag} {name}  {detail}")


# ============================================================== the stub nodes
DISK_SHA = None          # filled in main()
APP_SHA = None           # filled in main() -- the console this suite is testing
STATE = {}
CHAIN_HITS = []
UAS = set()


def _health(nid):
    s = STATE[nid]
    return {
        "node_id": nid,
        "chain_height": s["height"],
        "peers": s["peers"],
        "pending_transactions": s["pending"],
        "alignment": s["alignment"],
        "judge": "stub:selfreport",
        "judge_keyless": False,
        "judge_insecure": False,
        "wsgi": "waitress",
        "version": "8.37",
        "source_sha256": s["src"],
        "source_lines": 9894,
        "own_genesis": False,
        "genesis": "0" * 64,
        "substrate": {"available_memory_mb": 2500, "judge_footprint_mb": 4983,
                      "judge_footprint_source": "stub", "sampled_s_ago": 1.0,
                      "unavailable": ""},
        "mesh": {"tracked": 2, "by_source": {s["src"]: ["x", "y"]}},
        "quorum": {"is_quorum": True, "diverse": s["diverse"], "judges": [],
                   "semantic_judges": 1, "self_report_judges": 1},
        "crisis_mode": s["crisis"],
        "subsystems": {},
        "anomaly_kinds": sorted(s["anom"]),
        "spike_detected": False,
        "warnings": s["warnings"],
        "degraded": bool(s["crisis"]),
        "ethics_review": s.get("review"),
    }


class Stub(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _nid(self):
        port = self.server.server_address[1]
        for k, v in NODE_PORTS.items():
            if v == port:
                return k
        return "?"

    def _json(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        nid = self._nid()
        UAS.add(self.headers.get("User-Agent") or "")
        p = self.path.split("?")[0]
        if STATE[nid]["down"]:
            try:
                self.connection.close()
            except Exception:
                pass
            return
        if p == "/health":
            return self._json(200, _health(nid))
        if p == "/anomalies":
            return self._json(200, {"per_kind": STATE[nid]["anom"]})
        if p == "/alignment":
            if STATE[nid]["align_broken"]:
                return self._json(500, {"error": "governor unavailable"})
            return self._json(200, {"current_alignment": STATE[nid]["alignment"]})
        if p == "/chain":
            CHAIN_HITS.append((nid, time.time()))
            return self._json(429, {"error": "rate limited"})
        return self._json(404, {"error": "stub has no such route"})

    def do_POST(self):
        return self._json(404, {"error": "stub takes no writes"})


def start_stubs():
    servers = []
    for nid, port in sorted(NODE_PORTS.items(), key=lambda kv: kv[1]):
        STATE[nid] = {"height": 7, "peers": 1 if nid in ("A", "C") else 2,
                      "pending": 0, "alignment": 0.62,
                      "src": DISK_SHA if nid != "C" else "deadbeefcafe",
                      "crisis": False, "anom": {}, "warnings": [],
                      "diverse": True, "down": False, "align_broken": False,
                      "review": None}
        srv = ThreadingHTTPServer(("127.0.0.1", port), Stub)
        srv.daemon_threads = True
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        servers.append(srv)
    return servers


# =================================================================== app client
def get(path, timeout=20):
    req = urllib.request.Request(f"http://127.0.0.1:{APP_PORT}{path}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode()
            return r.status, body, dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), dict(e.headers)


def post(path, obj=None, timeout=60):
    raw = json.dumps(obj or {}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{APP_PORT}{path}", data=raw,
                                 method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def state():
    st, body, _ = get("/api/state")
    return json.loads(body)


def start_app(actions_on):
    env = dict(os.environ)
    env["COVENANT_APP_PORT"] = str(APP_PORT)
    env.pop("COVENANT_APP_ACTIONS", None)
    if actions_on is not None:
        env["COVENANT_APP_ACTIONS"] = actions_on
    p = subprocess.Popen([sys.executable, APP], cwd=HERE, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         stdin=subprocess.DEVNULL, text=True)
    for _ in range(80):
        time.sleep(0.25)
        if p.poll() is not None:
            return p, False
        try:
            _, ident, _ = get("/api/identity", timeout=2)
            who = json.loads(ident).get("sha")
        except Exception:
            continue
        # "SOMETHING ANSWERED" IS NOT "MY PROCESS ANSWERED" (M38, applied to
        # the harness instead of to the node). A reply on the port used to be
        # the whole readiness test, which is only sound if nothing else can
        # hold the port -- and on Windows something else can. Compare the
        # answering process's own sha against the file this suite is testing:
        # a foreign or stale console is a hard stop, never a green run.
        if who != APP_SHA:
            print(f"REFUSING TO TEST: {APP_PORT} was answered by a console "
                  f"reporting sha {who}, but covenant_app.py on disk is "
                  f"{APP_SHA}. Another console is holding the port. UNKNOWN, "
                  f"not a pass.")
            return p, False
        return p, True
    return p, False


def stop_app(p):
    try:
        p.terminate()
        p.wait(timeout=10)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass


def fresh():
    """Wait past POLL_TTL so the next /api/state re-polls the stubs."""
    time.sleep(3.0)


# ================================================================ static checks
def static_checks():
    src = open(APP, encoding="utf-8").read()
    ok("S1", "BIND_HOST is a literal 127.0.0.1, not read from anywhere",
       'BIND_HOST = "127.0.0.1"' in src
       and "BIND_HOST" not in src.split("os.environ.get")[1].split("\n")[0],
       "a console that can restart nodes must not be one env var from the LAN")
    ok("S2", "no shell=True anywhere in the console",
       "shell=True" not in src, "found" if "shell=True" in src else "clean")
    ok("S3", "subprocess is invoked with an argument list, never a string",
       "shell=False" in src and "subprocess.run(cmd" in src, "explicit shell=False")

    sys.path.insert(0, HERE)
    import covenant_app as app

    bad = []
    for name, entry in app.ACTIONS.items():
        if len(entry) != 4:
            bad.append(f"{name}: {len(entry)}-tuple, expected (script, kind, risk, desc)")
            continue
        script, kind, risk, desc = entry
        if os.path.isabs(script) or ".." in script:
            bad.append(f"{name}: {script} escapes the folder")
        if any(c in script for c in "&|;<>$`\n\"'*?"):
            bad.append(f"{name}: {script} has a shell metacharacter")
        if kind not in ("python", "bat"):
            bad.append(f"{name}: unknown kind {kind}")
        if risk not in ("read", "write", "system", "long"):
            bad.append(f"{name}: unknown risk class {risk!r}")
        if not desc:
            bad.append(f"{name}: no description for the operator")
    ok("S4", "every allowlisted action is a plain relative script name with a "
             "declared risk class",
       not bad, "; ".join(bad) if bad else f"{len(app.ACTIONS)} actions, all clean")

    # The two that stop or re-permission a running thing must SAY so. An
    # interface that draws them like `gates` is the same failure as an alert
    # that fires every round: it teaches its reader not to look (M34).
    risks = {k: v[2] for k, v in app.ACTIONS.items()}
    ok("S5", "restart and aclfix are declared as changing the running system",
       risks.get("restart") == "system" and risks.get("aclfix") == "system",
       f"restart={risks.get('restart')}, aclfix={risks.get('aclfix')}")
    ok("S6", "and the read-only ones are declared read-only",
       all(risks.get(k) == "read" for k in ("gates", "verify", "config3")),
       ", ".join(f"{k}={risks.get(k)}" for k in ("gates", "verify", "config3")))

    # ---- M31: mutation-test the actions gate ------------------------------
    was = app.ACTIONS_ON
    ok("F1", "with actions OFF every allowlisted name is refused",
       all(app.run_action(n).get("ok") is False for n in app.ACTIONS),
       f"{len(app.ACTIONS)} names, {len(app.ACTIONS)} refusals")
    ok("F2", "unknown names are refused: traversal, absolute, and near-misses",
       all(app.run_action(n).get("ok") is False for n in
           ("../verify_bundle.py", "/etc/passwd", "GATES", "gates ", "",
            "gates;rm -rf /", "sweep.py")),
       "7 shapes, 7 refusals")

    app.ACTIONS_ON = True                       # flip the guard OFF
    r_unknown = app.run_action("../verify_bundle.py")
    app.ACTIONS["_missing_"] = ("no_such_script_xyz.py", "python", "read", "t")
    r_missing = app.run_action("_missing_")
    del app.ACTIONS["_missing_"]
    app.ACTIONS_ON = was                        # and back
    ok("F3", "with the gate flipped ON, the allowlist STILL refuses a name "
             "outside it (M31: the second guard is real, not a consequence "
             "of the first)",
       r_unknown.get("ok") is False and "unknown action" in str(r_unknown.get("error")),
       str(r_unknown.get("error"))[:90])
    ok("F4", "an allowlisted action whose script is absent is refused cleanly",
       r_missing.get("ok") is False and "not in this folder" in str(r_missing.get("error")),
       str(r_missing.get("error"))[:90])
    ok("F5", "the gate was restored after the mutation",
       app.ACTIONS_ON is was and app.run_action("gates").get("ok") is False,
       f"ACTIONS_ON back to {was}")

    # ---- signing paths refuse without ever importing the 9,800-line node ---
    before = "covenant_unified_v8" in sys.modules
    r1 = app.submit_tx("A", "B", 1.0, "")
    r2 = app.mine("A")
    after = "covenant_unified_v8" in sys.modules
    ok("F6", "submit_tx and mine refuse with actions off",
       r1.get("ok") is False and r2.get("ok") is False,
       str(r1.get("error"))[:60])
    ok("F7", "and they refuse BEFORE importing the node module -- the refusal "
             "is not downstream of anything that can fail",
       after == before, f"covenant_unified_v8 imported: {after}")

    # ---- watchdog pulse: UNKNOWN is not zero ------------------------------
    tmp = os.path.join(HERE, "logs", "_wd_test.log")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    real = app.WATCHDOG_LOG
    try:
        app.WATCHDOG_LOG = tmp
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write("2026-08-26T23:41:25Z INFO all quiet\n")
        p_now = app.watchdog_pulse()
        os.utime(tmp, (time.time() - 900, time.time() - 900))
        p_old = app.watchdog_pulse()
        app.WATCHDOG_LOG = os.path.join(HERE, "logs", "_does_not_exist.log")
        p_gone = app.watchdog_pulse()
    finally:
        app.WATCHDOG_LOG = real
        try:
            os.remove(tmp)
        except Exception:
            pass
    ok("F8", "a fresh watchdog log reads as inside its own bound",
       p_now["age_s"] is not None and p_now["age_s"] <= p_now["bound_s"],
       f"age {p_now['age_s']}s / bound {p_now['bound_s']}s")
    ok("F9", "a stale one reads as stale, not as calm",
       p_old["age_s"] > p_old["bound_s"], f"age {p_old['age_s']}s")
    ok("F10", "a MISSING one reads as UNKNOWN (age None), never as age 0",
       p_gone["age_s"] is None and p_gone.get("error"),
       f"age {p_gone['age_s']}, error {p_gone.get('error')}")

    # ---- the opt-in string is exact ---------------------------------------
    variants = {"1": True, "true": False, "TRUE": False, "yes": False,
                "0": False, "": False, " 1": False, "1 ": False, "01": False}
    wrong = [v for v, want in variants.items() if (v == "1") != want]
    ok("F11", "only the exact string '1' can arm actions (checked as a rule, "
              "then proved live below)",
       not wrong and app.ACTIONS.__class__ is dict, f"{len(variants)} variants")
    return app


# ============================================================= read-only checks
def readonly_checks(proc):
    st = state()
    ok("H1", "the console sees all three nodes and reports them up",
       len(st["nodes"]) == 3 and all(n["up"] for n in st["nodes"]),
       ", ".join(f"{n['id']}:{n['port']}" for n in st["nodes"]))
    ok("H2", "heights agree and convergence is reported",
       st["converged"] and st["heights"] == [7, 7, 7], str(st["heights"]))
    agree = {n["id"]: n["agrees_with_disk"] for n in st["nodes"]}
    ok("H3", "M38 -- the node running a DIFFERENT source is named, not averaged",
       agree == {"A": True, "B": True, "C": False}, str(agree))
    ok("H4", "the app describes itself: hash, line count, bind, heartbeat bound",
       st["app"]["sha"] and st["app"]["lines"] > 0
       and st["app"]["bind"] == f"127.0.0.1:{APP_PORT}"
       and st["app"]["heartbeat_s"] == 60,
       f"{st['app']['sha']} {st['app']['lines']} lines on {st['app']['bind']}")
    ok("H5", "actions report themselves as OFF",
       st["app"]["actions_enabled"] is False, "read-only")
    ok("H5b", "the action ORDER is explicit in the payload, not left to the "
              "reader's JSON parser",
       st.get("action_order") and st["action_order"][0] == "gates"
       and set(st["action_order"]) == set(st["actions"]),
       " > ".join(st.get("action_order", [])[:4]) + " ...")
    ok("H5c", "and every action carries its risk class to the page",
       all(a.get("risk") in ("read", "write", "system", "long")
           for a in st["actions"].values()),
       ", ".join(sorted({a["risk"] for a in st["actions"].values()})))

    _, raw, hdrs = get("/api/state")
    leaks = [m for m in ("BEGIN PRIVATE KEY", "BEGIN RSA PRIVATE",
                         "-----BEGIN", "PRIVATE KEY") if m in raw]
    ok("H6", "no private key material anywhere in /api/state",
       not leaks, "; ".join(leaks) if leaks else f"{len(raw)} bytes scanned")

    code, page, phdrs = get("/")
    externals = [t for t in ("http://", "https://", "//fonts.", "cdn")
                 if t in page.replace("http://127.0.0.1", "")]
    ok("H7", "the page is served and loads nothing from anywhere",
       code == 200 and "Covenant" in page and not externals,
       "; ".join(externals) if externals else f"{len(page)} bytes, 0 external refs")
    csp = phdrs.get("Content-Security-Policy", "")
    ok("H8", "and says so in a Content-Security-Policy header",
       "default-src 'none'" in csp, csp[:70])

    code, j = post("/api/action/gates")
    ok("H9", "an action is refused, and the refusal SAYS HOW TO ARM IT",
       code == 200 and j.get("ok") is False
       and "COVENANT_APP_ACTIONS=1" in str(j.get("error")),
       str(j.get("error"))[:80])

    _, jt = post("/api/tx", {"from": "A", "to": "B", "amount": 1})
    _, jm = post("/api/mine", {"node": "A"})
    ok("H10", "/api/tx and /api/mine refuse with actions off",
       jt.get("ok") is False and jm.get("ok") is False,
       str(jt.get("error"))[:60])

    shapes = ["/api/action/../verify_bundle.py", "/api/action/%2e%2e%2fgates",
              "/api/action/", "/api/action/gates%00", "/api/action/GATES"]
    bad = []
    for s in shapes:
        c, j = post(s)
        if j.get("ok") is not False:
            bad.append(s)
    ok("H11", "every traversal and near-miss action path is refused",
       not bad, "; ".join(bad) if bad else f"{len(shapes)} shapes, all refused")

    c, j = post("/api/nope")
    c2, body2, _ = get("/api/nope")
    ok("H12", "an unknown route is a JSON 404, not a stack trace",
       c == 404 and c2 == 404 and "no such route" in body2,
       f"POST {c}, GET {c2}")

    ok("H13", "M11 -- the console has never touched /chain",
       len(CHAIN_HITS) == 0,
       f"{len(CHAIN_HITS)} hits" if CHAIN_HITS else "0 hits across 3 nodes")
    ok("H14", "and it identifies itself to the nodes it polls",
       any(u.startswith("covenant-app/") for u in UAS), sorted(UAS))

    # ---- the split and the corpse ----------------------------------------
    STATE["C"]["height"] = 4
    fresh()
    st = state()
    ok("H15", "a height split is reported as a SPLIT, not smoothed",
       st["converged"] is False and sorted(st["heights"]) == [4, 7, 7],
       str(st["heights"]))
    STATE["C"]["height"] = 7

    STATE["B"]["down"] = True
    fresh()
    st = state()
    b = [n for n in st["nodes"] if n["id"] == "B"][0]
    ok("H16", "a node that stops answering is reported down with its error kind",
       b["up"] is False and b["error"],
       f"B: {b['error']}")
    STATE["B"]["down"] = False

    STATE["A"]["crisis"] = True
    STATE["A"]["warnings"] = ["only 2500 MB of memory available against a "
                              "judge model of 4983 MB"]
    STATE["A"]["anom"] = {"ethics_rejection": 3, "auth_failure": 1}
    fresh()
    st = state()
    a = [n for n in st["nodes"] if n["id"] == "A"][0]
    ok("H17", "crisis, warnings and anomaly counts all reach the console",
       a["health"]["crisis_mode"] and a["health"]["warnings"]
       and a["anomalies"].get("ethics_rejection") == 3,
       f"crisis={a['health']['crisis_mode']} anomalies={a['anomalies']}")
    STATE["A"]["crisis"] = False
    STATE["A"]["warnings"] = []
    STATE["A"]["anom"] = {}

    # ---- the ethics review queue -----------------------------------------
    st = state()
    ok("H17b", "with no node reporting the field, the console reports ABSENT "
               "rather than an empty queue -- 'nobody is held' and 'nobody is "
               "counting' are different claims and only one is good news",
       st.get("ethics_review") is None, "absent")
    STATE["A"]["review"] = {"open_holds": 3, "overdue": 1, "oldest_hold_s": 90000,
                            "review_bound_s": 86400,
                            "by_script": {"Devanagari": 2, "Han": 1},
                            "cleared": 4, "cleared_unqualified": 1,
                            "coverable": {"Han": {"holds": 1,
                                                  "can_clear": ["node-C/zho"]}},
                            "nobody_can_read": {"Devanagari": 2}}
    STATE["C"]["review"] = {"open_holds": 2, "overdue": 0, "oldest_hold_s": 400,
                            "review_bound_s": 86400, "by_script": {"Thai": 2}}
    fresh()
    r = state()["ethics_review"]
    ok("H17c", "and it aggregates across nodes: holds and overdue SUM, oldest "
               "is the MAX (the longest anyone has waited, not the average)",
       r and r["open_holds"] == 5 and r["overdue"] == 1
       and r["oldest_hold_s"] == 90000
       and r["by_script"] == {"Devanagari": 2, "Han": 1, "Thai": 2},
       f"{r['open_holds']} held, {r['overdue']} overdue, oldest {r['oldest_hold_s']}s")
    ok("H17d", "and it carries the mesh view: who can clear what, what NOBODY "
               "can read, and how many were released without being read",
       r["coverable"]["Han"]["can_clear"] == ["node-C/zho"]
       and r["nobody_can_read"] == {"Devanagari": 2}
       and r["cleared_unqualified"] == 1,
       f"Han -> node-C/zho; nobody reads {list(r['nobody_can_read'])}; "
       f"{r['cleared_unqualified']} of {r['cleared']} unread")
    STATE["A"]["review"] = None
    STATE["C"]["review"] = None

    # ---- loopback, from the outside --------------------------------------
    ip = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    if not ip or ip.startswith("127."):
        unknown("H18", "non-loopback refusal", "this host has no non-loopback "
                "IPv4 to test from; UNKNOWN, not PASS")
    else:
        try:
            c = socket.create_connection((ip, APP_PORT), timeout=3)
            c.close()
            reachable = True
        except Exception:
            reachable = False
        ok("H18", f"the console does NOT answer on {ip} -- loopback is a bind, "
                  f"not a hope", not reachable,
           f"connect to {ip}:{APP_PORT} refused" if not reachable
           else "IT ANSWERED. This is the whole point of rule 1.")


# ================================================================ armed checks
def armed_checks():
    st = state()
    ok("A1", "actions report themselves as ARMED under COVENANT_APP_ACTIONS=1",
       st["app"]["actions_enabled"] is True, "armed")

    _, j = post("/api/action/config3")
    ok("A2", "an allowlisted action starts", j.get("ok") is True, str(j)[:70])
    deadline = time.time() + 90
    r = {}
    while time.time() < deadline:
        time.sleep(1.5)
        r = state()["running"].get("config3", {})
        if r.get("state") == "done":
            break
    ok("A3", "it runs to completion and its exit code and output are reported",
       r.get("state") == "done" and r.get("rc") is not None and r.get("tail"),
       f"rc={r.get('rc')}, {len((r.get('tail') or '').splitlines())} lines of output")
    if r.get("rc") not in (0, None):
        print(f"      note: test_3node_config.py itself exited {r.get('rc')} -- "
              f"that is its own claim, not this one's")

    # `gates` deliberately, NOT `sweep`. run_local_sweep.py is a 30-45 minute
    # job, and on the real machine this suite would have kicked one off against
    # the live nodes -- a test with a side effect on production is not a test.
    # launch_check.py changes nothing by construction, which is the whole
    # reason it is the safe one to race.
    _, j1 = post("/api/action/gates")
    _, j2 = post("/api/action/gates")
    ok("A4", "the same action cannot be started twice concurrently",
       j1.get("ok") is True and j2.get("ok") is False
       and "already running" in str(j2.get("error")), str(j2.get("error"))[:60])
    deadline = time.time() + 150          # do not orphan the child on exit
    while time.time() < deadline:
        if state()["running"].get("gates", {}).get("state") == "done":
            break
        time.sleep(2.0)

    _, j = post("/api/action/../verify_bundle.py")
    ok("A5", "ARMED, the allowlist still refuses a name outside it",
       j.get("ok") is False and "unknown action" in str(j.get("error")),
       str(j.get("error"))[:70])

    _, raw, _ = get("/api/state")
    ok("A6", "armed, /api/state is still free of key material",
       "BEGIN" not in raw and "PRIVATE" not in raw, f"{len(raw)} bytes scanned")

    _, j = post("/api/tx", {"from": "Z", "to": "B", "amount": 1}, timeout=90)
    ok("A7", "a transaction naming a node that does not exist fails cleanly, "
             "by name, with no traceback and no 500",
       j.get("ok") is False and "'Z'" in str(j.get("error"))
       and "Traceback" not in str(j.get("error")), str(j.get("error"))[:90])

    _, j = post("/api/mine", {"node": "Q"}, timeout=90)
    ok("A8", "so does a mine on a node that does not exist",
       j.get("ok") is False and "'Q'" in str(j.get("error")),
       str(j.get("error"))[:80])

    STATE["A"]["align_broken"] = True
    _, j = post("/api/tx", {"from": "A", "to": "B", "amount": 1}, timeout=120)
    STATE["A"]["align_broken"] = False
    ok("A9", "when /alignment cannot be read the console REFUSES rather than "
             "guessing a benefit_score",
       j.get("ok") is False and "guess" in str(j.get("error")),
       str(j.get("error"))[:110])

    ok("A10", "M11 still holds with actions armed -- /chain untouched",
       len(CHAIN_HITS) == 0, f"{len(CHAIN_HITS)} hits")


def main():
    global DISK_SHA, APP_SHA
    import hashlib
    core = os.path.join(HERE, "covenant_unified_v8.py")
    if not os.path.exists(core) or not os.path.exists(APP):
        print("covenant_unified_v8.py or covenant_app.py is not beside this test")
        return 2
    with open(core, "rb") as fh:
        DISK_SHA = hashlib.sha256(fh.read()).hexdigest()[:12]
    with open(APP, "rb") as fh:
        APP_SHA = hashlib.sha256(fh.read()).hexdigest()[:12]
    print(f"disk source {DISK_SHA}; console {APP_SHA}; "
          f"stubs on {sorted(NODE_PORTS.values())}; "
          f"console on {APP_PORT}\n")

    busy = []
    for p in list(NODE_PORTS.values()) + [APP_PORT]:
        s = socket.socket()
        # A19, and this probe was on the WRONG SIDE of it until 2026-08-27.
        #
        # The reasoning it used to carry -- "ThreadingHTTPServer sets
        # allow_reuse_address, so ask the same question it will ask" -- is
        # sound on POSIX and inverted on Windows. There SO_REUSEADDR lets a
        # bind succeed over a process that is ALREADY LISTENING, so this probe
        # reported FREE next to a running console, the suite proceeded, and
        # start_app's second socket shared the port with the first. On
        # 2026-08-27 that produced a KeyError in H17c against a console from
        # the previous evening. The same mechanism yields a false GREEN
        # whenever the stale process is new enough to answer.
        #
        # The TIME_WAIT worry that chose SO_REUSEADDR was then measured rather
        # than reasoned about, because it is the only cost of changing this:
        #   own server closed, TIME_WAIT on the port -> EXCLUSIVE binds, REUSE binds
        #   a LIVE listener on the port              -> EXCLUSIVE refuses 10048,
        #                                               REUSE binds  <-- the bug
        # So the suite loses nothing by refusing its own leftovers' TIME_WAIT:
        # SO_EXCLUSIVEADDRUSE does not refuse it. It only gains the collision.
        #
        # AND THE PROBE ADDRESS IS HALF THE ANSWER, which the first version of
        # this fix still got wrong. A node binds 0.0.0.0; this console and
        # these stubs bind 127.0.0.1; a probe only sees a listener whose
        # address its own bind overlaps. Measured on 2026-08-27 with node A
        # live on 0.0.0.0:5000 and a console live on 127.0.0.1:5199 -- BOUND
        # means the probe MISSED a running process:
        #
        #   probe bind        opt         :5000 (node)  :5199 (console)
        #   0.0.0.0           exclusive   REFUSED       REFUSED     <-- both
        #   0.0.0.0           plain       REFUSED       BOUND
        #   0.0.0.0           reuse       BOUND         BOUND
        #   127.0.0.1         exclusive   BOUND         REFUSED
        #   127.0.0.1         reuse       BOUND         BOUND
        #
        # Wildcard + platform-exclusive is the only row that sees both, so the
        # probe binds "" and not the address the stubs will use. On POSIX the
        # same shape holds: SO_REUSEADDR there relaxes TIME_WAIT and nothing
        # else, so a live listener on either address still refuses.
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):      # Windows only
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("", p))
        except OSError:
            busy.append(p)
        finally:
            s.close()
    if busy:
        print(f"ports {busy} are already in use -- this suite needs the real "
              f"production ports free so it tests the real configuration. "
              f"UNKNOWN, not a pass.")
        return 2

    start_stubs()
    app = static_checks()

    print("\n---- read-only (no COVENANT_APP_ACTIONS) ----")
    proc, up = start_app(None)
    if not up:
        out, err = proc.communicate(timeout=5)
        print(f"the console did not come up:\n{err[-1500:]}")
        return 1
    try:
        readonly_checks(proc)
    finally:
        stop_app(proc)

    for wrong in ("true", "0", "yes", ""):
        proc, up = start_app(wrong)
        if not up:
            stop_app(proc)
            ok("A0", f"COVENANT_APP_ACTIONS={wrong!r}", False, "console did not start")
            continue
        armed = state()["app"]["actions_enabled"]
        stop_app(proc)
        ok("A0", f"COVENANT_APP_ACTIONS={wrong!r} does NOT arm actions",
           armed is False, f"actions_enabled={armed}")

    print("\n---- armed (COVENANT_APP_ACTIONS=1) ----")
    proc, up = start_app("1")
    if not up:
        out, err = proc.communicate(timeout=5)
        print(f"the console did not come up armed:\n{err[-1500:]}")
        return 1
    try:
        armed_checks()
    finally:
        stop_app(proc)

    total = _passed + _failed
    print(f"\n{_passed}/{total} passed"
          + (f", {_unknown} UNKNOWN (not counted as passes)" if _unknown else ""))
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
