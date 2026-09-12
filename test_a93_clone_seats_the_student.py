#!/usr/bin/env python3
"""A93 -- a CLONE must seat the distilled student, not a model server it lacks.

WHAT BROKE. ops/quorum_policy.json was untracked from the repository on
2026-09-11 (11f22a8: the policy is the operator's answer, and a clone should
inherit the question, not the answer). Correct on its own terms -- and it
silently changed what a clone's gate is, because run_with_ollama_judge.py:52-55
falls back to a HARD-CODED "local,semantic" whenever there is no policy file,
discarding COVENANT_JUDGE_PROVIDERS entirely. Provider "local" is OllamaJudge.

So every fresh clone -- the phone kit, and the second operator this project has
been building toward -- came up with a judge pointed at a model server that is
not there, while /health reported operable_semantic_judges: 2 because nothing
probes a seat at startup. This PC never saw it: the policy file still exists
here, it is merely gitignored now.

HOW THIS TEST WORKS, and why it is not a grep. It builds a clone-equivalent
tree by COPYING this one and deleting the gitignored policy file (no git: the
suite runner stages to a temp directory with no .git in it -- A84b/A87). It then
runs the real mobile/covenant_phone.sh with a fake `python` first on PATH, which
captures the environment the script actually hands the node instead of starting
it. That environment is then fed to a real interpreter in the clone tree, which
asks the registry which class provider[0] resolves to.

The negative control is the point: the SAME machinery, given the pre-fix
environment, must still produce OllamaJudge. A guard that cannot fail on the bug
it guards is not a guard (A66 and the 35/36 fake guards of 2026-09-09).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
POLICY_REL = os.path.join("ops", "quorum_policy.json")
SKIP_DIRS = {".git", ".venv", "venv", ".claude", "logs", "__pycache__",
             "node_modules", ".pytest_cache", "strategy_reports"}

PROBE = r'''
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_with_ollama_judge          # module-level: applies policy, resolves providers
import covenant_unified_v8 as cov
providers = os.environ["COVENANT_JUDGE_PROVIDERS"]
first = providers.split(",")[0].strip()
built = cov.JudgeProviderRegistry.build(first, 0)
print("__RESULT__" + __import__("json").dumps(
    {"providers": providers, "first": first, "impl": type(built).__name__}))
'''


def _ignore(_dir, names):
    return [n for n in names if n in SKIP_DIRS]


class CloneSeatsTheStudent(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="a93_clone_")
        cls.tree = os.path.join(cls.tmp, "clone")
        shutil.copytree(HERE, cls.tree, ignore=_ignore, symlinks=False)
        # This is what makes it a CLONE and not this machine: the operator's
        # standing answer is gitignored, so a clone never receives it.
        p = os.path.join(cls.tree, POLICY_REL)
        if os.path.exists(p):
            os.remove(p)
        # the fake `python`: records the environment the shell script exports,
        # then exits without starting a node.
        cls.bin = os.path.join(cls.tmp, "bin")
        os.makedirs(cls.bin, exist_ok=True)
        shim = os.path.join(cls.bin, "python")
        with open(shim, "w", newline="\n") as fh:
            fh.write('#!/bin/sh\nenv > "$A93_ENV_OUT"\nexit 0\n')
        os.chmod(shim, 0o755)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_00_precondition_clone_has_no_policy(self):
        """If a clone ever ships the policy again this test is measuring nothing."""
        self.assertFalse(os.path.exists(os.path.join(self.tree, POLICY_REL)),
                         "clone-equivalent tree still has the operator's policy file")
        self.assertTrue(os.path.exists(os.path.join(self.tree, "ops",
                                                    "quorum_policy.example.json")),
                        "the example the clone is supposed to get is missing")

    def _env_the_script_exports(self):
        """Run the real phone script; return the environment it hands the node."""
        out = os.path.join(self.tmp, "captured.env")
        env = dict(os.environ)
        env["PATH"] = self.bin + os.pathsep + env["PATH"]
        env["A93_ENV_OUT"] = out
        env.pop("COVENANT_JUDGE_PROVIDERS_OVERRIDE", None)
        env.pop("COVENANT_JUDGE_PROVIDERS", None)
        r = subprocess.run(["sh", "mobile/covenant_phone.sh"], cwd=self.tree,
                           env=env, capture_output=True, text=True, timeout=120)
        self.assertTrue(os.path.exists(out),
                        "the script never reached its `exec python` line:\n"
                        + r.stdout + r.stderr)
        captured = {}
        for line in open(out, encoding="utf-8", errors="replace"):
            if "=" in line:
                k, v = line.rstrip("\n").split("=", 1)
                captured[k] = v
        return captured

    def _resolve(self, extra_env):
        probe = os.path.join(self.tree, "_a93_probe.py")
        with open(probe, "w", newline="\n") as fh:
            fh.write(PROBE)
        env = dict(os.environ)
        env.pop("COVENANT_JUDGE_PROVIDERS_OVERRIDE", None)
        env.pop("COVENANT_JUDGE_PROVIDERS", None)
        env.update(extra_env)
        r = subprocess.run([sys.executable, probe], cwd=self.tree, env=env,
                           capture_output=True, text=True, timeout=300)
        line = [l for l in (r.stdout + r.stderr).splitlines()
                if l.startswith("__RESULT__")]
        self.assertTrue(line, "probe produced no result:\n" + r.stdout + r.stderr)
        return json.loads(line[0][len("__RESULT__"):])

    def test_01_script_sets_the_only_variable_that_wins(self):
        captured = self._env_the_script_exports()
        self.assertIn("COVENANT_JUDGE_PROVIDERS_OVERRIDE", captured,
                      "covenant_phone.sh exported no OVERRIDE; with no policy file "
                      "every other providers variable is discarded")
        self.assertIn("deferring", captured["COVENANT_JUDGE_PROVIDERS_OVERRIDE"])

    def test_02_clone_seats_the_student(self):
        captured = self._env_the_script_exports()
        got = self._resolve({k: v for k, v in captured.items()
                             if k.startswith("COVENANT_")})
        self.assertNotEqual(
            got["impl"], "OllamaJudge",
            "a clone seated OllamaJudge: it will talk to 127.0.0.1:11434, which a "
            "phone does not run. Resolved providers=%r" % got["providers"])
        self.assertEqual(got["impl"], "DeferringJudge", got)

    def test_03_negative_control_the_old_wiring_still_breaks(self):
        """The pre-fix environment MUST still produce the broken seat here.

        If this ever starts passing as DeferringJudge, the fallback in
        run_with_ollama_judge.py changed and test_02 has stopped proving that
        the phone script is what fixed anything."""
        got = self._resolve({"COVENANT_JUDGE_PROVIDERS": "local"})
        self.assertEqual(
            got["impl"], "OllamaJudge",
            "the bug this test guards is no longer reproducible; re-derive the "
            "guard rather than trusting it (got %r)" % got)
        self.assertEqual(got["providers"], "local,semantic",
                         "the hard-coded no-policy fallback changed shape: " + repr(got))


if __name__ == "__main__":
    unittest.main(verbosity=2)
