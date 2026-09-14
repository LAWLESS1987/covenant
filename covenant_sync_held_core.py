#!/usr/bin/env python3
"""covenant_sync_held_core.py -- when the core changes, the held copies follow.

WHY THIS EXISTS (2026-09-14, the operator's instruction: "it should automatically
adjust"). `test_p18_version_collision.py` V3 says: no other `covenant_unified_v8*.py`
under the bundle root may declare the SAME `COVENANT_VERSION` as the live core
unless it is byte-identical to it. A node reporting a version that two different
files both claim tells an operator nothing at all.

Keeping that true was a MANUAL step, and manual steps are forgotten. On
2026-09-14 the core changed three times in an afternoon and the held copy under
`pending-v8.38/` was re-synced once, in the morning. Every commit after that
pushed automatically -- `.git/hooks/post-commit` sees to that -- so the sweep
went red on GitHub thirty-seven times in a row, once per commit, for a one-line
copy nobody had made. P18's own docstring says the pending-v8.38 case is what V3
was written for, "twice". This is the third. A rule that is correct and
re-broken every time is not a rule, it is a tax.

So: this does the copy, the pre-commit hook runs it (ops/pre-commit.synchold),
and the thing that used to be remembered is now done.

WHAT IT WILL NOT DO, which is most of the point:

  * It never touches a `.PRE-vX.Y.py` file. Those are BACKUPS -- the file that
    was there before that version -- and overwriting one destroys the only copy
    of what a rollback would restore. A PRE- file colliding with the live
    version is a real problem (it means the backup was taken one step too late,
    which is V4) and the answer to it is a person renaming the file, never a
    script silently flattening it.
  * It never touches a file this repository does not track. The bundle root has
    other things under it -- the operator's private phone app among them -- and
    an automation that edits outside what it ships is a much worse bug than the
    one it fixes.
  * It never guesses when git cannot answer. In covenant_one's staged copy there
    is no `.git` at all; asked there, it reports "cannot tell" and changes
    nothing, rather than treating silence as permission. Three answers, not two.
  * It never invents the rule. The scan, the version parse and the skip list are
    imported from `test_p18_version_collision`, whose checker is deliberately
    kept free of its own assertions so it can be reused. One implementation: a
    fixer that disagreed with the test would be worse than no fixer.

Run:
  python covenant_sync_held_core.py           re-sync and say what changed
  python covenant_sync_held_core.py --check   report only; exit 1 if out of sync
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

LIVE = "covenant_unified_v8.py"


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tracked(rel, root=None):
    """Is this path tracked by the repository at `root`? Returns True, False, or
    None for 'cannot tell' -- which is NOT False, and must not be treated as one.

    Takes a root so this can be run against a planted tree, the same reason
    test_p18's checker is kept separable. A fixer nobody can test on a tree they
    built on purpose is a fixer nobody can trust with a destructive operation."""
    root = root or HERE
    try:
        p = subprocess.run(["git", "-C", root, "ls-files", "--error-unmatch", "--", rel],
                           capture_output=True, timeout=60)
    except Exception:                                             # noqa: BLE001
        return None
    if p.returncode == 0:
        return True
    err = (p.stderr or b"").decode("utf-8", "replace").lower()
    if "not a git repository" in err or "not a work tree" in err:
        return None                       # no repository here: cannot tell, so do nothing
    return False


def collisions(root=None):
    """Every copy that declares the live version with different bytes.

    Each entry is (rel, path, why) where `why` is one of:
      "sync"      a held copy this repository tracks -- safe to overwrite
      "backup"    a .PRE- file -- REFUSED, a person must deal with it
      "untracked" outside what this repository ships -- left alone
      "unknown"   git could not be asked -- left alone
    """
    import test_p18_version_collision as P

    root = root or HERE
    live_path = os.path.join(root, LIVE)
    live_ver = P.declared_version(live_path)
    live_sha = _sha(live_path)
    out = []
    for c in P.scan(root):
        if os.path.abspath(c["path"]) == os.path.abspath(live_path):
            continue
        if c["version"] != live_ver or c["sha256"] == live_sha:
            continue
        if P.pre_version_from_name(c["name"]):
            out.append((c["rel"], c["path"], "backup"))
            continue
        t = tracked(c["rel"].replace(os.sep, "/"), root)
        out.append((c["rel"], c["path"], "sync" if t is True
                    else ("untracked" if t is False else "unknown")))
    return live_ver, live_sha, out


def main(argv=None):
    ap = argparse.ArgumentParser(description="re-sync held copies of the core")
    ap.add_argument("--check", action="store_true",
                    help="report only; exit 1 if anything is out of sync")
    ap.add_argument("--root", metavar="DIR", default=None,
                    help="operate on this tree instead of the one beside this file "
                         "(for tests against planted trees)")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.root) if a.root else HERE

    live_ver, live_sha, found = collisions(root)
    if not found:
        print("held copies: in sync (live %s, %s)" % (live_ver, live_sha[:12]))
        return 0

    changed, refused = [], []
    for rel, path, why in found:
        if why == "sync":
            if a.check:
                changed.append(rel)
                print("  OUT OF SYNC  %s" % rel)
            else:
                shutil.copyfile(os.path.join(root, LIVE), path)
                changed.append(rel)
                print("  re-synced    %s  -> %s" % (rel, live_sha[:12]))
        elif why == "backup":
            refused.append(rel)
            print("  REFUSED      %s declares %s and is a .PRE- BACKUP. Not overwriting a "
                  "backup: rename it or correct its version by hand (P18 V4)." % (rel, live_ver))
        elif why == "untracked":
            refused.append(rel)
            print("  left alone   %s declares %s but this repository does not track it" % (rel, live_ver))
        else:
            refused.append(rel)
            print("  left alone   %s declares %s; could not ask git whether it is tracked" % (rel, live_ver))

    print("")
    print("%s %d held cop%s; %d left for a person" % (
        "out of sync:" if a.check else "re-synced", len(changed),
        "y" if len(changed) == 1 else "ies", len(refused)))
    if a.check:
        return 1 if (changed or refused) else 0
    # A refusal is not a failure of this tool, but it IS unfinished work, and
    # saying so is the difference between an automation and a rug.
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
