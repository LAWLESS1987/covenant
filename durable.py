#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""durable.py -- writes that survive the power going out.

HIS REQUIREMENT, 2026-09-19: "Must survive power loss."

WHAT THE MACHINE ALREADY SURVIVES, measured before changing anything: every
node database is SQLite in WAL mode with `synchronous=FULL` (nodeA/B/C_prod,
nodeA/B_run, covenant_A). A committed block is on the platter before the commit
returns, so THE CHAIN ITSELF IS NOT THE PROBLEM and nothing here touches it.

WHAT IT DID NOT SURVIVE is every flat file beside the chain, because

    open(path, "w")   TRUNCATES FIRST.

The window between that truncation and the last byte being written is small
and it is not zero, and what is in it is not a missing file -- which a reader
would notice -- but a file that still exists, still opens, still parses as
"present", and is empty or half a record long. Three of those were live:

  * ops/app/requests.jsonl -- the update door's witness. note_request TRIMS it
    by reading every line and rewriting the file, so a power cut during the
    trim loses the whole audit trail rather than one row.
  * ops/app/latest.json -- which build the phone is offered. Truncated, the
    door answers "no build fetched yet" and the phone cannot update at all.
  * the trader's state -- orders_today and sealed_signals, which the daily caps
    are computed FROM. guards.preconditions refuses an unparseable state
    (G4.3), so it fails closed, but a state that comes back EMPTY rather than
    broken silently resets the count of orders placed today.

os.replace is atomic on Windows and POSIX alike: a reader sees the old file or
the new one and never a torn one. That is the whole mechanism.

ON THE DIRECTORY FSYNC, said plainly rather than implied. On POSIX the rename
itself needs the directory entry flushed, so `write_text` fsyncs the directory
too. Windows has no equivalent call and os.replace on NTFS is
metadata-journalled, so there is nothing to do and nothing is pretended.

THIS IS NOT THE FIRST COPY OF THIS CODE, which is the reason it is a module.
ai_memory_system/memory_store.py has had a correct `_atomic_write` since
before this file, as a private static method in an unrelated subsystem, and
memory_watchdog.py has a third partial one inline. "Added at one call site,
never migrated when a second caller needed it" is this project's PATCH LOG
item J, written about a security check that got forgotten exactly that way.

WHAT THIS STILL CANNOT PROMISE. A drive that lies about fsync -- consumer SSDs
with volatile write caches do -- cannot be made honest from here. Neither can a
filesystem mounted with barriers off. What is guaranteed is that THIS process
issues the flush and performs the rename atomically; what the hardware does
with the flush is outside the program, and saying so is cheaper than finding
out later that "durable" meant "durable if the disk was telling the truth".

    python durable.py --selftest
LICENCE: Apache-2.0.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

__all__ = ["write_text", "write_json", "append_line", "rewrite_lines", "fsync_dir"]


def fsync_dir(path):
    """Flush the DIRECTORY entry so the rename itself survives. No-op on
    Windows, which has no such call and does not need one for os.replace."""
    d = os.path.dirname(os.path.abspath(path)) or "."
    if not hasattr(os, "O_DIRECTORY"):
        return False
    fd = None
    try:
        fd = os.open(d, os.O_DIRECTORY)
        os.fsync(fd)
        return True
    except OSError:
        return False
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def write_text(path, text, fsync=True, newline="\n"):
    """Replace `path` with `text`, atomically. The old content survives any
    failure before the rename, including this process being killed."""
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-", suffix=".part")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline=newline) as fh:
            fh.write(text)
            fh.flush()
            if fsync:
                os.fsync(fh.fileno())          # the bytes, not just the buffer
        os.replace(tmp, path)                  # atomic on Windows and POSIX
    except BaseException:
        # THE TEMP FILE IS REMOVED ON EVERY FAILURE PATH, including
        # KeyboardInterrupt and SystemExit -- hence BaseException and not
        # Exception. A .tmp-*.part left in ops/ is litter that the next
        # discovery-based scan will find and try to read.
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    if fsync:
        fsync_dir(path)
    return path


def write_json(path, obj, indent=1, fsync=True, sort_keys=False):
    """write_text of `obj` as JSON. Serialisation happens BEFORE anything is
    replaced, so an object that will not serialise leaves the old file
    untouched rather than destroying it and then failing."""
    text = json.dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
    if indent is not None:
        text += "\n"
    return write_text(path, text, fsync=fsync)


def append_line(path, line, fsync=True):
    """Append one line and flush it to the platter.

    An append cannot corrupt what is already there -- the worst a power cut
    can do is leave the last line short, which every reader in this project
    already tolerates because they all skip a line that will not parse. The
    fsync is so the row is THERE at all: an audit ledger that loses the last
    ten minutes on a power cut is not much of an audit ledger, and these
    ledgers are written every ten minutes, not every millisecond, so the cost
    is nothing."""
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    if not line.endswith("\n"):
        line += "\n"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        if fsync:
            os.fsync(fh.fileno())
    return path


def rewrite_lines(path, lines, fsync=True):
    """Replace a line-oriented file wholesale, atomically. This is the one
    that mattered: trimming a ledger by rewriting it is the operation that
    can lose all of it."""
    body = "".join(l if l.endswith("\n") else l + "\n" for l in lines)
    return write_text(path, body, fsync=fsync)


def _selftest():
    import glob
    import shutil
    ok = fail = 0

    def check(label, cond, detail=""):
        nonlocal ok, fail
        if cond:
            ok += 1
        else:
            fail += 1
        print("  [%s] %s%s" % ("PASS" if cond else "FAIL", label,
                               ("  -- " + detail) if detail else ""))

    d = tempfile.mkdtemp(prefix="durable_")
    try:
        p = os.path.join(d, "x.json")
        write_json(p, {"a": 1})
        check("write_json creates the file with the content",
              json.load(open(p, encoding="utf-8")) == {"a": 1})

        write_json(p, {"a": 2})
        check("...and replaces it", json.load(open(p, encoding="utf-8")) == {"a": 2})

        # THE PROPERTY THAT MATTERS, driven rather than asserted: at the moment
        # before the rename, the TARGET must still hold the old content. That
        # is what "a reader never sees a torn file" means, and it is the thing
        # open(path,"w") cannot do.
        seen = {}
        real_replace = os.replace

        def spy(src, dst):
            seen["during"] = open(dst, encoding="utf-8").read()
            return real_replace(src, dst)

        os.replace = spy
        try:
            write_json(p, {"a": 3})
        finally:
            os.replace = real_replace
        check("the target still holds the OLD content right up to the rename",
              json.loads(seen.get("during", "{}")) == {"a": 2}, str(seen.get("during"))[:40])

        # BROKEN ON PURPOSE: a value json cannot serialise.
        before = open(p, encoding="utf-8").read()
        try:
            write_json(p, {"bad": {1, 2}})
            raised = False
        except TypeError:
            raised = True
        check("an unserialisable object raises and leaves the old file intact",
              raised and open(p, encoding="utf-8").read() == before)

        # BROKEN ON PURPOSE: the write itself fails after the temp exists.
        before = open(p, encoding="utf-8").read()

        class Boom:
            def __str__(self):
                raise RuntimeError("disk on fire")

        try:
            write_text(p, Boom())                       # fh.write raises
            raised = False
        except Exception:                                # noqa: BLE001
            raised = True
        check("a failure mid-write leaves the old file intact",
              raised and open(p, encoding="utf-8").read() == before)
        check("...and leaves no .tmp-*.part litter behind",
              glob.glob(os.path.join(d, ".tmp-*.part")) == [],
              str(glob.glob(os.path.join(d, ".tmp-*.part"))))

        lp = os.path.join(d, "l.jsonl")
        append_line(lp, '{"n":1}')
        append_line(lp, '{"n":2}\n')
        check("append_line appends, and normalises the newline",
              open(lp, encoding="utf-8").read() == '{"n":1}\n{"n":2}\n')

        rewrite_lines(lp, ['{"n":2}\n'])
        check("rewrite_lines replaces the file wholesale",
              open(lp, encoding="utf-8").read() == '{"n":2}\n')

        sub = os.path.join(d, "deep", "deeper", "y.json")
        write_json(sub, {"ok": True})
        check("a missing directory is created rather than raising",
              os.path.isfile(sub))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print("\ndurable: %d/%d passed" % (ok, ok + fail))
    return 0 if not fail else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    print(__doc__)
