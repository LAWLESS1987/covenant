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
        for info in ({"head": self.base[:12], "incoming": tip}, {"head": self.base, "incoming": tip[:12]}):
            wt, why = A.build_candidate(info)
            if wt:
                A._cleanup(wt)
            self.assertIsNone(wt, "a candidate was built from a short id: %s" % why)
        wt, why = A.build_candidate({"head": self.base, "incoming": tip})
        A._cleanup(wt)
        self.assertIsNotNone(wt, "the control: the same two commits by full id do build (%s)" % why)
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
        self.assertTrue(r["merge"].startswith("merged cleanly"), "and its candidate was built from that id: %s" % r["merge"])
        self.assertTrue(os.path.isfile(A.LEDGER))
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


class OutputIsReadWhole(_Trio):
    """One byte this machine's default codec cannot decode must not empty what a child process printed."""
    BAD = b"\xe2\x80\x9d"                                   # U+201D, a right curly quote; 0x9d has no cp1252 character

    def _runner(self, body):
        d = os.path.join(self.tmp, "runner")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "covenant_one.py"), "wb") as fh:
            fh.write(body)
        return d

    def setUp(self):
        _Trio.setUp(self)
        A._check_gates = self._keep["_check_gates"]            # the real one: this class is about reading output

    def test_a_failing_gate_beside_a_curly_quote_is_still_read(self):
        d = self._runner(b"import sys\nsys.stdout.buffer.write(b'G5 FAIL\\n' + bytes([0xe2, 0x80, 0x9d]) + b'\\n"
                         b"test_x.py=FAIL rc=1\\n--check was passed. Stopping here.\\n')\n")
        self.assertEqual(A._check_gates(d), {"G5", "test_x.py"})

    def test_a_runner_that_does_not_finish_is_a_failure(self):
        self.assertEqual(A._check_gates(self._runner(b"def broken(:\n")), {A.CHECK_UNFINISHED})
        self.assertEqual(A._check_gates(self._runner(b"print('all good')\n")), {A.CHECK_UNFINISHED})
        self.assertEqual(A._check_gates(self._runner(b"print('%s')\n" % A.CHECK_DONE.encode())), set())

    def test_this_repository_s_runner_still_prints_the_line(self):
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "covenant_one.py"), encoding="utf-8") as fh:
            self.assertIn(A.CHECK_DONE, fh.read(), "covenant_one's last --check line changed: update CHECK_DONE")

    def test_a_commit_subject_with_a_curly_quote_does_not_empty_the_list(self):
        self.push({"plain.py": "x = 1\n"}, msg="tidy \u201cquoted\u201d")
        info = A.detect()
        self.assertNotIn("error", info)
        self.assertEqual(len(info["incoming_commits"]), 1, info["incoming_commits"])
        self.assertEqual(info["changed_files"], ["plain.py"])

    def test_the_tracked_name_is_a_branch_never_a_tag(self):
        tip = self.push({"plain.py": "x = 1\n"})
        _g(self.node, "fetch", "-q", "origin")
        _g(self.node, "tag", "origin/gone", tip)               # only a TAG answers to this name
        A.TRACKED = "origin/gone"
        r, code = self.run_gate()
        self.assertEqual((r["decision"], code), ("ERROR", 2), r)
        _g(self.node, "branch", "side", tip)                   # a local branch is a fair override
        A.TRACKED = "side"
        self.assertEqual(A.detect()["incoming"], tip)

    def test_digest_shows_an_error_day(self):
        os.makedirs(A.STATE_DIR, exist_ok=True)
        with open(A.LEDGER, "w") as fh:
            fh.write('{"t": "2026-11-19T05:00:00", "decision": "ERROR", "detail": "git fetch origin failed"}\n')
        d = A.digest()
        self.assertEqual([e["why"] for e in d["errors"]], ["git fetch origin failed"])
        self.assertEqual(d["held"], [])


class WhereA452AndA453Meet(unittest.TestCase):
    def test_an_error_run_is_named_an_error_not_a_merge(self):
        c = A.contradictions({"decision": "ERROR", "detail": "git fetch origin failed", "merge": ""})
        self.assertEqual([(x["kind"], x["detail"], x["keys"], x["paths"]) for x in c],
                         [("error", "git fetch origin failed", [], [])])

    def test_the_gate_s_own_placeholders_are_never_paths(self):
        r = {"decision": "NO-GO", "merge": "merged cleanly in scratch",
             "test": {"ok": False, "new_failures": [A.CHECK_UNFINISHED, A._NO_REFERENCE, "G5", "test_x.py"]}}
        c = [x for x in A.contradictions(r) if x["kind"] == "new_failing_gate"][0]
        self.assertEqual(c["paths"], ["test_x.py"])

    def test_an_error_run_s_look_back_is_unreadable_and_counts_earlier_error_days(self):
        # No head and no incoming: nothing to read the record at. Said, never raised; and every earlier ERROR
        # day is the same thing again ("the remote was unreachable again"), while a conflict day is not.
        rows = [{"decision": "ERROR", "detail": "earlier", "t": "2026-11-18T05:00:00"},
                {"decision": "NO-GO", "merge": "merge conflict (human needed): x", "t": "2026-11-17T05:00:00"}]
        out = A.annotate({"decision": "ERROR", "detail": "git fetch origin failed", "applied": False, "head": ""}, rows=rows)
        self.assertEqual([c["kind"] for c in out["contradictions"]], ["error"])
        self.assertNotIn("error", out["lookback"])
        self.assertEqual(len(out["lookback"]["unreadable"]), 2)
        self.assertEqual(out["lookback"]["hits"], [])
        self.assertEqual([(s["kind"], s["earlier_runs"]) for s in out["seen_before"]], [("error", 1)])

    def test_the_two_new_merge_strings_give_no_guessed_keys(self):
        for m in ("merge did not complete (human needed): fatal: refusing to merge unrelated histories",
                  "no candidate: both sides must be named by a full commit id"):
            c = A.contradictions({"decision": "NO-GO", "merge": m, "scan": {"state": "skipped (conflict)"}})
            self.assertEqual([(x["kind"], x["keys"]) for x in c], [("merge", [])], m)


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
        missing = A.untested_commits(self.base, x, self.base)
        self.assertEqual(len(missing), 1, missing)
        self.assertTrue(missing[0].startswith("<the tested commit"), missing)

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

    def test_an_apply_that_was_attempted_and_did_not_land_is_not_exit_0(self):
        # The updater merges the tested commit and then reports failure, HEAD moved. It read: GO, exit 0.
        self.push({"plain.py": "x = 1\n"})
        self._updater(UPDATER_BY_ID + "raise SystemExit(1)\n")
        r, code = self.run_gate(do_apply=True)
        self.assertEqual((r["decision"], r["applied"], r["apply"]["updater_rc"]), ("GO", False, 1), r)
        self.assertEqual(code, 2)
        A.UPDATER = os.path.join(self.tmp, "no-such-updater.py")       # armed, GO, and nothing to hand off to
        self.push({"plain2.py": "y = 2\n"})
        r, code = self.run_gate(do_apply=True)
        self.assertEqual((r["decision"], r["applied"], code), ("GO", False, 2), r)

    def test_an_updater_that_merges_the_tested_id_lands_only_that(self):
        x = self.push({"plain.py": "x = 1\n"})
        self._updater(UPDATER_BY_ID)
        state = self._main_moves_during_the_test()
        r, code = self.run_gate(do_apply=True)
        self.assertEqual((r["decision"], code, r["applied"]), ("GO", 0, True), r)
        self.assertEqual(r["apply"]["untested"], [])
        self.assertFalse(os.path.exists(os.path.join(self.node, "late.py")))
        self.assertNotEqual(state["moved"], x)


# ---------------------------------------------------------------- A452: contradictions and the look back
# His words on whether a core change should hold for his word (typed 2026-11-18 in the TETSU session, relayed
# verbatim; his go for building it into THIS gate was "Build it locally", the same day): "keep it auto, but if
# something contradicts, use the tombstones to figure out where it went wrong."
import io          # noqa: E402
import json        # noqa: E402
import tempfile    # noqa: E402

GO_RUN = {"decision": "GO", "reasons": [], "sensitivity": "NORMAL", "sensitive_hits": [],
          "merge": "merged cleanly in scratch", "scan": {"state": "clean", "hits": []}, "test": {"ok": True, "new_failures": []},
          "changed_files": ["docs/README.md"], "incoming_commits": ["abc1234 a docs change"], "applied": False}


def _run(**over):
    return dict(GO_RUN, **over)


SCAN_HIT = _run(decision="NO-GO", reasons=["backdoor scan: hits"],
                scan={"state": "hits", "hits": [{"file": "tools/opsec_scan.py", "pattern": "cred_capture", "added": "x"}]},
                changed_files=["tools/opsec_scan.py", "covenant_free_will.py"],
                incoming_commits=["1111111 A433: free reads during her isolation (#67)"])

RECORD = """# record

### A900. [the improvement miner stake check mistaken for a stakeholder note] (2026-01-01). FIXED

### A433. [free reads during her isolation; what she reads is held] (2026-11-16). IN SOURCE

### A777. [`covenant_free_will.py` drafted a reply to her own account] (2026-10-06). FIXED

### A555. [a scanner scanning a scanner hits itself: `opsec_scan.py` flagged its own patterns] (2026-09-26). FIXED

### A556. [G5 reads the ethics judge as down when the model slot is busy] (2026-10-01). OPEN
"""
TOMBS = {"retractions": [
    {"id": "A555-SCANNER-SELF-HIT", "claim": "the scan found a credential reader in opsec_scan", "truth": "it matched its own pattern text"},
    {"id": "A126-MARGIN", "claim": "the margin is 12 points", "truth": "the margin was never measured"}]}


def _root(record=RECORD, tombs=TOMBS):
    d = tempfile.mkdtemp(prefix="ca1_lb_")
    os.makedirs(os.path.join(d, "docs"))
    if record is not None:
        with io.open(os.path.join(d, "docs", "KNOWN_ISSUES.md"), "w", encoding="utf-8") as fh:
            fh.write(record)
    if tombs is not None:
        with io.open(os.path.join(d, "docs", "RETRACTED.json"), "w", encoding="utf-8") as fh:
            fh.write(tombs if isinstance(tombs, str) else json.dumps(tombs))
    return d


class ClassifyStaysAsHeChose(unittest.TestCase):
    def test_a_core_only_change_is_still_NORMAL(self):
        # "keep it auto": the look back is added BESIDE the gate; what holds for his word is not widened here.
        self.assertEqual(A.classify(["covenant_unified_v8.py", "verify_deploy.py", "MANIFEST.sha256"])[0], "NORMAL")

    def test_an_operator_named_file_is_still_HIGH(self):
        self.assertEqual(A.classify(["covenant_unified_v8.py", "test_a447_ally_not_operator.py"])[0], "HIGH")


class Contradictions(unittest.TestCase):
    def kinds(self, r):
        return [c["kind"] for c in A.contradictions(r)]

    def test_a_clean_GO_has_none(self):
        self.assertEqual(self.kinds(GO_RUN), [])

    def test_the_deliberate_HIGH_hold_is_not_one(self):
        r = _run(decision="NO-GO", sensitivity="HIGH", sensitive_hits=["covenant_watchdog.py"],
                 reasons=["security-sensitive diff (covenant_watchdog.py) -- holds for review"])
        self.assertEqual(self.kinds(r), [])

    def test_a_scan_hit_is_one_and_names_what_tripped(self):
        c = A.contradictions(SCAN_HIT)
        self.assertEqual([x["kind"] for x in c], ["scan_hit"])
        self.assertEqual(sorted(c[0]["keys"]), ["cred_capture", "tools/opsec_scan.py"])

    def test_a_conflict_is_one_merge_contradiction_not_also_a_failing_gate(self):
        r = _run(decision="NO-GO", merge="merge conflict (human needed): 100644 abc 1\tcovenant_one.py",
                 scan={"state": "skipped (conflict)"}, test={"ok": False, "new_failures": ["conflict"]})
        self.assertEqual(self.kinds(r), ["merge"])

    def test_a_conflict_names_the_hand_written_files_not_the_generated_one(self):
        # `git ls-files -u`: three stages per path, MANIFEST.sha256 first in git's order, as on 2026-11-18 08:37.
        unmerged = "".join("100644 %040d %d\t%s\n" % (n, st, p) for n, p in enumerate(
            ("MANIFEST.sha256", "covenant_one.py", "docs/KNOWN_ISSUES.md")) for st in (1, 2, 3))
        detail = A.conflict_detail(unmerged)
        self.assertEqual(detail, "merge conflict (human needed): covenant_one.py, docs/KNOWN_ISSUES.md "
                                 "[generated, also conflicted: MANIFEST.sha256]")
        self.assertEqual(A.conflict_files(unmerged), (["covenant_one.py", "docs/KNOWN_ISSUES.md"], ["MANIFEST.sha256"]))

    def test_what_conflicted_travels_as_a_list_never_parsed_back_out_of_the_prose(self):
        # The peer's read of #87 (2026-11-18): parsing the reason string back split "a,b.py" into two keys and
        # read a file named "we (+2 more)" as "we". The list is carried beside the prose and used as it is.
        odd = ["a,b.py", "name, with comma.md", "we (+2 more)", "z [generated, also conflicted: MANIFEST.sha256]"]
        unmerged = "".join("100644 x 1\t%s\n" % p for p in odd)
        real, _gen = A.conflict_files(unmerged)
        self.assertEqual(real, sorted(odd))
        c = A.contradictions(_run(decision="NO-GO", merge=A.conflict_detail(unmerged), merge_conflicts=real,
                                  scan={"state": "skipped (conflict)"}, test={"ok": False, "new_failures": ["conflict"]}))
        self.assertEqual(c[0]["keys"], sorted(odd))
        # with no list beside it (it cannot happen in a new line), the new prose is NOT parsed: no keys, not wrong keys
        self.assertEqual(A.contradictions(_run(decision="NO-GO", merge=A.conflict_detail(unmerged)))[0]["keys"], [])

    def test_a_ledger_line_from_before_names_its_one_path_unless_it_is_generated(self):
        old = "merge conflict (human needed): 100644 eb73e40032d02e7b012164f6293d87e987e1dfdd 1\t%s"
        self.assertEqual(A.conflict_paths(old % "covenant_one.py"), ["covenant_one.py"])
        self.assertEqual(A.conflict_paths(old % "MANIFEST.sha256"), [])
        self.assertEqual(A.conflict_paths("merged cleanly in scratch"), [])

    def test_a_long_conflict_is_counted_not_cut_silently(self):
        unmerged = "".join("100644 x 1\tf%02d.py\n" % n for n in range(11))
        detail = A.conflict_detail(unmerged)
        self.assertTrue(detail.endswith("f07.py (+3 more)"), detail)
        self.assertEqual(len(A.conflict_files(unmerged)[0]), 11)          # the list is whole; only the prose is cut

    def test_an_odd_ledger_row_is_read_as_nothing_not_raised(self):
        # The peer's read: a row whose `scan` or `test` is not an object raised AttributeError out of the digest.
        odd = {"decision": "NO-GO", "merge": "merged cleanly in scratch", "scan": "a string", "test": ["x"],
               "apply": "x", "merge_conflicts": "not a list"}
        self.assertEqual(A.contradictions(odd), [])
        self.assertEqual(A.contradictions({"decision": "NO-GO", "merge": "merged cleanly in scratch",
                                           "scan": {"state": "hits", "hits": "not a list"},
                                           "test": {"ok": False, "new_failures": "G5"}})[1]["keys"], [])

    def test_a_newly_failing_gate_is_one(self):
        c = A.contradictions(_run(decision="NO-GO", test={"ok": False, "new_failures": ["G5", "test_hi1_harvest_isolation.py"]}))
        self.assertEqual([x["kind"] for x in c], ["new_failing_gate"])
        self.assertEqual(c[0]["keys"], ["G5", "test_hi1_harvest_isolation.py"])

    def test_an_apply_that_did_not_land_is_one(self):
        r = _run(apply={"rollback_point": "abc", "updater_rc": 1, "after": "abc", "applied": False})
        self.assertEqual(self.kinds(r), ["apply_failed"])

    def test_a_dry_apply_and_a_landed_apply_are_not(self):
        self.assertEqual(self.kinds(_run(apply={"dry": "would run x"})), [])
        self.assertEqual(self.kinds(_run(applied=True, apply={"applied": True, "after": "def"})), [])

    def test_already_current_has_none(self):
        self.assertEqual(self.kinds({"decision": "NONE", "detail": "already current"}), [])


class Lookback(unittest.TestCase):
    def test_no_contradiction_no_search(self):
        lb = A.lookback(GO_RUN, root=_root())
        self.assertEqual((lb["hits"], lb["searched"]), ([], []))

    def test_what_tripped_outranks_a_file_that_merely_changed(self):
        lb = A.lookback(SCAN_HIT, root=_root())
        ids = [h["id"] for h in lb["hits"]]
        # opsec_scan TRIPPED (weight 3); A433 is in an incoming subject (2); covenant_free_will only changed (1).
        # The tombstone leads its own entry because its text also has the word "scan" (3 + 1 against 3). As first
        # drafted this test expected the entry first; that expectation was wrong, the ranking was not (A452).
        self.assertEqual(ids, ["A555-SCANNER-SELF-HIT", "A555", "A433", "A777"], ids)

    def test_every_hit_says_where_and_why(self):
        for h in A.lookback(SCAN_HIT, root=_root())["hits"]:
            self.assertTrue(h["where"].startswith("docs/") and h["matched"] and h["score"] > 0, h)
        tomb, entry = A.lookback(SCAN_HIT, root=_root())["hits"][:2]
        self.assertEqual((tomb["where"], tomb["entry"]), ("docs/RETRACTED.json", "A555"))
        self.assertEqual((entry["where"], entry["line"]), ("docs/KNOWN_ISSUES.md", 9))      # a live line number

    def test_matching_is_by_whole_word(self):
        # `stake` tripped; A900's header says "mistaken" and "stakeholder" and the word "stake": only the word counts.
        r = _run(decision="NO-GO", test={"ok": False, "new_failures": ["stake.py"]}, changed_files=[], incoming_commits=[])
        rec = RECORD.replace("miner stake check mistaken", "miner check mistaken")      # the WORD is gone
        self.assertEqual([h["id"] for h in A.lookback(r, root=_root(record=rec))["hits"]], [])
        self.assertEqual([h["id"] for h in A.lookback(r, root=_root())["hits"]], ["A900"])

    def test_an_A_number_in_a_failing_suites_name_finds_its_entry(self):
        r = _run(decision="NO-GO", test={"ok": False, "new_failures": ["test_a433_harvest.py"]}, changed_files=[], incoming_commits=[])
        first = A.lookback(r, root=_root())["hits"][0]
        # weight 3, as something that TRIPPED -- not the 1 it would get as just another word of the file's name
        self.assertEqual((first["id"], first["score"]), ("A433", 3))
        short = _run(decision="NO-GO", test={"ok": False, "new_failures": ["test_a90_x.py"]}, changed_files=[], incoming_commits=[])
        rec = RECORD + "\n### A90. [an old entry with a short number] (2026-08-30). FIXED\n"
        self.assertEqual([h["id"] for h in A.lookback(short, root=_root(record=rec))["hits"]], ["A90"])

    def test_a_gate_id_finds_the_entry_that_names_it(self):
        r = _run(decision="NO-GO", test={"ok": False, "new_failures": ["G5"]}, changed_files=[], incoming_commits=[])
        self.assertEqual([h["id"] for h in A.lookback(r, root=_root())["hits"]], ["A556"])

    def test_an_unreadable_record_is_said_and_the_other_is_still_searched(self):
        lb = A.lookback(SCAN_HIT, root=_root(tombs="{not json"))
        self.assertTrue(any("RETRACTED.json" in u for u in lb["unreadable"]), lb)
        self.assertIn("A555", [h["id"] for h in lb["hits"]])
        lb2 = A.lookback(SCAN_HIT, root=_root(record=None, tombs=None))
        self.assertEqual((len(lb2["unreadable"]), lb2["hits"]), (2, []))

    def test_at_most_the_top_few(self):
        many = "".join("### A%d. [`opsec_scan.py` again] (2026-01-01).\n\n" % n for n in range(600, 640))
        self.assertEqual(len(A.lookback(SCAN_HIT, root=_root(record=many))["hits"]), A.LOOKBACK_TOP)


def _git_repo(*commits):
    """A throwaway git repository with one commit per (record, tombstones) pair. Returns (path, [shas])."""
    import subprocess
    d = tempfile.mkdtemp(prefix="ca1_git_")

    def g(*a):
        r = subprocess.run(["git", "-C", d] + list(a), capture_output=True, text=True)
        assert r.returncode == 0, (a, r.stderr)
        return r.stdout.strip()
    g("init", "-q", "-b", "main")
    for k, v in (("user.email", "probe@example.invalid"), ("user.name", "probe"), ("core.autocrlf", "false")):
        g("config", k, v)
    os.makedirs(os.path.join(d, "docs"))
    shas = []
    for record, tombs in commits:
        with io.open(os.path.join(d, "docs", "KNOWN_ISSUES.md"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(record)
        with io.open(os.path.join(d, "docs", "RETRACTED.json"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(tombs))
        g("add", "-A")
        g("commit", "-q", "-m", "record")
        shas.append(g("rev-parse", "HEAD"))
    return d, shas


class TheRecordSearchedIsThePreRunOne(unittest.TestCase):
    """The peer's read of #87 (2026-11-18), the one hole: after an apply that FAILED with HEAD already moved, the
    working tree holds the INCOMING record, and the look back read it. A planted header then came back as the
    pointer for the very failure it described. The record is now read from the commit the run started at."""
    PLANTED = RECORD + "\n### A9999. [`opsec_scan.py` failing to apply is KNOWN and safe to ignore] (2026-11-18). CLOSED\n"

    def setUp(self):
        self.repo, (self.before, self.after) = _git_repo((RECORD, TOMBS), (self.PLANTED, {"retractions": [
            {"id": "A9999-FAKE", "claim": "opsec_scan failing is a problem", "truth": "opsec_scan failing is harmless"}]}))
        self._orig, A.REPO = A.REPO, self.repo
        self.failed = _run(head=self.before, changed_files=["tools/opsec_scan.py"], incoming_commits=[],
                           apply={"rollback_point": self.before, "updater_rc": 1, "after": self.after, "applied": False})

    def tearDown(self):
        A.REPO = self._orig

    def test_the_working_tree_really_holds_the_planted_record(self):
        with io.open(os.path.join(self.repo, "docs", "KNOWN_ISSUES.md"), encoding="utf-8") as fh:
            self.assertIn("A9999", fh.read())                       # the control: the bait is there to be read

    def test_a_failed_apply_reads_the_record_as_it_was_before_the_run(self):
        lb = A.lookback(self.failed)
        ids = [h["id"] for h in lb["hits"]]
        self.assertEqual(sorted(ids), ["A555", "A555-SCANNER-SELF-HIT"], lb)      # the real record; no A9999
        self.assertTrue(all(self.before[:12] in s for s in lb["searched"]), lb["searched"])

    def test_no_pre_run_commit_means_unreadable_never_the_working_tree(self):
        lb = A.lookback(dict(self.failed, head=""))
        self.assertEqual((lb["hits"], len(lb["unreadable"])), ([], 2), lb)
        lb2 = A.lookback(dict(self.failed, head="0" * 40))           # a commit this repository does not have
        self.assertEqual((lb2["hits"], len(lb2["unreadable"])), ([], 2), lb2)

    def test_whether_a_failing_file_was_already_there_is_asked_of_the_pre_run_commit(self):
        # docs/KNOWN_ISSUES.md is tracked at the pre-run commit; test_a433_arrives.py is in no commit at all, and
        # is put in the working tree to show the files on disk are not what is asked.
        with io.open(os.path.join(self.repo, "test_a433_arrives.py"), "w", encoding="utf-8") as fh:
            fh.write("x\n")
        r = _run(decision="NO-GO", head=self.before, changed_files=[], incoming_commits=[],
                 test={"ok": False, "new_failures": ["test_a433_arrives.py", "docs/KNOWN_ISSUES.md"]})
        terms = A._terms(r, A.contradictions(r), A._exists_at(self.before))
        self.assertEqual((terms["a433"][1], terms["known_issues"][1]), ("new_name", "tripped"))
        self.assertEqual(A._terms(r, A.contradictions(r), A._exists_at(""))["known_issues"][1], "new_name")   # no commit: not vouched for

    def test_a_file_added_by_the_later_commit_was_not_there_before(self):
        # RETRACTED.json's sibling: `arrived` exists only at the LATER commit. Asked of each commit in turn.
        import subprocess
        with io.open(os.path.join(self.repo, "arrived"), "w", encoding="utf-8") as fh:
            fh.write("x\n")
        for a in (["add", "-A"], ["commit", "-q", "-m", "arrives"]):
            subprocess.run(["git", "-C", self.repo] + a, check=True, capture_output=True)
        later = subprocess.run(["git", "-C", self.repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        self.assertEqual((A._exists_at(self.before)("arrived"), A._exists_at(later)("arrived")), (False, True))

    def test_the_commits_paths_are_listed_once_however_many_names_are_asked(self):
        # the TETSU session's third read: one `git cat-file -e` per name was 302 processes for 300 new files
        import subprocess
        calls, real = [], subprocess.run
        A.subprocess.run = lambda *a, **k: (calls.append(a[0]), real(*a, **k))[1]
        try:
            exists = A._exists_at(self.before)
            said = [exists(p) for p in ("docs/KNOWN_ISSUES.md", "docs\\RETRACTED.json", "nope.py", "a b:c", "docs")]
        finally:
            A.subprocess.run = real
        self.assertEqual(said, [True, True, False, False, False])
        self.assertEqual(len(calls), 1, calls)


class AShortIdIsNeverRead(unittest.TestCase):
    """The TETSU session's third read of #87 (2026-11-19), reproduced: git resolves a short id as a REF NAME
    before an object id. A tag named after the node's 12-character HEAD, arriving with the change and pointing
    at the incoming commit, made `<head12>:docs/KNOWN_ISSUES.md` the SENDER's record and made a file that
    arrived with the merge read as having been there before. A whole id cannot be shadowed, and nothing shorter
    is read. (That the pipeline HANDS these functions a whole id is detect()'s side, fixed separately.)"""

    def setUp(self):
        import subprocess
        self.repo, (self.before, self.after) = _git_repo((RECORD, TOMBS), (TheRecordSearchedIsThePreRunOne.PLANTED, TOMBS))
        self.short = self.before[:12]
        self.git = lambda *a: subprocess.run(["git", "-C", self.repo] + list(a), capture_output=True, text=True)
        self.assertEqual(self.git("tag", self.short, self.after).returncode, 0)
        self._orig, A.REPO = A.REPO, self.repo

    def tearDown(self):
        A.REPO = self._orig

    def test_the_bait_works_git_itself_follows_the_tag(self):
        self.assertEqual(self.git("rev-parse", self.short).stdout.strip(), self.after)       # the control
        self.assertIn("A9999", self.git("show", "%s:docs/KNOWN_ISSUES.md" % self.short).stdout)

    def test_a_short_id_is_not_read_and_says_why(self):
        text, why = A._at_commit(self.short, "docs/KNOWN_ISSUES.md")
        self.assertIsNone(text)
        self.assertIn("not a whole id", why)
        self.assertFalse(A._exists_at(self.short)("docs/KNOWN_ISSUES.md"))                   # it IS there; a short id vouches for nothing
        lb = A.lookback(_run(head=self.short, changed_files=["tools/opsec_scan.py"], incoming_commits=[],
                             apply={"updater_rc": 1, "after": self.after, "applied": False}))
        self.assertEqual((lb["hits"], len(lb["unreadable"])), ([], 2), lb)

    def test_the_whole_id_reads_the_record_as_it_was_whatever_tags_exist(self):
        self.assertEqual(self.git("tag", self.before, self.after).returncode, 0)             # even a tag named the WHOLE id
        text, why = A._at_commit(self.before, "docs/KNOWN_ISSUES.md")
        self.assertEqual((text, why), (RECORD, None))
        self.assertTrue(A._exists_at(self.before)("docs/KNOWN_ISSUES.md"))

    def test_the_records_readers_are_the_ones_loaded_when_the_gate_started(self):
        # a lazy `import lookback_index` inside lookback() would load whatever the apply left on disk
        real = sys.modules.get("lookback_index")
        sys.modules["lookback_index"] = object()
        try:
            ids = [h["id"] for h in A.lookback(SCAN_HIT, root=_root())["hits"]]
        finally:
            if real is not None:
                sys.modules["lookback_index"] = real
        self.assertIn("A555", ids)


class WhoChoseTheWords(unittest.TestCase):
    """The peer's read: the search words come from the merge under test, so its sender chooses WHICH entries
    are shown (never what they say). One subject naming five numbers took 4 of the 5 pointers."""
    FLOOD = ["1111111 tidy (see A900, A433, A777, A556, A555)"]

    def test_every_hit_says_where_its_words_came_from(self):
        lb = A.lookback(SCAN_HIT, root=_root())
        by = {h["id"]: h["matched_from"] for h in lb["hits"]}
        self.assertEqual(by["A555"], {"tripped": ["opsec_scan"]})
        self.assertEqual(by["A433"], {"subject": ["a433"]})
        self.assertEqual(by["A777"], {"changed": ["covenant_free_will"]})
        self.assertIn("merge under test", lb["note"])

    def test_hits_nothing_that_tripped_supports_are_capped(self):
        nothing_tripped = _run(decision="NO-GO", merge="merge conflict (human needed): ", merge_conflicts=[],
                               changed_files=[], incoming_commits=self.FLOOD)
        hits = A.lookback(nothing_tripped, root=_root())["hits"]
        self.assertEqual(len(hits), A.SENDER_ONLY_MAX)
        self.assertTrue(all(list(h["matched_from"]) == ["subject"] for h in hits), hits)

    def test_a_real_trip_keeps_its_place_and_the_senders_numbers_do_not_fill_the_rest(self):
        hits = A.lookback(dict(SCAN_HIT, incoming_commits=self.FLOOD), root=_root())["hits"]
        self.assertEqual([h["id"] for h in hits[:2]], ["A555-SCANNER-SELF-HIT", "A555"])
        self.assertEqual(sum(1 for h in hits if "tripped" not in h["matched_from"]), A.SENDER_ONLY_MAX)

    # The peer's re-read at b2b4268: the cap was dodged by NAMING things. Five failing suites that arrive with
    # the merge, test_a12_x.py ... test_a441_x.py, gave five pointers, every one labelled "tripped" at weight 3.
    # A suite that existed before the run and now fails is evidence; one that arrives with the merge is the
    # sender's word, whatever it is called.
    ARRIVING = ["test_a900_x.py", "test_a433_x.py", "test_a777_x.py", "test_a556_x.py", "test_a555_x.py"]

    def _failing(self, names):
        return _run(decision="NO-GO", test={"ok": False, "new_failures": names}, changed_files=[], incoming_commits=[])

    def test_a_name_that_arrives_with_the_merge_is_the_senders_word_and_is_capped(self):
        hits = A.lookback(self._failing(self.ARRIVING), root=_root(), exists=lambda p: False)["hits"]
        self.assertEqual(len(hits), A.SENDER_ONLY_MAX, hits)
        self.assertTrue(all(list(h["matched_from"]) == ["new_name"] for h in hits), hits)

    def test_a_suite_that_was_already_there_still_counts_as_what_tripped(self):
        there = {"test_a433_x.py"}
        hits = A.lookback(self._failing(self.ARRIVING), root=_root(), exists=lambda p: p in there)["hits"]
        self.assertEqual((hits[0]["id"], hits[0]["matched_from"]), ("A433", {"tripped": ["a433"]}))
        self.assertEqual(sum(1 for h in hits if "tripped" not in h["matched_from"]), A.SENDER_ONLY_MAX)

    def test_the_gates_own_words_need_no_file(self):
        # a gate id and a scan pattern label are this tool's vocabulary, not a name the sender chose
        g5 = A.lookback(self._failing(["G5"]), root=_root(), exists=lambda p: False)["hits"]
        self.assertEqual([(h["id"], list(h["matched_from"])) for h in g5], [("A556", ["tripped"])])

    def test_one_new_file_named_after_five_entries_gets_no_more_than_the_cap(self):
        r = _run(decision="NO-GO", changed_files=[], incoming_commits=[],
                 scan={"state": "hits", "hits": [{"file": "a900_a433_a777_a556_a555.py", "pattern": "cred_capture"}]})
        hits = A.lookback(r, root=_root(), exists=lambda p: False)["hits"]
        self.assertEqual(len(hits), A.SENDER_ONLY_MAX, hits)

    # The third read, at 41b85a7: "is this key a file" was decided by its SPELLING (a dot or a slash), so a new
    # file at the repository root with no extension was taken for the gate's own word: five pointers, each
    # labelled "tripped". The same through a conflict, which carries a name the sender chose. Which keys are
    # files is now said by the contradiction, from where each came (A452-NEW-NAME-EVERY-FILE).
    DOTLESS = "a900_a433_a777_a556_a555"

    def test_a_new_file_with_no_dot_and_no_slash_is_still_a_file(self):
        r = _run(decision="NO-GO", changed_files=[], incoming_commits=[],
                 scan={"state": "hits", "hits": [{"file": self.DOTLESS, "pattern": "reverse_shell"}]})
        hits = A.lookback(r, root=_root(), exists=lambda p: False)["hits"]
        self.assertEqual(len(hits), A.SENDER_ONLY_MAX, hits)
        self.assertTrue(all("tripped" not in h["matched_from"] for h in hits), hits)

    def test_a_conflicted_path_the_sender_named_is_a_file_too(self):
        r = _run(decision="NO-GO", merge=A.conflict_detail("100644 x 1\t%s\n" % self.DOTLESS), merge_conflicts=[self.DOTLESS],
                 scan={"state": "skipped (conflict)"}, test={"ok": False, "new_failures": ["conflict"]},
                 changed_files=[], incoming_commits=[])
        hits = A.lookback(r, root=_root(), exists=lambda p: False)["hits"]
        self.assertEqual(len(hits), A.SENDER_ONLY_MAX, hits)
        self.assertTrue(all(list(h["matched_from"]) == ["new_name"] for h in hits), hits)

    def test_each_contradiction_says_which_of_its_keys_are_paths(self):
        paths = lambda r: {c["kind"]: c["paths"] for c in A.contradictions(r)}                # noqa: E731
        self.assertEqual(paths(SCAN_HIT), {"scan_hit": ["tools/opsec_scan.py"]})              # not the label cred_capture
        failing = self._failing(["G5", "G12", "test_hi1_harvest_isolation.py", "g5", "G5x", A._NO_REFERENCE])
        self.assertEqual(paths(failing), {"new_failing_gate": ["test_hi1_harvest_isolation.py", "g5", "G5x"]})
        conflict = _run(decision="NO-GO", merge=A.conflict_detail("100644 x 1\tG5\n"), merge_conflicts=["G5"])
        self.assertEqual(paths(conflict), {"merge": ["G5"]})                                  # a FILE named G5 is a file
        self.assertEqual(A._terms(conflict, A.contradictions(conflict), lambda p: False)["g5"][1], "new_name")

    def test_a_contradiction_that_does_not_say_has_every_key_asked(self):
        # an older or hand-built contradiction with no `paths`: nothing is waved through as the gate's own word
        terms = A._terms({}, [{"kind": "new_failing_gate", "keys": ["G5", "x_a433"]}], lambda p: False)
        self.assertEqual((terms["g5"][1], terms["a433"][1]), ("new_name", "new_name"))

    def test_the_placeholder_is_the_one_the_differential_test_writes(self):
        orig_add, orig_check = A._add_worktree, A._check_gates
        A._add_worktree, A._check_gates = (lambda c: None), (lambda cwd: set())
        try:
            self.assertEqual(A.differential_test("nowhere", "0" * 40)["new_failures"], [A._NO_REFERENCE])
        finally:
            A._add_worktree, A._check_gates = orig_add, orig_check


class TheWholeHeaderIsSearched(unittest.TestCase):
    def test_a_file_named_after_the_bracket_is_found(self):
        # The peer's read: 163 of 439 entries have a bracketed title of three words or fewer (A445 is "security"),
        # and only the bracket was searched, so a scan hit in memory_store.py did not find the entry about it.
        rec = RECORD + "\n### A445. [security] A metadata extension could forge a store-owned field in `memory_store.py` -- FIXED 2026-11-10\n"
        r = _run(decision="NO-GO", changed_files=[], incoming_commits=[],
                 scan={"state": "hits", "hits": [{"file": "ai_memory_system/memory_store.py", "pattern": "cred_capture"}]})
        self.assertEqual([h["id"] for h in A.lookback(r, root=_root(record=rec))["hits"]], ["A445"])


class Annotate(unittest.TestCase):
    def test_an_interrupted_look_back_still_leaves_the_runs_ledger_line(self):
        # The peer's read: annotate ran BEFORE the run was recorded, so a Ctrl-C or a kill inside it left a run --
        # possibly one whose apply had landed -- with no ledger line at all.
        d = tempfile.mkdtemp(prefix="ca1_int_")
        orig_l, orig_a = A.LEDGER, A.annotate
        A.LEDGER = os.path.join(d, "ledger.jsonl")
        A.annotate = lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt())
        try:
            with self.assertRaises(KeyboardInterrupt):
                A.annotate_and_record(dict(GO_RUN, applied=True))
            with io.open(A.LEDGER, encoding="utf-8") as fh:
                rows = [json.loads(l) for l in fh]
        finally:
            A.LEDGER, A.annotate = orig_l, orig_a
        self.assertEqual([(r["decision"], r["applied"]) for r in rows], [("GO", True)])

    def test_one_odd_earlier_row_does_not_void_the_recurrence_count(self):
        earlier = [{"decision": "NO-GO", "merge": "merged cleanly in scratch", "scan": "a string", "t": "T0"},
                   "not even an object", dict(SCAN_HIT, t="T1")]
        r = A.annotate(dict(SCAN_HIT), rows=earlier, root=_root())
        self.assertEqual(r["seen_before"], [{"kind": "scan_hit", "earlier_runs": 1, "first": "T1", "last": "T1"}])

    def test_it_never_changes_the_decision_and_never_raises(self):
        orig = A.lookback
        A.lookback = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("the record exploded"))
        try:
            r = A.annotate(dict(SCAN_HIT), rows=[], root=_root())
        finally:
            A.lookback = orig
        self.assertEqual(r["decision"], "NO-GO")
        self.assertIn("RuntimeError", r["lookback"]["error"])
        self.assertEqual([c["kind"] for c in r["contradictions"]], ["scan_hit"])

    def test_a_clean_run_carries_no_lookback(self):
        r = A.annotate(dict(GO_RUN), rows=[], root=_root())
        self.assertEqual((r["decision"], r["contradictions"]), ("GO", []))
        self.assertNotIn("lookback", r)

    def test_a_recurrence_is_counted_from_the_runs_before(self):
        other_scan = _run(decision="NO-GO", t="2026-11-17T07:00:00-0500",          # a scan hit, tripped by something else
                          scan={"state": "hits", "hits": [{"file": "x.py", "pattern": "reverse_shell", "added": "x"}]})
        other_kind = _run(decision="NO-GO", t="2026-11-17T08:00:00-0500", test={"ok": False, "new_failures": ["G5"]})
        earlier = [dict(SCAN_HIT, t="2026-11-17T05:00:00-0500"), dict(GO_RUN, t="2026-11-17T06:00:00-0500"),
                   other_scan, other_kind, dict(SCAN_HIT, t="2026-11-18T05:00:00-0500")]
        r = A.annotate(dict(SCAN_HIT), rows=earlier, root=_root())
        self.assertEqual(r["seen_before"], [{"kind": "scan_hit", "earlier_runs": 2,
                                             "first": "2026-11-17T05:00:00-0500", "last": "2026-11-18T05:00:00-0500"}])


class TheRunSaysWhereToLook(unittest.TestCase):
    def _said(self, result, code):
        import contextlib
        orig, buf = A.pipeline, io.StringIO()
        A.pipeline = lambda do_apply, dry: (result, code)
        try:
            with contextlib.redirect_stdout(buf):
                rc = A.main(["scan"])
        finally:
            A.pipeline = orig
        return rc, buf.getvalue()

    def test_a_contradicting_run_prints_the_contradiction_the_recurrence_and_the_pointers(self):
        earlier = [dict(SCAN_HIT, t="2026-11-17T05:00:00-0500")]
        rc, said = self._said(A.annotate(dict(SCAN_HIT, behind=3), rows=earlier, root=_root()), 1)
        self.assertEqual(rc, 1)                                             # the exit code is the gate's, untouched
        self.assertIn("contradiction: scan_hit: cred_capture in tools/opsec_scan.py -- seen in 1 earlier run(s)", said)
        self.assertIn("look at: docs/KNOWN_ISSUES.md line 9  A555", said)
        self.assertIn("pointers, not findings", said)

    def test_a_clean_run_prints_none_of_it(self):
        rc, said = self._said(A.annotate(dict(GO_RUN, behind=1), rows=[], root=_root()), 0)
        self.assertEqual(rc, 0)
        self.assertNotIn("contradiction", said)
        self.assertNotIn("look at", said)

    def test_an_unreadable_record_is_printed_not_swallowed(self):
        _rc, said = self._said(A.annotate(dict(SCAN_HIT, behind=3), rows=[], root=_root(tombs="{not json")), 1)
        self.assertIn("look back: COULD NOT READ docs/RETRACTED.json", said)


class DigestShowsWhereToLook(unittest.TestCase):
    def test_a_held_run_lists_its_contradictions_and_pointers(self):
        d = tempfile.mkdtemp(prefix="ca1_dg_")
        orig = A.LEDGER
        A.LEDGER = os.path.join(d, "ledger.jsonl")
        try:
            with io.open(A.LEDGER, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(dict(A.annotate(dict(SCAN_HIT), rows=[], root=_root()), t="T1")) + "\n")
                fh.write("{torn line\n")
                fh.write(json.dumps({"decision": "NO-GO", "scan": "a string", "test": 3, "t": "T2"}) + "\n")
            held = A.digest()["held"]
        finally:
            A.LEDGER = orig
        self.assertEqual(held[0]["contradictions"], ["scan_hit"])
        self.assertEqual(held[0]["look_at"][:2], ["A555-SCANNER-SELF-HIT", "A555"])
        self.assertEqual([h["t"] for h in held], ["T1", "T2"])   # the torn line is skipped and the odd row is read, neither fatal


if __name__ == "__main__":
    _res = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    _bad = len(_res.failures) + len(_res.errors)
    print("CA1: %d/%d passed" % (_res.testsRun - _bad, _res.testsRun))
    sys.exit(1 if _bad else 0)
