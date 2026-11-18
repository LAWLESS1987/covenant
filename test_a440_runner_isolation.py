"""A440: the workshop runner starts Python in ISOLATED mode (-I), so a module planted beside the hashed script
cannot shadow the standard library. Asked on the Hugging Face forum (topic 191990 #2): "a planted json.py beside
the hashed script loads unhashed if the script imports json and the child starts without -I, -P or
PYTHONSAFEPATH -- does the packet's launch pass any of those?" It does: -I, which on 3.11+ also sets safe_path.
Driven both ways: with -I the planted module is NOT imported; without -I (the control) it IS, so the test can
tell the difference and would go red if -I were ever dropped from the runner."""
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
HANDS = os.path.join(HERE, "covenant_tetsu_hands.py")
PROBE = "import json, sys; print('PLANTED' if getattr(json, 'PLANTED', False) else 'STDLIB')"


def _run(flags, cwd):
    cp = subprocess.run([sys.executable] + flags + ["-c", PROBE], cwd=cwd, capture_output=True, text=True, timeout=60)
    return (cp.stdout + cp.stderr).strip()


class A440RunnerIsolation(unittest.TestCase):
    def setUp(self):
        self.ws = tempfile.mkdtemp(prefix="a440-")
        with open(os.path.join(self.ws, "json.py"), "w", encoding="utf-8") as fh:
            fh.write("PLANTED = True\n")

    def test_runner_source_passes_isolated_flag(self):
        """The real runner's subprocess call passes -I (static pin: removing it goes red here)."""
        src = open(HANDS, encoding="utf-8").read()
        m = re.search(r"subprocess\.run\(\[sys\.executable,\s*\"-I\",\s*\"-c\",\s*RUNNER", src)
        self.assertIsNotNone(m, "covenant_tetsu_hands.run() must start the child with -I before -c RUNNER")

    def test_planted_sibling_does_not_load_under_isolated_mode(self):
        """With -I, the planted json.py beside the script is NOT imported (the stdlib wins)."""
        self.assertEqual(_run(["-I"], self.ws), "STDLIB")

    def test_control_planted_sibling_loads_without_isolation(self):
        """CONTROL: without -I the planted module IS imported -- proves the test can see the vector."""
        self.assertEqual(_run([], self.ws), "PLANTED")

    def test_isolated_mode_sets_safe_path(self):
        """On 3.11+ -I implies safe_path, so the script dir / cwd is not prepended to sys.path."""
        out = _run(["-I"], self.ws)  # sanity the probe ran
        flags = subprocess.run([sys.executable, "-I", "-c", "import sys; print(sys.flags.isolated, getattr(sys.flags, 'safe_path', 0))"],
                               capture_output=True, text=True, timeout=60).stdout.split()
        self.assertEqual(flags[0], "1", "isolated mode must be on")
        if sys.version_info >= (3, 11):
            self.assertEqual(flags[1], "True", "safe_path must be set under -I on 3.11+")


if __name__ == "__main__":
    unittest.main()
