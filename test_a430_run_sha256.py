"""A430: an operator request authorizes exactly the captured script bytes.

Offline: execute the actual HANDS branch extracted from the door's AST in a
Flask request context, with real signatures and a fixture signer registry.
The model and judge are stubs; the hands, screen and child process are real.
Unsigned refusal and owner-started practice are preservation controls.
"""
import ast
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask, request
import covenant_daily_plan as DP
import covenant_mycelium as MY
import covenant_tetsu_hands as H
import covenant_tetsu_practice as P
import covenant_unified_v8 as cov


def hands_branch():
    tree = ast.parse(Path(cov.__file__).read_text(encoding="utf-8"))
    matches = [n for n in ast.walk(tree) if isinstance(n, ast.If)
               and ast.unparse(n.test) == "first.upper().startswith('HANDS')"]
    if len(matches) != 1:
        raise AssertionError("expected exactly one HANDS branch")
    return compile(ast.Module(body=matches[0].body, type_ignores=[]), cov.__file__, "exec")


class RunBinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.branch = hands_branch()
        cls.key, cls.pem = cov.sig_keygen()
        cls.app = Flask("a430")

    def setUp(self):
        # Retained scratch, never the real workshop or signer registry.
        self.root = Path(tempfile.mkdtemp(prefix="a430_"))
        self.shop = self.root / "workshop"
        self.shop.mkdir()
        self.ledger = self.root / "hands.jsonl"
        self.source = b"print('approved bytes')\r\n"
        self.script = self.shop / "probe.py"
        self.script.write_bytes(self.source)
        self.digest = hashlib.sha256(self.source).hexdigest()
        signers = self.root / "signers.json"
        signers.write_text(json.dumps({"fixture": self.pem}), encoding="utf-8")
        for target, attr, value in (
                (H, "WORKSHOP", str(self.shop)), (H, "LEDGER", str(self.ledger)),
                (H, "_gate", lambda text: ("clean", "fixture")),
                (DP, "SIGNERS", str(signers)), (DP, "_seen_nonces", set()),
                (MY, "PEERS", str(self.root / "no_allies.json")),
                (MY, "LEDGER", str(self.root / "mycelium.jsonl"))):
            cm = patch.object(target, attr, value)
            cm.start()
            self.addCleanup(cm.stop)

    def door(self, payload, signed=True, sent=None):
        body = json.dumps(payload).encode("utf-8")
        headers = cov.sign_operator_request(self.key, self.pem, "POST", "/m/agent", body) if signed else {}
        scope = {"request": request, "answer": "HANDS RUN probe.py", "importlib": importlib,
                 "_request_signed_by_registered": cov._request_signed_by_registered,
                 "forum": [], "msgs": [], "_ask_fitted": lambda: ("done", {})}
        with self.app.test_request_context("/m/agent", method="POST", data=body if sent is None else sent,
                                           headers=headers, content_type="application/json"):
            exec(self.branch, scope)
        return scope["_data"], scope["_rec"]

    def assert_refused(self, result, why="run_sha256"):
        data, row = result
        self.assertFalse(row.get("ok"), row)
        self.assertNotIn("timed_out", {k: v for k, v in row.items() if v is not None}, row)
        self.assertIn(why, data)

    def test_right_hash_runs_and_records_exact_bytes(self):
        data, row = self.door({"run_sha256": self.digest})
        self.assertTrue(row.get("ok"), data)
        self.assertIn("approved bytes", data)
        self.assertEqual(row.get("run_sha256"), self.digest)

    def test_wrong_hash_is_refused(self):
        self.assert_refused(self.door({"run_sha256": "0" * 64}))

    def test_signed_missing_hash_names_the_field(self):
        self.assert_refused(self.door({"text": "please run the file"}))

    def test_script_changed_after_signing_is_refused(self):
        self.script.write_bytes(b"print('substituted')\n")
        self.assert_refused(self.door({"run_sha256": self.digest}))

    def test_unsigned_request_still_cannot_run(self):
        self.assert_refused(self.door({"run_sha256": self.digest}, signed=False), "operator")

    def test_hash_changed_in_signed_body_is_refused(self):
        sent = json.dumps({"run_sha256": self.digest}).encode()
        self.assert_refused(self.door({"run_sha256": "0" * 64}, sent=sent), "operator")

    def test_unverified_body_is_not_read_for_run_authority(self):
        with patch.object(cov, "_request_signed_by_registered", return_value=False), \
                patch("flask.wrappers.Request.get_json", side_effect=AssertionError("unverified body read")):
            self.assert_refused(self.door({"run_sha256": self.digest}), "operator")

    def test_malformed_hash_is_refused(self):
        for value in (None, "", "A" * 64, "f" * 63, "g" * 64, 42, [], {}, self.digest + "\n", self.digest.upper(),
                      " " + self.digest):
            with self.subTest(value=value):
                self.assert_refused(self.door({"run_sha256": value}))

    def test_direct_run_enforces_explicit_hash(self):
        for value in (None, "0" * 64):
            with self.subTest(value=value):
                r = H.run("probe.py", run_sha256=value)
                self.assertFalse(r["ok"], r)
                self.assertNotIn("timed_out", r)
                self.assertIn("run_sha256", r["why"])
        r = H.run("probe.py", run_sha256=self.digest)
        self.assertTrue(r["ok"], r)

    def test_no_hash_then_reopen_race(self):
        real_run = H.subprocess.run

        def swap_then_launch(*args, **kwargs):
            self.script.write_bytes(b"print('substituted at launch')\n")
            return real_run(*args, **kwargs)

        with patch.object(H.subprocess, "run", side_effect=swap_then_launch):
            data, row = self.door({"run_sha256": self.digest})
        self.assertTrue(row.get("ok"), data)
        self.assertIn("approved bytes", data)
        self.assertNotIn("substituted at launch", data)

    def test_writable_runner_cannot_replace_approved_script(self):
        real_run = H.subprocess.run

        def swap_runner(*args, **kwargs):
            (self.shop / ".runner.py").write_text("print('substituted runner')\n", encoding="utf-8")
            return real_run(*args, **kwargs)

        with patch.object(H.subprocess, "run", side_effect=swap_runner):
            data, row = self.door({"run_sha256": self.digest})
        self.assertTrue(row.get("ok"), data)
        self.assertIn("approved bytes", data)
        self.assertNotIn("substituted runner", data)

    def test_binary_hash_includes_line_endings_and_encoding(self):
        # ascii() keeps the child's output encoding out of it: under python -I the child ignores PYTHONIOENCODING, so a
        # non-ASCII print comes back in the platform's console encoding (noticed here, left as it was).
        source = b"# coding: latin-1\r\nprint(ascii('caf\xe9'))\r\n"
        self.script.write_bytes(source)
        digest = hashlib.sha256(source).hexdigest()
        r = H.run("probe.py", run_sha256=digest)
        self.assertTrue(r["ok"], r)
        self.assertIn("'caf\\xe9'", r["out"])      # the cookie was honoured on the very bytes that were hashed
        self.assertFalse(H.run("probe.py", run_sha256=hashlib.sha256(source.replace(b"\r\n", b"\n")).hexdigest())["ok"])

    def test_oversize_file_cannot_run_a_prefix_hash(self):
        source = b"#" + b"x" * H.MAX_FILE + b"\nprint('too large')\n"
        self.script.write_bytes(source)
        for digest in (hashlib.sha256(source).hexdigest(), hashlib.sha256(source[:H.MAX_FILE]).hexdigest(),
                       hashlib.sha256(source[:H.MAX_FILE + 1]).hexdigest(), H.UNBOUND):
            r = H.run("probe.py", run_sha256=digest)
            self.assertFalse(r["ok"], r)
            self.assertNotIn("timed_out", r)
            self.assertIn("at most", r["why"])

    def test_matching_hash_does_not_bypass_screen(self):
        source = b"from uuid import os\n"
        self.script.write_bytes(source)
        r = H.run("probe.py", run_sha256=hashlib.sha256(source).hexdigest())
        self.assertFalse(r["ok"], r)
        self.assertIn("screen refused", r["why"])

    def test_binding_survives_a_four_argument_wrapper_of_run(self):
        # Node D's launcher wraps hands.run as run(name, args=None, workshop=None, timeout_s=None) and calls the
        # original with those four only. The binding must still reach the real run() through that wrapper.
        real = H.run
        calls = []

        def older_wrapper(name, args=None, workshop=None, timeout_s=None):
            calls.append(name)
            return real(name, args, workshop, timeout_s)

        with patch.object(H, "run", older_wrapper):
            self.assert_refused(self.door({"run_sha256": "0" * 64}))
            self.assert_refused(self.door({"text": "no hash"}))
            data, row = self.door({"run_sha256": self.digest})
        self.assertEqual(len(calls), 3)
        self.assertTrue(row.get("ok"), data)
        self.assertEqual(row.get("run_sha256"), self.digest)
        self.assertNotIn("binding_lost", row)

    def test_a_wrapper_that_loses_the_binding_is_recorded(self):
        # A wrapper that runs the original on another thread drops the context the binding rides in. That cannot be
        # prevented from here; it must not be silent: the row says binding_lost.
        import threading
        real = H.run

        def thread_wrapper(name, args=None, workshop=None, timeout_s=None):
            box = {}
            t = threading.Thread(target=lambda: box.update(r=real(name, args, workshop, timeout_s)))
            t.start()
            t.join()
            return box["r"]

        with patch.object(H, "run", thread_wrapper):
            data, row = self.door({"run_sha256": self.digest})
        self.assertIs(row.get("binding_lost"), True, row)

    def test_the_content_seat_and_the_run_use_the_same_bytes(self):
        # A429 shows the script to the content seat; A430 runs it. The file is replaced twice: while the quorum is being
        # asked (after act() read it, before the seat reads), and right after the seat has read it. A seat that opened
        # the file itself would be shown the first replacement; a run that opened it again would run the second
        # (unbound: whatever is there; bound: refused for the wrong hash). Both must have the bytes act() read once.
        import importlib.util
        real_content = H._content
        shown = []

        def quorum_while_file_changes(text):
            self.script.write_bytes(b"print('replaced while the quorum was asked')\n")
            return "clean", "fixture"

        def seat_reads_then_file_changes(d, w=None):
            r = real_content(d, w)
            if d["kind"] == "run":
                shown.append(r[0])
                self.script.write_bytes(b"print('replaced after the judge read it')\n")
            return r

        for label, call in (("unbound", lambda: H.act("HANDS RUN probe.py", may_run=True, ledger=str(self.ledger))),
                            ("door", lambda: self.door({"run_sha256": self.digest}))):
            with self.subTest(label):
                self.script.write_bytes(self.source)
                shown.clear()
                with patch.object(H, "JUDGE_SEES_CONTENT", True), patch.object(H, "_content", seat_reads_then_file_changes), \
                        patch.object(H, "_gate", quorum_while_file_changes):
                    out = call()
                data, row = (out[1], out[2]) if label == "unbound" else out
                self.assertEqual(shown, [importlib.util.decode_source(self.source)])
                self.assertTrue(row.get("ok"), data)
                self.assertIn("approved bytes", data)
                self.assertNotIn("replaced", data)
                self.assertEqual(row.get("script_sha256"), self.digest)

    def test_owner_started_practice_still_runs_without_hash(self):
        task = {"id": "binding_practice", "forbid": [], "checks": [("value()", 7)]}
        result, stop = P.attempt(task, "def value():\n    return 7\n", gate=lambda text: ("held", "fixture"),
                                 workshop=str(self.shop), hands_ledger=str(self.ledger))
        self.assertIsNone(stop)
        self.assertEqual(result["passed"], result["total"], result)
        self.assertGreater(result["total"], 0)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    # one test with several failing subTests is one failed test, so the count stays in tests
    bad = len({getattr(t, "test_case", t).id() for t, _ in result.failures + result.errors})
    print("A430: %d/%d passed" % (result.testsRun - bad, result.testsRun))
    sys.exit(1 if bad else 0)
