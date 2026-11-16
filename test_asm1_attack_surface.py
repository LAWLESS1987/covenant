"""ASM1 (A438) -- the attack-surface map is driven both ways.

tools/attack_surface_map.py is the defensive COUNT PASS: it discovers the Flask
route surface, classifies exposure, cross-references each route to the suites
and to the gating calls in its handler, and emits a ranked hunt queue. This pins
its pure functions on fixtures (each marked case fails if the logic regresses --
e.g. /health must be READ, which breaks the moment classification goes back to
raw substring matching and "heal" catches "health"), and smoke-tests the real
tree so the mapper cannot silently stop finding routes."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import attack_surface_map as asm  # noqa: E402

FIXTURE = '''
class Node:
    def _routes(self):
        @self.app.route("/health", methods=["GET"])
        def health():
            return "ok"

        @self.app.route("/m/heal", methods=["POST"])
        def heal():
            if not _request_signed_by_registered(req):
                return 403
            return do_heal()

        @self.app.route("/stakes", methods=["GET"])
        def stakes():
            return list_stakes()

        @self.app.route("/claim_rewards", methods=["POST"])
        def claim():
            return pay()
'''


class Discover(unittest.TestCase):
    def test_finds_every_route_with_methods_and_handler(self):
        rs = {r.path: r for r in asm.discover_routes(FIXTURE)}
        self.assertEqual(set(rs), {"/health", "/m/heal", "/stakes", "/claim_rewards"})
        self.assertEqual(rs["/health"].methods, ["GET"])
        self.assertEqual(rs["/m/heal"].methods, ["POST"])
        self.assertEqual(rs["/m/heal"].handler, "heal")


class Classify(unittest.TestCase):
    def test_health_is_READ_not_EXEC(self):
        # the substring bug: "heal" must NOT match "health". Fails if classify
        # goes back to raw-substring matching.
        self.assertEqual(asm.classify_exposure("/health", ["GET"]), ("READ", 1))

    def test_heal_is_EXEC(self):
        self.assertEqual(asm.classify_exposure("/m/heal", ["POST"])[0], "EXEC")

    def test_get_only_is_always_read(self):
        self.assertEqual(asm.classify_exposure("/trading/net_pnl", ["GET"]), ("READ", 1))
        self.assertEqual(asm.classify_exposure("/stakes", ["GET"]), ("READ", 1))

    def test_money_and_control_posts(self):
        self.assertEqual(asm.classify_exposure("/stake", ["POST"])[0], "MONEY")
        self.assertEqual(asm.classify_exposure("/unstake", ["POST"])[0], "MONEY")
        self.assertEqual(asm.classify_exposure("/succession/register", ["POST"])[0], "CONTROL")

    def test_unknown_post_floors_to_write(self):
        self.assertEqual(asm.classify_exposure("/whatever_new", ["POST"]), ("WRITE", 2))


class Gating(unittest.TestCase):
    def test_present_and_absent(self):
        rs = {r.path: r for r in asm.discover_routes(FIXTURE)}
        self.assertIn("_request_signed_by_registered", asm.gating_of(rs["/m/heal"].body))
        self.assertEqual(asm.gating_of(rs["/health"].body), [])


class Coverage(unittest.TestCase):
    def test_adversarial_only_for_security_family_tags(self):
        idx = asm.build_test_index([("test_x.py", 'client.post("/m/heal")')])
        route = asm.discover_routes(FIXTURE)[1]  # /m/heal
        # JUDGE is a security-relevant family -> adversarial
        cov = asm.coverage(route, idx, {"test_x.py": "JUDGE"})
        self.assertEqual(cov["tests"], ["test_x.py"])
        self.assertEqual(cov["adversarial"], ["test_x.py"])
        # DEPLOYMENT is not -> mentioned, but not adversarial
        cov2 = asm.coverage(route, idx, {"test_x.py": "DEPLOYMENT"})
        self.assertEqual(cov2["tests"], ["test_x.py"])
        self.assertEqual(cov2["adversarial"], [])


class Queue(unittest.TestCase):
    def _row(self, path, cls, score, adversarial, gating):
        return {"path": path, "methods": ["POST"], "handler": "h", "source": "s",
                "class": cls, "score": score, "tests": [], "adversarial": adversarial,
                "gating": gating}

    def test_queued_when_uncovered_and_dropped_when_both(self):
        uncovered = self._row("/a", "EXEC", 5, [], [])
        covered = self._row("/b", "EXEC", 5, ["t"], ["g"])
        read = self._row("/c", "READ", 1, [], [])
        q = {r["path"] for r in asm.hunt_queue([uncovered, covered, read])}
        self.assertIn("/a", q)            # uncovered EXEC is queued
        self.assertNotIn("/b", q)         # adversarial test AND gating -> off the queue
        self.assertNotIn("/c", q)         # READ is below the threshold

    def test_both_ways_flipping_coverage_moves_a_route(self):
        row = self._row("/x", "MONEY", 4, ["t"], ["g"])
        self.assertNotIn("/x", {r["path"] for r in asm.hunt_queue([row])})
        row["adversarial"] = []           # remove the adversarial test
        self.assertIn("/x", {r["path"] for r in asm.hunt_queue([row])})

    def test_ranked_by_exposure(self):
        rows = [self._row("/w", "WRITE", 2, [], []),
                self._row("/e", "EXEC", 5, [], []),
                self._row("/m", "MONEY", 4, [], [])]
        order = [r["path"] for r in asm.hunt_queue(rows)]
        self.assertEqual(order, ["/e", "/m", "/w"])


class RealTreeSmoke(unittest.TestCase):
    def test_runs_and_finds_the_surface(self):
        rows, queue, meta = asm.build_report()
        self.assertGreaterEqual(meta["routes"], 20, "mapper stopped finding routes")
        paths = {r["path"] for r in rows}
        self.assertIn("/health", paths)
        self.assertIn("/m/agent", paths)
        # /health must be READ on the real tree too (not EXEC via the heal bug)
        health = next(r for r in rows if r["path"] == "/health")
        self.assertEqual(health["class"], "READ")
        # the report must name its blind spots -- a map that hides them lies
        text = asm.render(rows, queue, meta)
        self.assertIn("BLIND SPOTS", text)

    def test_mapper_does_not_credit_its_own_test(self):
        # the map's own test names routes as DATA (classification inputs); counting
        # it as coverage credited routes nobody attacked and HID real uncovered ones.
        # It must never appear as a test for any route. Fails if the exclusion drops.
        rows, _q, _m = asm.build_report()
        for r in rows:
            self.assertNotIn("test_asm1_attack_surface.py", r["tests"], r["path"])
            self.assertNotIn("test_asm1_attack_surface.py", r["adversarial"], r["path"])


if __name__ == "__main__":
    _res = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    _bad = len(_res.failures) + len(_res.errors)
    print("ASM1: %d/%d passed" % (_res.testsRun - _bad, _res.testsRun))
    sys.exit(1 if _bad else 0)
