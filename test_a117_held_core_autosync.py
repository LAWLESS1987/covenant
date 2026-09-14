#!/usr/bin/env python3
"""test_a117_held_core_autosync.py -- the held copies of the core follow the live
one automatically, and the automation refuses the cases it must never touch.

WHY THERE IS AN AUTOMATION TO TEST (2026-09-14). P18 V3 forbids any other copy
of `covenant_unified_v8*.py` from declaring the live `COVENANT_VERSION` with
different bytes. Keeping that true was a manual `cp`. The core changed three
times in one afternoon, the held copy was re-synced once, and because
`.git/hooks/post-commit` pushes every commit immediately the sweep went red on
GitHub thirty-seven times in a row -- once per commit -- for a copy nobody had
made. P18's docstring already called pending-v8.38 the case V3 was written for
"twice"; that was the third.

WHAT MAKES THIS WORTH TESTING HARD. The fixer OVERWRITES FILES. An automation
with a destructive operation in it earns trust only by proving what it will not
do, so most of these checks are refusals: a `.PRE-` backup must survive it
untouched (overwriting one destroys the only copy of what a rollback restores),
a file the repository does not track must survive it untouched, and a tree with
no git at all must come out exactly as it went in rather than being treated as
permission.

Every check runs against a PLANTED tree in the temp directory. Nothing here
reads or writes the real repository except to confirm the hook is installed.

Run:  python test_a117_held_core_autosync.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

RESULTS = []
CORE = "covenant_unified_v8.py"
SYNCER = os.path.join(HERE, "covenant_sync_held_core.py")


def check(label, ok, detail=""):
    RESULTS.append((label, bool(ok), detail))
    print("%-6s %-58s %s" % ("ok" if ok else "FAIL", label, detail))
    return bool(ok)


def sha(path):
    import hashlib
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def core_text(version, extra=""):
    """A file P18's AST reader will accept, small enough to plant many times."""
    return 'COVENANT_VERSION = "%s"\n\n\ndef nothing():\n    return %r\n%s' % (
        version, version, extra)


def run(root, *args):
    p = subprocess.run([sys.executable, SYNCER, "--root", root] + list(args),
                       capture_output=True, text=True, timeout=300, cwd=HERE)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def git(root, *args):
    return subprocess.run(["git", "-C", root] + list(args),
                          capture_output=True, text=True, timeout=120)


def plant(with_git=True):
    td = tempfile.mkdtemp(prefix="a117_")
    write(os.path.join(td, CORE), core_text("v9.99"))
    if with_git:
        git(td, "init", "-q")
        git(td, "add", CORE)
    return td


def main():
    # ------------------------------------------------ an in-sync tree is left alone
    td = plant()
    held = os.path.join(td, "pending-v9.98", CORE)
    write(held, core_text("v9.99"))
    git(td, "add", "pending-v9.98/" + CORE)
    before = sha(held)
    rc, out = run(td, "--check")
    check("A117.1a an in-sync tree reports in sync", rc == 0 and "in sync" in out,
          "rc=%d" % rc)
    rc2, _ = run(td)
    check("A117.1b and the fixer changes nothing", sha(held) == before and rc2 == 0, "")

    # ------------------------------------------------------- a drifted held copy
    write(held, core_text("v9.99", "\n# drift\n"))
    drifted = sha(held)
    rc, out = run(td, "--check")
    check("A117.2a --check finds the drift and exits 1", rc == 1 and "OUT OF SYNC" in out,
          "rc=%d" % rc)
    check("A117.2b ...and --check does NOT change the file", sha(held) == drifted, "")
    check("A117.2c ...and it names the file", CORE in out, "")

    rc, out = run(td)
    check("A117.3a the fixer re-syncs it", sha(held) == sha(os.path.join(td, CORE)),
          "re-synced" if "re-synced" in out else out[:50])
    check("A117.3b and exits 0 with nothing left for a person", rc == 0, "rc=%d" % rc)

    # ------------------------------------------- a .PRE- BACKUP is never overwritten
    td2 = plant()
    pre = os.path.join(td2, "covenant_unified_v8.PRE-v9.99.py")
    write(pre, core_text("v9.99", "\n# this is a BACKUP and must survive\n"))
    git(td2, "add", "covenant_unified_v8.PRE-v9.99.py")
    keep = sha(pre)
    rc, out = run(td2)
    check("A117.4a a .PRE- backup declaring the live version is REFUSED",
          "REFUSED" in out, out.strip().splitlines()[0][:60] if out.strip() else "")
    check("A117.4b ...and is left byte-for-byte intact", sha(pre) == keep, "")
    check("A117.4c ...and the tool exits non-zero so it is not mistaken for done",
          rc != 0, "rc=%d" % rc)

    # ------------------------------------------- an UNTRACKED copy is left alone
    td3 = plant()
    loose = os.path.join(td3, "somewhere", CORE)
    write(loose, core_text("v9.99", "\n# not tracked here\n"))
    keep3 = sha(loose)
    rc, out = run(td3)
    check("A117.5a a copy the repository does not track is left alone",
          "left alone" in out, "")
    check("A117.5b ...and is unchanged", sha(loose) == keep3, "")

    # ------------------------------------------------ no git at all: change nothing
    td4 = plant(with_git=False)
    nogit = os.path.join(td4, "held", CORE)
    write(nogit, core_text("v9.99", "\n# no repository here\n"))
    keep4 = sha(nogit)
    rc, out = run(td4)
    check("A117.6a with no git, the tool says it cannot tell",
          "could not ask git" in out or "left alone" in out, "")
    check("A117.6b ...and changes nothing", sha(nogit) == keep4, "")

    # ------------------------------------------------- the rule stays NARROW
    td5 = plant()
    other = os.path.join(td5, "archive", CORE)
    write(other, core_text("v8.01", "\n# a different version entirely\n"))
    git(td5, "add", "archive/" + CORE)
    keep5 = sha(other)
    rc, out = run(td5)
    check("A117.7a a copy declaring a DIFFERENT version is not touched",
          sha(other) == keep5, "")
    check("A117.7b ...and the tool reports the tree in sync", rc == 0 and "in sync" in out,
          "rc=%d" % rc)

    # ---------------------------------------------- the hook, as actually installed
    src = os.path.join(HERE, "ops", "pre-commit.synchold")
    inst = os.path.join(HERE, ".git", "hooks", "pre-commit")
    check("A117.8a the tracked hook source exists", os.path.isfile(src), src)
    if os.path.isdir(os.path.join(HERE, ".git")):
        check("A117.8b the hook is installed", os.path.isfile(inst), inst)
        if os.path.isfile(inst) and os.path.isfile(src):
            check("A117.8c the installed hook is the tracked one",
                  sha(inst) == sha(src), "")
    else:
        RESULTS.append(("A117.8b the hook is installed", None, "no .git here (staged copy)"))
        print("%-6s %-58s %s" % ("SKIP", "A117.8b the hook is installed",
                                 "no .git here (staged copy)"))

    # The hook must do NOTHING when the commit does not touch the core, and must
    # never block. Driven for real in a planted repository.
    if shutil.which("sh"):
        td6 = plant()
        shutil.copyfile(SYNCER, os.path.join(td6, "covenant_sync_held_core.py"))
        shutil.copyfile(os.path.join(HERE, "test_p18_version_collision.py"),
                        os.path.join(td6, "test_p18_version_collision.py"))
        shutil.copyfile(src, os.path.join(td6, "hook.sh"))
        h6 = os.path.join(td6, "pending-v9.98", CORE)
        write(h6, core_text("v9.99", "\n# drift the hook should fix\n"))
        git(td6, "add", "pending-v9.98/" + CORE)
        keep6 = sha(h6)

        # nothing staged that touches the core
        git(td6, "reset", "-q", "--", CORE)
        p = subprocess.run(["sh", "hook.sh"], cwd=td6, capture_output=True,
                           text=True, timeout=300)
        check("A117.9a the hook does nothing when the core is not in the commit",
              p.returncode == 0 and sha(h6) == keep6, "rc=%d" % p.returncode)

        # now the core IS staged
        git(td6, "add", CORE)
        p = subprocess.run(["sh", "hook.sh"], cwd=td6, capture_output=True,
                           text=True, timeout=300)
        out6 = (p.stdout or "") + (p.stderr or "")
        check("A117.9b with the core staged, the hook re-syncs the held copy",
              sha(h6) == sha(os.path.join(td6, CORE)), "")
        check("A117.9c ...and stages it into the same commit",
              "pending-v9.98" in git(td6, "diff", "--cached", "--name-only").stdout, "")
        check("A117.9d ...and exits 0 even though it could not write a manifest here",
              p.returncode == 0, "rc=%d; %s" % (p.returncode, "said so" if "MANIFEST" in out6 else "silent"))
    else:
        for lbl in ("A117.9a", "A117.9b", "A117.9c", "A117.9d"):
            RESULTS.append((lbl + " hook behaviour", None, "no POSIX sh on this machine"))
            print("%-6s %-58s %s" % ("SKIP", lbl + " hook behaviour", "no POSIX sh"))

    passed = sum(1 for _, o, _ in RESULTS if o is True)
    failed = sum(1 for _, o, _ in RESULTS if o is False)
    skipped = sum(1 for _, o, _ in RESULTS if o is None)
    print("")
    print("A117: %d passed, %d failed, %d skipped" % (passed, failed, skipped))
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                             # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)
