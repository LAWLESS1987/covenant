"""A500 -- a Debian tower runs ONE node under its OWN identity, listening on ONE address (2026-11-27).

linux/covenant_prod.sh (A492) is the laptop's A, B and C: it needs covenant_A.db.key, the founder key, and its
nodes listen on every interface. Its README told a fresh tower to copy that key, so every tower would have been
node A on the office network. linux/covenant_tower.sh and linux/run_node_bound.py are the tower's launcher instead.

Driven both ways:
  * TW1 (every platform) linux/run_node_bound.refusal(): every-interface binds, a missing database name, a
    production key name, and a key byte-identical to the founder key or node A-D's (in the checkout or in
    ~/.covenant-keys) are refused; a fresh tower's own key and a single address are accepted.
  * TW2 (where bash and /proc exist) linux/test_covenant_tower_sh.sh against fake nodes: must end "0 failed".
    Its mutants (linux/mutate_covenant_tower_sh.sh) are run by hand; each must be CAUGHT."""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("run_node_bound", os.path.join(HERE, "linux", "run_node_bound.py"))
RB = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RB)
POSIX = os.name != "nt" and os.path.isdir("/proc/self") and shutil.which("bash") and shutil.which("pgrep")


class TW1Refusal(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp(prefix="a500_")
        self.home = tempfile.mkdtemp(prefix="a500h_")
        self.addCleanup(shutil.rmtree, self.repo, True)
        self.addCleanup(shutil.rmtree, self.home, True)

    def why(self, **env):
        return RB.refusal(env, repo=self.repo, home=self.home)

    def put(self, folder, name, data):
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, name), "wb") as fh:
            fh.write(data)

    def test_every_interface_refused_one_address_accepted(self):
        for b in ("", "0.0.0.0", "::", "[::]", "  "):
            self.assertIn("every interface", self.why(COVENANT_BIND=b, COVENANT_DB_PATH="nodeE_prod.db"), b)
        self.assertIsNone(self.why(COVENANT_BIND="100.64.0.7", COVENANT_DB_PATH="nodeE_prod.db"))
        self.assertIsNone(self.why(COVENANT_BIND="127.0.0.1", COVENANT_DB_PATH="nodeE_prod.db"))

    def test_database_must_be_named(self):
        self.assertIn("COVENANT_DB_PATH", self.why(COVENANT_BIND="127.0.0.1"))

    def test_production_key_names_refused(self):
        for db in ("nodeA_prod.db", "nodeB_prod.db", "nodeC_prod.db", "nodeD_prod.db", "covenant_A.db"):
            self.assertIn("production node", self.why(COVENANT_BIND="127.0.0.1", COVENANT_DB_PATH=db), db)
        self.assertIsNone(self.why(COVENANT_BIND="127.0.0.1", COVENANT_DB_PATH="nodeE_prod.db"))

    def test_a_copied_founder_key_is_refused_wherever_the_founder_key_sits(self):
        for folder in (self.repo, os.path.join(self.home, ".covenant-keys")):
            with self.subTest(folder=folder):
                self.put(self.repo, "nodeE_prod.db.key", b"FOUNDER-PEM")
                self.put(folder, "covenant_A.db.key", b"FOUNDER-PEM")
                self.assertIn("copy of", self.why(COVENANT_BIND="127.0.0.1", COVENANT_DB_PATH="nodeE_prod.db"))
                self.put(folder, "covenant_A.db.key", b"ANOTHER-PEM")      # the other way: its own key
                self.assertIsNone(self.why(COVENANT_BIND="127.0.0.1", COVENANT_DB_PATH="nodeE_prod.db"))
                os.remove(os.path.join(folder, "covenant_A.db.key"))

    def test_a_copied_node_key_is_refused(self):
        self.put(self.repo, "nodeE_prod.db.key", b"NODE-D-PEM")
        self.put(self.repo, "nodeD_prod.db.key", b"NODE-D-PEM")
        self.assertIn("nodeD_prod.db.key", self.why(COVENANT_BIND="127.0.0.1", COVENANT_DB_PATH="nodeE_prod.db"))

    def test_an_absolute_database_path_is_checked_too(self):
        db = os.path.join(self.repo, "elsewhere", "nodeF_prod.db")
        self.put(os.path.dirname(db), "nodeF_prod.db.key", b"FOUNDER-PEM")
        self.put(self.repo, "covenant_A.db.key", b"FOUNDER-PEM")
        self.assertIn("copy of", self.why(COVENANT_BIND="127.0.0.1", COVENANT_DB_PATH=db))


@unittest.skipUnless(POSIX, "TW2 needs bash, pgrep and /proc (Linux); NOT RUN here")
class TW2Shell(unittest.TestCase):
    def test_launcher_suite_passes_against_fake_nodes(self):
        p = subprocess.run(["bash", os.path.join(HERE, "linux", "test_covenant_tower_sh.sh"), HERE],
                           capture_output=True, text=True, timeout=600, cwd=tempfile.gettempdir())
        tail = (p.stdout + p.stderr)[-2500:]
        self.assertEqual(p.returncode, 0, tail)
        self.assertRegex(p.stdout, r"RESULT: \d+ passed, 0 failed", tail)


if __name__ == "__main__":
    res = unittest.main(exit=False, verbosity=2).result
    run, bad = res.testsRun, len(res.failures) + len(res.errors)
    print("A500: %d/%d passed, %d skipped" % (run - bad - len(res.skipped), run - len(res.skipped), len(res.skipped)))
    sys.exit(1 if bad else 0)
