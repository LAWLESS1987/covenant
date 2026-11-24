#!/usr/bin/env python3
"""covenant_oslock.py -- one lock that cannot be won twice, written once (A482, after A459).

THE SHAPE IT REPLACES. A lock file made with O_EXCL, and "a lock older than N seconds is a dead holder's: remove it
and take it over". Two takers can both judge it stale; one moves it aside and makes its own, then the other's move
removes that FRESH lock and makes another, and both return as holders. A459-STALE-TAKEOVER is that race, found in
rolling_restart.py by the hub's read of PR #94 and in covenant_leviathan.acquire_lock by an outside review before
it; A459 fixed the instance and named two more copies (covenant_daily, covenant_free_will) without fixing them.

THE METHOD (A459's, now shared). A non-blocking exclusive OS lock (msvcrt.locking on Windows, fcntl.flock
elsewhere) on a file that is never moved or removed. The OS drops it when the holding process exits or dies, so
there is no stale lock and nothing to take over, and a process that holds no handle cannot release another's. The
handle is not inheritable (os.open's default since Python 3.4), so a child the holder starts never holds it. The
file's text names the holder, for a refusal message only; it is never read as the lock itself.

  h = acquire(path)            # a handle, or None when another holder has it
  release(h)                   # drops this handle's lock; the file stays
  held, note = held_by_other(path)   # probe without keeping it (takes and drops at once when free)
LICENCE: public domain.
"""
from __future__ import annotations

import json
import os
import sys
import time

_LOCK_BYTE = 1 << 20     # Windows locks a byte range; past the holder note, so the note stays readable
_HELD = {}               # path -> handle, for callers that keep only the path (release_path)


def _os_lock(fh):
    if os.name == "nt":
        import msvcrt
        fh.seek(_LOCK_BYTE)
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _os_unlock(fh):
    try:
        if os.name == "nt":
            import msvcrt
            fh.seek(_LOCK_BYTE)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass


def note(path):
    """What the lock file says about its holder ({} when it says nothing readable)."""
    try:
        with open(path, "rb") as fh:
            got = json.loads(fh.read(4096).decode("utf-8", "replace") or "{}")
        return got if isinstance(got, dict) else {}
    except (OSError, ValueError):
        return {}


def acquire(path):
    """The open handle when this process now holds the lock; None when another handle holds it. An OSError from
    opening the file itself is raised, so each caller decides what an unwritable place means."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fh = os.fdopen(os.open(path, os.O_RDWR | os.O_CREAT, 0o644), "r+b")
    try:
        _os_lock(fh)
    except OSError:
        fh.close()
        return None
    fh.seek(0)
    fh.truncate()
    fh.write(json.dumps({"pid": os.getpid(), "t": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                         "argv": sys.argv[1:]}).encode("utf-8"))
    fh.flush()
    _HELD[os.path.abspath(path)] = fh
    return fh


def release(fh):
    """Drop the lock this handle holds. False when there is no handle: a process cannot release another's."""
    if fh is None:
        return False
    for k, v in list(_HELD.items()):
        if v is fh:
            _HELD.pop(k, None)
    _os_unlock(fh)
    try:
        fh.close()
    except OSError:
        pass
    return True


def release_path(path):
    """Release by path, for callers that kept only the path. False when this process holds no handle for it."""
    fh = _HELD.pop(os.path.abspath(path), None)
    return release(fh) if fh is not None else False


def held_by_other(path):
    """(True, holder note) while another handle holds it; (False, {}) when it is free or the file does not exist.
    Takes and drops the lock at once when free, and never moves, removes or rewrites anything else."""
    if os.path.abspath(path) in _HELD:
        return True, note(path)
    if not os.path.exists(path):
        return False, {}
    try:
        fh = os.fdopen(os.open(path, os.O_RDWR), "r+b")
    except OSError:
        return False, {}
    try:
        _os_lock(fh)
    except OSError:
        fh.close()
        return True, note(path)
    _os_unlock(fh)
    fh.close()
    return False, {}
