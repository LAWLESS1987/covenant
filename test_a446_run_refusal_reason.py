"""A446: the reason handed to the model when a HANDS RUN is refused states the rule the door enforces.

Found by Jang-woo running signed-RUN packet v2.3 against 9d85f6c (HF 183807 #44, 2026-11-18): case 4 (unsigned, from
loopback) was refused as it should be, but the model was told RUN needs "a request from loopback or signed by a
registered key". Since A423 loopback alone may not run, and since A447 an ally key may not either: the door sets
may_run from covenant_unified_v8._request_signed_by_registered, which is true only for "signed:operator".

The earlier records of this shape (A348h, A263-DOCSTRING) tombstoned one wording each, and nothing tied a stated
reason to the gate that decides. This test does: every caller the text names as "not enough" is driven through the
door's own HANDS branch (extracted from the AST, as test_a430/test_a447 do) and must be refused with exactly that
text, and the caller the text names as enough (a request signed by one of his keys) must run. If the gate changes,
a case here goes red until the words change with it; if the words drift, the text checks go red.

Offline, real signatures, fixture registries and the nonce store (A444) in a temp dir (never ops/).
"""
import hashlib
import importlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask, request
import covenant_daily_plan as DP
import covenant_mycelium as MY
import covenant_tetsu_hands as H
import covenant_unified_v8 as cov
from test_a430_run_sha256 import hands_branch

FAR = "203.0.113.9"            # TEST-NET-3: neither loopback nor tailnet
LOOPBACK = "127.0.0.1"
TAILNET = "100.127.255.254"    # inside 100.64.0.0/10 (CGNAT), not a fleet node


class RunRefusalStatesTheRule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.branch = hands_branch()
        cls.op_key, cls.op_pem = cov.sig_keygen()
        cls.ally_key, cls.ally_pem = cov.sig_keygen()
        cls.app = Flask("a446")

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="a446_"))
        self.shop = self.root / "workshop"
        self.shop.mkdir()
        self.source = b"print('approved bytes')\n"
        (self.shop / "probe.py").write_bytes(self.source)
        self.digest = hashlib.sha256(self.source).hexdigest()
        signers = self.root / "signers.json"
        signers.write_text(json.dumps({"fixture-operator": self.op_pem}), encoding="utf-8")
        peers = self.root / "peers.json"
        for target, attr, value in (
                (H, "WORKSHOP", str(self.shop)), (H, "LEDGER", str(self.root / "hands.jsonl")),
                (H, "_gate", lambda text: ("clean", "fixture")),
                (DP, "SIGNERS", str(signers)), (DP, "_seen_nonces", set()), (DP, "NONCE_STORE", str(self.root / "nonces")),
                (MY, "PEERS", str(peers)), (MY, "LEDGER", str(self.root / "mycelium.jsonl")), (MY, "_seen", set())):
            cm = patch.object(target, attr, value)
            cm.start()
            self.addCleanup(cm.stop)
        MY.register_ally("fixture-ally", self.ally_pem, granted_by="a446 fixture", path=str(peers))

    def run_door(self, key, pem, addr):
        body = json.dumps({"run_sha256": self.digest}).encode("utf-8")
        headers = cov.sign_operator_request(key, pem, "POST", "/m/agent", body) if key is not None else {}
        scope = {"request": request, "answer": "HANDS RUN probe.py", "importlib": importlib,
                 "_request_signed_by_registered": cov._request_signed_by_registered,
                 "forum": [], "msgs": [], "_ask_fitted": lambda: ("done", {})}
        with self.app.test_request_context("/m/agent", method="POST", data=body, headers=headers,
                                           content_type="application/json", environ_base={"REMOTE_ADDR": addr}):
            exec(self.branch, scope)
        return scope["_data"], scope["_rec"]

    def test_every_caller_named_not_enough_is_refused_with_the_rule(self):
        # The text names three callers as "not enough": loopback alone, an ally key, a tailnet address. Plus a stranger.
        cases = {"loopback alone": (None, None, LOOPBACK), "an ally key": (self.ally_key, self.ally_pem, FAR),
                 "a tailnet address": (None, None, TAILNET), "unsigned stranger": (None, None, FAR)}
        for name, (key, pem, addr) in cases.items():
            with self.subTest(caller=name):
                data, row = self.run_door(key, pem, addr)
                self.assertTrue(row.get("refused"), (name, row))
                self.assertNotIn("approved bytes", data)
                self.assertEqual(data, H.RUN_REFUSED_DATA, name)

    def test_the_caller_named_enough_runs(self):
        # A request signed by one of his own keys, from an address that is neither loopback nor tailnet.
        data, row = self.run_door(self.op_key, self.op_pem, FAR)
        self.assertTrue(row.get("ok"), data)
        self.assertIn("approved bytes", data)
        self.assertNotEqual(data, H.RUN_REFUSED_DATA)

    def test_the_words_state_the_gate(self):
        t = H.RUN_REFUSED_DATA
        self.assertTrue(t.startswith("DATA: running a script needs the operator"))   # test_th1 and test_a429 read this
        self.assertIn("signed by one of his own registered keys", t)
        for named in ("Loopback alone", "an ally key", "a tailnet address"):
            self.assertIn(named, t)
        self.assertIn("is not enough", t)
        self.assertIsNone(re.search(r"(?i)from loopback or|loopback, or a request", t), t)
        self.assertIn("Nothing was run", t)

    def test_no_older_rule_left_in_the_module(self):
        src = Path(H.__file__).read_text(encoding="utf-8")
        self.assertNotIn("a request from loopback or signed by a registered", src)
        self.assertNotIn("(loopback, or a request signed by a registered", src)
        self.assertEqual(src.count("return True, RUN_REFUSED_DATA, rec"), 1)

    def test_the_door_still_decides_with_the_helper(self):
        # The words describe _request_signed_by_registered; test_a447 holds that helper to "signed:operator".
        src = Path(cov.__file__).read_text(encoding="utf-8")
        self.assertEqual(src.count("_may_run = _request_signed_by_registered(request)"), 1)


if __name__ == "__main__":
    # The runner scores a suite by its tally line; unittest.main prints none, so it would read as NO RESULT.
    _res = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    _bad = len(_res.failures) + len(_res.errors)
    print("A446: %d/%d passed" % (_res.testsRun - _bad, _res.testsRun))
    sys.exit(1 if _bad else 0)
