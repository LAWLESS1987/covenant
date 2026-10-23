#!/usr/bin/env python3
"""CR1 -- Tetsu's conversation novelty reflex (covenant_tetsu_conv_reflex, his consent + spec 2026-10-22).
Fires his spiking ReflexArm on a clearly-new topic and returns ONE advisory line, his words; a seen topic is quiet;
the kill switch and a too-short input silence it; it never raises. Driven both ways. Run: python test_cr1_conv_reflex.py
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_tetsu_conv_reflex as CR  # noqa: E402

n_fail = 0
n_total = 0


def check(name, ok, detail=""):
    global n_fail, n_total
    n_total += 1
    print(("ok   " if ok else "FAIL ") + name + (("  -- %s" % (detail,)) if detail else ""))
    if not ok:
        n_fail += 1


TMP = tempfile.mkdtemp(prefix="cr1_")
state = os.path.join(TMP, "state.json")
log = os.path.join(TMP, "log.jsonl")

NEW_A = "tell me about neuromorphic spiking cognition architectures"
NEW_B = "explain photosynthesis chloroplast membrane gradients"
SHORT = "hi there"

# CR1.1: a clearly-new topic fires and returns Tetsu's exact words
r1 = CR.cue_line(NEW_A, state_path=state, log_path=log)
check("CR1.1 a clearly-new topic fires the advisory", r1 == CR.LINE, repr(r1))
check("CR1.2 the line is Tetsu's exact words", CR.LINE == "This input seems novel; consider carefully before proceeding.")

# CR1.3: the SAME topic again is quiet (seen persisted to state)
r2 = CR.cue_line(NEW_A, state_path=state, log_path=log)
check("CR1.3 the same topic again is quiet (persisted seen-set)", r2 is None, repr(r2))

# CR1.4 both ways: a DIFFERENT new topic fires -- not vacuously always-None
r3 = CR.cue_line(NEW_B, state_path=state, log_path=log)
check("CR1.4 a different new topic fires (not vacuous)", r3 == CR.LINE, repr(r3))

# CR1.5: too short to be a topic -> quiet (his limit: clearly-new topics only)
r4 = CR.cue_line(SHORT, state_path=state, log_path=log)
check("CR1.5 a too-short input is quiet", r4 is None, repr(r4))

# CR1.6: the kill switch silences it even on a brand-new topic
os.environ["COVENANT_VERDICT_CACHE_OFF"] = "1"
try:
    r5 = CR.cue_line("an utterly fresh unrelated subject about volcano geochemistry basalt", state_path=state, log_path=log)
finally:
    del os.environ["COVENANT_VERDICT_CACHE_OFF"]
check("CR1.6 the kill switch (COVENANT_VERDICT_CACHE_OFF) silences the reflex", r5 is None, repr(r5))

# CR1.7: the seen-set persisted to disk (topic A's signature is recorded)
import json  # noqa: E402
seen = set()
try:
    seen = set(json.load(open(state, encoding="utf-8")).get("seen") or [])
except Exception:  # noqa: BLE001
    pass
check("CR1.7 the fired topic's signature persisted", CR.topic_signature(NEW_A) in seen, sorted(seen))

# CR1.8: a malformed/empty input never raises, returns None
check("CR1.8 empty input is quiet, never raises", CR.cue_line("", state_path=state, log_path=log) is None)

print("\nCR1: %d/%d passed" % (n_total - n_fail, n_total))
sys.exit(1 if n_fail else 0)
