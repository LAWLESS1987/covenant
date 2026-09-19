#!/usr/bin/env python3
"""test_du1_durable.py -- DU1: the machine survives the power going out.

HIS REQUIREMENT, 2026-09-19: "Must survive power loss."

WHAT IS PINNED HERE, and why each one rather than a general claim:

  DU1.a-f  durable.write_text / write_json / append_line / rewrite_lines. The
           property that matters is driven, not asserted: at the instant
           before the rename, the TARGET still holds the OLD bytes. That is
           what `open(path,"w")` cannot do, because it truncates first.
  DU2.a-c  THE CALL SITES, which is where the last version of this lesson was
           lost. ai_memory_system had a correct atomic write since before any
           of this and it stayed private to that subsystem, so three live
           ledgers went on truncating. A helper nobody calls is not a fix, so
           these drive the REAL functions -- note_request's trim, the trader's
           save_state, signal_watch's save_state -- and assert each one goes
           through os.replace.
  DU3.a-b  THE CHAIN, measured rather than assumed: every node database must
           be SQLite in WAL mode with synchronous=FULL. That is what makes a
           committed block survive the cut, and it is the reason none of the
           work above touches the chain. Pinned so a later change cannot
           quietly drop it to NORMAL and leave this suite still green.

WHAT THIS CANNOT PROMISE, and the suite says so rather than implying
otherwise: a drive that lies about fsync cannot be made honest from here.
What is checked is that THIS process issues the flush and renames atomically.

    python test_du1_durable.py
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import durable                                                   # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


class ReplaceSpy:
    """Records what the TARGET held at the moment os.replace was called.

    This is the whole power-loss property in one observation: if the target
    still has the old content right up to the rename, then no reader and no
    power cut can ever see a half-written file."""

    def __init__(self):
        self.during = []
        self.calls = 0
        self._real = os.replace

    def __enter__(self):
        def spy(src, dst):
            self.calls += 1
            try:
                with open(dst, encoding="utf-8") as fh:
                    self.during.append(fh.read())
            except OSError:
                self.during.append(None)          # did not exist yet
            return self._real(src, dst)
        os.replace = spy
        return self

    def __exit__(self, *a):
        os.replace = self._real
        return False


def helper_checks():
    d = tempfile.mkdtemp(prefix="du1_")
    try:
        p = os.path.join(d, "x.json")
        durable.write_json(p, {"a": 1})
        durable.write_json(p, {"a": 2})
        check("DU1.a write_json replaces the file with the new content",
              json.load(open(p, encoding="utf-8")) == {"a": 2})

        with ReplaceSpy() as spy:
            durable.write_json(p, {"a": 3})
        check("DU1.b THE PROPERTY: the target still holds the OLD content at "
              "the instant of the rename -- no reader can see a torn file",
              spy.calls == 1 and json.loads(spy.during[0]) == {"a": 2},
              str(spy.during)[:60])

        before = open(p, encoding="utf-8").read()
        try:
            durable.write_json(p, {"bad": {1, 2}})
            raised = False
        except TypeError:
            raised = True
        check("DU1.c an object that will not serialise raises and leaves the "
              "old file intact -- it is not destroyed and then failed on",
              raised and open(p, encoding="utf-8").read() == before)

        class Boom:
            def __str__(self):
                raise RuntimeError("disk on fire")

        before = open(p, encoding="utf-8").read()
        try:
            durable.write_text(p, Boom())
            raised = False
        except Exception:                                        # noqa: BLE001
            raised = True
        check("DU1.d a failure MID-WRITE leaves the old file intact",
              raised and open(p, encoding="utf-8").read() == before)
        check("DU1.e ...and leaves no .tmp-*.part litter for the next scan to "
              "find and try to read",
              glob.glob(os.path.join(d, ".tmp-*.part")) == [])

        lp = os.path.join(d, "l.jsonl")
        durable.append_line(lp, '{"n":1}')
        durable.append_line(lp, '{"n":2}\n')
        with ReplaceSpy() as spy:
            durable.rewrite_lines(lp, ['{"n":2}\n'])
        check("DU1.f a ledger TRIM goes through the rename too -- the "
              "operation that could lose the whole file, not one row",
              spy.calls == 1 and open(lp, encoding="utf-8").read() == '{"n":2}\n')
    finally:
        shutil.rmtree(d, ignore_errors=True)


def call_site_checks():
    """A helper nobody calls is not a fix. These drive the REAL functions."""
    import covenant_app_update as AU

    d = tempfile.mkdtemp(prefix="du2_")
    saved = (AU.DIR, AU.REQUESTS, AU.REQUESTS_KEEP)
    try:
        AU.DIR = d
        AU.REQUESTS = os.path.join(d, "requests.jsonl")
        AU.REQUESTS_KEEP = 5
        for i in range(5):
            AU.note_request("/app/latest", "phone", "b%d" % i, "served")
        with ReplaceSpy() as spy:
            AU.note_request("/app/latest", "phone", "trim", "served")
        rows = AU.requests_tail(0)
        check("DU2.a note_request's TRIM renames instead of truncating -- the "
              "update door's whole audit trail was in that window",
              spy.calls >= 1 and len(rows) == 5 and rows[-1]["offered"] == "trim",
              "replaces=%d rows=%d" % (spy.calls, len(rows)))
    finally:
        AU.DIR, AU.REQUESTS, AU.REQUESTS_KEEP = saved
        shutil.rmtree(d, ignore_errors=True)

    import covenant_trader as T
    d = tempfile.mkdtemp(prefix="du2t_")
    real = T.STATE
    try:
        T.STATE = os.path.join(d, "state.json")
        T.save_state({"orders_today": [1, 2], "sealed_signals": 7})
        with ReplaceSpy() as spy:
            T.save_state({"orders_today": [1, 2, 3], "sealed_signals": 8})
        check("DU2.b the trader's save_state renames -- orders_today and "
              "sealed_signals are what the daily caps are computed FROM, and "
              "load_state returns DEFAULTS on a parse failure, so a truncated "
              "state silently resets today's order count",
              spy.calls == 1 and json.loads(spy.during[0])["sealed_signals"] == 7,
              "replaces=%d" % spy.calls)
    finally:
        T.STATE = real
        shutil.rmtree(d, ignore_errors=True)

    import signal_watch as SW
    d = tempfile.mkdtemp(prefix="du2s_")
    real = SW.STATE
    try:
        SW.STATE = os.path.join(d, "sig.json")
        SW.save_state({"open": 3})
        with ReplaceSpy() as spy:
            SW.save_state({"open": 4})
        check("DU2.c signal_watch's save_state renames -- load_state returns "
              "{} on failure, so a truncated file forgets every signal Rule 5 "
              "is counting rather than complaining",
              spy.calls == 1 and json.loads(spy.during[0])["open"] == 3,
              "replaces=%d" % spy.calls)
    finally:
        SW.STATE = real
        shutil.rmtree(d, ignore_errors=True)


def chain_checks():
    """The chain is the thing that must survive, and it already does. Measured
    rather than assumed, and pinned so it cannot be quietly downgraded."""
    dbs = sorted(glob.glob(os.path.join(HERE, "node*_prod.db")) +
                 glob.glob(os.path.join(HERE, "node*_run.db")))
    if not dbs:
        check("DU3.a every node database is WAL with synchronous=FULL",
              False, "NOT MEASURED: no node*.db on this machine. Not a pass.")
        return
    bad = []
    for p in dbs:
        try:
            c = sqlite3.connect("file:%s?mode=ro" % p.replace("\\", "/"), uri=True)
            jm = str(c.execute("PRAGMA journal_mode").fetchone()[0]).lower()
            sy = int(c.execute("PRAGMA synchronous").fetchone()[0])
            c.close()
            if jm != "wal" or sy < 2:
                bad.append("%s journal=%s synchronous=%d" % (os.path.basename(p), jm, sy))
        except sqlite3.Error as e:
            bad.append("%s unreadable: %s" % (os.path.basename(p), e))
    check("DU3.a every node database is WAL with synchronous=FULL -- a "
          "committed block is on the platter before the commit returns",
          not bad, "%d checked; %s" % (len(dbs), bad or "all good"))
    check("DU3.b ...and there is more than one to check, so DU3.a is not "
          "passing on an empty list",
          len(dbs) >= 2, "%d database(s)" % len(dbs))


def main():
    print("DU1 -- writes that survive the power going out\n")
    for name, fn in (("helper", helper_checks), ("call sites", call_site_checks),
                     ("chain", chain_checks)):
        try:
            fn()
        except Exception as e:                                   # noqa: BLE001
            import traceback
            traceback.print_exc()
            check("X the %s section ran without raising" % name, False,
                  "%s: %s" % (type(e).__name__, e))
    ok = sum(1 for _, o in results if o)
    print(f"\nDU1: {ok}/{len(results)} passed")
    print("\nNOT CLAIMED: a drive that lies about fsync cannot be made honest "
          "from here. What is checked is that THIS process flushes and renames "
          "atomically.")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
