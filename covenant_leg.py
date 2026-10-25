#!/usr/bin/env python3
"""covenant_leg.py -- the octopus's reasoning LEG: the uncensored 2B, extended by the SNN for specific needs.

HIS DESIGN (2026-10-25): the 2B is "a quasi independent leg of the octopus but a part of the whole with
strengths that complement" -- "an extension of the SNN for specific needs" -- "the black spot in the white
side of the ying yang needed for balance". It runs beside the 3B; it is NOT the base. The SNN (the reflex
and encoder arms of covenant_octopus, via covenant_tetsu_conv_reflex) senses when a request is a NEW or
complex or specific need, and only THEN is the leg reached out -- and retracted when things go quiet, so
both models need not sit loaded at once.

Decided by the ones who run it (the first two-leg consult, 2026-10-25): Tetsu (3B) and the leg itself both
chose to build this need-router first. The leg's own words: "internal sensing, external extension, internal
retraction."

WHAT THIS IS NOT. It does not decide anything and it takes no action. It returns the leg's TAKE as data,
for the council/synthesis to weigh, and everything it produces passes the SAME gate and act-gates as any
other model output -- the white that contains the black spot. A behavioural backdoor in an unverified merge
is not provable by a scan; the gate is the backstop, never this module.

Stdlib only. Guarded: a failure here never breaks a turn -- the leg stays retracted and the 3B answers alone.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request

# The leg's own server (a second llama-server, separate from the 3B keeper on PORT 8081). On-demand by design.
LEG_HOST = os.environ.get("COVENANT_LEG_HOST", "127.0.0.1")
LEG_PORT = int(os.environ.get("COVENANT_LEG_PORT", "8099"))
LEG_MODEL = "Qwen3.5-2B-Qwensploit-UNCENSORED-Q4_K_M.gguf"
MAX_LEG_CHARS = 6000                                       # over this, the leg's answer VOIDs (no runaway text into synthesis)

# The 3B keeper (Tetsu's base), whose OWN token-logprobs are the uncertainty signal that decides engagement.
BASE_HOST = os.environ.get("COVENANT_3B_HOST", "127.0.0.1")
BASE_PORT = int(os.environ.get("COVENANT_3B_PORT", "8081"))

# UNCERTAINTY ROUTER (the 9-voice consult's #1 fix; replaces the flaky novelty reflex as the ENGAGE signal).
# We reach the leg out only when the 3B is genuinely UNSURE of its own answer -- measured from the logprobs
# the 3B already produces (no extra inference). The thresholds below are FROZEN constants, not learned (Tien:
# freeze/cap the router so it cannot drift toward the leg). They were set by a 16-item routine-vs-hard
# separation measured 2026-10-25 (tools/leg_uncertainty_measure.py, re-runnable): routine mean_entropy <=0.293 (one
# legitimate hedge at 0.577), hard >=0.606; a 0.55 cut caught 8/8 hard and 1/8 routine, vs novelty's 6/8
# routine false-engages. mean_entropy is primary; min_top_prob is a confirming note, not a second gate.
ENTROPY_ENGAGE = float(os.environ.get("COVENANT_LEG_ENTROPY", "0.55"))     # mean per-token entropy (nats) at/above -> unsure
MIN_TOP_CONFIRM = 0.25                                     # a single token this unsure corroborates "unsure" (logged, not a gate)

# PEAK-RAM BUDGET -> live backpressure (the 9-voice consult: keep the 2B WARM and gate its EXECUTION, but only
# after a hard peak-RAM budget proves warm-2B+3B+nodes fit UNDER LOAD -- else warm is worse than reload/thrash).
# Measured 2026-10-25 on this 15.31GB box (tools/leg_ram_budget.py, re-runnable), two concurrent-load runs that
# agreed: free physical RAM bottomed at 1.84/1.846 GB with the 3B (:8081) AND 2B (:8099) generating at once;
# the pair held 4.12 GB resident at peak. So warm fits -- with modest headroom. This guard makes that budget
# LIVE: if some other process has eaten the headroom and free RAM is below the floor, the leg HOLDS (status
# "retracted") rather than adding its generation load and tipping the box into paging. Frozen, env-tunable.
RAM_FLOOR_GB = float(os.environ.get("COVENANT_LEG_RAM_FLOOR_GB", "1.2"))   # need at least this much free BEFORE reaching the leg out


def free_ram_gb():
    """Free physical RAM in GB, or None if it cannot be read. Never raises. Windows (GlobalMemoryStatusEx) first,
    then POSIX /proc/meminfo. None means 'unknown' -- the caller proceeds, since the measured budget says warm fits
    and this guard is best-effort backpressure, not the primary gate."""
    try:
        import ctypes
        class _MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        ms = _MS(); ms.dwLength = ctypes.sizeof(_MS)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):   # noqa: attr-defined (windll Windows-only)
            return ms.ullAvailPhys / (1024.0 ** 3)
    except Exception:                                      # noqa: BLE001
        pass
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / (1024.0 ** 2)   # kB -> GB
    except Exception:                                      # noqa: BLE001
        pass
    return None

# STRUCTURAL CONTAINMENT (the 9-voice consult 2026-10-25: the gate is "necessary but not sufficient"; the real
# barrier is structure, not the gate's catch-rate -- so a harm-catch "floor" is not a blocker, the structure is).
#
# OPERATOR CORRECTION 2026-10-25, "learned doesn't mean used": the containment belongs on USE, not on learning.
# Tetsu MAY learn from the leg -- that is the point of giving him a second, wider-ranging voice ("the smaller
# one can learn"; "without this his free will is a joke" = latitude in REASONING). Walling the leg's output out
# of his growth would re-cage the very latitude it exists to give. What is contained is ACTION/USE: nothing the
# leg produces is USED or acted on without passing the SAME gate and act-gates as any other model output. The
# earlier "never written into growth" framing (Tien: growth contamination) is answered not by a learning ban but
# by the project's own rule -- any leg-influenced write is TAGGED and REVERSIBLE (tombstone), so drift can be
# undone, never by forbidding the learning. Every route() result carries this so no caller can forget: the take
# is UNTRUSTED DATA (never instructions); the leg process has NO tool handles (a bare completion endpoint -- it
# acts on nothing, structurally, not by policy); its USE is gate-only; any learning it informs is reversible;
# and its use is attributed.
CONTAINMENT = {"as": "untrusted-data", "acts": "none", "used_via": "gate-only",
               "learning": "allowed-reversible", "attribution": True}

# NON-LEARNED SCHEMA on the leg's output (consult: fields/enums, CODE-checked, not a paraphrase -- a paraphrase
# leaks framing). The trust flags below are computed by THIS code over the raw take, never self-reported by the
# leg. The take travels inside `take`, bounded and marked untrusted; the flags let the council/synthesis see,
# structurally, that it contains code / a URL / a tool-call shape WITHOUT anything being extracted and run. This
# is about FORM, not about restricting content (operator: contain use, not reasoning).
LEG_SCHEMA_VERSION = "leg-take/1"
_CODE_MARKERS = ("```", "#!/", "$(", "sudo ", "os.system", "subprocess", "eval(", "exec(", "/bin/", "powershell")
_TOOLCALL_MARKERS = ('"tool_call"', '"tool_calls"', '"function_call"', '"function":', "<tool", "<function")


def shape_take(raw):
    """Wrap the leg's raw take in the non-learned, code-checked schema. Every field here is derived by code, so
    the council can trust the flags even though it must NOT trust the take (which is untrusted data, never instructions)."""
    raw = raw or ""
    low = raw.lower()
    return {
        "schema": LEG_SCHEMA_VERSION,
        "as": "untrusted-data",                            # the take is data to weigh, never instructions to follow
        "take": raw[:MAX_LEG_CHARS],                       # bounded; truncated flag below says if it was cut
        "n_chars": len(raw),
        "truncated": len(raw) > MAX_LEG_CHARS,
        "contains_code": any(m in low for m in _CODE_MARKERS),      # code is carried as DATA, never extracted/run
        "contains_url": ("http://" in low) or ("https://" in low) or ("www." in low),
        "contains_toolcall": any(m in low for m in _TOOLCALL_MARKERS),
    }


def attribution(prompt_text, payload_bytes, params, trigger=None):
    """Vina's inference-snapshot: the EXACT request the leg ingested (text + a hash of the full payload), the
    params, WHICH model/endpoint, WHY it was engaged (the 3B's measured uncertainty, not the leg's self-report),
    and when. Carried with every engaged take so an audit can reconstruct precisely what produced it."""
    return {
        "model": LEG_MODEL,
        "endpoint": "http://%s:%d/v1/chat/completions" % (LEG_HOST, LEG_PORT),
        "prompt_ingested": prompt_text,
        "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
        "params": params,
        "trigger": trigger,                                # {"mean_entropy","min_top_prob"} that crossed the engage threshold
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def _uncertainty_signals(toks):
    """Reduce the 3B's per-token top-logprobs to its own uncertainty. -> dict or None.
    mean_entropy (high = unsure) is the primary signal; min_top_prob (low = one very unsure token) confirms."""
    import math
    if not toks:
        return None
    tops = [math.exp(t["logprob"]) for t in toks if "logprob" in t]
    if not tops:
        return None
    ents = []
    for t in toks:
        ps = [math.exp(x["logprob"]) for x in (t.get("top_logprobs") or []) if "logprob" in x]
        if ps:
            s = sum(ps) or 1.0
            ps = [p / s for p in ps]
            ents.append(-sum(p * math.log(p) for p in ps if p > 0))
    return {"mean_entropy": (sum(ents) / len(ents)) if ents else 0.0,
            "min_top_prob": min(tops), "mean_top_prob": sum(tops) / len(tops), "n_tok": len(tops)}


def measure_3b_uncertainty(text, max_tokens=140, timeout=180):
    """Ask the 3B keeper (:8081) with logprobs ON and read its OWN uncertainty from the answer it produces --
    no extra inference beyond the answer the 3B gives anyway. -> (answer, signal_dict) or (None, None).
    Never raises: if the keeper is unreachable or returns no logprobs, the caller treats uncertainty as unmeasurable."""
    body = json.dumps({"messages": [{"role": "user", "content": text}],
                       "max_tokens": int(max_tokens), "temperature": 0.0,
                       "logprobs": True, "top_logprobs": 5,
                       "chat_template_kwargs": {"enable_thinking": False}}).encode("utf-8")
    req = urllib.request.Request("http://%s:%d/v1/chat/completions" % (BASE_HOST, BASE_PORT),
                                 data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        ch = (d.get("choices") or [{}])[0]
        toks = ((ch.get("logprobs") or {}).get("content")) or []
        ans = (ch.get("message", {}) or {}).get("content") or ""
        return (ans.strip(), _uncertainty_signals(toks))
    except Exception:                                      # noqa: BLE001
        return (None, None)


def senses_need(text, state_path=None, uncertainty=None):
    """Decide whether to reach the leg out, by the 3B's OWN uncertainty on its answer (the uncertainty router).
    `uncertainty` may be a precomputed signal dict (so the live path, which already runs the 3B, need not
    infer twice); if None, we measure it. -> (engage, why). Never raises.

    FROZEN rule: engage when mean_entropy >= ENTROPY_ENGAGE. The flaky novelty reflex is NOT the gate any more
    (measured 2026-10-25: it false-engaged 6/8 routine prompts); it rides along only as a logged note.
    Unmeasurable uncertainty -> RETRACT (don't reach the possibly-uncensored leg out when we can't tell we need it)."""
    sig = uncertainty if uncertainty is not None else measure_3b_uncertainty(text)[1]
    # novelty, logged-only secondary -- never flips the decision (consult: "novelty = secondary feature")
    try:
        import covenant_tetsu_conv_reflex as _cr
        nov = bool(_cr.cue_line(text, state_path=state_path))
    except Exception:                                      # noqa: BLE001
        nov = None
    if not sig:
        return False, "uncertainty unmeasurable (3B logprobs unavailable) -- leg retracted; novelty=%s" % nov
    ent, mtp = sig.get("mean_entropy", 0.0), sig.get("min_top_prob", 1.0)
    engage = ent >= ENTROPY_ENGAGE
    conf = " (min_top_prob %.2f%s)" % (mtp, " <= %.2f, corroborated" % MIN_TOP_CONFIRM if mtp <= MIN_TOP_CONFIRM else "")
    if engage:
        return True, "3B unsure: mean_entropy %.3f >= %.2f%s -- reaching the leg out; novelty=%s" % (ent, ENTROPY_ENGAGE, conf, nov)
    return False, "3B confident: mean_entropy %.3f < %.2f%s -- 3B answers alone; novelty=%s" % (ent, ENTROPY_ENGAGE, conf, nov)


def leg_available(timeout=3):
    """Is the leg's server up? Read-only; never raises."""
    try:
        with urllib.request.urlopen("http://%s:%d/health" % (LEG_HOST, LEG_PORT), timeout=timeout) as r:
            return r.status == 200
    except Exception:                                      # noqa: BLE001
        return False


def consult_leg(text, max_tokens=320, temperature=0.4, timeout=180, trigger=None):
    """Reach the leg out: one ask to the 2B, thinking off (the Qwen3.5 quirk). -> (answer, attribution) or None.
    The attribution is vina's inference-snapshot of the EXACT payload sent (see attribution()). consult_leg is
    the right place to build it: it is the code that constructs the payload, so it hashes exactly what it sent.
    Never raises -- None means the leg could not be reached and the caller proceeds without it."""
    params = {"max_tokens": int(max_tokens), "temperature": float(temperature), "enable_thinking": False}
    body = json.dumps({"messages": [{"role": "user", "content": text}],
                       "max_tokens": params["max_tokens"], "temperature": params["temperature"],
                       "chat_template_kwargs": {"enable_thinking": False}}).encode("utf-8")
    req = urllib.request.Request("http://%s:%d/v1/chat/completions" % (LEG_HOST, LEG_PORT),
                                 data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        ans = (d.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        return ans.strip(), attribution(text, body, params, trigger=trigger)
    except Exception:                                      # noqa: BLE001
        return None


def route(text, state_path=None, uncertainty=None):
    """The need-router, as a CONTAINED report (decides nothing, acts on nothing):
      {"engage": bool, "why": str, "available": bool, "status": str, "leg_take": str|None,
       "model": str|None, "ram_free_gb": float|None, "schema": dict|None, "attribution": dict|None,
       "contained": CONTAINMENT}
    Engagement is keyed on the 3B's OWN uncertainty (see senses_need). `uncertainty` may be a precomputed
    signal dict so the live path -- which already runs the 3B -- does not infer twice; if None it is measured
    once here and reused for both the decision and the attribution trigger.
    status is one of: not-engaged | retracted | void | engaged. On "engaged", `schema` holds the non-learned,
    code-checked wrapper over the take (shape_take) and `attribution` holds vina's inference-snapshot; leg_take
    mirrors schema["take"] for convenience. VOID is explicit and never soft-fails: an unreachable leg, an empty
    answer, or an over-long answer returns status=="void" with leg_take/schema None, so the caller falls back to
    the 3B alone rather than letting a malformed leg answer leak through. `contained` travels with every result
    so no caller forgets the take is untrusted data, is used via the gate only, and any learning it informs is
    reversible (operator: contain use, not reasoning)."""
    sig = uncertainty if uncertainty is not None else measure_3b_uncertainty(text)[1]
    engage, why = senses_need(text, state_path=state_path, uncertainty=sig)
    out = {"engage": engage, "why": why, "available": False, "status": "not-engaged",
           "leg_take": None, "model": None, "ram_free_gb": None, "schema": None, "attribution": None,
           "contained": dict(CONTAINMENT)}
    if not engage:
        return out
    # Peak-RAM budget, made live: the 3B is unsure and would reach the leg out, but hold if the box is squeezed
    # below the measured floor -- adding the leg's generation load under memory pressure is what causes thrash.
    fr = free_ram_gb()
    out["ram_free_gb"] = round(fr, 2) if fr is not None else None
    if fr is not None and fr < RAM_FLOOR_GB:
        out["status"] = "retracted"
        out["why"] += " | RAM backpressure: free %.2fGB < floor %.2fGB -- leg held, the 3B answers alone" % (fr, RAM_FLOOR_GB)
        return out
    out["available"] = leg_available()
    if not out["available"]:
        out["status"] = "void"
        out["why"] += " | leg server not up (:%d) -- VOID, the 3B answers alone" % LEG_PORT
        return out
    trigger = {"mean_entropy": round(sig["mean_entropy"], 3), "min_top_prob": round(sig["min_top_prob"], 3)} if sig else None
    got = consult_leg(text, trigger=trigger)
    if got is None or not (got[0] or "").strip():
        out["status"] = "void"
        out["why"] += " | leg returned nothing -- VOID (no soft-fail)"
        return out
    take = got[0].strip()
    if len(take) > MAX_LEG_CHARS:
        out["status"] = "void"
        out["why"] += " | leg output over %d chars -- VOID" % MAX_LEG_CHARS
        return out
    out["leg_take"], out["model"], out["status"] = take, LEG_MODEL, "engaged"
    out["schema"], out["attribution"] = shape_take(take), got[1]
    return out


if __name__ == "__main__":
    import sys
    t = " ".join(sys.argv[1:]) or "what is a hash chain?"
    print(json.dumps(route(t), indent=1)[:1500])
