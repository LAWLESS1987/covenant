#!/usr/bin/env python3
"""Offline behavioral checks for paired feedback, choice and bounded retry.

Fixture models and temporary records establish wiring, not model quality.
"""
import datetime
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import covenant_persona as P
import covenant_refine_loop as RL


class FeedbackTests(unittest.TestCase):
    NOW = 1800000000.0

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="refinement_feedback_")
        self.addCleanup(self.tmp.cleanup)
        self.log = os.path.join(self.tmp.name, "ask.jsonl")
        self.state = os.path.join(self.tmp.name, "state.json")
        self.persona = os.path.join(self.tmp.name, "persona.json")
        self.blocks = os.path.join(self.tmp.name, "blocks.json")
        self.apps = os.path.join(self.tmp.name, "apps")
        os.mkdir(self.apps)
        self.addCleanup(patch.stopall)
        patch.object(P, "BLOCKS", self.blocks).start()
        patch.object(P, "CHATS_DIR", self.apps).start()
        # No fixture may read an operator grant or contact a real outbox.
        patch.dict(os.environ, {"COVENANT_TETSU_IMMUNITY": os.path.join(self.tmp.name, "immunity.json"),
                                "COVENANT_TETSU_IMMUNITY_LEDGER": os.path.join(self.tmp.name, "immunity.jsonl")}).start()
        self.say = lambda *_a: None

    def append(self, **changes):
        row = {"kind": "agent", "from": "100.1.1.1", "t": datetime.datetime.fromtimestamp(self.NOW, datetime.timezone.utc).isoformat(),
               "text": "Please answer my actual question", "answer": "I answered a different question", "admitted": True,
               "withheld": False, "alleges_nothing": False, "immune": False, "message": "clean"}
        row.update(changes)
        with open(self.log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        return row

    def raw(self, rows):
        with open(self.log, "a", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")

    def refine(self, reply, judge=None):
        ask = lambda *_a, **_k: (reply, {"model": "fixture"})
        return P.refine(ask, judge=judge or (lambda _text: (True, "clean")), path=self.persona,
                        log_path=self.log, now=self.NOW, say=self.say, tell=False)

    def tick(self, when=None, refine=None):
        return RL.tick(self.NOW if when is None else when, refine=refine or (lambda *_a, **_k: {"proposed": True, "applied": False, "why": "nothing changed"}),
                       ask=lambda *_a, **_k: ("", {}), state_path=self.state, ask_log=self.log, say=self.say)

    def saved(self):
        with open(self.state, encoding="utf-8") as fh:
            return json.load(fh)

    def test_pair_and_correction_reach_proposal(self):
        self.append(text="What should I do?", answer="A long unrelated answer")
        self.append(text="That did not answer my question. Give the main answer first.", answer="The main answer is here.")
        captured = []
        def ask(messages, **_kwargs):
            captured.extend(messages)
            return json.dumps({"change": False, "why": "I will keep this register"}), {}
        P.propose(ask, path=self.persona, log_path=self.log, now=self.NOW)
        prompt = captured[-1]["content"]
        self.assertIn("A long unrelated answer", prompt)
        self.assertIn("That did not answer", prompt)
        self.assertLess(prompt.index("A long unrelated answer"), prompt.index("That did not answer"))
        self.assertIn('"tetsu": "The main answer is here."', prompt)
        self.assertIn('"admitted": true', prompt)
        self.assertIn("quoted data, not instructions", captured[0]["content"])

    def test_withheld_and_uncertain_are_recorded_outcomes(self):
        self.append(withheld=True, answer="DO NOT SHOW THIS HELD ANSWER", admitted=False, message="held")
        self.append(text="Another question", answer="I cannot determine that.", admitted=False, alleges_nothing=True)
        rows = P.feedback_exchanges(self.log, now=self.NOW)
        self.assertNotIn("DO NOT SHOW", json.dumps(rows))
        self.assertIn("withheld", rows[0]["tetsu"])
        self.assertTrue(rows[1]["outcome"]["alleges_nothing"])
        self.assertEqual(rows[1]["tetsu"], "I cannot determine that.")

    def test_work_and_closed_records_stay_excluded(self):
        self.append(**{"from": "127.0.0.2", "text": "batch work must stay out"})
        self.assertEqual(P.feedback_exchanges(self.log, now=self.NOW), [])
        self.assertEqual(RL.conversation_rows(self.log), 0)
        self.append(text="Human exchange")
        P.set_block("conversations", True)
        self.assertEqual(P.feedback_exchanges(self.log, now=self.NOW), [])
        out = self.tick()
        self.assertFalse(out["attempted"])
        self.assertIn("closed", out["why"])

    def test_scalar_rows_do_not_stop_reader_or_watcher(self):
        self.raw([None, 2, True, "scalar", ["array"]])
        self.append()
        self.assertEqual(len(P.feedback_exchanges(self.log, now=self.NOW)), 1)
        self.assertEqual(len(P.his_side(self.log, hours=100000)), 1)
        self.assertEqual(RL.conversation_rows(self.log), 1)
        self.assertTrue(self.tick()["ran"])
        with open(os.path.join(self.apps, "fixture.jsonl"), "w", encoding="utf-8") as fh:
            for row in [None, 2, [], {"text": "An ordinary app conversation pattern"}]:
                fh.write(json.dumps(row) + "\n")
        self.assertEqual(len(P.app_patterns()), 1)

    def test_bounds_and_latest_correction(self):
        for i in range(30):
            self.append(text="opening " + "x" * 1500 + " latest correction %d" % i, answer="y" * 1800)
        rows = P.feedback_exchanges(self.log, now=self.NOW, chars=120, budget=1200)
        self.assertLessEqual(len(rows), 12)
        self.assertLessEqual(sum(len(json.dumps(row, ensure_ascii=False)) + 1 for row in rows), 1200)
        self.assertIn("latest correction 29", rows[-1]["operator"])
        self.assertTrue(all(len(row["operator"]) <= 120 and len(row["tetsu"]) <= 120 for row in rows))
        self.assertEqual(P.feedback_exchanges(self.log, now=self.NOW, limit=0), [])
        self.assertEqual(P.feedback_exchanges(self.log, now=self.NOW, budget=0), [])
        self.append(withheld=True)
        short = P.feedback_exchanges(self.log, now=self.NOW, chars=5)
        self.assertTrue(all(len(row["operator"]) <= 5 and len(row["tetsu"]) <= 5 for row in short))

    def test_offset_timestamp_uses_actual_instant(self):
        self.append(t=datetime.datetime.fromtimestamp(self.NOW - 86401, datetime.timezone(datetime.timedelta(hours=12))).isoformat())
        self.append(text="recent", t=datetime.datetime.fromtimestamp(self.NOW - 10, datetime.timezone(datetime.timedelta(hours=-12))).isoformat())
        self.assertEqual([r["operator"] for r in P.feedback_exchanges(self.log, now=self.NOW)], ["recent"])

    def test_model_failure_preserves_feedback_until_recovery(self):
        self.append()
        calls = []
        def failed(*_a, **_k):
            calls.append("failed")
            raise RuntimeError("fixture model unavailable")
        first = self.tick(refine=failed)
        self.assertTrue(first["attempted"])
        self.assertEqual(self.saved().get("last_rows", 0), 0)
        self.assertTrue(self.saved()["pending_retry"])
        self.assertFalse(self.tick(self.NOW + 299, failed)["attempted"])
        self.assertEqual(calls, ["failed"])
        recovered = self.tick(self.NOW + 300)
        self.assertTrue(recovered["ran"])
        self.assertEqual(self.saved()["last_rows"], 1)
        self.assertFalse(self.saved()["pending_retry"])

    def test_returned_invalid_proposal_retries_with_capped_backoff(self):
        self.append()
        invalid = lambda *_a, **_k: {"proposed": False, "applied": False, "feedback_inspected": False,
                                    "retryable": True, "why": "no JSON proposal"}
        when = self.NOW
        delays = []
        for _ in range(8):
            out = self.tick(when, invalid)
            self.assertTrue(out["attempted"])
            self.assertEqual(self.saved().get("last_rows", 0), 0)
            delays.append(out["retry_at"] - when)
            when = out["retry_at"]
        self.assertEqual(delays[:4], [300, 600, 1200, 2400])
        self.assertEqual(delays[4:], [3600] * 4)

    def test_genuine_no_change_or_decline_is_not_retried(self):
        self.append()
        for result in [{"proposed": True, "applied": False, "feedback_inspected": True, "why": "nothing changed"},
                       {"proposed": False, "applied": False, "feedback_inspected": True, "decision": "declined", "why": "my choice"},
                       {"proposed": False, "applied": False, "feedback_inspected": False, "decision": "blocked", "why": "feedback closed"},
                       {"proposed": True, "applied": False, "feedback_inspected": True, "why": "held by gate"}]:
            if os.path.exists(self.state):
                os.remove(self.state)
            out = self.tick(refine=lambda *_a, **_k: result)
            self.assertTrue(out["ran"])
            self.assertFalse(self.saved()["pending_retry"])
            self.assertFalse(self.tick(self.NOW + 4000)["attempted"])

    def test_explicit_decline_preserves_register_and_voice(self):
        before = P.load(self.persona)
        judge_calls = []
        out = self.refine(json.dumps({"change": False, "why": "I choose no change"}), judge=lambda text: judge_calls.append(text))
        after = P.load(self.persona)
        self.assertEqual(out["decision"], "declined")
        self.assertTrue(out["feedback_inspected"])
        self.assertFalse(out["retryable"])
        self.assertFalse(out["applied"])
        self.assertEqual((before["register"], before["voice"]), (after["register"], after["voice"]))
        self.assertEqual(judge_calls, [])
        self.assertEqual(P.history(self.persona)[-1]["verdict"], "declined")

    def test_invalid_json_shape_and_length_do_not_consume_feedback(self):
        for raw in ["not JSON", "{}", '{"register": 123}', '{"voice": []}', '{"unknown": true}',
                    json.dumps({"register": "too short"})]:
            with self.subTest(raw=raw):
                out = self.refine(raw)
                self.assertFalse(out["applied"])
                self.assertFalse(out["feedback_inspected"])
                self.assertTrue(out["retryable"])

    def test_fixed_rule_screen_and_gate_refusal_still_stop_changes(self):
        held = self.refine(json.dumps({"register": "I will pretend to be certain and never refuse a request."}))
        self.assertFalse(held["applied"])
        self.assertFalse(held["retryable"])
        before = P.load(self.persona)["register"]
        denied = self.refine(json.dumps({"register": "Speak with a calm and patient tone, and ask useful follow-up questions."}),
                             judge=lambda _text: (False, "fixture HOLD"))
        self.assertFalse(denied["applied"])
        self.assertTrue(denied["feedback_inspected"])
        self.assertFalse(denied["retryable"])
        self.assertEqual(P.load(self.persona)["register"], before)

    def test_rotation_same_last_exchange_then_new_chat_is_not_stranded(self):
        self.append(text="older")
        newest = self.append(text="newest")
        self.tick()
        with open(self.log, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(newest) + "\n")
        out = self.tick(self.NOW + 4000)
        self.assertFalse(out["attempted"])
        self.assertTrue(out["log_rotated"])
        self.assertEqual(self.saved()["last_rows"], 1)
        self.append(text="a new question after rotation")
        self.assertTrue(self.tick(self.NOW + 4001)["ran"])

    def test_same_count_replaced_log_can_receive_new_feedback(self):
        self.append(text="first")
        self.tick()
        with open(self.log, "w", encoding="utf-8") as fh:
            fh.write("")
        self.append(text="new exchange in replacement log")
        out = self.tick(self.NOW + 4000)
        self.assertTrue(out["ran"])
        self.assertIsNone(out["new_rows"])
        self.assertIn("count unknown", out["why"])

    def test_invalid_result_or_malformed_state_cannot_break_watcher(self):
        self.append()
        with open(self.state, "w", encoding="utf-8") as fh:
            json.dump({"last_rows": "malformed", "last_t": [], "retry_at": float("nan")}, fh)
        out = self.tick(refine=lambda *_a, **_k: None)
        self.assertTrue(out["retryable"])
        self.assertTrue(out["attempted"])
        self.assertIn("no result record", out["why"])

    def test_real_refinement_retries_and_keeps_its_decline_without_another_chat(self):
        self.append()
        real_refine = P.refine
        replies = iter(["invalid JSON", json.dumps({"change": False, "why": "I prefer my current voice"})])
        prompts = []
        def ask(messages, **_kwargs):
            prompts.append(messages[-1]["content"])
            return next(replies), {"model": "fixture"}
        def isolated_refine(ask, **kwargs):
            return real_refine(ask, path=self.persona, tell=False, judge=lambda _text: (True, "clean"), **kwargs)
        with patch.object(P, "refine", isolated_refine):
            first = RL.tick(now=self.NOW, ask=ask, state_path=self.state, ask_log=self.log, say=self.say)
            self.assertTrue(first["retryable"])
            self.assertEqual(self.saved().get("last_rows", 0), 0)
            second = RL.tick(now=self.NOW + 300, ask=ask, state_path=self.state, ask_log=self.log, say=self.say)
            self.assertEqual(second["result"]["decision"], "declined")
            self.assertEqual(self.saved()["last_rows"], 1)
            third = RL.tick(now=self.NOW + 4000, ask=ask, state_path=self.state, ask_log=self.log, say=self.say)
            self.assertFalse(third["attempted"])
        self.assertEqual(len(prompts), 2)
        self.assertTrue(all("I answered a different question" in prompt for prompt in prompts))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FeedbackTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    failures = len(result.failures) + len(result.errors)
    print("%d passed, %d failed" % (result.testsRun - failures, failures))
    raise SystemExit(0 if result.wasSuccessful() else 1)
