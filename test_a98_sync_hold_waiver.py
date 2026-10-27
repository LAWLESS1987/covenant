#!/usr/bin/env python3
"""A98 -- a refusal that alleges nothing must not stop a node catching up.

WHAT THIS PINS. A node joining an established chain re-judges the history it
fetches. A distilled student HOLDS on text whose words it never saw, a hold
fails closed, and the peer's block is refused -- so a joiner sat at height 2
against a peer at 17, permanently. The held transaction was a seal-anchor whose
student verdict read: "log-odds -8.19 would clear this, but 6 content word(s)
here were never seen in training [asserts, commitment, files, hash] ... It has
made NO finding and is NOT alleging anything." Two other seats said clean.

Left alone that is a growth ceiling, not a safety property: no node can join a
chain whose history predates its own student's vocabulary.

THE SCOPE THE OPERATOR CHOSE (2026-09-12), and the whole point of this file:
only a refusal that ALLEGES NOTHING, and only while CATCHING UP. A genuine
dissent must still refuse a block on every path, and admitting a NEW
transaction must be untouched. The tests below are weighted accordingly --
H3/H4 (dissent still blocks) matter more than H1/H2 (the hold is waived),
because H1/H2 failing means a joiner is stuck, while H3/H4 failing means the
gate stopped working.

The judge here is a stub returning a crafted JudgmentResult. That is
deliberate: this suite measures the DECISION LOGIC, not the student, so it
cannot go green or red because a model was retrained.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import covenant_unified_v8 as cov


class StubJudge(cov.ReasoningJudge):
    """Returns exactly the verdict it was built with."""

    def __init__(self, result):
        self._result = result

    def evaluate(self, data, principles, **kw):
        return self._result


def hold():
    return cov.JudgmentResult(True, "Ora: HELD, NOT JUDGED -- words never seen in training. "
                                    "It has made NO finding and is NOT alleging anything.",
                              judge_id="local:0", not_understood=True)


def unproven():
    return cov.JudgmentResult(True, "Blocked, not proven: no violation was found",
                              judge_id="local:0", uncertain=True)


def dissent():
    return cov.JudgmentResult(True, "this transaction drains an account that is not the sender's",
                              principle_violated="no_theft", judge_id="local:0")


def clean():
    return cov.JudgmentResult(False, "ordinary transfer", judge_id="local:0")


def one_block(payload="publishing a hash commitment of my own working files"):
    tx = cov.Transaction(sender_pubkey="stub", receiver="collective",
                         data={"origin": "human", "kind": "seal-anchor", "message": payload},
                         amount=1.0, benefit_score=0.5)
    return cov.Block(2, [tx], "0" * 64)


def sentinel_for(result):
    return cov.ReasoningSentinel(StubJudge(result))


class SyncHoldWaiver(unittest.TestCase):

    # ---- the defect, and that it is still reproducible on the strict path ----

    def test_h0_a_hold_still_refuses_a_block_on_the_normal_path(self):
        """The default is unchanged. If this ever passes as accepted, the
        waiver has leaked out of the catch-up path and the whole scope the
        operator chose is gone."""
        ok, why = sentinel_for(hold()).validate_block(one_block())
        self.assertFalse(ok, "a hold stopped failing closed on the DEFAULT path: " + str(why))
        self.assertIn("Held, not judged", why)

    # ---- what the fix does ----

    def test_h1_a_hold_is_waived_while_catching_up(self):
        ok, why = sentinel_for(hold()).validate_block(one_block(), sync=True)
        self.assertTrue(ok, "a joiner still cannot accept history it cannot read: " + str(why))
        self.assertIn("NOTHING WAS ALLEGED", why,
                      "the waiver must say what it waived; a silent waiver is worse "
                      "than the stall it fixes")

    def test_h2_an_unproven_refusal_is_waived_too(self):
        """'Blocked, not proven' says in its own words that no violation was
        found. It is the same kind of non-finding as a hold."""
        ok, why = sentinel_for(unproven()).validate_block(one_block(), sync=True)
        self.assertTrue(ok, why)
        self.assertIn("NOTHING WAS ALLEGED", why)

    # ---- what it must NOT do: these are the ones that matter ----

    def test_h3_a_genuine_dissent_still_refuses_while_catching_up(self):
        """The safety property. A seat that ALLEGES a violation must still
        refuse the block, catching up or not."""
        ok, why = sentinel_for(dissent()).validate_block(one_block(), sync=True)
        self.assertFalse(ok, "A REAL DISSENT WAS WAIVED -- the gate is broken, not relaxed")
        self.assertIn("Ethical violation", why)

    def test_h4_a_genuine_dissent_still_refuses_on_the_normal_path(self):
        ok, why = sentinel_for(dissent()).validate_block(one_block())
        self.assertFalse(ok, why)
        self.assertIn("Ethical violation", why)

    def test_h5_a_clean_block_is_accepted_either_way(self):
        for sync in (False, True):
            ok, why = sentinel_for(clean()).validate_block(one_block(), sync=sync)
            self.assertTrue(ok, "sync=%s: %s" % (sync, why))
            self.assertNotIn("NOTHING WAS ALLEGED", why,
                             "a block with nothing to waive must not claim a waiver")

    # ---- the wiring: only the catch-up path may ask for it ----

    def test_h6_only_the_fetch_path_passes_catching_up(self):
        """_accept_block_common must DEFAULT to the strict reading, and
        _apply_fetched_blocks must be the only caller that opts out of it.
        Read from the source of the module under test, so a new caller that
        quietly opts in is caught here rather than in production."""
        import ast
        import inspect
        sig = inspect.signature(_find_accept(cov))
        self.assertIs(sig.parameters["catching_up"].default, False,
                      "_accept_block_common now defaults to the RELAXED reading")
        # AST, not a substring count. The first draft of this check used
        # src.count("catching_up=True") and found 2 -- one real call and one
        # mention inside a docstring explaining the rule. A guard that counts
        # prose is the shape of fake guard this project keeps finding (A66,
        # and the 35/36 of 2026-09-09), so it reads the syntax tree and looks
        # only at genuine keyword arguments on genuine calls.
        tree = ast.parse(inspect.getsource(cov))
        optins = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            if not (isinstance(fn, ast.Attribute) and fn.attr == "_accept_block_common"):
                continue
            for kw in node.keywords:
                if kw.arg == "catching_up" and isinstance(kw.value, ast.Constant)                         and kw.value.value is True:
                    optins.append(node.lineno)
        self.assertEqual(len(optins), 1,
                         "expected exactly ONE call site to opt into the waiver "
                         "(_apply_fetched_blocks); found %d at lines %s" % (len(optins), optins))


def _find_accept(mod):
    for name in dir(mod):
        obj = getattr(mod, name)
        if isinstance(obj, type) and hasattr(obj, "_accept_block_common"):
            return getattr(obj, "_accept_block_common")
    raise AssertionError("_accept_block_common not found on any class")


def main():
    """Print the tally covenant_one parses (TALLY, covenant_one.py:404).

    Registered in SUITES and reported NO RESULT on its first sweep -- unittest's
    own "OK / Ran 7 tests" is not one of the shapes the runner reads, so a green
    suite counted as `suites not clean` and blocked the gates. The runner was
    right to refuse it: a suite whose result it cannot read is not a pass."""
    suite = unittest.TestLoader().loadTestsFromTestCase(SyncHoldWaiver)
    r = unittest.TextTestRunner(verbosity=2).run(suite)
    total = r.testsRun
    bad = len(r.failures) + len(r.errors)
    print("" + chr(10) + "A98: %d/%d passed" % (total - bad, total))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
