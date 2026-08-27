"""covenant_app.py -- the operational console. One page instead of fifteen .bat files.

WHAT IT IS.  A small HTTP server that runs beside the nodes, polls them, and
serves a single live page: every node's version, source hash, height, peers,
judge and warnings; the watchdog's pulse; the anomaly kinds; memory against the
judge's footprint; and -- when explicitly enabled -- the buttons for the things
that are currently a double-click and a text file, plus the transaction path.

FOUR RULES ARE STRUCTURAL, NOT CONFIGURABLE.

1. **LOOPBACK ONLY.** BIND_HOST is 127.0.0.1 and `main()` refuses to start if
   anything has changed it. There is no environment variable that moves it.
   This console can restart nodes and sign transactions; a console that can do
   that must not be one env var away from the network. If you want it on your
   phone, that is a different app with an auth story, and it should be built as
   one rather than reached by flipping a string here.

2. **ACTIONS ARE A FIXED ALLOWLIST, NEVER A COMMAND STRING.** ACTIONS maps a
   name to a script that already exists in this folder. Nothing in any request
   reaches a shell, an argument list, or a path. An ops console that can run an
   arbitrary string is a remote shell with a nicer font.

3. **ACTIONS ARE OFF UNTIL OPTED IN, AND THE OPT-IN IS ONE-WAY.** Only the exact
   string COVENANT_APP_ACTIONS=1 arms them; no value of it relaxes anything
   else. Same shape as COVENANT_FORCE_NO_SANDBOX (P4/P10) and
   COVENANT_REQUIRE_JUDGE_DIVERSITY (B2) -- nothing turns a control OFF from the
   environment.

4. **THE SIGNING KEY NEVER LEAVES THIS PROCESS.** It is read at the moment of
   signing, used, and dropped. It is never logged, never put in a response,
   never rendered. The browser sends "from A, to B, amount 5"; this process
   does the crypto. `/api/state` is asserted key-free by the suite.

AND IT DESCRIBES ITSELF, because P15 counted the long-lived processes on this
machine and found the fourth one -- ollama -- reporting nothing. This is the
fifth. So it prints its own source hash and line count at boot (P11), writes a
line to logs/app.log at least every 60 seconds even when nothing changes, and
states that bound in the banner so a longer gap is readable as death rather
than calm (P16).

WHAT IT DELIBERATELY DOES NOT DO.
  * It does not poll /chain. That route is rate-limited to 20 reads per 60s per
    node (M11) and a browser refreshing every two seconds would exhaust it and
    make a converged network look split. Height comes from /health.
  * It does not touch the XRP path. Those four locks are elsewhere and stay shut.
  * It does not restart itself, reconfigure anything, or write to any node's
    database.

    python covenant_app.py                 read-only
    COVENANT_APP_ACTIONS=1 covenant_app.py buttons live
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__)) or "."

# ---- rule 1. Not a setting. ------------------------------------------------
BIND_HOST = "127.0.0.1"
PORT = int(os.environ.get("COVENANT_APP_PORT", "5199"))

NODES = [("A", 5000), ("B", 5020), ("C", 5060)]
POLL_TTL = 2.5              # seconds a cached /health is served for
WATCHDOG_LOG = os.path.join(HERE, "logs", "watchdog.log")
APP_LOG = os.path.join(HERE, "logs", "app.log")
HEARTBEAT_S = 60            # the bound stated in the banner (P16)

# ---- rule 2. A name, not a command. ---------------------------------------
# The ORDER is the operator's reach, not the alphabet, and RISK is rendered.
# An interface that draws "run the twelve gates, which change nothing" and
# "stop all three production nodes" as the same button trains its reader to
# click without reading -- which is M34 arriving through the front door instead
# of through a permanently-firing alert.
#
#   read    touches nothing; safe to click while thinking
#   write   writes a file in this folder; touches no running process
#   system  stops, starts, or re-permissions something that is running
#   long    correct, but it will be a while
ACTIONS = {
    "gates":     ("launch_check.py",        "python", "read",   "Run the twelve gates. Changes nothing."),
    "verify":    ("verify_bundle.py",       "python", "read",   "Hash every shipped file against the manifest."),
    "config3":   ("test_3node_config.py",   "python", "read",   "Assert the three-node topology in the files that ship."),
    "portdiag":  ("AD_DIAG_PORTS.bat",      "bat",    "read",   "What is listening on the covenant port block."),
    "ports":     ("AO_PORT_PICK.bat",       "bat",    "read",   "Bind-probe 5000-5400 for free port blocks."),
    "dashboard": ("dashboard_render.py",    "python", "write",  "Render dashboard.html, the 3D mesh view."),
    "restart":   ("AB_RESTART_NODES.bat",   "bat",    "system", "Stop and start all three nodes and the watchdog. Refuses if the judge is not answering (P17)."),
    "aclfix":    (os.path.join("ops", "fix_key_acl.bat"), "bat", "system", "Tighten the NTFS ACL on the key files. Only ever removes access."),
    "sweep":     ("run_local_sweep.py",     "python", "long",   "The full suite sweep. 30 to 45 minutes, and it exercises the live nodes."),
}
ACTIONS_ON = os.environ.get("COVENANT_APP_ACTIONS") == "1"

_lock = threading.Lock()
_cache: dict = {}
_running: dict = {}          # action name -> {started, rc, tail}
_started = time.time()


def _self_id():
    try:
        with open(os.path.abspath(__file__), "rb") as fh:
            b = fh.read()
        return hashlib.sha256(b).hexdigest()[:12], b.count(b"\n") + 1
    except Exception as e:                      # never stop the app over this
        return f"unavailable ({e.__class__.__name__})", 0


SELF_SHA, SELF_LINES = _self_id()


def log(level, msg):
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {level:<5} {msg}"
    try:
        os.makedirs(os.path.dirname(APP_LOG), exist_ok=True)
        with open(APP_LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass
    print(line, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- node polling
def _get(port, path, timeout=4.0):
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}{path}",
                                     headers={"User-Agent": "covenant-app/1"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode()), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, e.__class__.__name__


def poll_node(nid, port):
    key = ("node", nid)
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < POLL_TTL:
            return hit[1]
    health, herr = _get(port, "/health")
    anom, _ = _get(port, "/anomalies", timeout=3.0)
    out = {
        "id": nid, "port": port,
        "up": health is not None,
        "error": herr,
        "health": health or {},
        "anomalies": (anom or {}).get("per_kind", {}),
    }
    with _lock:
        _cache[key] = (now, out)
    return out


def disk_source():
    p = os.path.join(HERE, "covenant_unified_v8.py")
    try:
        with open(p, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()[:12]
    except Exception:
        return None


def watchdog_pulse():
    try:
        mt = os.path.getmtime(WATCHDOG_LOG)
        with open(WATCHDOG_LOG, "rb") as fh:
            fh.seek(max(0, os.path.getsize(WATCHDOG_LOG) - 8192))
            tail = fh.read().decode("utf-8", "replace").strip().splitlines()
        recent = [t for t in tail[-40:] if " ALERT " in t]
        return {"age_s": int(time.time() - mt),
                "bound_s": 60,
                "last": tail[-1][:200] if tail else "",
                "alerts": [a[:220] for a in recent[-6:]]}
    except Exception as e:
        return {"age_s": None, "bound_s": 60, "last": "",
                "alerts": [], "error": e.__class__.__name__}


def build_state():
    nodes = [poll_node(nid, port) for nid, port in NODES]
    disk = disk_source()
    for n in nodes:
        h = n["health"]
        n["agrees_with_disk"] = bool(disk and h.get("source_sha256") == disk)
    heights = [n["health"].get("chain_height") for n in nodes if n["up"]]
    # ---- the ethics review queue, aggregated across nodes.
    #
    # Transactions the ethics model could not READ -- not ones it found fault
    # with. They are stopped, nothing has been alleged against any of them, and
    # they are waiting on a person. That person is whoever is reading this
    # page, which is the only reason this panel exists: a hold nobody sees is
    # not a safeguard, it is a pile, and a pile with no owner and no bound
    # grows until it is somebody's rent.
    #
    # Present only once a node's /health carries `ethics_review` (v8.38). Until
    # then this is absent rather than zero -- an empty queue and no queue are
    # different claims and only one of them is good news.
    review = None
    for n in nodes:
        r = n["health"].get("ethics_review")
        if not isinstance(r, dict):
            continue
        if review is None:
            review = {"open_holds": 0, "overdue": 0, "oldest_hold_s": 0,
                      "by_script": {}, "review_bound_s": r.get("review_bound_s", 0),
                      "cleared": 0, "cleared_unqualified": 0,
                      "coverable": {}, "nobody_can_read": {}, "nodes": []}
        review["open_holds"] += int(r.get("open_holds", 0))
        review["overdue"] += int(r.get("overdue", 0))
        review["oldest_hold_s"] = max(review["oldest_hold_s"],
                                      int(r.get("oldest_hold_s", 0)))
        for k, v in (r.get("by_script") or {}).items():
            review["by_script"][k] = review["by_script"].get(k, 0) + int(v)
        review["cleared"] += int(r.get("cleared", 0))
        review["cleared_unqualified"] += int(r.get("cleared_unqualified", 0))
        # who in the mesh can answer for what. A script that appears here can
        # be cleared by somebody; one in nobody_can_read is the whole network's
        # debt, and the next language anyone should fit.
        for k, v in (r.get("coverable") or {}).items():
            e = review["coverable"].setdefault(k, {"holds": 0, "can_clear": []})
            e["holds"] += int(v.get("holds", 0))
            for w in v.get("can_clear", []):
                if w not in e["can_clear"]:
                    e["can_clear"].append(w)
        for k, v in (r.get("nobody_can_read") or {}).items():
            review["nobody_can_read"][k] = review["nobody_can_read"].get(k, 0) + int(v)
        review["nodes"].append(n["id"])
    return {
        "when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "app": {"sha": SELF_SHA, "lines": SELF_LINES,
                "uptime_s": int(time.time() - _started),
                "bind": f"{BIND_HOST}:{PORT}",
                "actions_enabled": ACTIONS_ON,
                "heartbeat_s": HEARTBEAT_S},
        "disk_source": disk,
        "nodes": nodes,
        "watchdog": watchdog_pulse(),
        "ethics_review": review,
        "converged": bool(heights) and len(set(heights)) == 1,
        "heights": heights,
        "actions": {k: {"script": v[0], "risk": v[2], "desc": v[3]}
                    for k, v in ACTIONS.items()},
        # Explicit, because a JSON object is not a promise about order.
        "action_order": list(ACTIONS),
        "running": dict(_running),
    }


# ------------------------------------------------------------------- actions
def run_action(name):
    if not ACTIONS_ON:
        return {"ok": False, "error":
                "Actions are off. Start the app with COVENANT_APP_ACTIONS=1 "
                "-- and only that exact value arms them."}
    if name not in ACTIONS:
        return {"ok": False, "error": f"unknown action {name!r}"}
    script, kind, _risk, _desc = ACTIONS[name]
    path = os.path.join(HERE, script)
    if not os.path.exists(path):
        return {"ok": False, "error": f"{script} is not in this folder"}
    with _lock:
        if _running.get(name, {}).get("state") == "running":
            return {"ok": False, "error": f"{name} is already running"}
        _running[name] = {"state": "running", "started": time.time(),
                          "script": script, "rc": None, "tail": ""}

    def worker():
        # stdin=DEVNULL is load-bearing (M44): several of these .bat files end
        # in `pause`, and without it the child waits for a keypress that can
        # never arrive and the caller reports a working run as a failure.
        cmd = ([sys.executable, path] if kind == "python"
               else ["cmd", "/c", path] if os.name == "nt" else [path])
        try:
            p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True,
                               timeout=3600, shell=False,
                               stdin=subprocess.DEVNULL)
            out = (p.stdout or "") + (p.stderr or "")
            rc, tail = p.returncode, "\n".join(out.strip().splitlines()[-40:])
        except Exception as e:
            rc, tail = -1, f"{e.__class__.__name__}: {e}"
        with _lock:
            _running[name] = {"state": "done", "started": _running[name]["started"],
                              "finished": time.time(), "script": script,
                              "rc": rc, "tail": tail[-6000:]}
        log("INFO", f"action {name} ({script}) finished rc={rc}")

    log("INFO", f"action {name} ({script}) started")
    threading.Thread(target=worker, daemon=True).start()
    return {"ok": True, "started": name}


# -------------------------------------------------------------- the tx path
def _covenant():
    """Import the node module lazily. It is a 9,800-line import and the console
    must still serve a page on a machine where it will not load."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import covenant_unified_v8 as cov  # noqa: E402
    return cov


def _load_key(nid):
    """Read a node identity key at the moment of signing. It is never returned,
    never logged and never cached -- DEPLOYMENT.md calls this file the operator
    credential and the genesis mint key, and it is treated as one."""
    from cryptography.hazmat.primitives import serialization
    kp = os.path.join(HERE, f"node{nid}_prod.db.key")
    if not os.path.exists(kp):
        raise FileNotFoundError(f"no identity key for node {nid}")
    with open(kp, "rb") as fh:
        return serialization.load_pem_private_key(fh.read(), password=None)


_pub_cache: dict = {}


def _pub_pem(nid):
    """A node's PUBLIC key PEM -- the half that rides inside a transaction.

    The private half is loaded here, used to derive the public part, and
    dropped when this function returns. THE CACHE HOLDS ONLY THE PUBLIC PEM.
    The earlier shape of this called _load_key three times for one transfer
    (sender to sign, sender to name, receiver to name) -- two of which needed
    nothing but a public key. Touching a private key you do not need is not a
    vulnerability, it is a habit that becomes one."""
    from cryptography.hazmat.primitives import serialization
    with _lock:
        hit = _pub_cache.get(nid)
    if hit:
        return hit
    pem = _load_key(nid).public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    with _lock:
        _pub_cache[nid] = pem
    return pem


def submit_tx(sender, receiver, amount, memo):
    if not ACTIONS_ON:
        return {"ok": False, "error": "Actions are off (COVENANT_APP_ACTIONS=1)."}
    ports = dict(NODES)
    for who, nid in (("from", sender), ("to", receiver)):
        if nid not in ports:
            return {"ok": False, "error": f"{who} node {nid!r} is not one of "
                                          f"{sorted(ports)}"}
    cov = _covenant()
    port = ports[sender]
    # benefit_score is NOT guessed. The governor's drift band is what decides
    # whether a block carrying this is acceptable; substituting a plausible
    # number for one we could not read is how a console starts lying quietly.
    align, aerr = _get(port, "/alignment")
    cur = (align or {}).get("current_alignment")
    if cur is None:
        return {"ok": False, "error":
                f"cannot read /alignment on node {sender} ({aerr or 'no value'}). "
                f"benefit_score would be a guess, and a guess here is either "
                f"refused by the drift band or drags it. Fix the node first."}
    benefit = float(cur)
    sk = _load_key(sender)
    pem = _pub_pem(sender)
    to_pem = _pub_pem(receiver)
    reg = cov.RegistrationPoW.generate(pem, cov.BASE_REGISTRATION_DIFFICULTY)
    data = {"origin": "human"}
    if memo:
        data["memo"] = str(memo)[:512]
    tx = cov.Transaction(sender_pubkey=pem, receiver=to_pem, data=data,
                         amount=float(amount), benefit_score=benefit,
                         reg_nonce=reg)
    tx.sign(sk)
    body = {"sender_pubkey": pem, "receiver": to_pem, "data": data,
            "amount": float(amount), "timestamp": tx.timestamp,
            "benefit_score": benefit, "signature": tx.signature,
            "reg_nonce": reg}
    log("INFO", f"tx {sender}->{receiver} {amount} submitted for judging")
    st, js = _post(port, "/transactions", body, timeout=420)
    return {"ok": st == 200, "status": st, "response": js,
            "note": "the ethics judge runs inside this call; a warm verdict is "
                    "~12.8s and a cold model load is ~39.9s"}


def mine(nid):
    if not ACTIONS_ON:
        return {"ok": False, "error": "Actions are off (COVENANT_APP_ACTIONS=1)."}
    ports = dict(NODES)
    if nid not in ports:
        return {"ok": False, "error": f"node {nid!r} is not one of {sorted(ports)}"}
    cov = _covenant()
    port = ports[nid]
    sk = _load_key(nid)
    pem = _pub_pem(nid)
    raw = b"{}"
    hdrs = cov.sign_operator_request(sk, pem, "POST", "/mine", raw)
    hdrs["Content-Type"] = "application/json"
    log("INFO", f"mine requested on node {nid}")
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/mine", data=raw,
                                     method="POST", headers=hdrs)
        with urllib.request.urlopen(req, timeout=600) as r:
            return {"ok": True, "status": r.status,
                    "response": json.loads(r.read().decode())}
    except urllib.error.HTTPError as e:
        try:
            js = json.loads(e.read().decode())
        except Exception:
            js = {}
        return {"ok": False, "status": e.code, "response": js}
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}


def _post(port, path, body, timeout=60):
    raw = json.dumps(body).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=raw,
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
    except Exception as e:
        return 0, {"error": f"{e.__class__.__name__}: {e}"}


# ------------------------------------------------------------------- server
PAGE = None   # filled at import from covenant_app_page.html if present


class Handler(BaseHTTPRequestHandler):
    server_version = "covenant-app"

    def log_message(self, fmt, *args):
        pass                      # the app writes its own log; this one is noise

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        # This page never loads anything from anywhere. Say so.
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; style-src 'unsafe-inline'; "
                         "script-src 'unsafe-inline'; connect-src 'self'")
        self.end_headers()
        self.wfile.write(b)

    def _guard(self):
        """Rule 1, enforced per request as well as at bind. A proxy or a
        forwarded port cannot turn this into a network service."""
        host = self.client_address[0]
        if host not in ("127.0.0.1", "::1"):
            self._send(403, json.dumps({"error": "loopback only"}))
            return False
        return True

    def do_GET(self):
        if not self._guard():
            return
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            return self._send(200, page_html(), "text/html")
        if p == "/api/state":
            return self._send(200, json.dumps(build_state()))
        if p == "/api/identity":
            return self._send(200, json.dumps(
                {"sha": SELF_SHA, "lines": SELF_LINES,
                 "actions_enabled": ACTIONS_ON, "bind": f"{BIND_HOST}:{PORT}"}))
        return self._send(404, json.dumps({"error": "no such route"}))

    def do_POST(self):
        if not self._guard():
            return
        p = self.path.split("?")[0]
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n).decode() or "{}")
        except Exception:
            body = {}
        if p.startswith("/api/action/"):
            return self._send(200, json.dumps(run_action(p.rsplit("/", 1)[-1])))
        if p == "/api/tx":
            try:
                r = submit_tx(body.get("from", "A"), body.get("to", "B"),
                              float(body.get("amount", 1)), body.get("memo", ""))
            except Exception as e:
                r = {"ok": False, "error": f"{e.__class__.__name__}: {e}"}
            return self._send(200, json.dumps(r))
        if p == "/api/mine":
            try:
                r = mine(body.get("node", "A"))
            except Exception as e:
                r = {"ok": False, "error": f"{e.__class__.__name__}: {e}"}
            return self._send(200, json.dumps(r))
        return self._send(404, json.dumps({"error": "no such route"}))


def page_html():
    p = os.path.join(HERE, "covenant_app_page.html")
    try:
        with open(p, encoding="utf-8") as fh:
            return fh.read()
    except Exception as e:
        return (f"<title>Covenant Console</title><body style='font-family:monospace'>"
                f"<h1>covenant_app_page.html is missing</h1><p>{e}</p>"
                f"<p>The server is fine; the page file is not beside it.</p>")


def heartbeat():
    """P16 applied to this process. A line at least every HEARTBEAT_S even when
    nothing changes, so a longer gap in logs/app.log reads as death, not calm."""
    last = 0.0
    while True:
        time.sleep(5)
        if time.time() - last >= HEARTBEAT_S:
            st = build_state()
            up = [n["id"] for n in st["nodes"] if n["up"]]
            log("INFO", f"alive; nodes up {up or 'none'}; heights {st['heights']}; "
                        f"converged={st['converged']}; actions={ACTIONS_ON}")
            last = time.time()


class ExclusiveHTTPServer(ThreadingHTTPServer):
    """A19, carried to the console (2026-08-27).

    `HTTPServer` sets `allow_reuse_address = 1`, and on Windows that option is
    not POSIX's: it lets this process bind a port ANOTHER PROCESS IS ALREADY
    LISTENING ON. Both then sit in the accept queue and a client reaches an
    arbitrary one. The node fixed this in v8.30 (`_bind_exclusive`); the
    console shipped six days later without it.

    Measured here, not reasoned: on 2026-08-27 a console from 20:18 the
    previous evening (`48fff56ce81c`, 530 lines, no `ethics_review` field) was
    still listening on 5199. A second console started from the CURRENT source
    (`85ab6fb48bf5`, 573 lines) bound the same port with no error, `netstat`
    showed both LISTENING, and `/api/state` was answered by the OLD one --
    which is how `test_covenant_app.py` came to fail H17c with a KeyError
    against a build that predated the field it was testing for. A false RED
    that morning; the same mechanism yields a false GREEN whenever the stale
    process happens to be new enough to answer.

    The console's existing OSError handler already prints the right message.
    This is only what makes the OSError actually happen.
    """

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):      # Windows only
            self.allow_reuse_address = 0
            self.socket.setsockopt(socket.SOL_SOCKET,
                                   socket.SO_EXCLUSIVEADDRUSE, 1)
        # On POSIX nothing changes: SO_REUSEADDR is what lets a restart
        # reclaim its own port out of TIME_WAIT, and Linux already refuses a
        # live second listener on the same address.
        return super().server_bind()


def main():
    # Rule 1, asserted rather than trusted.
    if BIND_HOST not in ("127.0.0.1", "localhost"):
        print(f"REFUSING TO START: BIND_HOST is {BIND_HOST!r}. This console can "
              f"restart nodes and sign transactions; it binds loopback or it "
              f"does not run.", file=sys.stderr)
        return 2
    try:
        srv = ExclusiveHTTPServer((BIND_HOST, PORT), Handler)
    except OSError as e:
        print(f"cannot bind {BIND_HOST}:{PORT} -- {e}\n"
              f"Set COVENANT_APP_PORT to a free port; AO_PORT_PICK.bat finds one.",
              file=sys.stderr)
        return 1
    srv.daemon_threads = True
    banner = (f"Covenant console {SELF_SHA} ({SELF_LINES} lines) on "
              f"http://{BIND_HOST}:{PORT}  --  actions "
              f"{'ENABLED' if ACTIONS_ON else 'OFF (read-only)'}")
    print("=" * len(banner)); print(banner)
    print(f"loopback only, by construction. watching {[n for n, _ in NODES]}.")
    print(f"logs/app.log gets a line at least every {HEARTBEAT_S}s even when "
          f"nothing changes -- A LONGER GAP MEANS THIS PROCESS IS DEAD.")
    print("=" * len(banner), flush=True)
    log("INFO", f"console started {SELF_SHA} on {BIND_HOST}:{PORT}; "
                f"actions={ACTIONS_ON}; heartbeat {HEARTBEAT_S}s")
    threading.Thread(target=heartbeat, daemon=True).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        log("INFO", "console stopped by operator")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
