#!/usr/bin/env python3
"""A93 -- a CLONE must seat the distilled student, not a model server it lacks.

WHAT BROKE. ops/quorum_policy.json was untracked from the repository on
2026-09-11 (11f22a8: the policy is the operator's answer, and a clone should
inherit the question, not the answer). Correct on its own terms -- and it
silently changed what a clone's gate is, because the launcher (then named
run_with_ollama_judge.py, run_node.py since 2026-09-12) fell
back to a HARD-CODED "local,semantic" whenever there was no policy file,
discarding COVENANT_JUDGE_PROVIDERS entirely. Provider "local" was OllamaJudge
(a server no clone ran; the module was deleted on 2026-09-12).

So every fresh clone -- the phone kit, and the second operator this project has
been building toward -- came up with a judge pointed at a model server that is
not there, while /health reported operable_semantic_judges: 2 because nothing
probes a seat at startup. This PC never saw it: the policy file still exists
here, it is merely gitignored now.

HOW IT WAS CLOSED, in two steps. On 2026-09-12 the phone script first exported
COVENANT_JUDGE_PROVIDERS_OVERRIDE, the one variable the fallback could not
discard. That worked and was wrong: OVERRIDE beats the operator's own policy
file, so a phone operator's standing decision would have been silently ignored.
Later the same day the operator changed the fallback itself to
"deferring,semantic" and the override came out of the script. What this file
now pins is the second state: a policy-less tree seats the student with NO help
from the environment, and the phone script exports nothing about providers.

HOW THIS TEST WORKS, and why it is not a grep. It builds a clone-equivalent
tree by COPYING this one and deleting the gitignored policy file (no git: the
suite runner stages to a temp directory with no .git in it -- A84b/A87). It then
runs the real mobile/covenant_phone.sh with a fake `python` first on PATH, which
captures the environment the script actually hands the node instead of starting
it. That environment is then fed to a real interpreter in the clone tree, which
asks the registry which class provider[0] resolves to.

The controls are the point: an explicit OVERRIDE=local,semantic must still
produce the HTTP provider (so the probe is known to discriminate), and a plain
COVENANT_JUDGE_PROVIDERS=local must be IGNORED on a policy-less tree (the
fallback, not the shell, decides a clone's gate). A guard that cannot fail on
the bug it guards is not a guard (A66 and the 35/36 fake guards of 2026-09-09).
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
             "node_modules", ".pytest_cache", "strategy_reports",
             # 2026-09-12: a local build of mobile/app leaves hundreds of MB under
             # build/ and .gradle/; copying that into the clone-equivalent tree
             # would time this suite out. The APK build stages outside the tree
             # anyway, but a stray local build must not be able to break a sweep.
             "build", ".gradle", ".kotlin"}

PROBE = r'''
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_node          # module-level: applies policy, resolves providers
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

    def test_01_script_exports_nothing_about_providers(self):
        """The phone script must not pin the seat list. OVERRIDE beats the
        operator's own ops/quorum_policy.json, so a script that exported it
        would silently ignore a phone operator's standing decision. Resolution
        belongs to the launcher: policy if present, else its default."""
        captured = self._env_the_script_exports()
        self.assertNotIn("COVENANT_JUDGE_PROVIDERS_OVERRIDE", captured,
                         "covenant_phone.sh exports OVERRIDE again -- that silences a phone "
                         "operator's own policy file")
        self.assertNotIn("COVENANT_JUDGE_PROVIDERS", captured,
                         "covenant_phone.sh exports a providers list; with no policy the "
                         "launcher discards it, and with a policy the policy wins -- either "
                         "way it is a value that lies to whoever reads the script")

    def test_02_clone_seats_the_student(self):
        captured = self._env_the_script_exports()
        got = self._resolve({k: v for k, v in captured.items()
                             if k.startswith("COVENANT_")})
        self.assertNotEqual(
            got["impl"], "OpenAICompatJudge",
            "a clone seated an HTTP provider it does not run (there is no server "
            "on a phone). Resolved providers=%r" % got["providers"])
        self.assertEqual(got["impl"], "DeferringJudge", got)

    def test_03_control_an_explicit_override_still_wins(self):
        """The probe must be able to produce the BROKEN seat on demand, or a
        green test_02 proves nothing. OVERRIDE is the one variable that beats
        the fallback, so OVERRIDE=local,semantic must yield the HTTP provider
        (OpenAICompatJudge since the Ollama module was deleted, 2026-09-12)."""
        got = self._resolve({"COVENANT_JUDGE_PROVIDERS_OVERRIDE": "local,semantic"})
        self.assertEqual(got["impl"], "OpenAICompatJudge",
                         "the probe can no longer reach the broken seat; re-derive this "
                         "guard rather than trusting it (got %r)" % got)

    def test_04_the_shell_does_not_decide_a_clone_gate(self):
        """A plain COVENANT_JUDGE_PROVIDERS=local on a policy-less tree must be
        IGNORED: the launcher's default decides, not whatever a shell exported.
        This is the property the 2026-09-12 fallback change relies on."""
        got = self._resolve({"COVENANT_JUDGE_PROVIDERS": "local"})
        self.assertEqual(got["providers"], "deferring,semantic",
                         "no-policy fallback changed shape: " + repr(got))
        self.assertEqual(got["impl"], "DeferringJudge", got)


if __name__ == "__main__":
    unittest.main(verbosity=2)
