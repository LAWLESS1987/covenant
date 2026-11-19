"""CA1 -- covenant_adopt's gate is fail-closed and PROPOSE by default.

tools/covenant_adopt.py decides whether an incoming origin/main is safe to adopt (covenant-native, reusing
covenant_one's differential gate + node D's proven scan/classify patterns). This pins its gate both ways: GO
only when the diff is NORMAL, merges clean, the backdoor scan is clean, and no NEW gate fails; a HIGH
(security-sensitive) diff, a scan hit, an unclean merge, or a newly-failing gate each force NO-GO. And it pins
the two brakes that keep it safe: AUTO is OFF by default (PROPOSE-only -- a GO applies nothing without arming),
and apply refuses with no updater configured. Each NO-GO case fails if the gate stopped failing closed."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import covenant_adopt as A  # noqa: E402


class Classify(unittest.TestCase):
    def test_sensitive_paths_are_HIGH(self):
        for f in ("covenant_watchdog.py", "covenant_highway.py", "covenant_tetsu_hands.py",
                  "ops/operator_keys.json", "run_node.py", "covenant_grid_guard.py"):
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
        self.assertEqual(A.conflict_paths(detail), ["covenant_one.py", "docs/KNOWN_ISSUES.md"])
        c = A.contradictions(_run(decision="NO-GO", merge=detail, scan={"state": "skipped (conflict)"},
                                  test={"ok": False, "new_failures": ["conflict"]}))
        self.assertEqual(c[0]["keys"], ["covenant_one.py", "docs/KNOWN_ISSUES.md"])

    def test_a_ledger_line_from_before_names_its_one_path_unless_it_is_generated(self):
        old = "merge conflict (human needed): 100644 eb73e40032d02e7b012164f6293d87e987e1dfdd 1\t%s"
        self.assertEqual(A.conflict_paths(old % "covenant_one.py"), ["covenant_one.py"])
        self.assertEqual(A.conflict_paths(old % "MANIFEST.sha256"), [])
        self.assertEqual(A.conflict_paths("merged cleanly in scratch"), [])

    def test_a_long_conflict_is_counted_not_cut_silently(self):
        unmerged = "".join("100644 x 1\tf%02d.py\n" % n for n in range(11))
        detail = A.conflict_detail(unmerged)
        self.assertTrue(detail.endswith("f07.py (+3 more)"), detail)
        self.assertEqual(len(A.conflict_paths(detail)), 8)

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


class Annotate(unittest.TestCase):
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
            held = A.digest()["held"]
        finally:
            A.LEDGER = orig
        self.assertEqual(held[0]["contradictions"], ["scan_hit"])
        self.assertEqual(held[0]["look_at"][:2], ["A555-SCANNER-SELF-HIT", "A555"])
        self.assertEqual(len(held), 1)                    # the torn line is skipped, not fatal


if __name__ == "__main__":
    _res = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    _bad = len(_res.failures) + len(_res.errors)
    print("CA1: %d/%d passed" % (_res.testsRun - _bad, _res.testsRun))
    sys.exit(1 if _bad else 0)
