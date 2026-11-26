#!/usr/bin/env python3
"""covenant_gateway_attest.py -- A475 (2026-11-23): is the model behind the RTX gateway the one he agreed to?

Lawrence: "find a solution to protect the RTX gateway." The gateway on TETSU sends X-Leg-Manifest naming the sha256 of
the file it serves, and A470/A472/A474 check that name exactly against a pin approved in the tracked
ops/leg_policy.json. What that cannot see (A470's recorded limit, Codex's audit #1) is a compromised gateway that
NAMES the approved file and serves another model. This module measures the model itself, from its behaviour:

  - CANARIES. A pool of short prompts kept in private/gateway_canaries.json (untracked, so the public repository does
    not publish them). Each check asks PER_PASS of them, chosen at random, at temperature 0 with logprobs on.
  - FINGERPRINTS. At pin time `--record` stores, per approved manifest, each canary's greedy tokens, their logprobs
    and the top alternatives, keyed by the prompt's sha256 -- in the TRACKED ops/leg_fingerprints.json (no prompt
    text, no address), so git and the head commitment bind it beside the pin.
  - COMPARE. Same greedy tokens, each chosen token's logprob within the pin's tolerance, and at least 2 of the first
    token's top 3 alternatives the same. The tolerance is CALIBRATED per pin at record time: every canary is asked
    RECORD_RUNS times, one whose greedy tokens wobble is dropped, and tol = max(0.05, 4 x the largest run-to-run
    logprob drift), capped at 0.3. Why calibrated: the first live check (2026-11-23) held PHI on a 0.081-nat drift
    with a fixed 0.05 -- PHI had not changed; Phi-4-mini on TETSU's CPU is not bit-repeatable. That false hold is
    retired in .trash/ with its note.
  - HOLD. A mismatch is re-asked CONFIRM times; only if every re-ask mismatches too is the pin put in
    ops/gateway_attest_state.json "holds", and covenant_leg.approved() then refuses it, so the leg and that limb VOID
    before anything is sent. One that matches on a re-ask is reported "unsteady", never held. A later passing check,
    or a re-pin, lifts a hold. Unreachable, no fingerprint, or a manifest the gateway does not name are UNDETERMINED:
    reported, never a hold (investigate a signal, never convict on one).
  - ALARM. covenant_highway's detector gateway_impostor is PRESENT on any mismatch. Alarm only, no remedy: a model
    swap is a person's call (re-pin and re-record, or investigate), and auto-healing would erase the evidence.

WHAT IT CANNOT SEE. A gateway that recognises the canaries and sends only those to the real model. The pool is
private and sampled, which raises the cost, but every canary crosses TETSU, so a patient attacker there can learn
them. An independent measurement needs a key the gateway's user cannot read (a second OS account on TETSU, the
security plan's C2 -- his decision) or a reference copy of each model on another machine. Stdlib only.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_leg as LEG      # noqa: E402

FINGERPRINTS = os.path.join(HERE, "ops", "leg_fingerprints.json")
CANARIES = os.path.join(HERE, "private", "gateway_canaries.json")
STATE = LEG.ATTEST_STATE
TOL = 0.05                  # the floor; each pin's own tolerance is calibrated at record time (below)
TOL_CAP = 0.3               # over this a pin's noise is too large for logprobs to say much; tokens still decide
NOISE_FACTOR = 4            # tolerance = max(TOL, NOISE_FACTOR x the largest run-to-run drift seen at record time)
RECORD_RUNS = 3             # each canary asked this many times at record time; one whose tokens wobble is dropped
CONFIRM = 2                 # a mismatch is re-asked this many times; held only if every re-ask mismatches too
MAX_TOKENS = 8
TOP = 3
PER_PASS = 2
MIN_INTERVAL_S = 900
TIMEOUT_S = 60
MAX_FILE = 1 << 20


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _load(path, default):
    try:
        if os.path.getsize(path) > MAX_FILE:
            return default
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, type(default)) else default
    except (OSError, ValueError):
        return default


def _save(path, obj):
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".attest_", dir=d)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def canaries(path=None):
    """The private prompt pool: a JSON list of strings. [] when absent."""
    raw = _load(path or CANARIES, [])
    return [p for p in raw if isinstance(p, str) and p.strip()]


def targets():
    """[(name, url, pin, model)] for every REMOTE pinned model: the leg when it is not on loopback, and each limb."""
    out = []
    if not LEG._host_is_loopback(LEG.LEG_HOST):
        out.append(("LEG", "http://%s:%d/v1/chat/completions" % (LEG.LEG_HOST, LEG.LEG_PORT), LEG._leg_pin(), None))
    try:
        import covenant_limbs as LM
        for name, c in sorted(LM.load_config().items()):
            out.append((name, c["url"], c["manifest_sha256"], c["model"] or None))
    except Exception:                                        # noqa: BLE001 -- no limbs configured is not an error
        pass
    return [t for t in out if len(t[2]) == 64]


def probe(url, pin, model, prompt, opener=None, timeout=TIMEOUT_S):
    """One canary, greedy, logprobs on. -> list of [token, logprob, [top alternatives]], or None when the gateway does
    not name PIN (nothing of that reply is read). Raises on transport errors (the caller reports unreachable)."""
    payload = {"messages": [{"role": "user", "content": prompt}], "max_tokens": MAX_TOKENS, "temperature": 0.0,
               "seed": 7, "logprobs": True, "top_logprobs": TOP, "chat_template_kwargs": {"enable_thinking": False}}
    if model:
        payload["model"] = model
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    op = opener or LEG._no_redirect
    deadline = time.monotonic() + timeout
    with op.open(req, timeout=timeout) as r:
        if LEG.manifest_hex(str(r.headers.get("X-Leg-Manifest") or "")) != pin:
            return None
        raw = LEG.read_bounded(r, deadline)
    if raw is None or len(raw) > LEG.MAX_HTTP_BYTES:
        raise TimeoutError("reply incomplete or oversize")
    d = json.loads(raw.decode("utf-8", "replace"))
    toks = (((d.get("choices") or [{}])[0].get("logprobs") or {}).get("content")) or []
    return [[str(t.get("token")), float(t.get("logprob", 0.0)),
             [str(a.get("token")) for a in (t.get("top_logprobs") or [])][:TOP]] for t in toks]


def compare(want, got, tol=TOL):
    """-> (ok, why). Same greedy tokens; each logprob within tol; first token's top alternatives overlap >= 2."""
    if not want or not got:
        return False, "empty fingerprint or reply"
    if [w[0] for w in want] != [g[0] for g in got]:
        return False, "greedy tokens differ"
    worst = max(abs(w[1] - g[1]) for w, g in zip(want, got))
    if worst > tol:
        return False, "logprob moved %.3f nats (tolerance %.2f)" % (worst, tol)
    if len(set(want[0][2]) & set(got[0][2])) < min(2, len(want[0][2])):
        return False, "first token's top alternatives differ"
    return True, "match (max logprob difference %.4f)" % worst


def record(names=None, opener=None, path=None, pool=None):
    """Store fingerprints for every canary, for each target's CURRENT pin (pin time; a person or session runs this
    beside a re-pin). Only pins the tracked policy approves are recorded. -> {name: count or error}."""
    pool = pool if pool is not None else canaries()
    if not pool:
        return {"error": "no canaries in %s" % CANARIES}
    fps = _load(path or FINGERPRINTS, {})
    fps.setdefault("note", "A475: behavioural fingerprints of the models behind the TETSU gateway, per approved "
                           "manifest. Keys are sha256 of private canary prompts; no prompt text, no address. Re-record "
                           "beside every re-pin (python covenant_gateway_attest.py --record).")
    pins = fps.setdefault("pins", {})
    report = {}
    for name, url, pin, model in targets():
        if names and name not in names:
            continue
        kind = "leg" if name == "LEG" else "limb"
        if not LEG.approved(kind, pin, name):
            report[name] = "pin not approved (or held); not recorded"
            continue
        got, noise, dropped, failed = {}, 0.0, 0, None
        for p in pool:
            runs = []
            for _ in range(RECORD_RUNS):
                try:
                    fp = probe(url, pin, model, p, opener=opener)
                except Exception as e:                       # noqa: BLE001
                    failed = "unreachable (%s)" % type(e).__name__
                    break
                if fp is None:
                    failed = "gateway does not name the pin"
                    break
                runs.append(fp)
            if failed:
                break
            if not runs[0] or any([t[0] for t in r] != [t[0] for t in runs[0]] for r in runs[1:]):
                dropped += 1                                 # its greedy tokens wobble on the real model: no use
                continue
            noise = max([noise] + [abs(a[1] - b[1]) for r in runs[1:] for a, b in zip(runs[0], r)])
            got[_sha(p)] = runs[0]
        if failed:
            report[name] = failed
            continue
        tol = min(TOL_CAP, max(TOL, round(NOISE_FACTOR * noise, 4)))
        pins[pin] = {"target": name, "recorded": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                     "runs": RECORD_RUNS, "noise": round(noise, 4), "tol": tol, "dropped_unsteady": dropped,
                     "canaries": got}
        report[name] = {"canaries": len(got), "dropped_unsteady": dropped, "noise": round(noise, 4), "tol": tol}
    _save(path or FINGERPRINTS, fps)
    return report


def check(opener=None, rng=None, now=None, force=False, pool=None, fp_path=None, state_path=None):
    """Measure each remote target against its fingerprint. -> {"at", "results": {name: {pin, status, why}}}.
    status: ok | mismatch | no_fingerprint | unreachable | not_named. Rate-limited to MIN_INTERVAL_S unless force."""
    state_path = state_path or STATE
    st = _load(state_path, {})
    now = time.time() if now is None else now
    if not force and st.get("at_epoch") and now - float(st["at_epoch"]) < MIN_INTERVAL_S:
        return st
    pool = pool if pool is not None else canaries()
    by_sha = {_sha(p): p for p in pool}
    pins = _load(fp_path or FINGERPRINTS, {}).get("pins") or {}
    holds = st.get("holds") if isinstance(st.get("holds"), dict) else {}
    rng = rng or random.SystemRandom()
    results = {}
    for name, url, pin, model in targets():
        rec = pins.get(pin) or {}
        fp = rec.get("canaries") or {}
        try:
            tol = min(TOL_CAP, max(TOL, float(rec.get("tol", TOL))))
        except (TypeError, ValueError):
            tol = TOL
        usable = [h for h in fp if h in by_sha]
        if not usable:
            results[name] = {"pin": pin, "status": "no_fingerprint",
                             "why": "no recorded fingerprint for this pin with a canary in the private pool"}
            continue
        res = {"pin": pin, "status": "ok", "why": ""}
        for h in rng.sample(usable, min(PER_PASS, len(usable))):
            try:
                got = probe(url, pin, model, by_sha[h], opener=opener)
            except Exception as e:                           # noqa: BLE001
                res = {"pin": pin, "status": "unreachable", "why": type(e).__name__}
                break
            if got is None:
                res = {"pin": pin, "status": "not_named", "why": "the gateway did not name the pin"}
                break
            ok, why = compare(fp[h], got, tol)
            res["why"] = why
            if not ok:
                # Investigate a signal, never convict on one: re-ask the same canary; hold only if every re-ask
                # mismatches too. One that matches on a re-ask is reported unsteady, never held.
                again = []
                for _ in range(CONFIRM):
                    try:
                        g2 = probe(url, pin, model, by_sha[h], opener=opener)
                    except Exception:                        # noqa: BLE001
                        g2 = None
                    again.append(g2 is not None and not compare(fp[h], g2, tol)[0])
                if all(again):
                    res["status"] = "mismatch"
                    res["why"] = "%s, and on %d re-asks" % (why, CONFIRM)
                else:
                    res["status"] = "unsteady"
                    res["why"] = "%s once; a re-ask matched -- not held" % why
                break
        results[name] = res
        if res["status"] == "mismatch":
            holds[pin] = {"target": name, "since": holds.get(pin, {}).get("since") or
                          time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "why": res["why"]}
        elif res["status"] == "ok":
            holds.pop(pin, None)
    st = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "at_epoch": now, "results": results,
          "holds": holds}
    _save(state_path, st)
    return st


if __name__ == "__main__":
    if "--record" in sys.argv:
        print(json.dumps(record([a for a in sys.argv[2:] if not a.startswith("-")] or None), indent=1))
    else:
        out = check(force="--force" in sys.argv)
        print(json.dumps({k: v for k, v in out.items() if k != "at_epoch"}, indent=1))
