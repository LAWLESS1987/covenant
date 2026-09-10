#!/usr/bin/env python3
"""
A85 -- the manifest lists FILENAMES, and this repository is public.

THE HAZARD, measured 2026-09-10. `covenant_seal.py manifest` is the documented
way to refresh MANIFEST.sha256. Its walk excluded .venv, __pycache__, .git,
logs, node_modules and the scratch restore directories -- and not `private/`,
which is gitignored at .gitignore:210 precisely because a per-asset quantity is
the portfolio and CONSTITUTION II.4 keeps that unpublished.

Running the documented command produced:

    25859 in manifest, 25859 changed or missing
      24638 entries under .claude/worktrees   (leftover agent worktrees)
        466 entries under private/            (names like
                                               portfolio_whole_*.csv,
                                               coinbase_balances_*.csv)

MANIFEST.sha256 is TRACKED. The committed copy has zero private/ entries -- it
was built on 2026-09-09, before private/ had grown -- so nothing has been
published. The next regeneration would have published 466 filenames.

It was also simply wrong as a manifest: private/ is not part of the delivery, so
a verifier on another machine could never match it, and a record that reports
"25859 of 25859 changed" certifies nothing about anything.

THE GENERAL INVARIANT, which is what M3 pins. The two names are the instance;
the rule is that **the manifest must never list a path git refuses to track**.
Anything gitignored is either private, generated, or not part of the delivery --
all three are reasons it does not belong in a public integrity record. Pinning
the rule rather than the two directory names is what makes the next private
directory safe without another edit.

WHY THESE CHECKS ARE BEHAVIOURAL. They run the real `covenant_seal.walk()` over
the real tree and ask real `git check-ignore`. Nothing here reads the source of
covenant_seal.py or asserts on a string in it -- that is the fake-guard shape
A74 found in 35 of 36 suites.

CHECKS (fast, read-only, writes nothing):
  M1  the walk yields nothing under private/
  M2  the walk yields nothing under .claude/ (agent scratch and worktrees)
  M3  THE RULE: the walk yields nothing git ignores, whatever it is called
  M4  ...and it still covers the actual deliverables, so the exclusion did
      not over-reach into the thing the manifest is for
  M5  the COMMITTED MANIFEST.sha256 names no private/ path -- guarding the
      artifact on disk, not only the generator that writes it
"""
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_seal as S  # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    detail = "" if detail == "" or detail is None else str(detail)[:110]
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label,
                           ("  -- " + detail) if detail else ""))


def git_ignored(paths):
    """The subset of `paths` that git ignores. One batched call: asking 750
    times individually is slow enough that someone would be tempted to sample,
    and a sampled privacy check is not a privacy check."""
    if not paths:
        return set()
    # -z, BOTH WAYS. With newline-separated input the pipe translates "\n" to
    # "\r\n" on Windows, git takes the "\r" as part of the filename, and the
    # answers come back quoted with a trailing \r -- so the paths reported are
    # not the paths asked about. NUL separators have no such ambiguity, and a
    # privacy check whose own output is mangled is not a privacy check.
    p = subprocess.run(["git", "check-ignore", "-z", "--stdin"], cwd=HERE,
                       input="\0".join(paths).encode("utf-8"),
                       capture_output=True)
    # rc 0 = some ignored, 1 = none ignored, >1 = the command itself failed.
    if p.returncode > 1:
        return None                      # cannot tell; the caller must say so
    return {x.decode("utf-8", "replace").replace("\\", "/")
            for x in p.stdout.split(b"\0") if x.strip()}


def main():
    print("A85 -- the manifest must not list what git refuses to track\n")

    walked = [rel for rel, _full in S.walk()]
    check("M0 the walk returns a plausible tree at all (the premise)",
          len(walked) > 100, "%d files" % len(walked))

    under_private = [f for f in walked if f == "private" or f.startswith("private/")]
    check("M1 the walk yields nothing under private/ -- a per-asset quantity is "
          "the portfolio (CONSTITUTION II.4)",
          not under_private, "%d found: %s" % (len(under_private), under_private[:3]))

    under_claude = [f for f in walked if f.startswith(".claude/")]
    check("M2 the walk yields nothing under .claude/ -- agent scratch and "
          "leftover worktrees are not the delivery",
          not under_claude, "%d found" % len(under_claude))

    ignored = git_ignored(walked)
    if ignored is None:
        check("M3 THE RULE: nothing the walk yields is git-ignored", False,
              "git check-ignore did not run -- unknown, not clean")
    else:
        check("M3 THE RULE: nothing the walk yields is git-ignored, whatever it "
              "is named -- ignored means private, generated, or not shipped",
              not ignored, "%d ignored: %s" % (len(ignored), sorted(ignored)[:3]))

    # M4 -- the exclusion must not have eaten the delivery it exists to record.
    must_cover = ["covenant_unified_v8.py", "guards.py", "covenant_trader.py",
                  "docs/CONSTITUTION.md", "README.md"]
    walked_set = set(walked)
    missing = [f for f in must_cover if f not in walked_set]
    check("M4 ...and the walk still covers the actual deliverables, so the "
          "exclusion did not over-reach", not missing, missing)

    # M5 -- the artifact itself, not just the generator that writes it.
    mpath = os.path.join(HERE, "MANIFEST.sha256")
    if not os.path.exists(mpath):
        check("M5 the committed MANIFEST.sha256 names no private/ path", False,
              "MANIFEST.sha256 is absent -- unknown, not clean")
    else:
        body = io.open(mpath, encoding="utf-8", errors="replace").read()
        leaked = [ln for ln in body.splitlines()
                  if "private/" in ln or "\\private\\" in ln]
        check("M5 the committed MANIFEST.sha256 names no private/ path -- the "
              "artifact on disk, not only the generator",
              not leaked, "%d line(s)" % len(leaked))

    n = sum(1 for _, ok in results if ok)
    print("\nA85: %d/%d passed" % (n, len(results)))
    return 0 if n == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
