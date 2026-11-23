#!/usr/bin/env python3
"""test_a474_leg_policy.py -- A474 (2026-11-23, Codex's audit #6, on Lawrence's "fix").

private/leg.json and private/limbs.json are untracked: an edit to one could change the endpoint and the pin together
and pick another model, with nothing in git or the head commitment to show it. A474 lists the approved manifests in the
TRACKED ops/leg_policy.json; a remote consult whose pin is not listed there is refused BEFORE anything is sent.

  P1  leg: the pin is approved -> answered (the control)
  P2  leg: a pin not in the policy (from the private file) -> never asked
  P3  leg: an environment pin not in the policy, though the file's pin is approved -> never asked (env cannot widen)
  P4  leg: policy remote_allowed false -> never asked
  P5  leg: policy missing / malformed / oversize -> never asked (fail closed)
  P6  leg: loopback needs no policy (unchanged)
  P7  limb: an approved pin -> engaged;  P8 an unapproved pin -> VOID, opener never called
  P9  limb: approved for ANOTHER limb only -> VOID (per-limb lists)
  P10 the real ops/leg_policy.json parses and approves the live pins; it holds no IPv4 address
  P11 there is no environment override of the policy path
  M1  mutation: the leg's policy line removed -> P2 reaches the gateway
  M2  mutation: the limb's policy check removed -> P8 reaches the gateway

WHAT IT CANNOT SEE. A gateway that is itself compromised and claims the approved hash (A470's recorded limit: the pin
proves the gateway NAMED the agreed file, not what it ran). An attacker who edits the tracked policy too: that shows in
git and in the head commitment's tree, which is what this binding buys; it does not stop an owner-level edit.
"""
import importlib
import io
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
results = []
PIN = "c3" * 32
OTHER = "d4" * 32
REPLY = b'{"model": "leg-test", "choices": [{"message": {"content": "five"}}]}'
TMP = tempfile.mkdtemp(prefix="a474_")


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:200]), flush=True)


def write(name, obj):
    p = os.path.join(TMP, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(obj if isinstance(obj, str) else json.dumps(obj))
    return p


class _Resp(io.BytesIO):
    def __init__(self, body, headers):
        super().__init__(body)
        self.headers, self.status = headers, 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Opener:
    def __init__(self, headers, body=REPLY):
        self.headers, self.body, self.calls = headers, body, 0

    def open(self, req, timeout=None):
        self.calls += 1
        return _Resp(self.body, self.headers)


POL_OK = write("pol_ok.json", {"leg": {"remote_allowed": True, "approved_manifests": [PIN]},
                               "limbs": {"SMOL": [PIN], "PHI": [OTHER]}})
POL_NOREMOTE = write("pol_noremote.json", {"leg": {"remote_allowed": False, "approved_manifests": [PIN]}})
POL_BAD = write("pol_bad.json", "{not json")
POL_BIG = write("pol_big.json", json.dumps({"leg": {"remote_allowed": True, "approved_manifests": [PIN]},
                                            "pad": "x" * 70000}))
NO_POL = os.path.join(TMP, "absent.json")
ENV_KEYS = ("COVENANT_LEG_HOST", "COVENANT_LEG_PORT", "COVENANT_LEG_ALLOW_REMOTE", "COVENANT_LEG_MANIFEST",
            "COVENANT_LEG_LIVE", "COVENANT_LEG_FILE")


def leg_run(file_obj, policy, env=None, mutate=None):
    keep = {k: os.environ.get(k) for k in ENV_KEYS}
    try:
        for k in keep:
            os.environ.pop(k, None)
        os.environ["COVENANT_LEG_FILE"] = write("leg_%d.json" % len(os.listdir(TMP)), file_obj)
        os.environ.update(env or {})
        import covenant_leg as L
        L = importlib.reload(L)
        if mutate:
            mutate(L)
        L.POLICY_PATH = policy
        op = _Opener({"X-Leg-Manifest": PIN})
        L._no_redirect = op
        return L.consult_leg("q", max_tokens=5, timeout=5), op.calls
    finally:
        for k, v in keep.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v


def mutant(path, old, new):
    src = open(os.path.join(HERE, path), encoding="utf-8").read()
    assert src.count(old) == 1, "mutation target not found exactly once: %r" % old
    code = compile(src.replace(old, new), path + "_mutant", "exec")
    return lambda M: exec(code, M.__dict__)


REMOTE_FILE = {"host": "192.0.2.9", "port": 8099, "manifest_sha256": PIN, "allow_remote": True}

out, n = leg_run(REMOTE_FILE, POL_OK)
check("P1 leg, approved pin: answered", out is not None and out[0] == "five" and n == 1, (out, n))
out, n = leg_run(dict(REMOTE_FILE, manifest_sha256=OTHER), POL_OK)
check("P2 leg, the file's pin is not in the policy: never asked", out is None and n == 0, (out, n))
out, n = leg_run(REMOTE_FILE, POL_OK, {"COVENANT_LEG_MANIFEST": OTHER})
check("P3 leg, an env pin not in the policy (file's pin approved): never asked", out is None and n == 0, (out, n))
out, n = leg_run(REMOTE_FILE, POL_NOREMOTE)
check("P4 leg, policy remote_allowed false: never asked", out is None and n == 0, (out, n))
for tag, pol in (("missing", NO_POL), ("malformed", POL_BAD), ("over 64 KB", POL_BIG)):
    out, n = leg_run(REMOTE_FILE, pol)
    check("P5 leg, policy %s: never asked (fail closed)" % tag, out is None and n == 0, (out, n))
out, n = leg_run({"host": "127.0.0.1"}, NO_POL)
check("P6 leg on loopback: no policy needed (unchanged)", out is not None and n == 1, (out, n))

# limbs
os.environ.setdefault("COVENANT_QUIET", "1")
import covenant_leg as LEG      # noqa: E402
LEG = importlib.reload(LEG)
import covenant_limbs as LM     # noqa: E402
LM = importlib.reload(LM)
GOOD = json.dumps({"answer": "four", "evidence": "arithmetic", "confidence": "high"})
LIMB_BODY = json.dumps({"model": "smollm3", "choices": [{"message": {"content": GOOD}}]}).encode("utf-8")
LEG.LEG_INFLUENCE_LEDGER = os.path.join(TMP, "influence.jsonl")


def limb_run(name, pin, policy, mutate=None):
    if mutate:
        mutate(LM)
    LEG.POLICY_PATH = policy
    LEG.LEG_INFLUENCE_LEDGER = os.path.join(TMP, "influence.jsonl")     # never the live ledger, even after a reload
    cfg = {name: {"url": "http://127.0.0.1:1/v1/chat/completions", "model": "m", "label": name, "manifest_sha256": pin}}
    op = _Opener({"X-Leg-Manifest": pin}, LIMB_BODY)
    r = LM.consult(name, "two plus two?", config=cfg, opener=op)
    return r, op.calls


r, n = limb_run("SMOL", PIN, POL_OK)
check("P7 limb, approved pin: engaged", r["status"] == "engaged" and n == 1, (r["status"], r["why"], n))
r, n = limb_run("SMOL", OTHER, POL_OK)
check("P8 limb, unapproved pin: VOID, nothing sent", r["status"] == "void" and n == 0 and "leg_policy" in r["why"],
      (r["status"], r["why"], n))
r2, n2 = limb_run("PHI", PIN, POL_OK)
check("P9 limb, a pin approved only for another limb: VOID, nothing sent", r2["status"] == "void" and n2 == 0,
      (r2["status"], r2["why"], n2))

# the real policy file
REAL = os.path.join(HERE, "ops", "leg_policy.json")
raw = open(REAL, encoding="utf-8").read()
real = json.loads(raw)
LEG.POLICY_PATH = REAL
live_ok = LEG.approved("leg", "67ed9c4f6a0210b23ca2130c8b8e21a2ca9d474ec83f4cafd02bcaf16eaf6cb7") and \
    LEG.approved("limb", "388c6d430e4a766b7d956b37a234e3da0ca74dc931e513a4627df7621cf1c762", "SMOL") and \
    LEG.approved("limb", "74a426399a085f5db6818e727ed2e54a9e4b85d05edcb86f32140fa1c2c2d946", "PHI")
check("P10 the real policy parses, approves the live pins, and holds no IPv4 address",
      live_ok and not re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", raw), live_ok)
src = open(os.path.join(HERE, "covenant_leg.py"), encoding="utf-8").read()
pol_line = [l for l in src.splitlines() if l.startswith("POLICY_PATH")]
check("P11 the policy path has no environment override", len(pol_line) == 1 and "environ" not in pol_line[0], pol_line)

# mutations
out, n = leg_run(dict(REMOTE_FILE, manifest_sha256=OTHER), POL_OK,
                 mutate=mutant("covenant_leg.py", 'if remote and not approved("leg", pin):', "if False:"))
check("M1 the leg's policy line removed: P2's unapproved pin reaches the gateway", n == 1, (out, n))
r, n = limb_run("SMOL", OTHER, POL_OK,
                mutate=mutant("covenant_limbs.py", 'if not LEG.approved("limb", cfg["manifest_sha256"], out["limb"]):',
                              "if False:"))
check("M2 the limb's policy check removed: P8's unapproved pin reaches the gateway", n == 1, (r["status"], n))

print("\nA474: %d/%d passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
