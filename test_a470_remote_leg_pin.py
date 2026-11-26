#!/usr/bin/env python3
"""test_a470_remote_leg_pin.py -- A470: the leg may be served by the second PC, and only the pinned model file.

WHY (2026-11-22, his "Yes, use RTX leg", typed in the HF reply chat). The laptop's 2B leg on :8099 was not running, so
every LEG consult here VOIDed and the 3B answered alone. The second PC's gateway on :8099 serves the same weights
(d725b76f..., byte-identical to the laptop's file) and sends X-Leg-Manifest, a sha256 over weights, runner, flags,
sampler and chat template, as the limbs' gateways do (A402). covenant_leg had a remote switch
(COVENANT_LEG_ALLOW_REMOTE) but no pin, so a remote leg would have been asked whatever model answered there. A470 gives
the leg the limbs' pin: off loopback, no pin set = never asked; a reply whose X-Leg-Manifest does not name the pin =
VOID. Loopback is unchanged.

WHAT IT PINS (every check runs consult_leg with a fake opener in place of the network; none greps the source).
  L1  loopback host, no pin: answered (unchanged behaviour)
  R1  remote host, ALLOW_REMOTE, no pin: None, and the opener is never called
  R2  remote host, pin set, reply names it: answered, and the attribution carries the manifest
  R3  remote host, pin set, reply names another hash: None
  R4  remote host, pin set, reply carries no header: None
  R5  remote host, a pin that is not 64 characters: None, opener never called
  R6  remote host without ALLOW_REMOTE: None, opener never called (the older guard still stands)
  F1  private/leg.json (pointed to by COVENANT_LEG_FILE) supplies host, pin and remote switch: answered
  F2  the file's pin holds: another hash is VOID
  F3  a file without "allow_remote": true: never asked
  F4  an environment variable wins over the file
  F5  an unreadable file is no file: the loopback default
  Every check points COVENANT_LEG_FILE somewhere, so this machine's own private/leg.json never decides a result.
  M1  mutation (the real source, that one line replaced by `if False:`): the header comparison removed -> R3's wrong
      hash is answered (the pin is what refuses it)
  M2  mutation (likewise): the no-pin refusal removed -> R1 reaches the gateway
  M2b (2026-11-23, A474): with the policy check added, the no-pin line removed ALONE no longer reaches the gateway;
      M2 as run since then removes both lines (the M2 line above is kept as first written)

WHAT IT CANNOT SEE. The real gateway, the network, or that the gateway's hash is honest: the pin proves the gateway
NAMED the agreed file, as the limbs' pin does; it cannot prove what the far machine actually ran. Measured live on
2026-11-22 (not by this suite): right pin answered "5" from leg-qwen3.5-2b-uncensored; wrong pin and no pin VOIDed.
"""
import importlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
results = []
PIN = "af5610ac749131db122e79f5f5c806af2497925e0ac90b08f64e8f0e5f6a9605"
REPLY = b'{"model": "leg-test", "choices": [{"message": {"content": "five"}}]}'


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:200]), flush=True)


class _Resp(io.BytesIO):
    def __init__(self, body, headers):
        super().__init__(body)
        self.headers = headers
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Opener:
    def __init__(self, headers):
        self.headers, self.calls = headers, 0

    def open(self, req, timeout=None):
        self.calls += 1
        return _Resp(REPLY, self.headers)


NO_FILE = os.path.join(HERE, "no-such-dir-a470", "leg.json")      # never the machine's real private/leg.json
# A474: a remote consult also needs its pin approved in ops/leg_policy.json. These checks are about the A470 pin and
# header logic, so they run against a TEST policy approving PIN (never the real file, which approves the live hash).
import json as _json, tempfile as _tf
POLICY = os.path.join(_tf.mkdtemp(prefix="a470pol_"), "leg_policy.json")
with open(POLICY, "w", encoding="utf-8") as _fh:
    _json.dump({"leg": {"remote_allowed": True, "approved_manifests": [PIN]}, "limbs": {}}, _fh)


def run(env, headers, mutate=None):
    """Load covenant_leg fresh under env, swap in a fake opener, ask once. -> (result, opener calls).
    COVENANT_LEG_FILE points at a file that does not exist unless the check names one, so this machine's own
    private/leg.json (which holds a real pin) can never make a check pass or fail."""
    keep = {k: os.environ.get(k) for k in ("COVENANT_LEG_HOST", "COVENANT_LEG_PORT", "COVENANT_LEG_ALLOW_REMOTE",
                                           "COVENANT_LEG_MANIFEST", "COVENANT_LEG_LIVE", "COVENANT_LEG_FILE")}
    try:
        for k in keep:
            os.environ.pop(k, None)
        os.environ["COVENANT_LEG_FILE"] = NO_FILE
        os.environ.update(env)
        import covenant_leg as L
        L = importlib.reload(L)
        if mutate:
            mutate(L)
        L.POLICY_PATH = POLICY                  # A474: after any mutation, which re-runs the module's top level
        op = _Opener(headers)
        L._no_redirect = op
        out = L.consult_leg("q", max_tokens=5, timeout=5)
        return out, op.calls
    finally:
        for k, v in keep.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v


REMOTE = {"COVENANT_LEG_HOST": "192.0.2.9", "COVENANT_LEG_PORT": "8099", "COVENANT_LEG_ALLOW_REMOTE": "1"}

out, n = run({"COVENANT_LEG_HOST": "127.0.0.1"}, {})
check("L1 loopback, no pin: answered as before", out is not None and out[0] == "five" and n == 1, (out, n))

out, n = run(dict(REMOTE), {"X-Leg-Manifest": PIN})
check("R1 remote with no pin: never asked", out is None and n == 0, (out, n))

out, n = run(dict(REMOTE, COVENANT_LEG_MANIFEST=PIN), {"X-Leg-Manifest": PIN})
check("R2 remote, reply names the pin: answered, manifest in the attribution",
      out is not None and out[0] == "five" and out[1].get("manifest") == PIN, out)

out, n = run(dict(REMOTE, COVENANT_LEG_MANIFEST=PIN), {"X-Leg-Manifest": "0" * 64})
check("R3 remote, reply names another hash: VOID", out is None and n == 1, (out, n))

out, n = run(dict(REMOTE, COVENANT_LEG_MANIFEST=PIN), {})
check("R4 remote, reply carries no manifest: VOID", out is None and n == 1, (out, n))

out, n = run(dict(REMOTE, COVENANT_LEG_MANIFEST=PIN[:20]), {"X-Leg-Manifest": PIN})
check("R5 remote, a pin that is not a sha256: never asked", out is None and n == 0, (out, n))

out, n = run({"COVENANT_LEG_HOST": "192.0.2.9", "COVENANT_LEG_MANIFEST": PIN}, {"X-Leg-Manifest": PIN})
check("R6 remote without ALLOW_REMOTE: never asked (the older guard stands)", out is None and n == 0, (out, n))


# The file route: what every node process reads, so a node the watchdog revives is wired like one a restart starts.
import json
import tempfile
tmpd = tempfile.mkdtemp(prefix="a470_")


def leg_file(d):
    p = os.path.join(tmpd, "leg_%d.json" % len(os.listdir(tmpd)))
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(d, fh)
    return p


FILE_OK = {"host": "192.0.2.9", "port": 8099, "manifest_sha256": PIN, "allow_remote": True}
out, n = run({"COVENANT_LEG_FILE": leg_file(FILE_OK)}, {"X-Leg-Manifest": PIN})
check("F1 host, pin and remote switch from the file: answered with the manifest",
      out is not None and out[1].get("manifest") == PIN, (out, n))
out, n = run({"COVENANT_LEG_FILE": leg_file(FILE_OK)}, {"X-Leg-Manifest": "0" * 64})
check("F2 the file's pin holds: another hash is VOID", out is None and n == 1, (out, n))
out, n = run({"COVENANT_LEG_FILE": leg_file(dict(FILE_OK, allow_remote=False))}, {"X-Leg-Manifest": PIN})
check("F3 a file without allow_remote true: never asked", out is None and n == 0, (out, n))
out, n = run({"COVENANT_LEG_FILE": leg_file(FILE_OK), "COVENANT_LEG_HOST": "127.0.0.1"}, {})
check("F4 the environment wins over the file: loopback, answered without a manifest", out is not None and n == 1, (out, n))
bad = os.path.join(tmpd, "bad.json")
open(bad, "w").write("{not json")
out, n = run({"COVENANT_LEG_FILE": bad}, {})
check("F5 an unreadable file is no file: the loopback default", out is not None and n == 1, (out, n))

# ---- A472: the findings of Codex's audit, each verified on the A470 code before the fix
import subprocess
import urllib.request as _ur

# S1: the header must EQUAL the pin -- a header carrying another hash and the pin together passed the old substring test
out, n = run(dict(REMOTE, COVENANT_LEG_MANIFEST=PIN), {"X-Leg-Manifest": "0" * 64 + "," + PIN})
check("S1 a header with another hash AND the pin: VOID (exact equality)", out is None and n == 1, (out, n))

# S2: no proxy, ever: the opener carries ProxyHandler({}) (an env proxy at import would otherwise carry a private ask)
import covenant_leg as _L0
_L0 = importlib.reload(_L0)
_ph = [h for h in _L0._no_redirect.handlers if isinstance(h, _ur.ProxyHandler)]
_env_proxy = subprocess.run([sys.executable, "-c", "import covenant_leg as L, urllib.request as u; "
                             "print([h.proxies for h in L._no_redirect.handlers if isinstance(h, u.ProxyHandler)])"],
                            cwd=HERE, capture_output=True, text=True,
                            env=dict(os.environ, http_proxy="http://192.0.2.1:3128", HTTP_PROXY="http://192.0.2.1:3128",
                                     COVENANT_LEG_FILE=NO_FILE)).stdout.strip()
check("S2 with http_proxy set at import, the leg's opener still has no proxy", _env_proxy in ("[]", "[{}]"), _env_proxy)

# S3: a SET environment switch decides: ALLOW_REMOTE=0 beats the file's allow_remote: true; an empty pin beats the file's
out, n = run({"COVENANT_LEG_FILE": leg_file(FILE_OK), "COVENANT_LEG_ALLOW_REMOTE": "0"}, {"X-Leg-Manifest": PIN})
check("S3 file allow_remote true + env ALLOW_REMOTE=0: never asked", out is None and n == 0, (out, n))
out, n = run({"COVENANT_LEG_FILE": leg_file(FILE_OK), "COVENANT_LEG_MANIFEST": ""}, {"X-Leg-Manifest": PIN})
check("S3b file pin + env MANIFEST set empty: never asked (the empty pin decides)", out is None and n == 0, (out, n))

# S4: a text port in the file does not crash the import (it crashed covenant_leg AND covenant_limbs before)
_bad = leg_file({"host": "192.0.2.9", "port": "abc", "allow_remote": True, "manifest_sha256": PIN})
_r = subprocess.run([sys.executable, "-c", "import covenant_leg as L, covenant_limbs; print(L.LEG_PORT)"],
                    cwd=HERE, capture_output=True, text=True, env=dict(os.environ, COVENANT_LEG_FILE=_bad))
check("S4 a text port in the file: both modules import, the port is the default", _r.returncode == 0 and _r.stdout.strip() == "8099",
      (_r.returncode, _r.stdout.strip(), _r.stderr.strip()[-120:]))

# S5: one overall deadline for the body -- a server that drips bytes just inside each socket timeout is cut off
class _Drip(_Resp):
    """Like a real socket-backed response from a server that drips one byte every 0.4 s: read(n) BLOCKS until n bytes
    (here: gives up after 6 s), read1(n) returns the one byte that has arrived."""
    def read(self, n=-1):
        t0 = time.time(); got = b""
        while (n < 0 or len(got) < n) and time.time() - t0 < 6:
            time.sleep(0.4); got += b"x"
        return got

    def read1(self, n=-1):
        time.sleep(0.4)
        return b"x"


class _DripOpener(_Opener):
    def open(self, req, timeout=None):
        self.calls += 1
        return _Drip(b"", self.headers)


def run_drip(env):
    keep = {k: os.environ.get(k) for k in ("COVENANT_LEG_HOST", "COVENANT_LEG_ALLOW_REMOTE", "COVENANT_LEG_MANIFEST", "COVENANT_LEG_FILE")}
    try:
        for k in keep:
            os.environ.pop(k, None)
        os.environ["COVENANT_LEG_FILE"] = NO_FILE; os.environ.update(env)
        import covenant_leg as L
        L = importlib.reload(L); L.POLICY_PATH = POLICY; L._no_redirect = _DripOpener({"X-Leg-Manifest": PIN})
        t0 = time.time(); out = L.consult_leg("q", max_tokens=5, timeout=1)
        return out, time.time() - t0
    finally:
        for k, v in keep.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v


import time
out, secs = run_drip(dict(REMOTE, COVENANT_LEG_MANIFEST=PIN))
check("S5 a dripping server is cut off at the overall deadline (timeout 1 s)", out is None and secs < 2.5, (out, round(secs, 2)))

# Mutations: the real source with one A470 line changed, loaded as its own module, run the same way. Each must let
# through what its check refuses -- or the check is not what refuses it.
def mutant(old, new):
    src = open(os.path.join(HERE, "covenant_leg.py"), encoding="utf-8").read()
    assert src.count(old) == 1, "mutation target not found exactly once: %r" % old
    code = compile(src.replace(old, new), "covenant_leg_mutant", "exec")

    def apply(L):
        exec(code, L.__dict__)                  # same module object, mutated functions
    return apply


m1 = mutant("if remote and manifest_hex(served_manifest) != pin:", "if False:")
out, n = run(dict(REMOTE, COVENANT_LEG_MANIFEST=PIN), {"X-Leg-Manifest": "0" * 64}, mutate=m1)
check("M1 header comparison removed: R3's wrong hash is answered", out is not None and n == 1, (out, n))

# M2 as first written (2026-11-22) removed only the no-pin line and expected R1 to reach the gateway. Since A474 the
# policy check also refuses an empty pin, so that mutant is now refused by the second layer: M2b records exactly that,
# and M2 removes BOTH lines to show that together they are what refuses R1 (2026-11-23).
def mutant2(pairs):
    src = open(os.path.join(HERE, "covenant_leg.py"), encoding="utf-8").read()
    for old, new in pairs:
        assert src.count(old) == 1, "mutation target not found exactly once: %r" % old
        src = src.replace(old, new)
    code = compile(src, "covenant_leg_mutant", "exec")
    return lambda L: exec(code, L.__dict__)


m2b = mutant("if remote and len(pin) != 64:", "if False:")
out, n = run(dict(REMOTE), {"X-Leg-Manifest": ""}, mutate=m2b)
check("M2b no-pin refusal removed alone: R1 is still never asked (A474's policy layer holds)", out is None and n == 0, (out, n))

m2 = mutant2([("if remote and len(pin) != 64:", "if False:"), ('if remote and not approved("leg", pin):', "if False:")])
out, n = run(dict(REMOTE), {"X-Leg-Manifest": ""}, mutate=m2)
check("M2 no-pin refusal AND policy check removed: R1 reaches the gateway", n == 1, (out, n))

print("\nA470: %d/%d passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
