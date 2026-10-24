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

# --- A381: associative recall via his spiking encoder ---
enc = os.path.join(TMP, "enc.json")
A = "quantum entanglement spooky distance correlation measurement"
B = "quantum entanglement spooky distance correlation physics"   # shares 5/6 content words with A, different signature
UNREL = "baking sourdough bread fermentation yeast proofing"
check("CR1.9 the first topic has nothing to connect to (quiet)", CR.recall_line(A, state_path=enc) is None)
rb = CR.recall_line(B, state_path=enc)
check("CR1.10 a strongly-related later topic connects to the earlier one",
      bool(rb) and rb.startswith("This connects to an earlier topic:") and "entanglement" in rb, repr(rb))
check("CR1.11 an unrelated topic is quiet (both ways -- not vacuously firing)",
      CR.recall_line(UNREL, state_path=enc) is None)
os.environ["COVENANT_VERDICT_CACHE_OFF"] = "1"
try:
    rk = CR.recall_line(A, state_path=enc)
finally:
    del os.environ["COVENANT_VERDICT_CACHE_OFF"]
check("CR1.12 recall respects the kill switch", rk is None)

# Caller and privacy partitions: no live/default paths are used in these probes.
sa = CR.conversation_scope("caller-a", True)
sb = CR.conversation_scope("caller-b", True)
sap = CR.conversation_scope("caller-a", False)
scoped_state = os.path.join(TMP, "scoped.json")
scoped_enc = os.path.join(TMP, "scoped-enc.json")
scoped_log = os.path.join(TMP, "scoped.jsonl")
check("CR1.13 private first topic cues", CR.cue_line(A, scoped_state, scoped_log, scope=sa) == CR.LINE)
check("CR1.14 own repeat stays quiet", CR.cue_line(A, scoped_state, scoped_log, scope=sa) is None)
check("CR1.15 another caller has an independent seen set", CR.cue_line(A, scoped_state, scoped_log, scope=sb) == CR.LINE)
check("CR1.16 public mode has an independent seen set", CR.cue_line(A, scoped_state, scoped_log, scope=sap) == CR.LINE)
CR.recall_line(A, scoped_enc, scope=sa)
check("CR1.17 another caller cannot recall a private topic", CR.recall_line(B, scoped_enc, scope=sb) is None)
check("CR1.18 public mode cannot recall a private topic", CR.recall_line(B, scoped_enc, scope=sap) is None)
check("CR1.19 own private recall still works", CR.recall_line(B, scoped_enc, scope=sa) is not None)
check("CR1.20 scoped logging leaves shared log absent", not os.path.exists(scoped_log))
legacy_bytes = open(enc, "rb").read()
check("CR1.21 legacy shared topics are not imported", CR.recall_line(B, enc, scope=sa) is None)
check("CR1.22 legacy shared topics are not rewritten", open(enc, "rb").read() == legacy_bytes)
check("CR1.23 invalid scope produces no advisory", CR.cue_line(A, scoped_state, scoped_log, scope="") is None)
check("CR1.24 scope cannot traverse directories", os.path.dirname(CR._scoped_path(scoped_state, "../../outside")) == TMP)

# Keep the experiment's own regression guard on the existing CR1 sweep path.
import unittest
from test_cue_eval import OfflineEvaluationTest
evaluation_checks = unittest.defaultTestLoader.loadTestsFromTestCase(OfflineEvaluationTest)
check("CR1.25 offline counterfactual evidence guard", unittest.TextTestRunner().run(evaluation_checks).wasSuccessful())

print("\nCR1: %d/%d passed" % (n_total - n_fail, n_total))
sys.exit(1 if n_fail else 0)
