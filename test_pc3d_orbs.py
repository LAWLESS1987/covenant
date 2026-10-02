"""Offline orb inventory and real inline JavaScript regressions; no live node calls."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.request

import covenant_pc3d as pc3d


def healthy():
    return {"self": {"node_id": "A", "chain_height": 7}, "peers": [{"node_id": "100.64.0.2:5001"}],
            "mesh": [{"node_id": name, "port": port, "version": "v8.41", "chain_height": 7,
                      "peers": 2, "degraded": False, "warnings": [], "me": name == "A"}
                     for name, port in (("A", 5000), ("B", 5020), ("C", 5060))],
            "detail": {"highway": {key: "absent" for key in pc3d.HIGHWAY_ORB_DETECTORS},
                       "phone": {"last_checkin_hours": 0.1}, "forum": [{"sent": True}],
                       "money": {"comfortable": True}, "queue": 2}, "voice": {"pitch": 0.8, "rate": 0.95}}


class OrbInventoryTests(unittest.TestCase):
    def test_history_skips_scalar_and_other_callers_without_losing_completed_turns(self):
        from flask import Flask, request
        app = Flask(__name__)
        api = SimpleNamespace(app=app, node=SimpleNamespace(node_id="fixture"))
        def caller():
            return True, request.remote_addr
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ask.jsonl"
            rows = [None, [], 1, "scalar", {"kind": "agent", "from": "127.0.0.1", "text": "remember", "answer": "I remember"},
                    {"kind": "council", "from": "other", "text": "private to other", "answer": "other reply"},
                    {"kind": "agent", "from": "127.0.0.1", "text": "held turn", "answer": "", "withheld": True, "message": "fixture verdict"}]
            path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            with patch.dict(os.environ, {"COVENANT_ASK_LOG": str(path)}):
                pc3d.register(api, caller, lambda addr: ("refused", 403), SimpleNamespace())
                result = app.test_client().get("/pc/3d/history").get_json()
            self.assertEqual([row["q"] for row in result["turns"]], ["remember", "held turn"])
            self.assertEqual(result["turns"][0]["a"], "I remember")
            self.assertTrue(result["turns"][1]["withheld"])
            self.assertEqual(result["turns"][1]["why"], "fixture verdict")

    def row(self, snapshot, ident):
        return next(row for row in pc3d.orb_inventory(snapshot) if row["id"] == ident)

    def test_missing_and_incomplete_highway_never_green(self):
        for value in (None, {}, {"node_down": "absent"}, {"node_down": "surprise"}):
            with self.subTest(value=value):
                row = self.row({"detail": {"highway": value}}, "highway")
                self.assertEqual(row["status"], "unknown")
                self.assertEqual(len(row["detail"]), 7)

    def test_highway_requires_all_measurements_and_preserves_attention(self):
        snapshot = healthy()
        self.assertEqual(self.row(snapshot, "highway")["status"], "ok")
        snapshot["detail"]["highway"]["source_drift"] = "PRESENT"
        snapshot["detail"]["highway"]["node_down"] = "unknown"
        row = self.row(snapshot, "highway")
        self.assertEqual(row["status"], "attention")
        self.assertEqual(row["detail"]["source_drift"], "present")

    def test_every_orb_has_unique_identity_and_actual_detail(self):
        snapshot = healthy()
        rows = pc3d.orb_inventory(snapshot)
        self.assertEqual(len(rows), 9)
        self.assertEqual(len(set(row["id"] for row in rows)), 9)
        snapshot["mesh"] = [{"node_id": "?", "port": p, "down": True, "why": "ConnectionRefusedError"}
                            for p in (5000, 5020, 5060)]
        nodes = [row for row in pc3d.orb_inventory(snapshot) if row["id"].startswith("node:")]
        self.assertEqual(len(set(row["name"] for row in nodes)), 3)
        self.assertTrue(all(row["status"] == "attention" and "ConnectionRefusedError" in row["summary"] for row in nodes))

    def test_degraded_node_warnings_are_carried(self):
        snapshot = healthy()
        snapshot["mesh"][1].update(degraded=True, warnings=["local guard is unavailable"])
        row = self.row(snapshot, "node:5020:1")
        self.assertEqual(row["status"], "unknown")
        self.assertIn("local guard is unavailable", row["detail"]["warnings"])

    def test_incomplete_or_malformed_health_cannot_claim_green(self):
        for update in ({"node_id": "?"}, {"chain_height": True}, {"peers": -1}, {"version": None}, {"degraded": None}):
            with self.subTest(update=update):
                snapshot = healthy()
                snapshot["mesh"][0].update(update)
                self.assertEqual(self.row(snapshot, "node:5000:0")["status"], "unknown")

    def test_phone_age_and_declared_records_have_strict_types(self):
        for age in (-1, float("nan"), float("inf"), True, "0.1", 10**1000):
            with self.subTest(age=age):
                snapshot = healthy()
                snapshot["detail"]["phone"]["last_checkin_hours"] = age
                self.assertEqual(self.row(snapshot, "phone")["status"], "unknown")
        snapshot = healthy()
        snapshot["detail"]["phone"]["last_checkin_hours"] = 25
        snapshot["detail"]["forum"] = [{"sent": "false"}]
        snapshot["detail"]["money"]["comfortable"] = "false"
        self.assertEqual(self.row(snapshot, "phone")["status"], "attention")
        self.assertEqual(self.row(snapshot, "forum")["status"], "unknown")
        self.assertEqual(self.row(snapshot, "money")["status"], "unknown")

    def test_peer_address_is_not_device_or_health_proof(self):
        row = self.row(healthy(), "peer:0:100.64.0.2:5001")
        self.assertEqual(row["status"], "unknown")
        self.assertIn("identity", row["detail"]["note"])

    def test_inline_javascript_runs_without_three_and_cancels_stale_turns(self):
        node = os.environ.get("COVENANT_TEST_NODE") or shutil.which("node")
        if not node:
            self.fail("Node.js is required for the browser regressions; set COVENANT_TEST_NODE or PATH")
        with tempfile.TemporaryDirectory(prefix="pc3d-js-") as temporary:
            temp = Path(temporary)
            scripts = re.findall(r"<script([^>]*)>(.*?)</script>", pc3d.PAGE, re.S)
            for index, (attributes, source) in enumerate(scripts):
                if "importmap" in attributes:
                    continue
                path = temp / ("page-%s.%s" % (index, "mjs" if "module" in attributes else "cjs"))
                path.write_text(source, encoding="utf-8")
                subprocess.run([node, "--check", str(path)], check=True, capture_output=True, text=True)
            fixture = healthy()
            fixture["orbs"] = pc3d.orb_inventory(fixture)
            (temp / "fixture.json").write_text(json.dumps(fixture), encoding="utf-8")
            source = next(source for attributes, source in scripts if not attributes.strip())
            (temp / "page.cjs").write_text(source, encoding="utf-8")
            runner = Path(__file__).with_name("test_pc3d_ui.cjs")
            result = subprocess.run([node, str(runner), str(temp)], check=True, capture_output=True, text=True)
            self.assertIn("PC3d UI regression checks passed", result.stdout)

    def test_gated_state_returns_all_node_warnings_and_shared_inventory(self):
        from flask import Flask, request
        class Response:
            def __init__(self, value): self.value = value
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self): return json.dumps(self.value).encode()
        fixture = healthy()
        nodes = {str(row["port"]): dict(row) for row in fixture["mesh"]}
        nodes["5020"].update(degraded=True, warnings=["the real reason on B"])
        fake_modules = {
            "covenant_persona": SimpleNamespace(load=lambda: {}, clamp_voice=lambda _: fixture["voice"], brief=lambda: "fixture"),
            "covenant_immunity": SimpleNamespace(status=lambda: {}),
            "covenant_highway": SimpleNamespace(last_sense=lambda: fixture["detail"]["highway"]),
            "covenant_reconnect": SimpleNamespace(signs_of_him=lambda: {"phone": {"hours": 0.1}, "chat": {"hours": 2}}),
            "covenant_tetsu_money": SimpleNamespace(status=lambda: {"comfortable": True}, holdings=lambda: {}),
            "covenant_free_will": SimpleNamespace(sends=lambda: []),
            "covenant_teacher_queue": SimpleNamespace(pending=lambda: ([], None)),
        }
        app = Flask("orb-fixture")
        api = SimpleNamespace(app=app, node=SimpleNamespace(node_id="A", chain=[1], peers=[]))
        caller = lambda: (request.remote_addr == "127.0.0.1", request.remote_addr)
        cov = SimpleNamespace(COVENANT_VERSION="v8.41", CORE_SOURCE_SHA256="fixture")
        pc3d.register(api, caller, lambda _: ({"status": "error"}, 403), cov)
        def get_health(url, timeout):
            self.assertRegex(url, r"^http://127\.0\.0\.1:(5000|5020|5060)/health$")
            return Response(nodes[url.split(":")[-1].split("/")[0]])
        with patch.dict(sys.modules, fake_modules), patch.object(urllib.request, "urlopen", side_effect=get_health) as network:
            client = app.test_client()
            denied = client.get("/pc/3d/state", environ_base={"REMOTE_ADDR": "192.0.2.1"})
            self.assertEqual(denied.status_code, 403)
            network.assert_not_called()
            state = client.get("/pc/3d/state", environ_base={"REMOTE_ADDR": "127.0.0.1"}).get_json()
            self.assertEqual(network.call_count, 3)
            self.assertEqual(state["orbs"], pc3d.orb_inventory(state))
            self.assertEqual(self.row(state, "node:5020:1")["detail"]["warnings"], ["the real reason on B"])
            self.assertEqual(self.row(state, "node:5020:1")["status"], "unknown")
            self.assertEqual(self.row(state, "highway")["status"], "ok")


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__)))
    failures = len(result.failures) + len(result.errors)
    print("ORBS: %d/%d passed" % (result.testsRun - failures, result.testsRun))
    raise SystemExit(0 if result.wasSuccessful() else 1)
