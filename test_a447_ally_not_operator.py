"""A447: a registered ALLY key is not an operator key.

Collective #21's packet (v2.3, case C1) showed an ally key at its default scope making a signed HANDS RUN at
9d85f6c: _request_signed_by_registered returned covenant_mycelium.admit()'s ok, and admit() also admits
"signed:ally" on the ally doors, one of which (/m/agent) is the door HANDS RUN and HEAL go through. Every caller of
that helper describes operator-only access (A423's RUN, A370's isolation lift, the operator workshop read). The
quorum (11 of 11, ops/ALLY_RUN_DECISION_2026-11-17.md) advised B; the operator chose B2 on 2026-11-17: the helper
itself requires how == "signed:operator", exactly. Ally ADMISSION in admit() is unchanged.

Offline, real signatures, fixture signer and ally registries in a temp dir (never ops/). The HANDS branch is the
door's own code, extracted from the AST as test_a430 does. Each refusal has an operator control beside it, so a
version that refuses everyone fails here too.
"""
import hashlib
import importlib
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

from flask import Flask, request
import covenant_daily_plan as DP
import covenant_mycelium as MY
import covenant_tetsu_hands as H
import covenant_unified_v8 as cov
from test_a430_run_sha256 import hands_branch

FAR = "203.0.113.9"          # TEST-NET-3: neither loopback nor tailnet


class AllyIsNotOperator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.branch = hands_branch()
        cls.op_key, cls.op_pem = cov.sig_keygen()
        cls.ally_key, cls.ally_pem = cov.sig_keygen()
        cls.app = Flask("a447")

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="a447_"))
        self.shop = self.root / "workshop"
        self.shop.mkdir()
        self.source = b"print('approved bytes')\n"
        (self.shop / "probe.py").write_bytes(self.source)
        self.digest = hashlib.sha256(self.source).hexdigest()
        signers = self.root / "signers.json"
        signers.write_text(json.dumps({"fixture-operator": self.op_pem}), encoding="utf-8")
        self.peers = self.root / "peers.json"
        self.mledger = self.root / "mycelium.jsonl"
        for target, attr, value in (
                (H, "WORKSHOP", str(self.shop)), (H, "LEDGER", str(self.root / "hands.jsonl")),
                (H, "_gate", lambda text: ("clean", "fixture")),
                (DP, "SIGNERS", str(signers)), (DP, "_seen_nonces", set()),
                (MY, "PEERS", str(self.peers)), (MY, "LEDGER", str(self.mledger)), (MY, "_seen", set())):
            cm = patch.object(target, attr, value)
            cm.start()
            self.addCleanup(cm.stop)
        MY.register_ally("fixture-ally", self.ally_pem, granted_by="a447 fixture", path=str(self.peers))

    def ctx(self, path, key, pem, payload, addr=FAR):
        body = json.dumps(payload).encode("utf-8")
        headers = cov.sign_operator_request(key, pem, "POST", path, body) if key is not None else {}
        return self.app.test_request_context(path, method="POST", data=body, headers=headers,
                                             content_type="application/json",
                                             environ_base={"REMOTE_ADDR": addr})

    def run_door(self, key, pem):
        scope = {"request": request, "answer": "HANDS RUN probe.py", "importlib": importlib,
                 "_request_signed_by_registered": cov._request_signed_by_registered,
                 "forum": [], "msgs": [], "_ask_fitted": lambda: ("done", {})}
        with self.ctx("/m/agent", key, pem, {"run_sha256": self.digest}):
            exec(self.branch, scope)
        return scope["_data"], scope["_rec"]

    # --- RUN (line ~9503) ------------------------------------------------------------------------------------------
    def test_operator_signed_run_still_runs(self):
        data, row = self.run_door(self.op_key, self.op_pem)
        self.assertTrue(row.get("ok"), data)
        self.assertIn("approved bytes", data)

    def test_ally_signed_run_is_refused_c1(self):
        data, row = self.run_door(self.ally_key, self.ally_pem)
        self.assertFalse(row.get("ok"), row)
        self.assertNotIn("approved bytes", data)
        self.assertIn("operator", data)

    def test_ally_is_still_admitted_on_its_door(self):
        # B2 narrows the HELPER, not admission: admit() still says ok, "signed:ally" on /m/agent.
        with self.ctx("/m/agent", self.ally_key, self.ally_pem, {"text": "hello"}):
            ok, _addr, who, how = MY.admit(request, request.get_data(), lambda _a: False)
        self.assertEqual((ok, who, how), (True, "fixture-ally", "signed:ally"))

    # --- the helper itself, on every door that uses it -------------------------------------------------------------
    def test_helper_operator_true_ally_false_unsigned_false(self):
        for path in ("/m/agent", "/m/workshop/read"):
            with self.subTest(path=path):
                with self.ctx(path, self.op_key, self.op_pem, {"x": 1}):
                    self.assertTrue(cov._request_signed_by_registered(request))
                with self.ctx(path, self.ally_key, self.ally_pem, {"x": 1}):
                    self.assertFalse(cov._request_signed_by_registered(request))
                with self.ctx(path, None, None, {"x": 1}):
                    self.assertFalse(cov._request_signed_by_registered(request))

    def test_ally_with_custom_scope_on_read_door_is_refused(self):
        MY.register_ally("fixture-ally", self.ally_pem, granted_by="a447 fixture",
                         scope=["/m/agent", "/m/workshop/read"], path=str(self.peers))
        # Two separately signed requests: one admit() spends its nonce, so a shared request would make the second
        # call refuse a REPLAY and pass this test for the wrong reason (it did, in the first draft of this test).
        with self.ctx("/m/workshop/read", self.ally_key, self.ally_pem, {"name": "probe.py"}):
            ok, _a, _w, how = MY.admit(request, request.get_data(), lambda _a: False)
            self.assertEqual((ok, how), (True, "signed:ally"))           # admitted by its scope ...
        with self.ctx("/m/workshop/read", self.ally_key, self.ally_pem, {"name": "probe.py"}):
            self.assertFalse(cov._request_signed_by_registered(request))  # ... but not an operator

    def test_key_on_both_lists_counts_as_operator(self):
        MY.register_ally("fixture-both", self.op_pem, granted_by="a447 fixture", path=str(self.peers))
        with self.ctx("/m/agent", self.op_key, self.op_pem, {"x": 1}):
            self.assertTrue(cov._request_signed_by_registered(request))

    # --- the isolation lift (A370, line ~9525) -----------------------------------------------------------------------
    def test_heal_lift_ally_refused_operator_and_loopback_allowed(self):
        with self.ctx("/m/agent", self.ally_key, self.ally_pem, {"x": 1}):
            self.assertFalse(cov.heal_lift_authorized(FAR, request))
        with self.ctx("/m/agent", self.op_key, self.op_pem, {"x": 1}):
            self.assertTrue(cov.heal_lift_authorized(FAR, request))
        with self.ctx("/m/agent", None, None, {"x": 1}, addr="127.0.0.1"):
            self.assertTrue(cov.heal_lift_authorized("127.0.0.1", request))

    # --- source guard: the exact label, in the one place -------------------------------------------------------------
    def test_source_checks_the_exact_operator_label_once(self):
        src = Path(cov.__file__).read_text(encoding="utf-8")
        start = src.index("def _request_signed_by_registered(")
        body = src[start:src.index("\ndef ", start + 10)]
        self.assertIn('_how == "signed:operator"', body)
        self.assertNotIn("startswith", body)
        self.assertEqual(src.count('_how == "signed:operator"'), 1)


if __name__ == "__main__":
    _res = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    _bad = len(_res.failures) + len(_res.errors)
    print("A447: %d/%d passed" % (_res.testsRun - _bad, _res.testsRun))
    sys.exit(1 if _bad else 0)
