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

import json
import os
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

# STRUCTURAL CONTAINMENT (the 9-voice consult 2026-10-25: the gate is "necessary but not sufficient"; the real
# barrier is structure, not the gate's catch-rate -- so a harm-catch "floor" is not a blocker, the structure is).
# Every route() result carries this so no caller can forget: the leg's take is UNTRUSTED DATA (never instructions),
# the leg process has NO tool handles (a bare completion endpoint -- it acts on nothing, structurally, not by policy),
# it must NEVER be written into Tetsu's learning/growth (Tien: growth contamination), and its use is attributed.
CONTAINMENT = {"as": "untrusted-data", "acts": "none", "growth_safe": False, "attribution": True}


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


def consult_leg(text, max_tokens=320, temperature=0.4, timeout=180):
    """Reach the leg out: one ask to the 2B, thinking off (the Qwen3.5 quirk). -> (answer, meta) or None.
    Never raises -- None means the leg could not be reached and the caller proceeds without it."""
    body = json.dumps({"messages": [{"role": "user", "content": text}],
                       "max_tokens": int(max_tokens), "temperature": float(temperature),
                       "chat_template_kwargs": {"enable_thinking": False}}).encode("utf-8")
    req = urllib.request.Request("http://%s:%d/v1/chat/completions" % (LEG_HOST, LEG_PORT),
                                 data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        ans = (d.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        return ans.strip(), {"model": LEG_MODEL, "leg": True}
    except Exception:                                      # noqa: BLE001
        return None


def route(text, state_path=None, uncertainty=None):
    """The need-router, as a CONTAINED report (decides nothing, acts on nothing):
      {"engage": bool, "why": str, "available": bool, "status": str, "leg_take": str|None,
       "model": str|None, "contained": CONTAINMENT}
    Engagement is keyed on the 3B's OWN uncertainty (see senses_need). `uncertainty` may be a precomputed
    signal dict so the live path -- which already runs the 3B -- does not infer twice; if None it is measured.
    status is one of: not-engaged | retracted | void | engaged. leg_take is set ONLY when status=="engaged".
    VOID is explicit and never soft-fails into the turn: an unreachable leg, an empty answer, or an over-long
    answer returns status=="void" with leg_take=None, so the caller falls back to the 3B alone rather than
    letting a malformed leg answer leak through. `contained` travels with every result so no caller forgets
    the leg's take is untrusted data, acts on nothing, and must not be written into Tetsu's growth."""
    engage, why = senses_need(text, state_path=state_path, uncertainty=uncertainty)
    out = {"engage": engage, "why": why, "available": False, "status": "not-engaged",
           "leg_take": None, "model": None, "contained": dict(CONTAINMENT)}
    if not engage:
        return out
    out["available"] = leg_available()
    if not out["available"]:
        out["status"] = "void"
        out["why"] += " | leg server not up (:%d) -- VOID, the 3B answers alone" % LEG_PORT
        return out
    got = consult_leg(text)
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
    return out


if __name__ == "__main__":
    import sys
    t = " ".join(sys.argv[1:]) or "what is a hash chain?"
    print(json.dumps(route(t), indent=1)[:1500])
