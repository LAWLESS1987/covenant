#!/usr/bin/env python3
"""
test_g7_pause.py -- G7 (2026-09-16): one actor can be paused without stopping
the others, and a pause never blinds anything.

ASKED: "ensure they all running independent so you can pause tasks for restart
and update". Before this, one thing in the system could be paused -- the trader,
via TRADER_HALT -- and the highway's repair pass had no process of its own, so
pausing it meant killing the watchdog, which is what restarts dead nodes.

THE CONTRACT, and every line of it is driven both ways here:
  a paused actor TAKES NO ACTION and GOES ON OBSERVING.

  G7.1  pause/resume/list round-trip, in a temp directory.
  G7.2  a pause carries its reason, because a switch with no reason is a switch
        nobody dares turn off.
  G7.3  the highway, paused, performs NO repair -- the spy remedy is never
        entered -- and still reports what it sensed, including what is present.
  G7.4  ...and unpaused, the same conditions do reach the remedy.
  G7.5  the watchdog, with restarts paused, does NOT launch a node: the Popen
        spy records nothing. No real node is started by this suite.
  G7.6  ...and unpaused, it does launch (spy only, still no real node).
  G7.7  pausing one actor does not pause another.
  G7.8  the trader is REPORTED, not re-implemented: paused("trader") follows
        TRADER_HALT, and this module refuses to arm or disarm the trader.
  G7.9  a pause is reported on every round, with its age, so a system left
        half-off for a week says so.
  G7.11 (A348j) "earn" and "tetsu", read by name since A222 and A175, are said
        in the report and in --list while they stand.
  G7.12 (A348j) every actor name a module passes to covenant_pause's paused()
        or pause(), found by walking the tree, is listed in ACTORS.
  G7.13 (A349 S2) standing() reads a switch as it is on disk: None when absent,
        and a present file stands whatever its bytes -- so free's isolation
        never writes over a pause someone set by hand.

    python test_g7_pause.py
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile

import covenant_pause as P

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


def main():
    real_dir, real_halt = P.PAUSE_DIR, P.TRADER_HALT
    tmp = tempfile.mkdtemp(prefix="g7_")
    P.PAUSE_DIR = os.path.join(tmp, "pause")
    P.TRADER_HALT = os.path.join(tmp, "TRADER_HALT")
    try:
        # ---- G7.1 / G7.2: the switch itself
        was, _ = P.paused("highway")
        P.pause("highway", "updating the detectors")
        on, why = P.paused("highway")
        P.resume("highway")
        off, _ = P.paused("highway")
        check("G7.1 pause, then resume, and the state follows",
              not was and on and not off, "was=%s on=%s off=%s" % (was, on, off))
        check("G7.2 the pause carries the reason it was set with",
              "updating the detectors" in why, why[:60])

        # ---- G7.3 / G7.4: the highway
        import covenant_highway as H
        calls = []
        real_rl = dict(H.REMEDIES["rotate_log"])
        real_det = H.DETECTORS
        try:
            H.REMEDIES["rotate_log"] = dict(
                real_rl, fn=lambda measured, dry_run=True: (calls.append(1), (True, "spy"))[1])
            H.DETECTORS = {"log_bloat": lambda health=None: {"state": H.PRESENT,
                                                             "measured": {"fixture": True}}}
            led = tempfile.mktemp(suffix="_g7.jsonl")

            P.pause("highway", "G7")
            alerts, infos = H.run_once(dry_run=False, ledger=led, cooldown_s=0)
            check("G7.3 paused, the highway repairs nothing", not calls, "calls=%d" % len(calls))
            check("G7.3b ...and still says what it sensed, naming what is present",
                  any("PAUSED" in i and "log_bloat" in i for i in infos), str(infos)[:110])
            check("G7.3c ...and raises no alert for being paused, because a pause is a choice",
                  not alerts, str(alerts)[:80])

            P.resume("highway")
            H.run_once(dry_run=False, ledger=led, cooldown_s=0)
            check("G7.4 mutation: unpaused, the same condition reaches the remedy",
                  bool(calls), "calls=%d" % len(calls))
        finally:
            H.REMEDIES["rotate_log"] = real_rl
            H.DETECTORS = real_det
            P.resume("highway")

        # ---- G7.5 / G7.6: the watchdog's restart action, with a Popen spy so
        # that no node is ever actually launched by this test.
        import covenant_watchdog as W
        import subprocess as _sp
        spawned = []
        real_popen = W.subprocess.Popen
        real_wlog = W.LOGDIR
        real_wfile = W.LOGFILE
        # A stand-in database and key, in the temp dir: since A244 a relaunch
        # refuses a node whose files are not there or are empty (G7.6r/s/u),
        # so a node that should launch must have them. Absolute paths, so
        # nothing is created in the real tree.
        zz_db = os.path.join(tmp, "nodeZZ_test.db")
        for _f in (zz_db, zz_db + ".key"):
            with open(_f, "w") as _fh:
                _fh.write("stand-in")
        node = {"id": "ZZ", "port": 5990, "db": zz_db,
                "key": zz_db + ".key", "peers": ""}
        try:
            # The watchdog's own log and the node log it opens both go to a
            # temp directory: the first run of this suite left an empty
            # logs/nodeZZ.log in the real tree and a line in the real
            # watchdog log about a node that does not exist. A test that
            # litters the thing it measures is measuring its own litter.
            W.LOGDIR = os.path.join(tmp, "logs")
            # LOGFILE too (2026-10-04): log() writes there, not under LOGDIR, so
            # this block's PAUSED and A244 lines landed in the REAL watchdog log,
            # which the self-eval and Tetsu's daily read for alerts.
            W.LOGFILE = os.path.join(W.LOGDIR, "watchdog.log")
            os.makedirs(W.LOGDIR, exist_ok=True)
            W.subprocess.Popen = lambda *a, **k: spawned.append(a) or _FakeProc()

            P.pause("watchdog-restarts", "G7")
            out = W.start_node(node)
            check("G7.5 with restarts paused the watchdog launches nothing",
                  out is False and not spawned, "returned %r, spawned %d" % (out, len(spawned)))

            P.resume("watchdog-restarts")
            W.start_node(node)
            check("G7.6 mutation: unpaused, it launches",
                  len(spawned) == 1, "spawned %d" % len(spawned))

            # A244: what a sweep's staged copy looks like from inside -- this
            # tree's ports, no database, no key. On 2026-10-03 the relaunch
            # minted identities there and served all three ports at height 1.
            ghost = {"id": "ZZ", "port": 5990, "db": "nodeZZ_absent.db",
                     "key": "nodeZZ_absent.db.key", "peers": ""}
            out = W.start_node(ghost)
            check("G7.6r A RELAUNCH NEVER CREATES (A244): no database and no key in "
                  "the launching tree -- nothing launched, and it says so",
                  out is False and len(spawned) == 1,
                  "returned %r, spawned %d" % (out, len(spawned)))
            os.unlink(zz_db + ".key")
            out = W.start_node(node)
            check("G7.6s ...and a database whose key is missing is refused too: the "
                  "identity is the thing a staged copy mints",
                  out is False and len(spawned) == 1,
                  "returned %r, spawned %d" % (out, len(spawned)))

            # rolling_restart, the path that did it: stop and health are stubbed,
            # so no process is touched even if the guard is gone.
            import rolling_restart as RR
            stops, said = [], []
            real_stop, real_health = RR.stop, RR.health
            RR.stop = lambda *a, **k: stops.append(a)
            RR.health = lambda port: None
            try:
                ok_rr = RR.restart_one(ghost, "x", said.append)
            finally:
                RR.stop, RR.health = real_stop, real_health
            check("G7.6t ...and rolling_restart does not STOP a node its tree cannot "
                  "relaunch -- on 2026-10-03 the copy took each node down first",
                  ok_rr is False and not stops and any("A244" in s for s in said),
                  "returned %r, stops %d, said %s" % (ok_rr, len(stops), said[-1:]))

            # An empty database beside a real key: the staged copy of 10-03 now
            # holds 0-byte databases, and a relaunch over one boots at height 1.
            with open(zz_db + ".key", "w") as _fh:
                _fh.write("stand-in")
            open(zz_db, "w").close()
            out = W.start_node(node)
            check("G7.6u ...and an EMPTY database is not a chain: refused",
                  out is False and len(spawned) == 1,
                  "returned %r, spawned %d" % (out, len(spawned)))

            # The leak's own door: one_pass runs the highway, and in a tree that
            # cannot relaunch its nodes it must run it DRY. HERE and NODES point
            # at the temp dir, both ways.
            real_here, real_nodes = W.HERE, W.NODES
            try:
                W.HERE = tmp
                W.NODES = [{"id": "ZZ", "port": 5990, "db": "nodeZZ_test.db",
                            "key": "nodeZZ_test.db.key", "peers": ""}]
                staged = W.highway_may_act()                  # empty db: a copy
                with open(zz_db, "w") as _fh:
                    _fh.write("stand-in")
                production = W.highway_may_act()
            finally:
                W.HERE, W.NODES = real_here, real_nodes
            check("G7.6v the highway may ACT only from a tree that can relaunch its "
                  "nodes -- a staged copy's watchdog pass runs it dry (A244)",
                  staged is False and production is True,
                  "staged copy -> %r, production -> %r" % (staged, production))
        finally:
            W.subprocess.Popen = real_popen
            W.LOGDIR = real_wlog
            W.LOGFILE = real_wfile
            P.resume("watchdog-restarts")

        # ---- G7.7: independence
        P.pause("nightly", "G7")
        n_on, _ = P.paused("nightly")
        h_on, _ = P.paused("highway")
        w_on, _ = P.paused("watchdog-restarts")
        check("G7.7 pausing one actor leaves the others running",
              n_on and not h_on and not w_on,
              "nightly=%s highway=%s watchdog=%s" % (n_on, h_on, w_on))

        # ---- G7.8: the trader is reported, never re-implemented
        t_off, _ = P.paused("trader")
        with open(P.TRADER_HALT, "w", encoding="utf-8") as fh:
            fh.write("stop")
        t_on, t_why = P.paused("trader")
        ok_pause, msg = P.pause("trader", "should refuse")
        ok_resume, _ = P.resume("trader")
        check("G7.8 the trader's state follows TRADER_HALT, both ways",
              not t_off and t_on, "%s -> %s" % (t_off, t_on))
        check("G7.8b this module refuses to arm or disarm the trader",
              not ok_pause and not ok_resume and "TRADER_HALT" in msg, msg[:70])
        check("G7.8c ...and removing the halt file is what resumes it",
              (os.unlink(P.TRADER_HALT), P.paused("trader")[0])[1] is False)

        # ---- G7.9: a pause is visible on every round, with its age
        _a, infos = P.report()
        # A348j: this asserted "hours" NOT in the line, and report() writes " for N.N h", so the age
        # promised above was never checked. It is now, with what the pause stops.
        check("G7.9 a standing pause is reported, with its age and what it stops",
              any(re.match(r"paused: nightly for \d+\.\d h -- ", i) and P.ACTORS["nightly"] in i for i in infos),
              str(infos)[:110])
        check("G7.9b ...and the report raises no alert -- a pause is a decision, not a fault",
              not _a, str(_a)[:60])
        P.resume("nightly")
        _a2, infos2 = P.report()
        check("G7.9c ...and it stops being reported once resumed",
              not any("nightly" in i for i in infos2), str(infos2)[:80])

        # ---- G7.11 (A348j): earn and tetsu were paused by name and never listed
        P.pause("earn", "G7 earn")
        P.pause("tetsu", "G7 tetsu")
        _a3, infos3 = P.report()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            P.main(["--list"])
        listed = {ln.split()[0]: ln.split()[1] for ln in buf.getvalue().splitlines() if ln.strip()}
        P.resume("earn")
        P.resume("tetsu")
        check("G7.11 a standing earn or tetsu pause is said in the watchdog's report and in --list",
              any(i.startswith("paused: earn for ") for i in infos3) and any(i.startswith("paused: tetsu for ") for i in infos3)
              and listed.get("earn") == "PAUSED" and listed.get("tetsu") == "PAUSED",
              "report %s; list earn=%s tetsu=%s" % ([i[:24] for i in infos3], listed.get("earn"), listed.get("tetsu")))

        # ---- G7.13 (A349 S2): standing() -- what free's round re-reads before her automatic isolation, so a
        # pause someone set by hand is never written over. A file that is present stands, whatever its bytes.
        none_before = P.standing("ambassador")
        P.pause("ambassador", "operator: holding free, G7")
        by_pause = P.standing("ambassador")
        P.resume("ambassador")
        check("G7.13 standing() is None with no pause, and the reason of one pause() wrote",
              none_before is None and by_pause is not None and "operator: holding free, G7" in by_pause
              and P.standing("ambassador") is None, (none_before, by_pause))
        os.makedirs(P.PAUSE_DIR, exist_ok=True)
        hand = os.path.join(P.PAUSE_DIR, "ambassador")
        with open(hand, "wb") as fh:                 # what Windows PowerShell 5.1's `"stop" > file` writes: UTF-16
            fh.write("stop, mine\r\n".encode("utf-16"))
        s_utf16 = P.standing("ambassador")
        with open(hand, "wb") as fh:
            pass
        s_empty = P.standing("ambassador")
        os.unlink(hand)
        os.makedirs(hand)                            # present, and cannot be read as a file at all
        s_dir = P.standing("ambassador")
        os.rmdir(hand)
        check("G7.13b a present switch stands whatever its bytes: UTF-16, empty, or unreadable (a directory in its place)",
              s_utf16 is not None and s_empty == "" and s_dir == "", (s_utf16, s_empty, s_dir))
    finally:
        P.PAUSE_DIR, P.TRADER_HALT = real_dir, real_halt

    check("G7.10 the real pause directory and the real TRADER_HALT are untouched",
          P.PAUSE_DIR == real_dir and P.TRADER_HALT == real_halt
          and not os.path.exists(real_halt), "halt exists: %s" % os.path.exists(real_halt))

    # ---- G7.12 (A348j): the class -- an actor read by name and missing from ACTORS
    root = os.path.dirname(os.path.abspath(P.__file__))
    consumed, files = _pause_names_consumed(root)
    unlisted = sorted(n for n in consumed if n not in P.ACTORS)
    print("  G7.12 read %d module(s) that name covenant_pause; actor names they pass: %s"
          % (len(files), ", ".join("%s (%s)" % (n, ", ".join(sorted(consumed[n]))) for n in sorted(consumed))))
    check("G7.12 the walk sees all three shapes: a literal (earn), a constant (tetsu-immunity), a loop (tetsu)",
          {"earn", "tetsu-immunity", "tetsu"} <= set(consumed), sorted(consumed))
    check("G7.12b every actor name a module pauses or reads is listed in ACTORS, so --list shows it",
          not unlisted, "unlisted: %s" % ["%s in %s" % (n, sorted(consumed[n])) for n in unlisted])

    failed =[n for n, ok in results if not ok]
    print(f"\nG7: {len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
    return 1 if failed else 0


def _pause_names_consumed(root):
    """({actor name: {files}}, [files read]): every name a module passes to covenant_pause's paused() or pause(),
    by DISCOVERY (A348j; rule 2): walk the tree, prune .git, .claude (worktrees, A267), .trash and virtualenvs by
    path, keep the .py files whose text names covenant_pause, skip test_*.py and covenant_pause.py itself, and
    read each call's first argument as a string literal, a module-level string constant, or the target of a for
    over a literal tuple or list. What it cannot see: a name computed at run time or passed through any other
    variable, and a call made through an alias not named paused or pause."""
    import ast
    prune = {".git", ".claude", ".trash", ".venv", "venv", "node_modules", "__pycache__"}
    names, files = {}, []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in prune]
        for fn in fns:
            if not fn.endswith(".py") or fn.startswith("test_") or fn == "covenant_pause.py":
                continue
            fp = os.path.join(dp, fn)
            try:
                with open(fp, encoding="utf-8", errors="replace") as fh:
                    src = fh.read()
                tree = ast.parse(src) if "covenant_pause" in src else None
            except (OSError, SyntaxError, ValueError):
                continue
            if tree is None:
                continue
            files.append(fp)
            consts = {t.id: n.value.value for n in tree.body if isinstance(n, ast.Assign)
                      and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
                      for t in n.targets if isinstance(t, ast.Name)}
            loops = {}
            for n in ast.walk(tree):
                if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and isinstance(n.iter, (ast.Tuple, ast.List)):
                    loops.setdefault(n.target.id, []).extend(
                        e.value for e in n.iter.elts if isinstance(e, ast.Constant) and isinstance(e.value, str))
            for n in ast.walk(tree):
                if not isinstance(n, ast.Call) or not n.args:
                    continue
                f = n.func
                callee = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
                if callee not in ("paused", "pause"):
                    continue
                a = n.args[0]
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    found = [a.value]
                elif isinstance(a, ast.Name):
                    found = [consts[a.id]] if a.id in consts else loops.get(a.id, [])
                else:
                    found = []
                for v in found:
                    names.setdefault(v, set()).add(os.path.relpath(fp, root).replace(os.sep, "/"))
    return names, files


class _FakeProc:
    pid = 99999

    def poll(self):
        return None


if __name__ == "__main__":
    sys.exit(main())
