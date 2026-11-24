"""Redundant client for TETSU's model doors (2026-11-04, operator: "We need the PCs to
interact without you. There has to be redundancy.").

TETSU's own_consult panel answers on several doors (all port 8300), each on a different
network plane: one on the hosted tailnet (dialed directly) and the headscale planes
(dialed through the laptop's own userspace SOCKS proxies on loopback). This client tries
the configured doors IN ORDER and falls through on connection error or timeout, so a
consult survives any one plane dropping, and it records which door answered.
(A469, 2026-11-22: a consult POST that reached a door and then timed out no longer falls through; it raises
SentNoAnswer, because the question may still be running on the same panel behind every door. A door the request
never reached, an HTTP error reply, and every GET still fall through as above.)

Door ADDRESSES are NOT in this file. The node IPs are the operator's private tailnet
identifiers and must never be committed (the opsec push guard enforces this). They live in
a gitignored config -- `ops/tetsu_doors.json` by default, or the path in the
COVENANT_TETSU_DOORS environment variable -- a JSON list of {"name","base","socks"} where
socks is null to dial directly or "127.0.0.1:PORT" to dial through that SOCKS5 proxy.
`ops/tetsu_doors.example.json` is the tracked template (placeholder addresses only).

Transport is curl (SOCKS5h for the headscale doors, direct for the hosted one); no Python
SOCKS dependency.

The uncensored 27B on the panel GENERATES, never JUDGES; answers are labelled as TETSU
models, never as Tetsu. Per the operator the 27B is unbound: NO token cap by default; the
ceiling is its 6144-token context window.

API (mirrors TETSU's own_consult, commit 7cd5200 in the TETSU repo):
    panel(timeout=6)                      -> {"door", "panel", "attempts"}
    consult(question, models=None, system=None, thinking=False, max_tokens=None)
                                          -> {"door", "result", "attempts"}
    reachable(timeout=6)                  -> [{"door","ok","detail"}, ...]  (diagnostic)
load_doors(path=None)                     -> the configured door list (or [])
Raises NoDoorsConfigured when nothing is configured, AllDoorsDown when none answered.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

CURL = shutil.which("curl") or "curl"
_CODE_SENTINEL = "\n@@HTTP_CODE@@"


class NoDoorsConfigured(Exception):
    """No door config found. Create ops/tetsu_doors.json (see ops/tetsu_doors.example.json)
    or set COVENANT_TETSU_DOORS to its path."""


class AllDoorsDown(Exception):
    """No configured door answered. `attempts` lists {"door","error"} per door tried."""

    def __init__(self, attempts):
        self.attempts = attempts
        super().__init__(
            "no TETSU door answered: "
            + "; ".join("%s=%s" % (a["door"], a["error"]) for a in attempts)
        )


class SentNoAnswer(AllDoorsDown):
    """A469: a POST reached a door and no answer came before the timeout. It is NOT sent to another door: every
    door leads to the same panel, so the question may still be running there, and a second copy would run beside it.
    A subclass of AllDoorsDown, so every caller that handles AllDoorsDown handles this too."""


def _default_config_path():
    return os.environ.get("COVENANT_TETSU_DOORS") or \
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "ops", "tetsu_doors.json")


def load_doors(path=None):
    """Read the gitignored door config. Returns a list of {"name","base","socks"}; [] if the
    file is absent or unreadable (callers raise NoDoorsConfigured when they need doors)."""
    p = path or _default_config_path()
    try:
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return []
    out = []
    for d in data if isinstance(data, list) else []:
        if isinstance(d, dict) and d.get("base"):
            out.append({"name": d.get("name") or d["base"], "base": d["base"], "socks": d.get("socks")})
    return out


def _curl(method, url, socks, timeout, payload=None):
    """One curl request. Returns (http_code, body). http_code 0 means the request did not
    complete (connection refused / timeout / resolve failure) -- the signal to fall through."""
    code, body, _sent = _curl_sent(method, url, socks, timeout, payload)
    return code, body


def _curl_sent(method, url, socks, timeout, payload=None):
    """_curl, plus whether the request's body left for the door: (http_code, body, sent). sent is True when curl
    uploaded bytes (curl's size_upload; measured 2026-11-22: 16 after a send that then timed out, 0 after a refused
    connection), False when it uploaded none, None when that cannot be told (curl itself was killed)."""
    cmd = [CURL, "-s", "-S",
           "--connect-timeout", str(max(1, min(int(timeout), 10))),
           "--max-time", str(int(timeout)),
           "-o", "-", "-w", _CODE_SENTINEL + "%{http_code}|%{size_upload}"]
    if socks:
        cmd += ["--socks5-hostname", socks]
    if method == "POST":
        cmd += ["-X", "POST", "-H", "Content-Type: application/json", "--data-binary", "@-"]
    cmd.append(url)
    # Bytes in and out, decoded HERE as UTF-8 (2026-11-05). text=True decoded with the locale code page
    #   (cp1252 on Windows): a 27B answer carrying a right double quote (E2 80 9D) raised inside
    #   subprocess's reader thread, stdout came back empty, and every door was reported "no response" --
    #   a working door read as a down one. A decode failure is now named as one. Test: TC1 "UTF-8, both ways".
    try:
        p = subprocess.run(cmd, input=(payload or "").encode("utf-8"), capture_output=True,
                           timeout=int(timeout) + 5)
    except subprocess.TimeoutExpired:
        return 0, "timeout", None
    except OSError as e:
        return 0, "curl error: %s" % e, False
    raw = p.stdout or b""
    p_stderr = (p.stderr or b"").decode("utf-8", errors="replace")
    sentinel = _CODE_SENTINEL.encode("ascii")
    idx = raw.rfind(sentinel)
    if idx < 0:
        return 0, (p_stderr or "no response").strip()[:200], None
    code_s, _, up_s = raw[idx + len(sentinel):].decode("ascii", errors="replace").strip().partition("|")
    try:
        sent = int(up_s) > 0
    except ValueError:
        sent = None
    try:
        body = raw[:idx].decode("utf-8")
    except UnicodeDecodeError as e:
        return 0, "decode error: the door answered, but not in UTF-8 (%s)" % e, sent
    try:
        return int(code_s), body, sent
    except ValueError:
        return 0, (p_stderr or "no response").strip()[:200], sent


def _resolve(doors):
    if doors is None:
        doors = load_doors()
    if not doors:
        raise NoDoorsConfigured(
            "no doors configured: create ops/tetsu_doors.json (see ops/tetsu_doors.example.json) "
            "or set COVENANT_TETSU_DOORS")
    return doors


def _try_doors(path, method, timeout, payload=None, doors=None):
    doors = _resolve(doors)
    attempts = []
    for d in doors:
        code, body, sent = _curl_sent(method, d["base"] + path, d.get("socks"), timeout, payload)
        if code == 200:
            try:
                parsed = json.loads(body)
            except ValueError:
                parsed = body
            return d["name"], parsed, attempts
        attempts.append({"door": d["name"], "error": ("http %d" % code) if code else body})
        # A469 (2026-11-22): a POST that LEFT for a door and got no reply is not sent to the next door. Every door
        # leads to the same panel on TETSU, so it may still be running there; the old fall-through ran a slow
        # model's question twice at once (seen: 802 s = 2 x 400, and 0.56 tok/s on a model that does 2.5-5).
        # An HTTP reply (code != 0) or a door the request never reached (sent False) still falls through. A GET
        # (panel, reachable) asks for nothing to be run, so it still falls through on a timeout.
        if method == "POST" and not code and sent is not False:
            attempts[-1]["error"] += " (sent, no answer: not re-sent to another door; it may still be running there)"
            raise SentNoAnswer(attempts)
    raise AllDoorsDown(attempts)


def panel(timeout=6, doors=None):
    """GET /panel from the first door that answers. Returns {"door","panel","attempts"}."""
    name, parsed, attempts = _try_doors("/panel", "GET", timeout, doors=doors)
    panel_map = parsed.get("panel", parsed) if isinstance(parsed, dict) else parsed
    return {"door": name, "panel": panel_map, "attempts": attempts}


def consult(question, models=None, system=None, thinking=False, max_tokens=None,
            timeout=180, doors=None):
    """POST /consult to the first door that answers.

    max_tokens defaults to None -> the field is OMITTED, so the model runs uncapped (the
    operator's rule; the ceiling is the 27B's 6144-token context). Pass an int only to cap
    deliberately. Returns {"door","result","attempts"}."""
    body = {"question": question, "thinking": bool(thinking)}
    if models is not None:
        body["models"] = models
    if system is not None:
        body["system"] = system
    if max_tokens is not None:
        body["max_tokens"] = int(max_tokens)
    name, parsed, attempts = _try_doors("/consult", "POST", timeout, json.dumps(body), doors)
    return {"door": name, "result": parsed, "attempts": attempts}


def reachable(timeout=6, doors=None):
    """Diagnostic: which doors answer /panel right now. [{"door","ok","detail"}, ...]."""
    out = []
    for d in _resolve(doors):
        code, bdy = _curl("GET", d["base"] + "/panel", d.get("socks"), timeout)
        out.append({"door": d["name"], "ok": code == 200,
                    "detail": "ok" if code == 200 else (("http %d" % code) if code else bdy)})
    return out


if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "reach"
    try:
        if cmd == "reach":
            for r in reachable():
                print("%-10s %-4s %s" % (r["door"], "UP" if r["ok"] else "down", r["detail"]))
        elif cmd == "panel":
            print(json.dumps(panel(), indent=1))
        elif cmd == "consult":
            q = sys.argv[2] if len(sys.argv) > 2 else "Reply with the single word READY."
            models = sys.argv[3].split(",") if len(sys.argv) > 3 else None
            print(json.dumps(consult(q, models=models), indent=1))
        else:
            print("usage: covenant_tetsu_client.py [reach | panel | consult <question> [model,model]]")
    except NoDoorsConfigured as e:
        print("not configured: %s" % e)
        sys.exit(2)
