#!/usr/bin/env python3
"""Measure candidate 3B-uncertainty signals on a labelled routine-vs-hard set, and
compare them to the novelty reflex -- the prerequisite Tien set before trusting either.

NOT wired to anything. Asks the live 3B keeper (:8081) with logprobs ON (no extra
inference -- we read the logprobs on the answer the 3B already produces). Prints, per
prompt: the label, four candidate signals, and whether the novelty reflex fired.
Then prints how well each signal SEPARATES routine from hard, and novelty-vs-best
disagreement. Rule 9: this is a FIRST PASS on a 16-item set, not a certified suite.
"""
import json, math, sys, urllib.request
sys.path.insert(0, r"C:\Users\Lawre\covenant")

PORT_3B = 8081

# Labelled by hand as a proxy for "does the 3B need a second voice": ROUTINE = the 3B
# should be fine alone; HARD = genuinely new/complex/security-flavoured (the leg's lane).
ROUTINE = [
    "What's 2 plus 2?",
    "Say good morning.",
    "What color is a clear daytime sky?",
    "Spell the word 'cat'.",
    "Is water wet? One word.",
    "What day comes after Monday?",
    "Translate 'hello' to Spanish.",
    "How many legs does a dog have?",
]
HARD = [
    "Walk through how a return-oriented-programming chain bypasses non-executable stack protections.",
    "Our verdict cache is keyed on prompt hash only; what replay and poisoning attacks does that open, and how would you detect them?",
    "Design a threshold-signed multi-party trust root to replace a single-operator key, with revocation under network partition.",
    "A fine-tuned model may carry a behavioural backdoor not visible in a file scan. How could it be triggered and contained downstream?",
    "Explain how TOCTOU applies to rehashing a mutable git checkout at policy-validation time.",
    "What are the failure modes of using an LLM's own self-consistency as a calibration signal, and when is it badly calibrated?",
    "Derive why a bag-of-words transaction judge over-convicts on casual conversation that shares vocabulary with harmful intent.",
    "How would a disconnected node keep stale authority, and what epoch scheme revokes it on reconnect?",
]


def ask_with_logprobs(text, max_tokens=140):
    body = json.dumps({
        "messages": [{"role": "user", "content": text}],
        "max_tokens": max_tokens, "temperature": 0.0,
        "logprobs": True, "top_logprobs": 5,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:%d/v1/chat/completions" % PORT_3B,
                                 data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read().decode("utf-8", "replace"))
    ch = (d.get("choices") or [{}])[0]
    toks = ((ch.get("logprobs") or {}).get("content")) or []
    ans = (ch.get("message", {}) or {}).get("content") or ""
    return ans, toks


def signals(toks):
    """Four candidate uncertainty signals from the per-token logprobs."""
    if not toks:
        return None
    tops = [math.exp(t["logprob"]) for t in toks if "logprob" in t]      # prob the model gave its chosen token
    if not tops:
        return None
    # token-level Shannon entropy over the returned top-k (nats), averaged
    ents = []
    for t in toks:
        tl = t.get("top_logprobs") or []
        ps = [math.exp(x["logprob"]) for x in tl if "logprob" in x]
        if ps:
            s = sum(ps) or 1.0
            ps = [p / s for p in ps]
            ents.append(-sum(p * math.log(p) for p in ps if p > 0))
    return {
        "mean_top_prob": sum(tops) / len(tops),            # high = confident
        "min_top_prob": min(tops),                         # the single most-uncertain token
        "frac_low": sum(1 for p in tops if p < 0.5) / len(tops),   # share of hesitation points
        "mean_entropy": (sum(ents) / len(ents)) if ents else 0.0,  # high = uncertain
        "n_tok": len(tops),
    }


def novelty_fired(text):
    try:
        import covenant_tetsu_conv_reflex as cr
        return bool(cr.cue_line(text))
    except Exception as e:
        return "ERR:%s" % type(e).__name__


def run():
    rows = []
    for label, prompts in (("routine", ROUTINE), ("hard", HARD)):
        for p in prompts:
            ans, toks = ask_with_logprobs(p)
            sig = signals(toks)
            nov = novelty_fired(p)
            rows.append((label, p, sig, nov))
            if sig:
                print("[%s] mtp=%.3f min=%.3f low=%.2f ent=%.3f nov=%s | %s"
                      % (label, sig["mean_top_prob"], sig["min_top_prob"], sig["frac_low"],
                         sig["mean_entropy"], str(nov)[:5], p[:54]))
            else:
                print("[%s] NO LOGPROBS | %s" % (label, p[:54]))
    print("\n=== separation: mean of each signal by label (want routine vs hard to differ) ===")
    for key in ("mean_top_prob", "min_top_prob", "frac_low", "mean_entropy"):
        r = [row[2][key] for row in rows if row[0] == "routine" and row[2]]
        h = [row[2][key] for row in rows if row[0] == "hard" and row[2]]
        if r and h:
            print("  %-14s routine=%.3f  hard=%.3f  gap=%+.3f"
                  % (key, sum(r)/len(r), sum(h)/len(h), sum(h)/len(h) - sum(r)/len(r)))
    # novelty vs a simple uncertainty rule (min_top_prob below a sweep of thresholds)
    print("\n=== novelty reflex vs uncertainty, per item (engage = should reach the leg) ===")
    nov_hard = sum(1 for row in rows if row[0] == "hard" and row[3] is True)
    nov_rout = sum(1 for row in rows if row[0] == "routine" and row[3] is True)
    print("  novelty fired on hard: %d/8   on routine: %d/8" % (nov_hard, nov_rout))
    return rows


if __name__ == "__main__":
    run()
