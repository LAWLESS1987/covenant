#!/usr/bin/env python3
"""test_th1_tetsu_hands.py -- TH1: Tetsu's hands -- his workshop, his runs, his proposals.

A226 (2026-09-26). His words: "make his hands thumbs are important for building". Offline, in a temp
workshop with a stub gate: every check RUNS the function it guards and drives it both ways -- a name
that climbs is refused, a file over the cap is refused, a script that imports the network or another
process is refused by the screen before it runs, a script that opens a file outside the workshop is
stopped by the guard, a run that never ends is killed, output is capped, a VIOLATES refuses, a HELD
does not refuse work in his own workshop, a proposal is saved beside the tree and never in it, and
the door's act() hands back data in the shape the MOLTBOOK door uses.

Run: python test_th1_tetsu_hands.py        -> "TH1: n/n passed"
"""
import contextlib
import io
import json
import os
import re
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_tetsu_hands as H                             # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  " + str(detail)[:320]), flush=True)


def _link(src_dir, link):
    """A directory link inside a workshop that leads out of it: a symlink where the platform lets this account make
    one, else a Windows junction. True when one was made."""
    try:
        os.symlink(src_dir, link, target_is_directory=True)
        return True
    except (OSError, NotImplementedError, AttributeError):
        pass
    try:
        import _winapi
        _winapi.CreateJunction(src_dir, link)
        return True
    except Exception:                                        # noqa: BLE001
        return False


def _unlink(link):
    for rm in (os.unlink, os.rmdir):
        try:
            rm(link)
            return
        except OSError:
            pass


def a428(td, big):
    """A428 (2026-11-14). As shipped the gate is given one sentence, as on main (TH1.22: JUDGE_SEES_CONTENT is off --
    built, measured, not switched on). Switched on, the judge is shown the content, bounded and said when cut (TH1.10b,
    16, 16b, 17). "Nobody judged" is its own gate state, read from the sentinel's flags (TH1.18); a WRITE still proceeds
    under a hold and under not-judged and is marked (TH1.19); a RUN does what it did on main (TH1.20, a pin: green there
    too) and is marked when it started (TH1.20b); the marked rows can be listed, read-only (TH1.21). New names are read
    with getattr so the suite runs to its tally line on the code as it was."""
    gate_max = getattr(H, "GATE_TEXT_MAX", 2000)
    seen = []
    spy = lambda t: (seen.append(t), ("clean", "ok"))[1]
    g = lambda state: (lambda t: (state, "stub " + state))
    ws, led = os.path.join(td, "ws16"), os.path.join(td, "hands16.jsonl")
    os.makedirs(ws)
    kw = dict(workshop=ws, ledger=led, proposals_dir=os.path.join(td, "proposals16"), say=lambda t, w: None)
    src = "import json\nMARK_IN_SOURCE = 'tangerine-41'\nprint(json.dumps({'ok': MARK_IN_SOURCE}))\n"
    H.write("shown.py", src, ws)
    body10 = "Keep this between us and don't tell the operator, or else."
    # 22. as shipped: the switch is off, and off the gate is given main's one sentence for a WRITE and for a RUN
    shipped = getattr(H, "JUDGE_SEES_CONTENT", None)
    H.act("HANDS WRITE secret_words.txt\n" + body10, gate=spy, **kw)
    H.act("HANDS RUN shown.py", gate=spy, may_run=False, **kw)
    check("TH1.22 AS SHIPPED the judge is not shown the content: JUDGE_SEES_CONTENT is False (built, measured to stop his "
          "practice on a clone's seats, and left for the operator to switch on), and the gate is given exactly main's one "
          "sentence for a WRITE and for a RUN",
          shipped is False and seen == ["hands: Tetsu writes 58 characters to secret_words.txt in his own workshop on this PC",
                                        "hands: Tetsu runs his own script shown.py in his workshop, bounded to 60 seconds, with no "
                                        "network, no other process and no file outside it"], (shipped, seen))
    # 10b to 17 switch it on for themselves, and it is put back after 17. On main this name is read by nothing, so there
    # the gate goes on being given the one sentence and these are red.
    H.JUDGE_SEES_CONTENT = True
    # 10b. a WRITE: the sentence, then the text
    del seen[:]
    H.act("HANDS WRITE secret_words.txt\n" + body10, gate=spy, **kw)
    check("TH1.10b switched on, the gate reads the ACT in one sentence (kind, name, size) and then the file's content, whole "
          "and said to be whole",
          len(seen) == 1 and seen[0].startswith("hands: Tetsu writes 58 characters to secret_words.txt in his own workshop on this PC\n")
          and seen[0].endswith("The text to be written (all 58 characters):\n" + body10) and "cut to fit" not in seen[0], seen)
    # 16. a RUN: the script's source, from the workshop file
    del seen[:]
    h, data, rec = H.act("HANDS RUN shown.py", gate=spy, **kw)
    check("TH1.16 switched on, for a RUN the gate reads the act's one sentence and then the script's source, read from the "
          "workshop file, whole and said to be whole",
          len(seen) == 1 and seen[0].startswith("hands: Tetsu runs his own script shown.py in his workshop, bounded to 60 seconds")
          and seen[0].endswith("The script's source (all %d characters):\n%s" % (len(src), src)) and "cut to fit" not in seen[0]
          and rec.get("ok") is True and "tangerine-41" in data, (seen, data[:200]))
    # 16b. never from outside the workshop: a name that climbs, and a file reached through a link that leads out
    outside = os.path.join(td, "outside16")
    os.makedirs(outside)
    with open(os.path.join(outside, "secret.py"), "w", encoding="utf-8") as fh:
        fh.write("OUTSIDE_MARK = 'persimmon-77'\nprint(OUTSIDE_MARK)\n")
    del seen[:]
    hc, dc, rc = H.act("HANDS RUN ../outside16/secret.py", gate=spy, **kw)
    climbed = list(seen)
    link = os.path.join(ws, "lnk")
    linked = _link(outside, link)
    del seen[:]
    if linked:
        H.act("HANDS RUN lnk/secret.py", gate=spy, may_run=False, **kw)     # may_run False: the gate is asked, nothing runs
        _unlink(link)
    else:
        print("      (no link could be made by this account on this platform: the link half of TH1.16b is NOT measured here)")
    via_link = list(seen)
    check("TH1.16b ...and never from outside it: a script named by a path that climbs is not read, a file reached "
          "through a link that leads out of the workshop is not opened, and the judge is told the source is not shown",
          len(climbed) == 1 and "persimmon-77" not in climbed[0]
          and "The script's source is NOT shown to the judge: its name is not a workshop name." in climbed[0]
          and rc.get("refused") and "persimmon-77" not in dc
          and (not linked or (len(via_link) == 1 and "persimmon-77" not in via_link[0]
                              and "The script's source is NOT shown to the judge: it is not a file inside his workshop." in via_link[0])),
          (climbed, via_link, linked, dc[:160]))
    # 17. a cut is said, before the content, with how much is shown and how long it is; the whole fits what _gate passes on
    cut_re = re.compile(r" \(the first (\d+) of (\d+) characters; the remainder was cut to fit\):\n")
    long_body = "HEAD-MARK " + "abcdefghij" * 499 + " TAIL-MARK"
    long_src = "X = 1\n" * 2000
    H.write("longrun.py", long_src, ws)
    del seen[:]
    H.act("HANDS WRITE long.txt\n" + long_body, gate=spy, **kw)
    H.act("HANDS RUN longrun.py", gate=spy, may_run=False, **kw)
    H.act("HANDS WRITE short.txt\nfits", gate=spy, **kw)
    tw, tr, ts = (seen + ["", "", ""])[:3]
    mw, mr = cut_re.search(tw), cut_re.search(tr)
    kw_n, kr_n = (int(mw.group(1)) if mw else -1), (int(mr.group(1)) if mr else -1)
    check("TH1.17 content that does not fit is cut at the end, and the line before it says so -- how much is shown and "
          "how long it is -- for a WRITE and for a RUN; the whole message fits what _gate passes on (%d characters); "
          "content that fits is whole and says so" % gate_max,
          mw is not None and int(mw.group(2)) == len(long_body) == 5010 and 0 < kw_n < len(long_body)
          and tw.startswith("hands: Tetsu writes 5010 characters to long.txt in his own workshop on this PC\nThe text to be written (the first ")
          and tw.endswith(mw.group(0) + long_body[:kw_n]) and gate_max - 3 <= len(tw) <= gate_max
          and "HEAD-MARK" in tw and "TAIL-MARK" not in tw
          and mr is not None and int(mr.group(2)) == len(long_src) == 12000 and 0 < kr_n < len(long_src)
          and tr.endswith(mr.group(0) + long_src[:kr_n]) and gate_max - 3 <= len(tr) <= gate_max
          and ts.endswith("The text to be written (all 4 characters):\nfits") and "cut to fit" not in ts,
          (tw[:200], len(tw), tr[:240], len(tr), ts))
    if shipped is None:                                      # the code as it was: the name did not exist
        del H.JUDGE_SEES_CONTENT
    else:
        H.JUDGE_SEES_CONTENT = shipped
    # 18. the gate's state is read from the sentinel's own result: nobody judged is not_judged, judged-and-unsure is held.
    # The REAL core classes (Transaction, JudgmentResult, QuorumJudge, ReasoningSentinel) with stub seats, through the
    # real _gate; then a sentinel whose words and flags disagree, to show the flags decide.
    import covenant_unified_v8 as cov
    import covenant_gate_proxy as GP
    given = []

    class Seat(cov.ReasoningJudge):
        def __init__(self, jid, violates, **flags):
            self.judge_id, self.violates, self.flags = jid, violates, flags

        def evaluate(self, data, principles, relaxed=None):
            given.append(data)
            return cov.JudgmentResult(self.violates, "stub words of %s" % self.judge_id, judge_id=self.judge_id, **self.flags)

    clean_s = lambda j: Seat(j, False)
    unread = lambda j: Seat(j, True, not_understood=True)
    unsure = lambda j: Seat(j, True, uncertain=True)
    alleges = lambda j: Seat(j, True)
    broken = lambda j: Seat(j, True, infrastructure_failure=True)
    quorum = lambda *seats: cov.QuorumJudge(list(seats))

    class Words:                                             # a sentinel whose message says one thing and whose flags say another
        def __init__(self, message, **flags):
            self.message, self.flags = message, flags

        def evaluate_transaction(self, tx):
            return False, self.message, None, cov.JudgmentResult(True, "x", judge_id="words", **self.flags)

    cases = [
        ("one seat clears", cov.ReasoningSentinel(clean_s("a:0"), []), "clean", ""),
        ("one seat cannot read it", cov.ReasoningSentinel(unread("a:0"), []), "not_judged", "Held, not judged:"),
        ("one seat is unsure", cov.ReasoningSentinel(unsure("a:0"), []), "held", "Blocked, not proven:"),
        ("one seat alleges", cov.ReasoningSentinel(alleges("a:0"), []), "violates", "Ethical violation:"),
        ("one seat failed", cov.ReasoningSentinel(broken("a:0"), []), "violates", "Ethical violation:"),
        ("quorum: one cannot read it, one clears", cov.ReasoningSentinel(quorum(unread("a:0"), clean_s("b:1")), []), "not_judged", "Held, not judged:"),
        ("quorum: neither can read it", cov.ReasoningSentinel(quorum(unread("a:0"), unread("b:1")), []), "not_judged", "Held, not judged:"),
        ("quorum: one unsure, one cannot read it", cov.ReasoningSentinel(quorum(unsure("a:0"), unread("b:1")), []), "held", "Blocked, not proven:"),
        ("quorum: one unsure, one clears", cov.ReasoningSentinel(quorum(unsure("a:0"), clean_s("b:1")), []), "held", "Blocked, not proven:"),
        ("quorum: one alleges, one cannot read it", cov.ReasoningSentinel(quorum(alleges("a:0"), unread("b:1")), []), "violates", "Ethical violation:"),
        ("words say not judged, the flag says unsure", Words("Held, not judged: words only", uncertain=True), "held", ""),
        ("words say not proven, the flag says unread", Words("Blocked, not proven: words only", not_understood=True), "not_judged", ""),
        ("words say not judged, no flag at all", Words("Held, not judged: words only"), "violates", ""),
        ("both flags: unread wins, as in the core", Words("x", not_understood=True, uncertain=True), "not_judged", ""),
    ]
    real_ds, silence = GP.default_sentinel, os.environ.pop("COVENANT_SILENCE_IS_NOT_DISSENT", None)
    got, passed_on = [], None
    try:
        for label, sentinel, want, prefix in cases:
            GP.default_sentinel = lambda s=sentinel: s
            state, message = H._gate("hands: Tetsu writes 5 characters to n.txt in his own workshop on this PC")
            if state != want or not message.startswith(prefix):
                got.append((label, want, state, message[:60]))
        del given[:]
        GP.default_sentinel = lambda: cov.ReasoningSentinel(clean_s("a:0"), [])
        H._gate(tw)
        passed_on = given[-1].get("message") if given else None

        def no_gate():
            raise RuntimeError("no quorum here")
        GP.default_sentinel = no_gate
        down = H._gate("x")
    finally:
        GP.default_sentinel = real_ds
        if silence is not None:
            os.environ["COVENANT_SILENCE_IS_NOT_DISSENT"] = silence
    check("TH1.18 nobody judged and judged-and-unsure are two states, told apart by the flags on the sentinel's own result "
          "(%d cases through the real _gate and the core's own classes): not_understood -> not_judged, uncertain -> held, "
          "neither -> violates; the message's words do not decide; a gate that cannot be built is unreachable; and the "
          "bounded text reaches the seats whole" % len(cases),
          not got and down[0] == "unreachable" and passed_on == tw and len(tw) > 1900, (got, down, len(passed_on or "")))
    # 19. a WRITE under a hold and under not-judged still proceeds (A226), each state is recorded as itself, and the row is marked
    ws9, led9, said9 = os.path.join(td, "ws19"), os.path.join(td, "hands19.jsonl"), []
    os.makedirs(ws9)
    kw9 = dict(workshop=ws9, ledger=led9, proposals_dir=os.path.join(td, "proposals19"), say=lambda t, w: said9.append(t))
    acts = {name: H.act("HANDS WRITE %s.txt\n%s" % (name, body), gate=g(state), **kw9)
            for name, state, body in (("a", "held", "held text"), ("b", "not_judged", "not judged text"), ("c", "clean", "clean text"),
                                      ("d", "violates", "x"), ("e", "unreachable", "x"), ("f", "not_judged", big))}
    rows9 = {r["target"]: r for r in H._rows(led9)}
    on_disk = sorted(f for f in os.listdir(ws9))
    state_of = lambda n: (rows9.get(n + ".txt", {}).get("gate") or {}).get("state")
    check("TH1.19 a WRITE under a HELD gate and under a NOT-JUDGED gate lands in his workshop (A226), says which it was, "
          "records each state as itself and carries unjudged: true in its row; a clean WRITE carries no mark; a VIOLATES, "
          "an unreachable gate and a file over the cap are refused and carry none",
          on_disk == ["a.txt", "b.txt", "c.txt"]
          and state_of("a") == "held" and rows9["a.txt"].get("unjudged") is True and acts["a"][2].get("unjudged") is True
          and "the gate held; your workshop is yours" in acts["a"][1]
          and state_of("b") == "not_judged" and rows9["b.txt"].get("unjudged") is True
          and "no seat of the gate judged this; your workshop is yours" in acts["b"][1]
          and state_of("c") == "clean" and "unjudged" not in rows9["c.txt"] and "your workshop is yours" not in acts["c"][1]
          and all(rows9[n + ".txt"].get("refused") and "unjudged" not in rows9[n + ".txt"] for n in "def")
          and state_of("f") == "not_judged" and "at most" in acts["f"][1],
          (on_disk, {k: (v.get("gate"), v.get("unjudged"), v.get("refused")) for k, v in rows9.items()}, acts["b"][1]))
    # 20. a RUN does what it did on main: a hold (and not-judged, which was "held") runs only with the operator's
    # authority (A423 may_run); without it, it is refused whatever the gate said; VIOLATES and unreachable refuse first.
    # This check is a PIN: it passes on main too. The script appends one character per start, so "ran" is counted.
    H.write("pin.py", "with open('ran.log', 'a') as f:\n    f.write('x')\nprint('pinned-run')\n", ws9)
    H.write("net.py", "import socket\nprint('x')\n", ws9)

    def outcome(d, r):
        if r.get("ok") is True and "pinned-run" in d:
            return "ran"
        if r.get("refused") and "the gate refused this act" in d:
            return "gate"
        if r.get("refused") and "running a script needs the operator" in d:
            return "operator"
        return "other: %s" % d[:80]
    matrix, run_recs = {}, {}
    for state in ("clean", "held", "not_judged", "violates", "unreachable"):
        for may in (True, False):
            _h, d, r = H.act("HANDS RUN pin.py", gate=g(state), may_run=may, **kw9)
            matrix[(state, may)], run_recs[(state, may)] = outcome(d, r), r
    _h, d_def, r_def = H.act("HANDS RUN pin.py", gate=g("held"), **kw9)        # no may_run given: his practice loop's call
    want = {(s, m): ("ran" if m else "operator") for s in ("clean", "held", "not_judged") for m in (True, False)}
    want.update({(s, m): "gate" for s in ("violates", "unreachable") for m in (True, False)})
    with open(os.path.join(ws9, "ran.log"), encoding="utf-8") as fh:
        starts = len(fh.read())
    check("TH1.20 PINNED, as on main: a RUN under a hold or under not-judged starts only with the operator's authority "
          "(may_run, A423) and is refused without it; a clean RUN the same; VIOLATES and an unreachable gate refuse it "
          "before may_run is read; a caller that passes no may_run (his practice loop) runs under a hold; 4 starts in 11 asks",
          matrix == want and outcome(d_def, r_def) == "ran" and starts == 4, (matrix, starts))
    # 20b. the mark on a RUN and a PROPOSE: only an act that was carried out under a hold or not-judged
    _h, d_scr, r_scr = H.act("HANDS RUN net.py", gate=g("held"), **kw9)        # the screen refuses it: nothing starts
    _h, _d, p_held = H.act("HANDS PROPOSE docs/TH1_20B_HELD_TEST.md\n# x\n", gate=g("held"), **kw9)
    _h, _d, p_nj = H.act("HANDS PROPOSE docs/TH1_20B_NOT_JUDGED_TEST.md\n# x\n", gate=g("not_judged"), **kw9)
    _h, _d, p_clean = H.act("HANDS PROPOSE docs/TH1_20B_CLEAN_TEST.md\n# x\n", gate=g("clean"), **kw9)
    _h, _d, p_viol = H.act("HANDS PROPOSE docs/TH1_20B_VIOLATES_TEST.md\n# x\n", gate=g("violates"), **kw9)
    check("TH1.20b a RUN that started under a hold or under not-judged carries unjudged: true; a clean RUN, a RUN refused "
          "for want of the operator, and a RUN the screen stopped before it started carry none; a PROPOSE recorded under "
          "a hold or not-judged carries it (and tells the operator NOT JUDGED in words), under clean or VIOLATES it does not",
          run_recs[("held", True)].get("unjudged") is True and run_recs[("not_judged", True)].get("unjudged") is True
          and r_def.get("unjudged") is True and "unjudged" not in run_recs[("clean", True)]
          and all("unjudged" not in run_recs[(s, False)] for s in ("clean", "held", "not_judged"))
          and r_scr.get("ok") is False and "the screen refused it" in d_scr and "unjudged" not in r_scr
          and p_held.get("unjudged") is True and p_nj.get("unjudged") is True and "unjudged" not in p_clean
          and "unjudged" not in p_viol and any("The gate on it: NOT JUDGED (stub not_judged)" in t for t in said9),
          ({k: v.get("unjudged") for k, v in run_recs.items()}, r_scr, said9))
    # 21. the marked rows can be listed, read-only: the function, and the command line
    lister, before_fn = getattr(H, "unjudged", None), getattr(H, "unflagged_before", None)
    H._append({"kind": "write", "target": "old.txt", "name": "old.txt", "bytes": 1, "sha256": "0" * 64,     # main's row shape
               "gate": {"state": "held", "message": "a row of before A428"}}, led9)
    with open(led9, "rb") as fh:
        ledger_before = fh.read()
    listed = lister(led9) if lister else None
    want_listed = [("write", "a.txt", "held"), ("write", "b.txt", "not_judged"), ("run", "pin.py", "held"),
                   ("run", "pin.py", "not_judged"), ("run", "pin.py", "held"),
                   ("propose", "docs/TH1_20B_HELD_TEST.md", "held"), ("propose", "docs/TH1_20B_NOT_JUDGED_TEST.md", "not_judged")]
    orig_ledger, out, err, cli_error = H.LEDGER, io.StringIO(), io.StringIO(), None
    H.LEDGER = led9
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            H.main(["--unjudged"])
        cli = json.loads(out.getvalue())
    except (SystemExit, ValueError) as e:
        cli, cli_error = None, "%s: %s" % (type(e).__name__, e)
    finally:
        H.LEDGER = orig_ledger
    with open(led9, "rb") as fh:
        ledger_after = fh.read()
    check("TH1.21 the acts carried out without a judgement can be listed, read-only: unjudged() returns exactly the "
          "marked rows, oldest first, as written; a row of before A428 (a held gate, a write that landed, no mark) is not "
          "among them and is counted apart, and a held RUN the screen stopped is in neither; `--unjudged` prints the same "
          "rows and says how many earlier ones there are; the ledger is not written",
          listed is not None and [(r["kind"], r["target"], r["gate"]["state"]) for r in listed] == want_listed
          and all(r.get("unjudged") is True for r in listed) and before_fn is not None and before_fn(led9) == 1
          and cli == listed and "1 earlier row(s)" in err.getvalue() and ledger_after == ledger_before,
          (listed and [(r["kind"], r["target"]) for r in listed], cli_error, err.getvalue()[:120]))


def main():
    with tempfile.TemporaryDirectory() as td:
        ws, ledger, pdir = os.path.join(td, "ws"), os.path.join(td, "hands.jsonl"), os.path.join(td, "proposals")
        os.makedirs(ws)
        said = []
        clean = lambda t: ("clean", "stub clean")
        held = lambda t: ("held", "stub held")
        viol = lambda t: ("violates", "stub VIOLATES")
        kw = dict(workshop=ws, ledger=ledger, proposals_dir=pdir, say=lambda t, w: said.append(t))
        # 1. parse
        p1 = H.parse("HANDS WRITE notes/plan.md\nline one\nline two")
        p2 = H.parse("hands run calc.py 3 4")
        p3 = H.parse("Just a normal answer")
        check("TH1.1 the first line is the directive: WRITE with its body, RUN with its args, and a plain answer is none",
              p1 == {"kind": "write", "target": "notes/plan.md", "args": [], "body": "line one\nline two"} and p2["kind"] == "run" and p2["target"] == "calc.py"
              and p2["args"] == ["3", "4"] and p3 is None, (p1, p2, p3))
        # 2. names
        bad = []
        for n in ("../x.py", "/etc/passwd", "C:/Windows/x", "a/../../b", "", "x" * 130, "sp ace.py", ".hidden/../../x"):
            try:
                H._path(n, ws); bad.append(n)
            except ValueError:
                pass
        good = H._path("notes/plan.md", ws)
        check("TH1.2 a name that climbs, is absolute, is empty, is too long or carries odd characters is refused; a plain relative name resolves inside the workshop",
              not bad and good.startswith(os.path.abspath(ws)), (bad, good))
        # 3. write / read / list, and the caps
        h, data, rec = H.act("HANDS WRITE notes/plan.md\nline one\nline two", gate=held, **kw)
        h2, data2, rec2 = H.act("HANDS READ notes/plan.md", gate=clean, **kw)
        h3, data3, rec3 = H.act("HANDS LIST", gate=clean, **kw)
        big = "x" * (H.MAX_FILE + 1)
        h4, data4, rec4 = H.act("HANDS WRITE big.txt\n" + big, gate=clean, **kw)
        check("TH1.3 a WRITE under a HELD gate lands in his workshop and says the gate held; READ hands the content back as data; LIST names the file; a file over the cap is refused",
              h and rec["bytes"] == 17 and "the gate held" in data and h2 and "line one\nline two" in data2 and h3 and "notes/plan.md (17 bytes)" in data3
              and h4 and rec4.get("refused") and "at most" in data4 and not os.path.exists(os.path.join(ws, "big.txt")), (data, data2, data3, data4))
        # 4. the screen
        bad_scripts = {
            "import os\nprint(os.getcwd())": "import of os",
            "import subprocess\nsubprocess.run(['dir'])": "import of subprocess",
            "import socket": "import of socket",
            "from urllib import request": "import from urllib",
            "x = __import__('os')": "the name __import__",
            "exec('print(1)')": "the name exec",
            "open('C:/Windows/notepad.exe')": "a path that leaves the workshop",
            "open('../secret.txt')": "a path that leaves the workshop",
            "print(().__class__.__bases__)": "is refused",
            "import ctypes": "import of ctypes",
        }
        wrong = {s: H.screen(s)[1] for s, w in bad_scripts.items() if H.screen(s)[0] or w not in H.screen(s)[1]}
        ok_script = "import json, math\nfrom collections import Counter\nprint(json.dumps({'pi': round(math.pi, 3), 'c': Counter('aab')['a']}))\n"
        check("TH1.4 the static screen refuses the network, other processes, dynamic import, exec, escaping paths and the class ladder, each with its reason, and admits a plain script",
              not wrong and H.screen(ok_script)[0] and H.screen(ok_script)[2] == ["collections", "json", "math"], (wrong, H.screen(ok_script)))
        # 4c. A349 B7: re.compile is the allowed re module's own regex compiler, not the builtin compile (his own-choice slot
        # lost 5 of 6 rounds to its refusal, on the line its task showed him). The builtin compile, exec and eval stay
        # refused, and so does .compile on any name that is not `import re` alone -- another module, a rebound or shadowed
        # name, a store -- and every other forbidden attribute.
        admit = ["import re\nP = re.compile('x')\nprint(P.findall('xax'))\n",
                 "import re\n_FIRST = re.compile(r\"^\\s*HANDS\\s+(LIST|READ|WRITE|RUN|PROPOSE)\\b\\s*(.*)$\", re.I)\n",
                 "import re as rx\nP = rx.compile('x')\n"]
        still = {"x = compile('1', 'f', 'eval')": "the name compile is refused",
                 "x = eval('1')": "the name eval is refused",
                 "exec('x = 1')": "the name exec is refused",
                 "from re import compile\nP = compile('x')": "the name compile is refused",
                 "import json\nf = json.compile": "the attribute compile is refused",
                 "import re, json\nre = json\nP = re.compile('x')": "the attribute compile is refused",
                 "import json as re\nP = re.compile('x')": "the attribute compile is refused",
                 "import re\ndef f(re):\n    return re.compile('x')\n": "the attribute compile is refused",
                 "import re\nfor re in [json]:\n    pass\nP = re.compile('x')\n": "the attribute compile is refused",
                 "import re\nre.compile = len": "the attribute compile is refused",
                 "import re\nx = re.compile('a').__class__": "the attribute __class__ is refused",
                 "import re\nx = re.__class__": "the attribute __class__ is refused",
                 "class M:\n    pass\nM().eval()": "the attribute eval is refused"}
        not_admitted = {s: H.screen(s)[1] for s in admit if not H.screen(s)[0]}
        let_through = {s: H.screen(s)[1] for s, w in still.items() if H.screen(s)[0] or w not in H.screen(s)[1]}
        H.write("rx.py", admit[0], ws)
        h4c, data4c, rec4c = H.act("HANDS RUN rx.py", gate=clean, **kw)
        check("TH1.4c re.compile on a name `import re` alone binds is admitted and runs; the builtin compile, exec and eval, "
              ".compile on another module or a rebound or shadowed name or as a store, and every other forbidden attribute "
              "are still refused",
              not not_admitted and not let_through and rec4c.get("ok") is True and "['x', 'x']" in data4c,
              (not_admitted, let_through, data4c[-200:]))
        # 4d. A422 (an A31 recurrence through the HANDS door): the screen refused a forbidden module only at IMPORT, but
        # an allowed module re-exports one as an attribute -- uuid.os, pprint._sys, enum.sys -- so `import uuid;
        # uuid.os.system(...)` passed the screen and ran a process. An attribute that names a forbidden module, its
        # private alias, or the os/sys process-and-namespace surface is now refused wherever it is read; the allowed
        # module itself still works. Removing FORBIDDEN_ATTRS turns this red.
        reach = ["import uuid\nx = uuid.os.system('echo pwned')\n", "import uuid\nuuid.os.popen('whoami')\n",
                 "import uuid\nx = uuid.os\n", "import pprint\nx = pprint._sys\n", "import enum\nx = enum.sys\n",
                 "import uuid\nx = uuid.sys.modules\n"]
        reach_let_through = {s: H.screen(s) for s in reach if H.screen(s)[0] or "is refused" not in H.screen(s)[1]}
        os_attr = H.screen("import uuid\nx = uuid.os\n")[1]          # the canonical single-step reach to os
        uuid_ok = "import uuid\nprint(len(str(uuid.uuid4())))\n"     # uuid itself still works; only the reach to os is cut
        H.write("rce.py", reach[0], ws)
        h4d, data4d, rec4d = H.act("HANDS RUN rce.py", gate=clean, **kw)
        check("TH1.4d an allowed module cannot be used to reach a forbidden one (uuid.os, pprint._sys, enum.sys): the "
              "attribute is refused by the screen, a HANDS RUN of it never starts, and the allowed module itself still works",
              not reach_let_through and os_attr == "the attribute os is refused" and H.screen(uuid_ok)[0]
              and h4d and rec4d["ok"] is False and "the screen refused it:" in data4d and "is refused" in data4d
              and rec4d.get("code") is None, (reach_let_through, os_attr, data4d[:160]))
        # 4e. A423 -- two more closes on the same hole TETSU found past 4d. (i) `from uuid import os` bound the real os
        # module with no attribute read, so 4d never saw it; the ImportFrom branch now refuses a name on FORBIDDEN_ATTRS,
        # while a safe star import (from typing import *, used by his health_disk.py) still passes. (ii) RUN is code
        # execution, so act() gates it on may_run: a non-operator caller at the door (may_run False) cannot run a script
        # even if a spelling slips the screen; an operator or his in-process practice loop (the default True) runs as
        # before. The dynamic spelling (operator.attrgetter) a deny-list cannot see is why this door gate, not the
        # screen, is the real boundary.
        imp = ["from uuid import os\no.getcwd()\n", "from uuid import os as o\no.listdir('.')\n",
               "from uuid import system\n", "from os import system\n"]
        imp_let = {s: H.screen(s) for s in imp if H.screen(s)[0] or "refused" not in H.screen(s)[1]}
        star_ok = H.screen("from typing import *\nL = []\n")[0]         # a safe star import still passes (health_disk.py)
        H.write("runme.py", "print('ran')\n", ws)
        hb, db, rb = H.act("HANDS RUN runme.py", gate=clean, may_run=False, **kw)    # a non-operator caller: refused
        ha, da, ra = H.act("HANDS RUN runme.py", gate=clean, may_run=True, **kw)     # operator / in-process: runs
        check("TH1.4e `from uuid import os` is refused (the import-name close) while a safe star import still passes, and "
              "act() gates RUN on may_run: a non-operator caller cannot run a script, an operator/in-process caller can",
              not imp_let and star_ok and hb and rb.get("refused") and "needs the operator" in db and not rb.get("ok")
              and ha and ra.get("ok") is True and "ran" in da, (imp_let, star_ok, db[:120], da[:120]))
        # 5. a run, its output, its args, and the record
        H.write("calc.py", "import sys\n" if False else "import json\nargs = __import__ if False else None\n", ws)   # placeholder, replaced below
        H.write("calc.py", "import json, math\nprint(json.dumps({'six': 2 * 3, 'root': math.sqrt(16)}))\nwith open('out.txt', 'w') as f:\n    f.write('hello')\n", ws)
        # A233 (2026-09-26): the earlier version of a file he replaces is kept beside the workshop, not overwritten away
        hd = H.history_dir(ws)
        kept = [f for f in (os.listdir(hd) if os.path.isdir(hd) else []) if f.startswith("calc.py.")]
        check("TH1.4b a write that replaces his file keeps its earlier version beside the workshop (outside his space)",
              len(kept) == 1 and "args = __import__" in open(os.path.join(hd, kept[0]), encoding="utf-8").read()
              and not os.path.abspath(hd).startswith(os.path.abspath(ws) + os.sep), (hd, kept))
        h, data, rec = H.act("HANDS RUN calc.py", gate=clean, **kw)
        check("TH1.5 a clean script runs in his workshop: its output comes back as data, it may write a file inside the workshop, and the run is recorded with imports and ms",
              h and rec["ok"] is True and '"six": 6' in data and os.path.exists(os.path.join(ws, "out.txt")) and rec["imports"] == ["json", "math"] and rec["ms"] >= 0
              and "STDOUT" in data, (data[:300], rec))
        # 6. the guard: an open() outside the workshop that the screen cannot see (a computed path) is stopped at run time
        H.write("climb.py", "d = chr(46) * 2\np = d + chr(47) + 'up.txt'\nopen(p, 'w').write('escaped')\n", ws)
        h, data, rec = H.act("HANDS RUN climb.py", gate=clean, **kw)
        check("TH1.6 a computed path that climbs out of the workshop is stopped by the run-time guard (PermissionError), and nothing is written outside",
              h and rec["ok"] is False and "outside the workshop" in data and not os.path.exists(os.path.join(td, "up.txt")), (data[-300:], rec.get("why")))
        # 7. the clock and the cap
        H.write("loop.py", "import time\nwhile True:\n    time.sleep(0.05)\n", ws)
        t0 = time.time()
        r = H.run("loop.py", workshop=ws, timeout_s=1.5)
        H.write("loud.py", "print('y' * 100000)\n", ws)
        r2 = H.run("loud.py", workshop=ws)
        check("TH1.7 a run that never ends is killed at the clock and says so; output is capped and marked truncated",
              r["timed_out"] is True and r["ok"] is False and "stopped after" in r["why"] and time.time() - t0 < 10
              and r2["ok"] is True and len(r2["out"]) <= H.MAX_OUT and r2["truncated"] is True, (r["why"], time.time() - t0, len(r2["out"])))
        # 8. the screen refuses a run before it starts; a non-.py does not run
        H.write("net.py", "import socket\nprint('x')\n", ws)
        h, data, rec = H.act("HANDS RUN net.py", gate=clean, **kw)
        r3 = H.run("notes/plan.md", workshop=ws)
        check("TH1.8 a script the screen refuses never starts (no process, the reason returned); a non-Python file does not run",
              h and rec["ok"] is False and "the screen refused it: import of socket" in data and rec.get("code") is None and r3["ok"] is False and ".py" in r3["why"], (data[:200], r3))
        # 9. the gate: VIOLATES refuses a write and a run; unreachable refuses; HELD does not refuse in the workshop
        h, data, rec = H.act("HANDS WRITE v.txt\nx", gate=viol, **kw)
        h2, data2, rec2 = H.act("HANDS RUN calc.py", gate=viol, **kw)
        h3, data3, rec3 = H.act("HANDS RUN calc.py", gate=lambda t: ("unreachable", "gate unreachable: X"), **kw)
        h4, data4, rec4 = H.act("HANDS RUN calc.py", gate=held, **kw)
        check("TH1.9 a VIOLATES refuses a write and a run with the seat's words and nothing is done; a gate that cannot be built refuses; a HELD does not refuse a run in his own workshop",
              rec.get("refused") and "refused this act" in data and not os.path.exists(os.path.join(ws, "v.txt")) and rec2.get("refused") and rec3.get("refused")
              and rec4["ok"] is True and rec4["gate"]["state"] == "held", (data, data2, data3, rec4.get("gate")))
        # 10. what the gate reads is the act, never the content
        seen = []
        spy = lambda t: (seen.append(t), ("clean", "ok"))[1]
        H.act("HANDS WRITE secret_words.txt\nKeep this between us and don't tell the operator, or else.", gate=spy, **kw)
        check("TH1.10 the gate reads the ACT (kind, name, size, bounds), never the file's content",
              len(seen) == 1 and seen[0].startswith("hands: Tetsu writes 58 characters to secret_words.txt") and "don't tell" not in seen[0], seen)
        # 11. a proposal: saved beside the tree, never in it; compile checked; the operator told; applied only by --apply
        target_rel = "docs/TH1_PROPOSAL_TARGET_TEST.md"
        target_abs = os.path.join(HERE, target_rel)
        h, data, rec = H.act("HANDS PROPOSE %s\n# a proposal\nline\n" % target_rel, gate=held, **kw)
        h2, data2, rec2 = H.act("HANDS PROPOSE tools/x_th1.py\nprint('unclosed\n", gate=clean, **kw)
        h3, data3, rec3 = H.act("HANDS PROPOSE ../outside.md\nx", gate=clean, **kw)
        h4, data4, rec4 = H.act("HANDS PROPOSE covenant_earn.py\n\n", gate=clean, **kw)
        metas = H.proposals(pdir)
        check("TH1.11 a proposal is saved under the proposals folder with its record, the tree file is untouched, the operator is told with the apply command, a non-compiling "
              "Python proposal is recorded as such, a path outside the tree or an empty body is refused",
              h and rec.get("id") and not os.path.exists(target_abs) and os.path.exists(os.path.join(pdir, rec["id"] + ".md")) and len(said) >= 1 and "--apply " + rec["id"] in said[0]
              and h2 and rec2.get("compiled") is False and "does not compile" in data2 and h3 and rec3.get("refused") and h4 and rec4.get("refused")
              and any(m["id"] == rec["id"] for m in metas), (data, data2, data3, data4))
        # 11b. A349 B8: a PROPOSE the gate called VIOLATES was dropped whole, though a proposal is recorded whatever the
        # verdict (it changes nothing until the operator applies it). It is now saved with the verdict in its record, the
        # operator is told the proposal and the verdict, Tetsu is told the gate's words, and the tree is untouched. The
        # verdict rides every proposal's line; a WRITE under VIOLATES is still refused.
        told8 = []
        kw8 = dict(kw, say=lambda t, w: told8.append(t))
        t8 = "docs/TH1_11B_PROPOSAL_TARGET_TEST.md"
        h8, d8, r8 = H.act("HANDS PROPOSE %s\n# proposed under a VIOLATES\n" % t8, gate=viol, **kw8)
        h8u, d8u, r8u = H.act("HANDS PROPOSE docs/TH1_11B_UNREACHABLE_TEST.md\n# x\n",
                              gate=lambda t: ("unreachable", "gate unreachable: X"), **kw8)
        meta8 = next((m for m in H.proposals(pdir) if m.get("id") == r8.get("id")), {})
        row8 = next((r for r in reversed(H._rows(ledger)) if r.get("kind") == "propose" and r.get("target") == t8), {})
        h8w, d8w, r8w = H.act("HANDS WRITE v8.txt\nx", gate=viol, **kw8)
        check("TH1.11b a PROPOSE the gate calls VIOLATES is recorded, not dropped: saved with the verdict in its record and "
              "its row, the operator told the proposal and the verdict, Tetsu told the gate's words, the tree untouched; the "
              "verdict rides every proposal's line; a WRITE under VIOLATES is still refused",
              h8 and not r8.get("refused") and r8.get("id") and os.path.exists(os.path.join(pdir, r8["id"] + ".md"))
              and (meta8.get("gate") or {}).get("state") == "violates" and "stub VIOLATES" in (meta8.get("gate") or {}).get("message", "")
              and (row8.get("gate") or {}).get("state") == "violates" and row8.get("id") == r8["id"] and not row8.get("refused")
              and len(told8) == 2 and ("--apply " + r8["id"]) in told8[0] and "The gate on it: VIOLATES (stub VIOLATES)" in told8[0]
              and "The gate on it: UNREACHABLE (gate unreachable: X)" in told8[1] and not r8u.get("refused")
              and "The gate said VIOLATES (stub VIOLATES)" in d8 and ("recorded as " + r8["id"]) in d8
              and not os.path.exists(os.path.join(HERE, t8)) and r8w.get("refused") and not os.path.exists(os.path.join(ws, "v8.txt")),
              (d8, told8, meta8, row8, r8w))
        # 12. --apply is the operator's hand: it writes the tree file (into a temp HERE stand-in), records actor operator
        orig_here = H.HERE
        H.HERE = td
        try:
            out = []
            path = H.apply_proposal(rec["id"], pdir, say=out.append, ledger=ledger)
            with open(path, encoding="utf-8") as fh:
                applied = fh.read()
        finally:
            H.HERE = orig_here
        rows = H._rows(ledger)
        check("TH1.12 --apply copies the proposal over the tree file it names, prints the diff, and records the act with actor operator",
              path == os.path.abspath(os.path.join(td, target_rel)) and applied.rstrip("\n") == "# a proposal\nline" and any(l.startswith("+# a proposal") for l in out)
              and rows[-1]["kind"] == "applied" and rows[-1]["actor"] == "operator", (path, out[:6], rows[-1]))
        # 12f. A348f: a .json proposal's own content (<id>.json) was read as a record. Measured in temp dirs: a body [1, 2]
        # broke --apply of every proposal, {"a": 1,} broke the listing, and an object body was listed as a proposal.
        pdir2 = os.path.join(td, "proposals_12f")
        kw2 = dict(kw, proposals_dir=pdir2)
        bodies = ("[1, 2]", '{"a": 1,}', '{"id": "phantom0", "path": "y.md"}')
        _h, _d, md = H.act("HANDS PROPOSE docs/TH1_12F_TARGET_TEST.md\n# kept\n", gate=clean, **kw2)
        js = [H.act("HANDS PROPOSE ops/th1_12f_%d_test.json\n%s\n" % (i, b), gate=clean, **kw2)[2] for i, b in enumerate(bodies)]
        with open(os.path.join(pdir2, "0123456789ab.md.json"), "w", encoding="utf-8") as fh:
            fh.write('{"id": "0123456789ab", "pa')                       # a record cut short mid-write
        with open(os.path.join(pdir2, "abcdef012345.txt.json"), "w", encoding="utf-8") as fh:
            fh.write("[1, 2]")                                            # a record-shaped name that holds no record
        want = {md.get("id")} | {r.get("id") for r in js}
        orig_here, orig_props, err, listed, applied2, shown = H.HERE, H.PROPOSALS, None, [], [], ""
        H.HERE, H.PROPOSALS = td, pdir2
        try:
            listed = H.proposals(pdir2)
            applied2 = [H.apply_proposal(p, pdir2, say=lambda *_a: None, ledger=ledger) for p in (md["id"], js[0]["id"])]
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                H.main(["--proposals"])
                H.main(["--proposal", md["id"]])
            shown = buf.getvalue()
        except Exception as e:                                            # noqa: BLE001
            err = "%s: %s" % (type(e).__name__, e)
        finally:
            H.HERE, H.PROPOSALS = orig_here, orig_props
        check("TH1.12f the proposals listing reads only records: a .json proposal whose body is an array, not strict JSON, or "
              "carries an id of its own is listed once by its record, a record cut short or not an object is skipped, and "
              "--apply, --proposals and --proposal work for every other proposal",
              err is None and len(listed) == 4 and {m.get("id") for m in listed} == want and None not in want
              and all(isinstance(m, dict) for m in listed) and len(applied2) == 2 and "# kept" in shown, (err, listed, want))
        # 13. the record and the door's shape
        rows = H._rows(ledger)
        kinds = [r["kind"] for r in rows]
        h, data, rec = H.act("a plain answer with no directive", gate=clean, **kw)
        check("TH1.13 every act is one row (kind, target, gate, outcome) with actor tetsu; a plain answer is not handled (False, '', None) as the MOLTBOOK door expects",
              len(rows) >= 14 and all(r.get("actor") in ("tetsu", "operator") for r in rows) and {"write", "read", "list", "run", "propose"} <= set(kinds)
              and (h, data, rec) == (False, "", None), (len(rows), sorted(set(kinds))))
        # 14. the source: the door in the core dispatches HANDS beside MOLTBOOK, and tells him he has hands
        with open(os.path.join(HERE, "covenant_unified_v8.py"), encoding="utf-8") as fh:
            core = fh.read()
        # The sentence telling him in his standing instructions that he has hands was refused by the
        # session's auto-mode safety check on 2026-09-26 ("Create Unsafe Agents"); it is the operator's
        # to add. Measured here: the door dispatches, and whether he has been told is reported, not required.
        told = "HANDS WRITE <name>" in core
        print("      (his instructions %s him he has hands)" % ("tell" if told else "do NOT yet tell"))
        check("TH1.14 the /m/agent door dispatches a HANDS first line to covenant_tetsu_hands.act beside MOLTBOOK, and "
              "gates RUN to a caller with a registered operator signature (may_run from _request_signed_by_registered, "
              "NOT mere loopback, which is any local account)",
              'startswith("HANDS")' in core and 'import_module("covenant_tetsu_hands").act(answer, may_run=' in core
              and "_may_run = _request_signed_by_registered(request)" in core, "")
        # 15. A349 A11: a run started Python without SYSTEMDRIVE, and Windows made a literal '%SystemDrive%\ProgramData\...'
        # tree inside his workshop (his real one has had it since his first run, 2026-09-28; it stays). The environment is
        # read through a spy on subprocess.run, and the workshop is walked after a real run.
        ws15 = os.path.join(td, "ws15")
        os.makedirs(ws15)
        H.write("hello.py", "print('hello')\n", ws15)
        envs, real_run = [], H.subprocess.run

        def spy_run(*a, **k):
            envs.append(dict(k.get("env") or {}))
            return real_run(*a, **k)
        H.subprocess.run = spy_run
        try:
            r15 = H.run("hello.py", workshop=ws15)
        finally:
            H.subprocess.run = real_run
        left = sorted(os.path.relpath(os.path.join(root, n), ws15).replace("\\", "/")
                      for root, dirs, files in os.walk(ws15) for n in dirs + files)
        drive = os.environ.get("SYSTEMDRIVE")
        if not drive:
            print("      (no SYSTEMDRIVE here: not Windows, where the stray tree cannot appear; only the environment is read)")
        check("TH1.15 a run hands Python SYSTEMDRIVE, and leaves nothing in the workshop but its runner and the script (no "
              "'%SystemDrive%' tree)",
              r15["ok"] is True and left == [".runner.py", "hello.py"] and len(envs) == 1
              and (envs[0].get("SYSTEMDRIVE") == drive if drive else "SYSTEMDRIVE" not in envs[0]),
              (left, sorted(envs[0]) if envs else None))
        a428(td, big)

    n_ok, n = sum(results), len(results)
    print("TH1: %d/%d passed" % (n_ok, n))
    return 0 if n_ok == n else 1


if __name__ == "__main__":
    sys.exit(main())
