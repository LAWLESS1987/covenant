"""Lost replies cannot rerun a conversational action within the reply window."""
import json
import base64
import os
import tempfile
import threading
import unittest
from unittest.mock import patch

from flask import Flask, jsonify, make_response
from covenant_conversation import ConversationReplies


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.context = self.app.app_context()
        self.context.push()
        self.addCleanup(self.context.pop)
        self.now = 0
        self.cache = ConversationReplies(capacity=2, retention=10, clock=lambda: self.now)
        self.calls = 0

    def work(self):
        self.calls += 1
        return jsonify(status="success", answer="work completed", number=self.calls)

    def reply(self, body=None, caller="alice", door="agent", work=None):
        return make_response(self.cache.reply(caller, door,
                                             body if body is not None else {"text": "help", "request_id": "turn-1"},
                                             work or self.work))

    def test_same_id_returns_original_bytes_and_does_not_repeat_work(self):
        first = self.reply()
        second = self.reply()
        self.assertEqual(first.data, second.data)
        self.assertEqual(first.status_code, second.status_code)
        self.assertEqual(first.content_type, second.content_type)
        self.assertEqual(self.calls, 1)

    def test_same_id_cannot_be_repurposed_for_a_different_turn(self):
        self.reply()
        conflict = self.reply({"text": "different action", "request_id": "turn-1"})
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(self.calls, 1)

    def test_caller_and_door_are_independent(self):
        self.reply()
        self.reply(caller="bob")
        self.assertEqual(self.calls, 2)
        self.cache = ConversationReplies()
        self.reply()
        self.reply(door="council")
        self.assertEqual(self.calls, 4)

    def test_legacy_requests_remain_ordinary_turns(self):
        self.reply({"text": "hello"})
        self.reply({"text": "hello"})
        self.assertEqual(self.calls, 2)

    def test_invalid_id_never_reaches_work(self):
        for request_id in ("", "x" * 129, [], 12, "a/b", "a\n", True):
            with self.subTest(request_id=request_id):
                self.assertEqual(self.reply({"request_id": request_id}).status_code, 400)
        self.assertEqual(self.calls, 0)

    def test_capacity_preserves_existing_records_without_running_new_work(self):
        self.reply()
        self.reply({"request_id": "turn-2"})
        self.assertEqual(self.reply({"request_id": "turn-3"}).status_code, 503)
        self.assertEqual(self.reply().get_json()["number"], 1)
        self.assertEqual(self.calls, 2)

    def test_expiry_explicitly_ends_replay_protection(self):
        self.reply()
        self.now = 9.9
        self.reply()
        self.assertEqual(self.calls, 1)
        self.now = 10
        self.reply()
        self.assertEqual(self.calls, 2)

    def test_refusals_and_failure_statuses_are_replayed(self):
        def refused():
            self.calls += 1
            return jsonify(status="success", withheld=True, answer="", message="mutual benefit not established"), 200
        self.assertTrue(self.reply(work=refused).get_json()["withheld"])
        self.assertTrue(self.reply(work=refused).get_json()["withheld"])
        self.assertEqual(self.calls, 1)
        self.cache = ConversationReplies()
        def unavailable():
            self.calls += 1
            return jsonify(status="error", message="keeper unavailable"), 503
        self.assertEqual(self.reply(work=unavailable).status_code, 503)
        self.assertEqual(self.reply(work=unavailable).status_code, 503)
        self.assertEqual(self.calls, 2)

    def test_exception_after_work_is_remembered(self):
        def broken():
            self.calls += 1
            raise RuntimeError("fixture, after action")
        first = self.reply(work=broken)
        self.assertEqual(first.status_code, 503)
        self.assertEqual(self.reply(work=broken).data, first.data)
        self.assertEqual(self.calls, 1)

    def test_pending_turn_is_not_repeated_or_expired(self):
        begun, finish = threading.Event(), threading.Event()
        results = []
        def slow():
            self.calls += 1
            begun.set()
            if not finish.wait(5):
                raise RuntimeError("fixture timeout")
            return self.work()
        def worker():
            with self.app.app_context():
                results.append(self.reply(work=slow))
        thread = threading.Thread(target=worker)
        thread.start()
        try:
            self.assertTrue(begun.wait(5))
            self.now = 1000
            pending = self.reply(work=slow)
            self.assertEqual(pending.status_code, 409)
            self.assertTrue(pending.get_json()["in_progress"])
            self.assertEqual(self.calls, 1)
        finally:
            finish.set()
            thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(results), 1)
        self.assertEqual(self.reply().data, results[0].data)
        self.assertEqual(self.calls, 2)  # slow's start plus its single completed work


class DoorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix="conversation_doors_")
        cls.env = patch.dict(os.environ, {
            "COVENANT_MODEL_STUB": "1", "COVENANT_QUIET": "1",
            "COVENANT_ASK_LOG": os.path.join(cls.scratch.name, "ask.jsonl"),
            "COVENANT_TEACHER_QUEUE": os.path.join(cls.scratch.name, "queue.jsonl"),
            "COVENANT_TETSU_IMMUNITY": os.path.join(cls.scratch.name, "no_grant.json"),
            "COVENANT_TETSU_IMMUNITY_LEDGER": os.path.join(cls.scratch.name, "immunity.jsonl"),
            "COVENANT_PAUSE_DIR": os.path.join(cls.scratch.name, "pause"),
        })
        cls.env.start()
        import covenant_unified_v8 as cov
        import covenant_council as council
        cls.cov, cls.council = cov, council
        cls.master = cov.CovenantUnifiedMaster("REPLAY", host="127.0.0.1", port=5495,
                                             p2p_port=5496, db_path=os.path.join(cls.scratch.name, "fixture.db"))
        cls.master.add_genesis_block()
        cls.master.node.sentinel = cov.ReasoningSentinel(cov.MockJudge(), cov.DIVINE_PRINCIPLES)
        cls.fixture_keys = [cov.sig_keygen()[0] for _ in range(2)]
        cls.counter = 0

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        cls.scratch.cleanup()

    def setUp(self):
        type(self).counter += 1
        self.addr = "100.72.3.%d" % self.counter
        self.client = self.master.api.app.test_client()
        self.system = patch("covenant_persona.compose_system", return_value="fixture standing system")
        self.system.start()
        self.addCleanup(self.system.stop)
        import covenant_daily_plan as plan
        import covenant_mycelium as mycelium
        self.plan, self.mycelium = plan, mycelium
        self.signers = os.path.join(self.scratch.name, "signers-%d.json" % self.counter)
        for index, key in enumerate(self.fixture_keys):
            plan.register_signer("fixture-phone-%d" % index, plan.pubkey_pem(key), self.signers)
        for module, attribute, value in [
                (plan, "SIGNERS", self.signers), (plan, "_seen_nonces", set()),
                (mycelium, "PEERS", os.path.join(self.scratch.name, "no-allies.json")),
                (mycelium, "LEDGER", os.path.join(self.scratch.name, "wire-%d.jsonl" % self.counter)),
                (mycelium, "_seen", set())]:
            fixture = patch.object(module, attribute, value)
            fixture.start()
            self.addCleanup(fixture.stop)

    def post(self, path, body, addr=None):
        return self.client.post(path, json=body, environ_base={"REMOTE_ADDR": addr or self.addr})

    def signed_post(self, path, body, addr="192.168.1.3", key_index=0, headers=None, pem=None):
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        key = self.fixture_keys[key_index]
        headers = headers or self.cov.sign_operator_request(key, pem or self.plan.pubkey_pem(key), "POST", path, raw)
        return self.client.post(path, data=raw, headers=headers, content_type="application/json",
                                environ_base={"REMOTE_ADDR": addr})

    def test_agent_retry_replays_one_model_answer(self):
        with patch("covenant_model.ask", return_value=("I can help with that.", {"model": "fixture", "ms": 1})) as ask:
            body = {"text": "hello", "request_id": "agent-repeat"}
            first = self.post("/m/agent", body)
            second = self.post("/m/agent", body)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(second.data, first.data)
        self.assertEqual(ask.call_count, 1)

    def test_retry_cannot_repeat_tetsus_heal_action(self):
        with patch("covenant_model.ask", side_effect=[("HEAL", {"model": "fixture"}),
                                                      ("I checked the fixture repair.", {"model": "fixture"})]) as ask, \
                patch("covenant_tetsu_heal.act", return_value=(True, "fixture repair", {"kind": "heal"})) as heal:
            body = {"text": "check and repair", "request_id": "heal-repeat"}
            first = self.post("/m/agent", body)
            second = self.post("/m/agent", body)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(second.data, first.data)
        self.assertEqual(heal.call_count, 1)
        self.assertEqual(ask.call_count, 2)

    def test_council_retry_uses_carried_complete_pairs_once(self):
        carried = [{"role": "user", "content": "Please remember the blue orb"},
                   {"role": "assistant", "content": "I remember the blue orb"}]
        steps = [{"role": "reviser", "content": "fixture answer", "model": "fixture", "ms": 1}]
        with patch.object(self.council, "deliberate", return_value=(steps, "The blue orb.")) as deliberate:
            body = {"text": "which orb?", "history": carried, "request_id": "council-repeat"}
            first = self.post("/pc/council", body)
            second = self.post("/pc/council", body)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first.data, second.data)
        self.assertEqual(deliberate.call_count, 1)
        self.assertEqual(deliberate.call_args.args[1], carried)

    def test_authentication_is_required_even_for_a_cached_id(self):
        body = {"text": "hello", "request_id": "auth-repeat"}
        with patch("covenant_model.ask", return_value=("Hello.", {"model": "fixture"})) as ask, \
                patch("covenant_mycelium.admit", return_value=(False, "192.168.1.2", "", "fixture")):
            self.assertEqual(self.post("/m/agent", body).status_code, 200)
            self.assertEqual(self.post("/m/agent", body, "192.168.1.2").status_code, 403)
        self.assertEqual(ask.call_count, 1)

    def test_signed_lan_auth_is_checked_once_per_request(self):
        for path in ("/m/agent", "/pc/council"):
            with self.subTest(path=path), \
                    patch("covenant_mycelium.admit", return_value=(True, self.addr, "fixture-phone", "signed")) as admit, \
                    patch("covenant_model.ask", return_value=("Hello.", {"model": "fixture", "ms": 1})), \
                    patch.object(self.council, "deliberate", return_value=([{"role": "reviser", "content": "Hello.", "model": "fixture", "ms": 1}], "Hello.")):
                body = {"text": "hello", "request_id": "lan-repeat"}
                self.assertEqual(self.post(path, body, "192.168.1.3").status_code, 200)
                self.assertEqual(self.post(path, body, "192.168.1.3").status_code, 200)
                self.assertEqual(admit.call_count, 2)

    def test_real_signed_keys_at_one_lan_address_cannot_share_cached_reply(self):
        body = {"text": "hello", "request_id": "distinct-verified-keys"}
        with patch("covenant_model.ask", side_effect=[("Reply for the first key.", {"model": "fixture"}),
                                                    ("Reply for the second key.", {"model": "fixture"})]) as ask:
            first = self.signed_post("/m/agent", body)
            second = self.signed_post("/m/agent", body, key_index=1)
            first_retry = self.signed_post("/m/agent", body)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(second.status_code, 200, second.data)
        self.assertNotEqual(first.data, second.data)
        self.assertEqual(first_retry.data, first.data)
        self.assertEqual(ask.call_count, 2)

    def test_real_signed_identity_survives_a_lan_address_change(self):
        body = {"text": "hello", "request_id": "verified-key-new-address"}
        with patch("covenant_model.ask", return_value=("I remember this turn.", {"model": "fixture"})) as ask:
            first = self.signed_post("/m/agent", body, addr="192.168.1.3")
            second = self.signed_post("/m/agent", body, addr="192.168.1.4")
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(second.data, first.data)
        self.assertEqual(ask.call_count, 1)

    def test_cache_does_not_bypass_real_signature_or_nonce_verification(self):
        body = {"text": "hello", "request_id": "verify-before-replay"}
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        headers = self.cov.sign_operator_request(self.fixture_keys[0], self.plan.pubkey_pem(self.fixture_keys[0]), "POST", "/m/agent", raw)
        with patch("covenant_model.ask", return_value=("Authenticated reply.", {"model": "fixture"})) as ask:
            first = self.signed_post("/m/agent", body, headers=headers)
            reused = self.signed_post("/m/agent", body, headers=headers)
            forged = self.cov.sign_operator_request(self.fixture_keys[1], self.plan.pubkey_pem(self.fixture_keys[0]), "POST", "/m/agent", raw)
            denied = self.signed_post("/m/agent", body, headers=forged)
            fresh = self.signed_post("/m/agent", body)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(reused.status_code, 403, reused.data)
        self.assertEqual(denied.status_code, 403, denied.data)
        self.assertEqual(fresh.data, first.data)
        self.assertEqual(ask.call_count, 1)

    def test_signed_tailnet_to_lan_retry_does_not_repeat_heal(self):
        body = {"text": "check and repair", "request_id": "same-key-two-roads"}
        with patch("covenant_model.ask", side_effect=[("HEAL", {"model": "fixture"}),
                                                      ("The fixture repair completed.", {"model": "fixture"})]) as ask, \
                patch("covenant_tetsu_heal.act", return_value=(True, "fixture repair", {"kind": "heal"})) as heal:
            first = self.signed_post("/m/agent", body, addr=self.addr)
            retry = self.signed_post("/m/agent", body)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(retry.data, first.data)
        self.assertEqual(heal.call_count, 1)
        self.assertEqual(ask.call_count, 2)

    def test_real_council_signature_is_required_for_cached_reply(self):
        body = {"text": "consider this", "request_id": "council-key-two-roads"}
        steps = [{"role": "reviser", "content": "Council reply.", "model": "fixture", "ms": 1}]
        with patch.object(self.council, "deliberate", return_value=(steps, "Council reply.")) as deliberate:
            first = self.signed_post("/pc/council", body, addr=self.addr)
            retry = self.signed_post("/pc/council", body)
            unsigned = self.post("/pc/council", body, "192.168.1.3")
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(retry.data, first.data)
        self.assertEqual(unsigned.status_code, 403, unsigned.data)
        self.assertEqual(deliberate.call_count, 1)

    def test_unverified_tailnet_pubkey_cannot_borrow_a_signed_reply(self):
        body = {"text": "hello", "request_id": "unverified-header-is-not-identity"}
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        bad_headers = self.cov.sign_operator_request(self.fixture_keys[1], self.plan.pubkey_pem(self.fixture_keys[0]), "POST", "/m/agent", raw)
        with patch("covenant_model.ask", side_effect=[("Verified-key reply.", {"model": "fixture"}),
                                                    ("Tailnet-only reply.", {"model": "fixture"})]) as ask:
            signed = self.signed_post("/m/agent", body, addr=self.addr)
            unverified = self.signed_post("/m/agent", body, addr="100.72.4.100", headers=bad_headers)
            verified_retry = self.signed_post("/m/agent", body)
        self.assertEqual(signed.status_code, 200, signed.data)
        self.assertEqual(unverified.status_code, 403, unverified.data)
        self.assertNotEqual(unverified.data, signed.data)
        self.assertEqual(verified_retry.data, signed.data)
        self.assertEqual(ask.call_count, 1)

    def test_verified_identity_is_independent_of_pem_transport_newlines(self):
        body = {"text": "hello", "request_id": "canonical-key-identity"}
        pem = self.plan.pubkey_pem(self.fixture_keys[0])
        windows_pem = pem.replace("\n", "\r\n")
        self.assertNotEqual(base64.b64encode(pem.encode()), base64.b64encode(windows_pem.encode()))
        with patch("covenant_model.ask", return_value=("Same verified public key.", {"model": "fixture"})) as ask:
            first = self.signed_post("/m/agent", body, pem=pem)
            retry = self.signed_post("/m/agent", body, pem=windows_pem)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(retry.status_code, 200, retry.data)
        self.assertEqual(retry.data, first.data)
        self.assertEqual(ask.call_count, 1)

    def test_reused_tailnet_signature_cannot_fall_back_to_a_second_identity(self):
        body = {"text": "hello", "request_id": "tailnet-nonce-replay"}
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        headers = self.cov.sign_operator_request(self.fixture_keys[0], self.plan.pubkey_pem(self.fixture_keys[0]), "POST", "/m/agent", raw)
        with patch("covenant_model.ask", return_value=("The work is complete.", {"model": "fixture"})) as ask:
            first = self.signed_post("/m/agent", body, addr=self.addr, headers=headers)
            reused = self.signed_post("/m/agent", body, addr=self.addr, headers=headers)
            fresh = self.signed_post("/m/agent", body, addr=self.addr)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(reused.status_code, 403, reused.data)
        self.assertEqual(fresh.data, first.data)
        self.assertEqual(ask.call_count, 1)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    failed = len(result.failures) + len(result.errors)
    print("CREPLAY: %d/%d passed" % (result.testsRun - failed, result.testsRun))
    raise SystemExit(0 if result.wasSuccessful() else 1)
