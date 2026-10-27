#!/usr/bin/env python3
"""test_r2_redundancy.py -- R2: the redundancy audit must not cry wolf.

WHAT R2 PINS, and why each property earned its place.

redundancy.py asks one question at every scale -- how many independent
carriers, and what survives the first loss. Its value is entirely in being
believed, which means the ways it can lie matter more than the ways it can be
right.

  S*  SEGMENTS, NOT SUBSTRINGS. The regression. The first version of the
      principle check matched the substring "ai_memory" against tracked paths
      and reported twelve VIOLATIONS -- every one a file under
      ai_memory_system/, which is the SOFTWARE, public on purpose, and not the
      private record at ~/ai_memory at all. On the same day, .gitignore's
      `*_secret*` swallowed test_e1_secret_egress.py and held CI red for a day.
      Twice in one day, one error: a pattern that cannot tell a thing from a
      thing ABOUT it. A guard that flags twelve innocent files to catch none is
      not cautious; nobody reads the thirteenth line of a report that has
      already cried wolf twelve times.
  L*  every level answers the SAME question and returns a countable N, because
      growth must add scales and not mechanisms. A level that needed its own
      kind of answer would be a level that does not belong.
  H*  the count is honest about what carriers SHARE. Four copies on one disk is
      not four; four nodes in one console group is not four. A redundancy
      figure that counts names rather than failure domains is a lie told with
      true numbers.
  R*  it only READS. It may run git to observe, and must never run git to
      change.
  F*  it fails SAFE. Any level that cannot be measured is reported UNKNOWN and
      never counted as redundant, because an unmeasured level is not a safe one.

Pure: no network, no writes, no node required.
"""
import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import redundancy as r   # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'}  {label}"
          f"{'' if ok else '  ' + str(detail)[:170]}", flush=True)


def flagged(path):
    """Reimplements the classifier's decision for one path.

    A COPY, and read it as one: S1-S3 below can only ever check this
    restatement of the rule. S1b/S2b run the shipped code instead.
    See shipped_flags().
    """
    segs = re.split(r"[\\/]", path)
    base = segs[-1] if segs else ""
    return (any(s in r.FORBIDDEN_SEGMENTS for s in segs[:-1])
            or base in r.FORBIDDEN_NAMES)


def shipped_flags(path):
    """Ask the SHIPPED classifier about one path -- by running it.

    WHY THIS EXISTS. flagged() above is a hand copy of the two branch
    conditions inside principle_check, so S1-S3 assert against the copy and
    never against the tool. Replacing both of those conditions with `False`
    -- the audit blind to the private corpus, the node keys and the audit
    chain, which is the exact failure this file exists to prevent -- left the
    suite at 17/17 passed, exit 0. A test that re-implements the thing it
    guards cannot notice that thing being deleted.

    So: stub the tracked-file listing, run the real principle_check, and
    report what it actually decided.

    Returns True or False, or None if the stub was never consulted -- which
    would mean the classifier stopped reading `git ls-files` and any answer
    here is about nothing. None counts as failure at the call site; it must
    never read as a pass.

    Read-only, no subprocess, no writes: _run is restored in a finally, so the
    real-tree call at F2/F3 still measures the real tree.
    """
    seen = []
    real = r._run

    def fake(cmd, timeout=10):
        if list(cmd[:2]) == ["git", "ls-files"]:
            seen.append(tuple(cmd))
            return path
        return ""

    try:
        r._run = fake
        findings, _ = r.principle_check()
    finally:
        r._run = real
    return bool(findings) if seen else None


def main():
    print("R2 -- the redundancy audit, and the ways it could lie\n")

    # ---- S: the regression -- segments, not substrings ---------------------
    must_flag = [
        "ai_memory/some-memory.md",
        "ai_memory/audit.jsonl",
        ".covenant-keys/node.pem",
        "docs/audit.jsonl",
        "ai_memory_backups/20260830/x.md",
    ]
    must_allow = [
        "ai_memory_system/main.py",
        "ai_memory_system/docs/EXPORT_FORMATS.md",
        "ai_memory_system/test_memory_system.py",
        "docs/ai_memory_notes.md",
        "redundancy.py",
    ]
    bad_miss = [p for p in must_flag if not flagged(p)]
    bad_hit = [p for p in must_allow if flagged(p)]
    check("S1 the private record, the backups and the keys are all caught",
          not bad_miss, bad_miss)
    check("S2 THE REGRESSION: ai_memory_system/ is NOT caught. It is the "
          "software, public on purpose. The first version flagged twelve of "
          "its files for containing the substring 'ai_memory' -- a guard that "
          "cannot tell the record from code ABOUT the record",
          not bad_hit, bad_hit)
    check("S3 a doc that merely NAMES the store in its filename is not "
          "treated as the store",
          not flagged("docs/ai_memory_notes.md"))
    check("S4 matching is on whole path segments, never substrings -- the "
          "property that makes S2 hold rather than an exception list",
          "ai_memory" in r.FORBIDDEN_SEGMENTS
          and "ai_memory_system" not in r.FORBIDDEN_SEGMENTS,
          r.FORBIDDEN_SEGMENTS)

    # S1b/S2b ask S1/S2 of the CODE rather than of the copy. S4 inspects the
    # DATA -- the tuple -- and the regression was in the MATCHING, which had
    # no coverage at all: with both branch conditions in principle_check
    # replaced by False, so that nothing tracked is ever reported, this suite
    # still passed 17/17. F3 could not see it either, because "found nothing"
    # is exactly what a dead classifier also returns. These two run it.
    miss = [p for p in must_flag if shipped_flags(p) is not True]
    hit = [p for p in must_allow if shipped_flags(p) is not False]
    check("S1b ...and it is the SHIPPED classifier that catches them. S1 "
          "asked a restatement living in this file; this one feeds "
          "principle_check a tracked listing and reads the verdict it "
          "returns, so deleting the check in redundancy.py turns this red",
          not miss, miss)
    check("S2b ...and it is the SHIPPED classifier that lets "
          "ai_memory_system/ through -- the regression of S2, decided by the "
          "code that ships rather than by a copy that would go on saying the "
          "right thing long after the tool stopped",
          not hit, hit)

    # ---- L: one question, every scale --------------------------------------
    check("L1 there are levels, and each is (tag, name, callable)",
          len(r.LEVELS) >= 5
          and all(len(x) == 3 and callable(x[2]) for x in r.LEVELS),
          r.LEVELS)
    counts = {}
    for tag, name, fn in r.LEVELS:
        try:
            n, detail, note = fn()
        except Exception as e:                               # noqa: BLE001
            check("L2 every level answers without raising (%s)" % tag, False, e)
            continue
        counts[tag] = n
        if not isinstance(n, int) or n < 0:
            check("L2 %s returns a countable N" % tag, False, n)
    check("L2 every level answered with a countable N -- the same question at "
          "every scale, which is what lets a new level be a new ROW and not "
          "new machinery",
          len(counts) == len(r.LEVELS), counts)
    check("L3 the operator level is measured, and is the one that caps the "
          "structure. If this ever reads above 1 without a second person "
          "genuinely holding keys, the measurement has started lying",
          counts.get("L5") == 1, counts.get("L5"))

    # ---- H: honest about shared failure ------------------------------------
    src = open(os.path.join(HERE, "redundancy.py"), encoding="utf-8").read()
    for tag, name, fn in r.LEVELS:
        if tag != "L1":
            continue
        _, _, note = fn()
        check("H1 the record level SAYS that copies sharing a disk are not "
              "independent -- counting names instead of failure domains is a "
              "lie told with true numbers",
              "disk" in note.lower() and "share" in note.lower(), note[:120])
    for tag, name, fn in r.LEVELS:
        if tag != "L3":
            continue
        _, _, note = fn()
        check("H2 the node level SAYS four nodes in one console group is a "
              "redundancy of 1, and cites the outage that proved it",
              "console" in note.lower() and "1" in note, note[:120])
    check("H3 the report names the weakest level as the cap, rather than "
          "reporting an average -- an average hides exactly the level that "
          "decides the outcome",
          "weakest" in src and "capped" in src)

    # ---- R: it only reads --------------------------------------------------
    tree = ast.parse(src)
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                called.add(f.id)
            elif isinstance(f, ast.Attribute):
                called.add(f.attr)
    banned = called & {"system", "remove", "unlink", "rmtree", "rename",
                       "mkdir", "makedirs", "urlopen", "sendall", "kill"}
    check("R1 it calls nothing that deletes, moves, creates or transmits. It "
          "may run git to OBSERVE and must never run git to CHANGE",
          not banned, sorted(banned))
    git_cmds = re.findall(r"\[\"git\",\s*\"([a-z-]+)\"", src)
    check("R2 every git subcommand it runs is read-only",
          all(g in ("ls-files", "remote", "status", "log", "rev-parse",
                    "check-ignore") for g in git_cmds), git_cmds)
    check("R3 no file is opened for writing anywhere in it",
          not re.search(r"open\([^)]*[\"'][wa]", src))

    # ---- F: fails safe -----------------------------------------------------
    check("F1 an unmeasurable level is reported UNKNOWN and NOT counted as "
          "redundant -- an unmeasured level is not a safe one",
          "UNKNOWN" in src and "not counted as redundant" in src.lower()
          or "Not counted as redundant" in src)
    findings, ign = r.principle_check()
    check("F2 the principle check runs on the real tree and returns a list, "
          "not an exception", isinstance(findings, list))
    check("F3 ...and finds NOTHING today: nothing tracked carries the corpus, "
          "the audit chain or the keys. If this ever fails, stop and read it "
          "before adding another copy of anything",
          findings == [], findings)
    check("F4 the bound is stated in the source, not left to good intentions "
          "-- survival bought by breaking the rule is not survival",
          "mutual benefit" in src.lower())

    n = len(results)
    ok = sum(results)
    print(f"\nR2: {ok}/{n} passed")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
