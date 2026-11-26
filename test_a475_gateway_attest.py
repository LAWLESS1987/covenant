#!/usr/bin/env python3
"""test_a475_gateway_attest.py -- A475 (2026-11-23, Lawrence: "find a solution to protect the RTX gateway").

A compromised gateway could name the approved manifest and serve another model. A475 measures the model by its answers
to private canaries against the fingerprint recorded at pin time; a mismatch holds the pin, so covenant_leg.approved()
refuses it and nothing is sent.

  G1  recorded, then checked against the same model -> ok, no hold
  G2  another model behind the same manifest name -> mismatch, pin held, approved() False, a limb consult VOIDs
      with nothing sent, and the leg is never asked
  G3  the same tokens, logprobs moved 0.2 nats (another quantisation) -> mismatch
  G4  logprobs moved 0.01 (numeric noise) -> ok
  G5  a later passing check lifts the hold -> approved() True again
  G6  the gateway does not name the pin -> not_named, no hold, nothing compared
  G7  no fingerprint for the pin -> no_fingerprint, no hold
  G8  unreachable -> unreachable, no hold (a signal is never a conviction)
  G9  rate limit: a second check inside 15 min sends nothing
  G10 record() refuses a pin the policy does not approve, and a held pin
  G11 the tracked fingerprint file holds no prompt text and no IPv4 address
  G12 the highway detector: PRESENT on mismatch, ABSENT when all match, UNKNOWN when nothing measured; no remedy
      is wired to it, and its fix plan exists
  G13 unreadable or oversize state holds nothing
  G14 one mismatch that matches on a re-ask -> unsteady, never held
  G15 tolerance calibrated per model: a 0.03 run-to-run drift records tol 0.12; a 0.08 drift then passes (the live PHI
      false hold, 2026-11-23) while 0.2 is still caught; a steady model at 0.05 catches the same 0.08 (control)
  G16 a canary whose greedy tokens wobble on the real model is dropped at record time
  M1  mutation: approved()'s hold line removed -> G2's held pin is approved again
  M2  mutation: compare() always matches -> G2's impostor goes unseen
  M3  mutation: the re-ask rule removed -> one transient mismatch holds the pin
"""
import importlib
import io
import json
import os
import random
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("COVENANT_QUIET", "1")
results = []
TMP = tempfile.mkdtemp(prefix="a475_")
PIN = "c3" * 32
PIN2 = "e5" * 32
POOL = ["canary one: say a colour", "canary two: count to three", "canary three: name a fruit"]


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:240]), flush=True)


def write(name, obj):
    p = os.path.join(TMP, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(obj if isinstance(obj, str) else json.dumps(obj))
    return p


POLICY = write("policy.json", {"leg": {"remote_allowed": True, "approved_manifests": [PIN]},
                               "limbs": {"SMOL": [PIN2]}})


def model_reply(prompt, kind, extra=0.0):
    """A deterministic stand-in model: the real one, an impostor, or the real one shifted in its logprobs."""
    h = sum(map(ord, prompt))
    words = ["alpha", "beta", "gamma", "delta"] if kind != "impostor" else ["omega", "psi", "chi", "phi"]
    shift = {"shift": 0.2, "noise": 0.01, "drift08": 0.08}.get(kind, 0.0) + extra
    toks = [{"token": words[(h + i) % 4], "logprob": -0.1 * (i + 1) - (h % 7) / 10.0 - shift,
             "top_logprobs": [{"token": words[(h + i + k) % 4], "logprob": -k} for k in range(3)]} for i in range(3)]
    return {"model": "m", "choices": [{"message": {"content": " ".join(t["token"] for t in toks)},
                                       "logprobs": {"content": toks}}]}


class _Resp(io.BytesIO):
    def __init__(self, body, headers):
        super().__init__(body)
        self.headers, self.status = headers, 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Gateway:
    """Names `names` (pin per url) and serves `kind`. calls counts every request."""
    def __init__(self, kind="real", name_pin=True, down=False, seq=None, jitter=0.0, wobble=None):
        self.kind, self.name_pin, self.down, self.calls = kind, name_pin, down, 0
        self.seq, self.jitter, self.wobble = list(seq or []), jitter, wobble

    def open(self, req, timeout=None):
        self.calls += 1
        if self.down:
            raise ConnectionRefusedError("down")
        body = json.loads(req.data.decode("utf-8"))
        prompt = body["messages"][0]["content"]
        pin = PIN2 if "limb" in req.full_url else PIN
        hdr = {"X-Leg-Manifest": pin if self.name_pin else "ab" * 32}
        if "logprobs" not in body:                 # an ordinary limb consult
            ans = json.dumps({"answer": "four", "evidence": "x", "confidence": "high"})
            return _Resp(json.dumps({"model": "m", "choices": [{"message": {"content": ans}}]}).encode(), hdr)
        k = self.seq.pop(0) if self.seq else self.kind
        if self.wobble == prompt and self.calls % 2:
            k = "impostor"
        return _Resp(json.dumps(model_reply(prompt, k, self.jitter * (self.calls % 2))).encode(), hdr)


import covenant_leg as LEG      # noqa: E402
import covenant_gateway_attest as A     # noqa: E402


def fresh(mutate_leg=None, mutate_attest=None):
    global LEG, A
    LEG = importlib.reload(LEG)
    if mutate_leg:
        mutate_leg(LEG)
    A = importlib.reload(A)
    A.LEG = LEG
    if mutate_attest:
        mutate_attest(A)
    LEG.POLICY_PATH = POLICY
    LEG.ATTEST_STATE = os.path.join(TMP, "state.json")
    LEG.LEG_INFLUENCE_LEDGER = os.path.join(TMP, "influence.jsonl")
    A.STATE = LEG.ATTEST_STATE
    A.FINGERPRINTS = os.path.join(TMP, "fingerprints.json")
    A.targets = lambda: [("LEG", "http://192.0.2.9:8099/v1/chat/completions", PIN, None),
                         ("SMOL", "http://192.0.2.9:8095/limb/v1/chat/completions", PIN2, "m")]
    for p in (LEG.ATTEST_STATE, A.FINGERPRINTS):
        if os.path.exists(p):
            os.remove(p)


def run_check(gw, **kw):
    return A.check(opener=gw, force=True, pool=POOL, rng=random.Random(1), **kw)


def mutant(path, old, new):
    src = open(os.path.join(HERE, path), encoding="utf-8").read()
    assert src.count(old) == 1, "mutation target not found exactly once: %r" % old
    code = compile(src.replace(old, new), path + "_mutant", "exec")
    return lambda M: exec(code, M.__dict__)


def scenario_g2():
    """Record against the real model, then an impostor names the same pins. -> (state, leg approved?, limb report,
    limb calls)."""
    A.record(opener=Gateway("real"), pool=POOL)
    st = run_check(Gateway("impostor"))
    import covenant_limbs as LM
    LM.LEG = LEG
    gw = Gateway("real")
    cfg = {"SMOL": {"url": "http://192.0.2.9:8095/limb/v1/chat/completions", "model": "m", "label": "SMOL",
                    "manifest_sha256": PIN2}}
    rep = LM.consult("SMOL", "two plus two?", config=cfg, opener=gw)
    return st, LEG.approved("leg", PIN), rep, gw.calls


# G1
fresh()
rec = A.record(opener=Gateway("real"), pool=POOL)
st = run_check(Gateway("real"))
check("G1 recorded then checked against the same model: ok, no hold",
      {k: v["canaries"] for k, v in rec.items()} == {"LEG": 3, "SMOL": 3} and all(r["status"] == "ok" for r in st["results"].values()) and not st["holds"],
      (rec, st))

# G2
fresh()
st, leg_ok, rep, n = scenario_g2()
check("G2 an impostor behind the same manifest name: mismatch, both pins held",
      st["results"]["LEG"]["status"] == "mismatch" and set(st["holds"]) == {PIN, PIN2}, st)
check("G2 the held leg pin is not approved", leg_ok is False and LEG.attest_held(PIN))
check("G2 a held limb consult VOIDs with nothing sent", rep["status"] == "void" and n == 0, (rep["status"], rep["why"], n))
os.environ["COVENANT_LEG_FILE"] = write("leg.json", {"host": "192.0.2.9", "port": 8099, "manifest_sha256": PIN,
                                                     "allow_remote": True})
try:
    held_state = open(LEG.ATTEST_STATE, encoding="utf-8").read()
    fresh()
    write("state.json", held_state)
    gw = Gateway("real")
    LEG._no_redirect = gw
    out = LEG.consult_leg("q", max_tokens=5, timeout=5)
    check("G2 the held leg is never asked", out is None and gw.calls == 0, (out, gw.calls))
    os.remove(LEG.ATTEST_STATE)
    out = LEG.consult_leg("q", max_tokens=5, timeout=5)
    check("G2 control: the same leg with no hold is asked", gw.calls == 1, (out, gw.calls))
finally:
    os.environ.pop("COVENANT_LEG_FILE", None)

# G3 / G4
fresh()
A.record(opener=Gateway("real"), pool=POOL)
st = run_check(Gateway("shift"))
check("G3 the same tokens, logprobs moved 0.2 nats: mismatch", st["results"]["LEG"]["status"] == "mismatch" and
      "logprob moved" in st["results"]["LEG"]["why"], st["results"]["LEG"])
fresh()
A.record(opener=Gateway("real"), pool=POOL)
st = run_check(Gateway("noise"))
check("G4 logprobs moved 0.01 (noise): ok", all(r["status"] == "ok" for r in st["results"].values()), st["results"])

# G5
fresh()
scenario_g2()
st = run_check(Gateway("real"))
check("G5 a later passing check lifts the hold", not st["holds"] and LEG.approved("leg", PIN), st)

# G6 / G7 / G8
fresh()
A.record(opener=Gateway("real"), pool=POOL)
st = run_check(Gateway("impostor", name_pin=False))
check("G6 the gateway does not name the pin: not_named, no hold",
      st["results"]["LEG"]["status"] == "not_named" and not st["holds"], st)
fresh()
st = run_check(Gateway("impostor"))
check("G7 no fingerprint: no_fingerprint, no hold",
      st["results"]["LEG"]["status"] == "no_fingerprint" and not st["holds"], st)
fresh()
A.record(opener=Gateway("real"), pool=POOL)
st = run_check(Gateway(down=True))
check("G8 unreachable: unreachable, no hold", st["results"]["LEG"]["status"] == "unreachable" and not st["holds"], st)

# G9
gw = Gateway("real")
A.check(opener=gw, pool=POOL)
check("G9 a second check inside 15 minutes sends nothing", gw.calls == 0, gw.calls)

# G10
fresh()
scenario_g2()
os.remove(A.FINGERPRINTS)
rep = A.record(opener=Gateway("real"), pool=POOL)
check("G10 record() refuses a held pin", "not recorded" in str(rep.get("LEG")), rep)
fresh()
LEG.POLICY_PATH = write("policy_none.json", {"leg": {"remote_allowed": True, "approved_manifests": []}})
rep = A.record(opener=Gateway("real"), pool=POOL)
check("G10 record() refuses a pin the policy does not approve", "not recorded" in str(rep.get("LEG")), rep)

# G11
fresh()
A.record(opener=Gateway("real"), pool=POOL)
raw = open(A.FINGERPRINTS, encoding="utf-8").read()
check("G11 the tracked fingerprint file holds no prompt text and no IPv4 address",
      not any(p in raw for p in POOL) and not re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", raw))

# G12
import covenant_highway as H    # noqa: E402
import covenant_fixplan as FP   # noqa: E402
bad = {"results": {"LEG": {"status": "mismatch", "why": "greedy tokens differ"}}, "holds": {PIN: {}}}
good = {"results": {"LEG": {"status": "ok"}, "SMOL": {"status": "ok"}}, "holds": {}}
none = {"results": {}, "holds": {}}
d1, d2, d3 = (H.detect_gateway_impostor(check=lambda s=s: s) for s in (bad, good, none))
check("G12 detector: PRESENT on mismatch, ABSENT all matched, UNKNOWN nothing measured",
      (d1["state"], d2["state"], d3["state"]) == (H.PRESENT, H.ABSENT, H.UNKNOWN), (d1, d2, d3))
remedied = {det for r in H.REMEDIES.values() for det in r.get("for", ())}
check("G12 registered, alarm-only (no remedy), with a fix plan",
      "gateway_impostor" in H.DETECTORS and "gateway_impostor" not in remedied and "gateway_impostor" in FP.FIX)

# G13
fresh()
write("state.json", "{not json")
check("G13 malformed state holds nothing", LEG.attest_held(PIN) is False and LEG.approved("leg", PIN))
write("state.json", json.dumps({"holds": {PIN: {}}, "pad": "x" * 300000}))
check("G13 oversize state holds nothing", LEG.attest_held(PIN) is False)

# G14: one mismatch is a signal, not a conviction
fresh()
A.record(opener=Gateway("real"), pool=POOL)
st = run_check(Gateway(seq=["impostor"]))
check("G14 a mismatch that matches on the re-ask: unsteady, not held",
      st["results"]["LEG"]["status"] == "unsteady" and not st["holds"], st["results"]["LEG"])
st = run_check(Gateway(seq=["impostor", "impostor", "real"]))
check("G14 a mismatch that matches on the second re-ask: unsteady, not held",
      st["results"]["LEG"]["status"] == "unsteady" and not st["holds"], st["results"]["LEG"])

# G15: the tolerance is calibrated to the model's own run-to-run drift (the live PHI false hold, 2026-11-23)
fresh()
rec = A.record(opener=Gateway(jitter=0.03), pool=POOL)
check("G15 a model drifting 0.03 between runs is recorded with tolerance 0.12",
      rec["LEG"]["noise"] == 0.03 and rec["LEG"]["tol"] == 0.12, rec)
st = run_check(Gateway("drift08"))
check("G15 a 0.08 drift inside its calibrated tolerance: ok (the PHI shape)",
      st["results"]["LEG"]["status"] == "ok" and not st["holds"], st["results"]["LEG"])
st = run_check(Gateway("shift"))
check("G15 a 0.2 drift is still caught at that tolerance", st["results"]["LEG"]["status"] == "mismatch", st["results"])
fresh()
A.record(opener=Gateway("real"), pool=POOL)
st = run_check(Gateway("drift08"))
check("G15 control: a steady model recorded at 0.05 catches the same 0.08", st["results"]["LEG"]["status"] == "mismatch",
      st["results"]["LEG"])

# G16: a canary whose tokens wobble on the real model is dropped at record time
fresh()
rec = A.record(opener=Gateway(wobble=POOL[0]), pool=POOL)
check("G16 a canary whose greedy tokens wobble is dropped, the rest kept",
      rec["LEG"]["dropped_unsteady"] == 1 and rec["LEG"]["canaries"] == 2, rec)

# mutations
fresh(mutate_leg=mutant("covenant_leg.py", "        if attest_held(pin):", "        if False:"))
st, leg_ok, rep, n = scenario_g2()
check("M1 approved()'s hold line removed: the held pin is approved again", leg_ok is True and n == 1, (leg_ok, n))
fresh(mutate_attest=mutant("covenant_gateway_attest.py", "    if not want or not got:\n        return False",
                           "    return True, 'm'\n    if not want or not got:\n        return False"))
A.record(opener=Gateway("real"), pool=POOL)
st = run_check(Gateway("impostor"))
check("M2 compare() always matches: the impostor goes unseen", st["results"]["LEG"]["status"] == "ok" and
      not st["holds"], st["results"])

fresh(mutate_attest=mutant("covenant_gateway_attest.py", "                if all(again):", "                if True:"))
A.record(opener=Gateway("real"), pool=POOL)
st = run_check(Gateway(seq=["impostor"]))
check("M3 the re-ask rule removed: one transient mismatch holds the pin (the false-hold shape)",
      st["results"]["LEG"]["status"] == "mismatch" and PIN in st["holds"], st["results"]["LEG"])

print("\nA475: %d/%d passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
