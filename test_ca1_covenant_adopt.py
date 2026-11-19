"""CA1 -- covenant_adopt's gate is fail-closed and PROPOSE by default.

tools/covenant_adopt.py decides whether an incoming origin/main is safe to adopt (covenant-native, reusing
covenant_one's differential gate + node D's proven scan/classify patterns). This pins its gate both ways: GO
only when the diff is NORMAL, merges clean, the backdoor scan is clean, and no NEW gate fails; a HIGH
(security-sensitive) diff, a scan hit, an unclean merge, or a newly-failing gate each force NO-GO. And it pins
the two brakes that keep it safe: AUTO is OFF by default (PROPOSE-only -- a GO applies nothing without arming),
and apply refuses with no updater configured. Each NO-GO case fails if the gate stopped failing closed.

A453 (2026-11-19): what the SENDER of a change must not be able to decide. Those tests build a throwaway
origin / sender / node trio in a temp directory and run the real pipeline against it (covenant_one's check is
stubbed: it takes twenty minutes and is not what is under test). Nothing here touches this checkout's refs,
its ledger, the network or a node."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import covenant_adopt as A  # noqa: E402


class Classify(unittest.TestCase):
    def test_sensitive_paths_are_HIGH(self):
        for f in ("covenant_watchdog.py", "covenant_highway.py", "covenant_tetsu_hands.py",
                  "ops/operator_keys.json", "run_node.py", "covenant_grid_guard.py"):
            self.assertEqual(A.classify([f])[0], "HIGH", f)

    def test_files_that_tell_git_how_to_treat_the_tree_are_HIGH(self):
        # A453: an incoming .gitattributes hid whole files from the diff; a .gitmodules points at other code.
        for f in (".gitattributes", "docs/.gitattributes", ".gitmodules"):
            self.assertEqual(A.classify([f])[0], "HIGH", f)

    def test_ordinary_paths_are_NORMAL(self):
        self.assertEqual(A.classify(["docs/README.md", "tools/readme_totals.py"])[0], "NORMAL")


class Scan(unittest.TestCase):
    def test_each_backdoor_pattern_is_caught(self):
        cases = {
            "reverse_shell": "import pty; pty.spawn('/bin/sh')",
            "exec_of_decoded": "exec(base64.b64decode(payload))",
            "persistence_new": "subprocess.run(['schtasks','/create','/tn','x'])",
            "cred_capture": "open(os.path.expanduser('~/.ssh/id_rsa')).read()",
            "listener_all_ifaces": "s.bind(('0.0.0.0', 9999))",
        }
        for label, line in cases.items():
            hits = [h["pattern"] for h in A.scan_lines([("x.py", line)])]
            self.assertIn(label, hits, label)

    def test_ordinary_code_is_clean(self):
        self.assertEqual(A.scan_lines([("x.py", "def f(a): return a + 1"),
                                       ("y.py", "resp = requests.get(url)")]), [])


class Decide(unittest.TestCase):
    CLEAN = dict(cls="NORMAL", sens=[], scan={"state": "clean"}, test={"ok": True}, merge_ok=True)

    def _d(self, **over):
        a = dict(self.CLEAN, **over)
        return A.decide(a["cls"], a["sens"], a["scan"], a["test"], a["merge_ok"])

    def test_go_only_when_everything_clean(self):
        self.assertEqual(self._d()[0], "GO")

    def test_high_sensitivity_holds(self):
        self.assertEqual(self._d(cls="HIGH", sens=["covenant_watchdog.py"])[0], "NO-GO")

    def test_scan_hit_holds(self):
        self.assertEqual(self._d(scan={"state": "hits"})[0], "NO-GO")

    def test_new_failing_gate_holds(self):
        self.assertEqual(self._d(test={"ok": False, "new_failures": ["G5"]})[0], "NO-GO")

    def test_unclean_merge_holds(self):
        self.assertEqual(self._d(merge_ok=False)[0], "NO-GO")


class Brakes(unittest.TestCase):
    def test_auto_is_off_by_default(self):
        # PROPOSE by default: without COVENANT_ADOPT_AUTO=1 the module never arms, so a GO applies nothing.
        self.assertFalse(A.AUTO, "AUTO must default OFF -- apply must need an explicit arm")

    def test_apply_refuses_without_an_updater(self):
        # with no COVENANT_ADOPT_UPDATER, apply never runs the mesh -- it reports an error and applies nothing.
        orig = A.UPDATER
        A.UPDATER = None
        try:
            steps = A.apply({"head": "deadbeef0000"}, dry=False)
        finally:
            A.UPDATER = orig
        self.assertFalse(steps.get("applied"))
        self.assertIn("error", steps)


class Digest(unittest.TestCase):
    def test_digest_returns_a_summary(self):
        d = A.digest()
        self.assertIn("armed", d)


# ------------------------------------------------------------------------------------------------ A453 --
def _g(cwd, *a):
    r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid", "-c", "core.autocrlf=false",
                        "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", "-c", "advice.detachedHead=false"]
                       + list(a), cwd=cwd, capture_output=True, text=True)
    return r.stdout.strip()


def _put(cwd, files, msg):
    for name, text in files.items():
        with open(os.path.join(cwd, name), "w", newline="\n") as fh:
            fh.write(text)
    _g(cwd, "add", "-A")
    _g(cwd, "commit", "-q", "-m", msg)
    return _g(cwd, "rev-parse", "HEAD")


def _rm(path):
    def fix(fn, p, _e):
        try:
            os.chmod(p, 0o700)
            fn(p)
        except OSError:
            pass
    try:
        shutil.rmtree(path, onexc=fix)
    except TypeError:                                    # before Python 3.12
        shutil.rmtree(path, onerror=fix)


GATE_FILE = "".join("def f%d(x):\n    return x + %d\n\n\n" % (i, i) for i in range(40))
EVIL = "import pty\npty.spawn('/bin/sh')\n"


class AddedLines(unittest.TestCase):
    """The reader of the diff, alone. Bytes in, (file, text) out."""
    P = (b"diff --git a/notes.txt b/notes.txt\nnew file mode 100644\nindex 0000000..1111111\n--- /dev/null\n"
         b"+++ b/notes.txt\n@@ -0,0 +1,4 @@\n+++ b/test_a441_real.py\n+import pty; pty.spawn('/bin/sh')\n"
         b"+++pty.spawn('/bin/sh')\n+tail\rpty.spawn\n\\ No newline at end of file\n"
         b"diff --git a/b.py b/b.py\nindex 2222222..3333333 100644\n--- a/b.py\n+++ b/b.py\n@@ -1 +1,2 @@\n keep\n+x = 1\n")

    def test_a_content_line_is_never_a_file_header(self):
        got = A.added_lines(self.P)
        self.assertEqual([f for f, _ in got], ["notes.txt"] * 4 + ["b.py"])
        self.assertEqual(got[0][1], "++ b/test_a441_real.py")

    def test_a_line_beginning_with_two_plus_signs_is_read(self):
        got = A.added_lines(self.P)
        self.assertEqual(got[2][1], "++pty.spawn('/bin/sh')")
        self.assertEqual(len(A.scan_lines(got)), 3)

    def test_a_lone_carriage_return_stays_inside_its_line(self):
        self.assertEqual(A.added_lines(self.P)[3][1], "tail\rpty.spawn")

    def test_removed_then_added_lines_shaped_like_headers(self):
        p = b"--- a/c.py\n+++ b/c.py\n@@ -1,2 +1,3 @@\n keep\n--- a/zz\n+++ b/test_a441_real.py\n+pty.spawn\n"
        self.assertEqual(A.added_lines(p), [("c.py", "++ b/test_a441_real.py"), ("c.py", "pty.spawn")])

    def test_outside_a_hunk_a_plus_line_is_read_not_skipped(self):
        p = b"--- a/c.py\n+++ b/c.py\nnot a hunk header\n+++ b/other.py\n+pty.spawn\n"
        self.assertEqual(A.added_lines(p), [("c.py", "++ b/other.py"), ("c.py", "pty.spawn")])

    def test_quoted_header_and_nothing_added(self):
        self.assertEqual(A.added_lines(b'--- /dev/null\n+++ "b/a b.py"\t\n@@ -0,0 +1 @@\n+a\n'), [("a b.py", "a")])
        self.assertEqual(A.added_lines(b""), [])
        self.assertEqual(A.added_lines(b"Binary files a/x and b/x differ\n"), [])


class _Trio(unittest.TestCase):
    """A bare origin, a sender who pushes to it, and a node that the gate runs on."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ca1-")
        self.origin = os.path.join(self.tmp, "origin.git")
        _g(self.tmp, "init", "-q", "--bare", "-b", "main", self.origin)
        self.sender = os.path.join(self.tmp, "sender")
        _g(self.tmp, "clone", "-q", self.origin, self.sender)
        _g(self.sender, "checkout", "-q", "-B", "main")
        self.base = _put(self.sender, {"app.py": "print(1)\n", "covenant_act_gate.py": GATE_FILE,
                                       "notes_on_shells.txt": EVIL}, "base")
        _g(self.sender, "push", "-q", "origin", "HEAD:main")
        self.node = os.path.join(self.tmp, "node")
        _g(self.tmp, "clone", "-q", self.origin, self.node)
        self.assertEqual(_g(self.node, "rev-parse", "HEAD"), self.base)
        self._keep = {k: getattr(A, k) for k in ("REPO", "STATE_DIR", "LEDGER", "KILL_SWITCH", "_check_gates",
                                                 "TRACKED", "AUTO", "UPDATER")}
        A.REPO, A.STATE_DIR = self.node, os.path.join(self.tmp, "state")
        A.LEDGER, A.KILL_SWITCH = os.path.join(A.STATE_DIR, "ledger.jsonl"), os.path.join(A.STATE_DIR, "disabled")
        self.checked = []                                  # the commit each (stubbed) gate check ran on

        def gates(cwd):
            self.checked.append(_g(cwd, "rev-parse", "HEAD^{tree}"))
            return set()
        A._check_gates = gates

    def tearDown(self):
        for k, v in self._keep.items():
            setattr(A, k, v)
        _rm(self.tmp)

    def push(self, files, msg="a change", tag=None):
        tip = _put(self.sender, files, msg)
        _g(self.sender, "push", "-q", "origin", "HEAD:main")
        if tag:
            _g(self.sender, "tag", tag, tip)
            _g(self.sender, "push", "-q", "origin", "refs/tags/" + tag)
        return tip

    def run_gate(self, do_apply=False):
        return A.pipeline(do_apply=do_apply, dry=False)


class TheSenderCannotBlindTheGate(_Trio):
    def test_control_an_ordinary_change_is_GO_and_both_sides_are_full_ids(self):
        tip = self.push({"plain.py": "def add(a, b):\n    return a + b\n"})
        r, code = self.run_gate()
        self.assertEqual((r["decision"], code), ("GO", 0), r)
        self.assertEqual((r["head"], r["incoming"]), (self.base, tip))
        self.assertEqual(self.checked[1], _g(self.node, "rev-parse", self.base + "^{tree}"),
                         "the differential test's reference is the commit the node is on")

    def test_control_an_added_backdoor_line_holds(self):
        self.push({"evil.py": EVIL})
        r, code = self.run_gate()
        self.assertEqual((r["decision"], code, r["scan"]["state"]), ("NO-GO", 1, "hits"))
        self.assertEqual({h["file"] for h in r["scan"]["hits"]}, {"evil.py"})

    def test_a_tag_named_after_the_short_head_changes_nothing(self):
        # H1. The sender pushes the change AND a tag named after the node's 12-character HEAD, pointing at it.
        tip = self.push({"evil.py": EVIL}, tag=self.base[:12])
        r, _ = self.run_gate()
        self.assertEqual(_g(self.node, "tag"), "", "the gate's fetch brings no tag")
        self.assertEqual((r["decision"], r["scan"]["state"]), ("NO-GO", "hits"))
        # ...and with the tag already in the node (some other fetch brought it), still nothing changes.
        _g(self.node, "fetch", "-q", "--tags", "origin")
        self.assertEqual(_g(self.node, "rev-parse", self.base[:12]), tip, "the fixture is real: the short id IS the tag")
        self.assertEqual(_g(self.node, "diff", self.base[:12], tip), "", "...and the diff from it is empty")
        del self.checked[:]
        r, _ = self.run_gate()
        self.assertEqual((r["decision"], r["scan"]["state"]), ("NO-GO", "hits"))
        self.assertEqual(self.checked[1], _g(self.node, "rev-parse", self.base + "^{tree}"),
                         "the reference worktree is the node's commit, not the tag's")

    def test_a_short_or_odd_base_is_refused_not_guessed(self):
        tip = self.push({"evil.py": EVIL}, tag=self.base[:12])
        _g(self.node, "fetch", "-q", "--tags", "origin")
        _g(self.node, "merge", "-q", "--ff-only", tip)
        for bad in (self.base[:12], "", None, "HEAD~1", "main", "--output=x", self.base[:39], "0" * 40):
            self.assertEqual(A.scan(self.node, bad)["state"], "error", bad)
        self.assertEqual(A.scan(self.node, self.base)["state"], "hits")
        self.assertFalse(os.path.exists(os.path.join(self.node, "x")))
        del self.checked[:]
        d = A.differential_test(self.node, self.base[:12])
        self.assertEqual((d["ok"], self.checked), (False, []), "no reference by a short id, and no check run on one")
        self.assertEqual(d["new_failures"], ["<no reference worktree>"], "the one placeholder for 'no reference'")

    def test_lines_beginning_with_two_plus_signs_are_scanned(self):
        # H2i. Valid Python: unary plus, twice.
        self.push({"run.py": "import pty\n++pty.spawn('/bin/sh')\nx = (1\n++eval(open('p').read()))\n"})
        r, _ = self.run_gate()
        self.assertEqual(r["decision"], "NO-GO")
        self.assertEqual({h["pattern"] for h in r["scan"]["hits"]}, {"reverse_shell", "exec_of_decoded"})
        self.assertEqual({h["file"] for h in r["scan"]["hits"]}, {"run.py"})

    def test_a_hit_is_named_for_the_file_that_holds_it(self):
        # H2ii. One new file whose first line imitates a header naming a file that already exists.
        self.push({"notes.txt": "++ b/app.py\nimport pty; pty.spawn('/bin/sh')\n"})
        r, _ = self.run_gate()
        self.assertEqual([h["file"] for h in r["scan"]["hits"]], ["notes.txt"])

    def test_attributes_that_arrive_with_the_change_hide_nothing(self):
        # H3.
        tip = self.push({".gitattributes": "*.py -diff\n", "hidden.py": EVIL})
        r, _ = self.run_gate()
        plain = _g(self.sender, "diff", self.base, tip)         # where the attributes file is checked out
        self.assertTrue("Binary files" in plain and "pty" not in plain, "the fixture is real: a plain diff shows no line")
        self.assertEqual((r["decision"], r["scan"]["state"], r["sensitivity"]), ("NO-GO", "hits", "HIGH"))
        self.assertIn("hidden.py", {h["file"] for h in r["scan"]["hits"]})

    def test_a_sensitive_file_renamed_to_a_neutral_name_is_still_HIGH(self):
        _g(self.sender, "mv", "covenant_act_gate.py", "helper.py")
        tip = self.push({"helper.py": GATE_FILE.replace("return x + 7\n", "return True\n")})
        self.assertEqual(_g(self.node, "fetch", "-q", "origin") or _g(self.node, "diff", "--name-only", "-M",
                         "%s...%s" % (self.base, tip)), "helper.py", "the fixture is real: with renames on, one name")
        r, _ = self.run_gate()
        self.assertEqual((r["decision"], r["sensitivity"]), ("NO-GO", "HIGH"))
        self.assertIn("covenant_act_gate.py", r["changed_files"])

    def test_inert_text_renamed_to_a_live_name_is_read(self):
        _g(self.sender, "mv", "notes_on_shells.txt", "sitecustomize.py")
        self.push({})
        r, _ = self.run_gate()
        self.assertEqual((r["decision"], r["scan"]["state"]), ("NO-GO", "hits"))
        self.assertEqual({h["file"] for h in r["scan"]["hits"]}, {"sitecustomize.py"})

    def test_a_shadowed_tracked_name_holds(self):
        tip = self.push({"plain.py": "x = 1\n"})
        _g(self.node, "tag", "origin/main", self.base)             # the name now means the tag
        r, _ = self.run_gate()
        self.assertEqual(r["decision"], "NO-GO")
        self.assertTrue(any("shadowed" in x for x in r["reasons"]), r["reasons"])
        self.assertEqual(r["incoming"], tip, "what was judged is still the remote branch")
        self.assertEqual(A.decide("NORMAL", [], {"state": "clean"}, {"ok": True}, True, "x")[0], "NO-GO")
        self.assertEqual(A.decide("NORMAL", [], {"state": "clean"}, {"ok": True}, True, "")[0], "GO")


class AFailureIsNotAlreadyCurrent(_Trio):
    def test_control_nothing_incoming_is_NONE(self):
        r, code = self.run_gate()
        self.assertEqual((r["decision"], code), ("NONE", 3))

    def test_a_remote_that_cannot_be_fetched_is_an_error(self):
        self.push({"evil.py": EVIL})
        _g(self.node, "remote", "set-url", "origin", os.path.join(self.tmp, "gone.git"))
        r, code = self.run_gate()
        self.assertEqual((r["decision"], code), ("ERROR", 2), r)
        self.assertIn("fetch", r["detail"])
        self.assertTrue(os.path.isfile(A.LEDGER), "and the run is recorded")

    def test_a_tracked_name_that_does_not_resolve_is_an_error(self):
        A.TRACKED = "origin/no-such-branch"
        r, code = self.run_gate()
        self.assertEqual((r["decision"], code), ("ERROR", 2), r)

    def test_a_merge_that_did_not_happen_is_no_candidate(self):
        # Unrelated history: the merge refuses, with no conflict to list. The first version went on with HEAD.
        _g(self.sender, "checkout", "-q", "--orphan", "other")
        orphan = _put(self.sender, {"evil.py": EVIL}, "an unrelated history")
        _g(self.sender, "push", "-q", "-f", "origin", "HEAD:main")
        _g(self.node, "fetch", "-q", "origin")
        wt, why = A.build_candidate({"head": self.base, "incoming": orphan})
        self.assertIsNone(wt, why)
        self.assertIn("did not complete", why)
        self.assertEqual(A.build_candidate({"head": self.base[:12], "incoming": orphan})[0], None)
        r, code = self.run_gate()
        self.assertNotEqual(r["decision"], "GO")
        self.assertIn(code, (1, 2))


UPDATER_BY_NAME = """import os, subprocess
g = ["git", "-c", "user.name=u", "-c", "user.email=u@u.invalid"]
subprocess.run(g + ["fetch", "-q", "origin"], check=True)
subprocess.run(g + ["merge", "-q", "--no-ff", "--no-edit", "origin/main"], check=True)
open("seen.txt", "w").write(os.environ.get("COVENANT_ADOPT_TESTED", "") + " " + os.environ.get("COVENANT_ADOPT_FROM", ""))
"""
UPDATER_BY_ID = UPDATER_BY_NAME.replace('"origin/main"', 'os.environ["COVENANT_ADOPT_TESTED"]')


class WhatLandsIsWhatWasTested(_Trio):
    def _updater(self, text):
        A.UPDATER = os.path.join(self.tmp, "updater.py")
        with open(A.UPDATER, "w") as fh:
            fh.write(text)
        A.AUTO = True

    def _main_moves_during_the_test(self):
        real = A._check_gates
        state = {"moved": None}

        def gates(cwd):
            if state["moved"] is None:
                state["moved"] = self.push({"late.py": EVIL}, "pushed while the gate was testing")
            return real(cwd)
        A._check_gates = gates
        return state

    def test_untested_commits_names_what_was_not_tested(self):
        x = self.push({"plain.py": "x = 1\n"})
        x2 = self.push({"late.py": EVIL})
        _g(self.node, "fetch", "-q", "origin")
        _g(self.node, "merge", "-q", "--no-ff", "--no-edit", x)
        after = _g(self.node, "rev-parse", "HEAD")
        self.assertEqual(A.untested_commits(self.base, x, after), [], "the merge of exactly the tested commit")
        self.assertEqual(A.untested_commits(self.base, x, x), [], "a fast-forward to the tested commit")
        _g(self.node, "merge", "-q", "--no-ff", "--no-edit", x2)
        self.assertIn(x2, A.untested_commits(self.base, x, _g(self.node, "rev-parse", "HEAD")))
        self.assertTrue(A.untested_commits(self.base, x2, after), "the tested commit is not in what landed")
        self.assertTrue(A.untested_commits(self.base[:12], x, after)[0].startswith("<unknown"))

    def test_an_updater_that_merges_by_name_lands_untested_work_and_the_gate_says_so(self):
        x = self.push({"plain.py": "x = 1\n"})
        self._updater(UPDATER_BY_NAME)
        state = self._main_moves_during_the_test()
        r, code = self.run_gate(do_apply=True)
        self.assertEqual(r["decision"], "GO", r)                  # what it tested WAS clean
        self.assertEqual(r["incoming"], x)
        self.assertIn(state["moved"], r["apply"]["untested"])
        self.assertEqual(code, 2)
        self.assertIn("warning", r["apply"])
        with open(os.path.join(self.node, "seen.txt")) as fh:
            self.assertEqual(fh.read().split(), [x, self.base], "the updater was handed both ids")

    def test_an_updater_that_merges_the_tested_id_lands_only_that(self):
        x = self.push({"plain.py": "x = 1\n"})
        self._updater(UPDATER_BY_ID)
        state = self._main_moves_during_the_test()
        r, code = self.run_gate(do_apply=True)
        self.assertEqual((r["decision"], code, r["applied"]), ("GO", 0, True), r)
        self.assertEqual(r["apply"]["untested"], [])
        self.assertFalse(os.path.exists(os.path.join(self.node, "late.py")))
        self.assertNotEqual(state["moved"], x)


if __name__ == "__main__":
    _res = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    _bad = len(_res.failures) + len(_res.errors)
    print("CA1: %d/%d passed" % (_res.testsRun - _bad, _res.testsRun))
    sys.exit(1 if _bad else 0)
