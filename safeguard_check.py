#!/usr/bin/env python3
"""safeguard_check.py -- verify the memory record, print its fingerprint.

Exists as a file rather than as an inline -c string because cmd.exe eats a bare
% in a batch file, which silently corrupted the format specifiers and made the
check report "does not verify" on a record that verified fine. A false alarm in
the alarming direction is worse than no check, so the logic lives here.

Same convention GO.bat already states: logic in Python, control flow in .bat.

Exit 0 -- verified, safe to back up.
Exit 1 -- drifted, missing, or unreadable. Do NOT back up over a good copy.
Exit 2 -- no store found.
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    root = os.environ.get("AI_MEMORY_ROOT", "")
    if not root or not os.path.isdir(root):
        print("    no store at %s" % (root or "<unset AI_MEMORY_ROOT>"))
        return 2

    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(here, "ai_memory_system"))
    try:
        from memory_store import MemoryStore
    except Exception as e:                                   # noqa: BLE001
        print("    cannot load the store code: %s: %s" % (type(e).__name__, e))
        return 1

    try:
        store = MemoryStore(root)
        r = store.state_root()
        v = store.verify_integrity()
    except Exception as e:                                   # noqa: BLE001
        print("    cannot read the store: %s: %s" % (type(e).__name__, e))
        return 1

    drifted = list(v.get("drifted", []))
    missing = list(v.get("missing", []))
    unver = list(v.get("unverifiable", []))

    print("    memories  : %d" % r["memories"])
    print("    root      : %s" % r["root"])
    print("    integrity : ok=%s  drifted=%d  missing=%d"
          % (v.get("ok"), len(drifted), len(missing)))
    if unver:
        # Not a failure. Older entries predate content digests and cannot be
        # checked either way, which is a different thing from being wrong.
        print("    note      : %d predate content digests (unverifiable, "
              "not drifted)" % len(unver))

    if not v.get("ok") or drifted or missing:
        for n in drifted[:5]:
            print("      DRIFTED  %s" % n)
        for n in missing[:5]:
            print("      MISSING  %s" % n)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
