#!/usr/bin/env python3
"""XB1 -- the provenance/export logs have an export boundary (Moltbook 2026-10-26, u/neo_konsi_s2bw:
"the trace exporter is your agent's least reviewed data-access API ... it needs its own authorization
boundary"). Covenant's leg-influence ledger and the WITHHELD (private, A263) teacher twin hold provenance
that must never leave the machine via a push. They are gitignored and untracked today -- this pins that so a
refactor dropping a .gitignore line is caught, not silent.

Driven BOTH ways (rule 8): the sensitive provenance logs must be IGNORED, and a control source file
(covenant_leg.py) must NOT be ignored and MUST be tracked -- so the check distinguishes and is not the vacuous
"everything is ignored". Authoritative matcher is `git check-ignore`; where the runner has no .git (covenant_one
stages to a temp dir), the git checks report NO RESULT and a .gitignore text-membership check runs instead, so
there is always a measurement and the blind spot is named (rule 9). Stdlib only."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

SENSITIVE = [                                                   # provenance/export logs that must stay off every push
    "ops/leg_influence.jsonl",                                 # leg-influenced learning tombstones (A389/CXR-5)
    "ops/teacher_queue.withheld.jsonl",                        # private items answered locally, withheld (A263)
    "ops/teacher_queue.jsonl",                                 # the teacher queue itself (runtime)
]
CONTROL = "covenant_leg.py"                                    # a tracked source file: must NOT be ignored

fails, results = [], []


def ok(name, cond, detail=""):
    results.append(bool(cond))
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -- " + str(detail)[:160]))
    if not cond:
        fails.append(name)


def _git(args):
    """Run a git command at HERE; return (rc, out) or None if git/repo is unavailable."""
    try:
        p = subprocess.run(["git", "-C", HERE] + args, capture_output=True, text=True, timeout=20,
                           env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
        return p.returncode, (p.stdout or "").strip()
    except Exception:                                          # noqa: BLE001 -- no git / no repo
        return None


def check_ignored(path):
    r = _git(["check-ignore", path])
    if r is None:
        return None
    return r[0] == 0                                           # check-ignore exits 0 iff the path is ignored


def is_tracked(path):
    r = _git(["ls-files", "--error-unmatch", path])
    if r is None:
        return None
    return r[0] == 0


git_ok = _git(["rev-parse", "--is-inside-work-tree"]) is not None and _git(["rev-parse", "--is-inside-work-tree"])[0] == 0

if git_ok:
    for p in SENSITIVE:
        ign = check_ignored(p)
        ok("XB1 %s is IGNORED (never pushed)" % p, ign is True, "check-ignore says not ignored")
        trk = is_tracked(p)
        ok("XB1 %s is NOT tracked (no committed copy)" % p, trk is False, "it is tracked -- a committed copy exists")
    # the other way: a real source file is neither ignored nor untracked -- the check is not vacuous
    ok("XB1 control %s is NOT ignored (the boundary is specific, not 'everything')" % CONTROL,
       check_ignored(CONTROL) is False, "the control file reads as ignored -- the matcher is broken")
    ok("XB1 control %s IS tracked" % CONTROL, is_tracked(CONTROL) is True, "control not tracked")
else:
    # NO RESULT for the git checks (no .git where the runner runs it). Fall back to .gitignore membership so
    # there is still a measurement; name the blind spot rather than pass on absence (A129/NO RESULT).
    print("XB1 NOTE: no git repo here (the runner's staged tree) -- git check-ignore NOT RUN; "
          "falling back to .gitignore text membership. Blind spot: a rule that matches by pattern "
          "rather than exact path is not verified here.")
    gi = os.path.join(HERE, ".gitignore")
    rules = set()
    if os.path.isfile(gi):
        rules = {ln.strip() for ln in open(gi, encoding="utf-8", errors="ignore") if ln.strip() and not ln.startswith("#")}
    ok("XB1 .gitignore present to check", bool(rules), gi)
    for p in SENSITIVE:
        ok("XB1 .gitignore names %s as an ignore rule" % p, p in rules, "no exact ignore rule for it")
    ok("XB1 control %s is NOT a .gitignore rule" % CONTROL, CONTROL not in rules, "control is ignored")

print("\nXB1: %d/%d passed" % (sum(1 for r in results if r), len(results)))
raise SystemExit(1 if fails else 0)
