#!/usr/bin/env python3
"""mutation_probe.py -- the A74 method as a repeatable tool, not a one-off.

WHY THIS EXISTS. G3 (test_g3_behavioural_guards.py) counts the fake-guard shape
a machine can SEE in the source -- `"literal" in src`. By its own honest
accounting it catches 7 of the 28 guards confirmed fake on 2026-09-09. The
other 21 fail SEMANTICALLY: the test re-implements its subject and checks the
copy; the fixture is hand-copied from the answer; only the except-branch runs,
so the gate is never once observed admitting anything; the assertion is aimed
at the wrong region. No AST pattern can tell those from a real check. Only
breaking the behaviour and watching the suite can.

A74 did exactly that on 2026-09-09: 36 suspected guards mutated, each in its own
git worktree, and 35 did not notice. That was a person's afternoon, run once.
This file is that method as a table you can re-run: for each (suite, subject,
mutation) it stands up ONE staging worktree at HEAD, confirms the suite is GREEN
unmutated, writes the mutated bytes, runs the suite again, and asks the one
question -- did the suite go RED, and did it go red ON ITS OWN CHECK?

WHAT A VERDICT MEANS, AND WHAT IT DOES NOT.
  CAUGHT         green unmutated, red (with its own FAIL line) when mutated.
                 The guard noticed. This is evidence the guard is real FOR THIS
                 ONE MUTATION -- never a clean bill of health for the suite.
  MISSED         green unmutated, STILL GREEN when the behaviour is broken.
                 This is a LEAD, in the A74 sense: "prove this one", never
                 "this guard is broken". It is surfaced, never auto-fixed -- a
                 flagged guard is evidence to investigate, same invariant as
                 the dedup and recurrence work.
  INDETERMINATE  the baseline was not green, the mutation did not apply the
                 expected number of times, or the mutant run died with a
                 traceback and no own FAIL line (a NO RESULT is not a pass and
                 is not a catch either). Reported loudly, never folded in.

RULE-10 NOTE. This tool MEASURES. It does not edit any guard it flags, and it
restores every mutated file before the next target. It fails the process on an
INDETERMINATE (something could not be measured) and on no MISSED by itself --
because a MISSED is a lead for a person, and turning a lead into a red build is
the operator's call (rule 5), not this tool's.

Mutations are byte-level and newline-free substrings, so CRLF/LF checkout does
not change them; each declares how many times it must apply, and a count that
does not match ABORTS that target rather than guessing (rule 2/7).

Run:  python tools/mutation_probe.py            measure, print a table
      python tools/mutation_probe.py --verbose  also print each mutant's tail
LICENCE: public domain.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Two groups. FIRST, a "handful of high-value guards" (the brief): the reserve
# clamp A74 named as its worst case, its unit-level floor, the tally parser K2
# pins, and the venue money-gate V2 pins. SECOND (added when the probe was
# pointed at the A74 SEMANTIC MISSES): three suites A74 REPAIRED 2026-09-09 by
# adding a behavioural check beside a source-reading one. For these, the probe
# re-breaks the exact behaviour each repair's own journal names, so a CAUGHT is
# that repair still earning its green and a MISSED would be a regression lead --
# NOT a fresh find (these were already repaired). k3's owner-only repair
# (MainnetGuardError translation / require_owner_only narrowing) is a documented
# candidate left OUT for now: its mutation is an ACL/icacls insertion whose
# verdict would turn on the platform, not on the guard. Each target names the
# behaviour in words so a MISSED reads as a sentence, not a diff.
TARGETS = [
    {
        "id": "f5-plan-clamp",
        "suite": "test_f5_reserve.py",
        "subject": "covenant_trader.py",
        "behaviour": "plan() clamps a sell down to the sellable units "
                     "(the 50% reserve and the frozen HOLD_ONLY floor)",
        "find": b"qty = sellable",
        "replace": b"qty = qty  # mutation_probe: clamp neutralised",
        "count": 2,  # both clamps, exactly as A74 deleted them
    },
    {
        "id": "f5-frozen-floor",
        "suite": "test_f5_reserve.py",
        "subject": "guards.py",
        "behaviour": "sellable_units returns 0.0 (KNOWN zero) for a HOLD_ONLY "
                     "asset with no baseline -- nothing of it is sellable",
        "find": b"return 0.0 if full else None",
        "replace": b"return (held or 0.0) if full else None",
        "count": 1,
    },
    {
        "id": "k2-tally-parser",
        "suite": "test_k2_tally_arithmetic.py",
        "subject": "run_all_tests.sh",
        "behaviour": "the sweep parser reads the TOTAL from the 'N/M passed' "
                     "A/B form (cut -d/ -f2), not the passed count",
        "find": b"cut -d/ -f2",
        "replace": b"cut -d/ -f1",
        "count": 1,
    },
    {
        "id": "v2-venue-live-default",
        "suite": "test_v2_venue_guarantee.py",
        "subject": "venues.py",
        "behaviour": "a venue adapter's place() defaults live=False -- an order "
                     "goes to VALIDATE, never the live book, unless armed",
        "find": b'live=False, ordertype="market", price=None):',
        "replace": b'live=True, ordertype="market", price=None):',
        "count": 1,
    },
    # ---- A74-repaired suites: confirm the repair still catches the break ----
    {
        "id": "b2-arming-block",
        "suite": "test_b2_quorum_diversity.py",
        "subject": "covenant_unified_v8.py",
        "behaviour": "build_semantic_quorum arms COVENANT_REQUIRE_JUDGE_DIVERSITY "
                     "on the report's answer -- it refuses a NON-diverse quorum, "
                     "never a genuinely diverse one (E3b walks the diverse case, "
                     "where A74's E3 only ever reached its except-branch)",
        "find": b'if not rep.get("diverse"):',
        "replace": b"if True:  # mutation_probe: arm on every build",
        "count": 1,
    },
    {
        "id": "r2-private-record-flag",
        "suite": "test_r2_redundancy.py",
        "subject": "redundancy.py",
        "behaviour": "principle_check FLAGS a git-tracked path inside a private "
                     "segment (the record, the backups, the keys); S1b/S2b run "
                     "the shipped classifier, not the hand-copied rule A74 found",
        "find": b"if any(s in FORBIDDEN_SEGMENTS for s in segments[:-1]):",
        "replace": b"if False and any(s in FORBIDDEN_SEGMENTS "
                   b"for s in segments[:-1]):",
        "count": 1,
    },
    {
        "id": "p20-self-eval-write-gate",
        "suite": "test_p20_watchdog_self_eval.py",
        "subject": "covenant_watchdog.py",
        "behaviour": "one_pass actually WRITES the self-eval ledger when the round "
                     "gate fires; E11c/d RUN one_pass and read the bytes, where "
                     "A74's source-reading E11a/b stay green on this same break",
        "find": b'if SELF_EVAL_EVERY > 0 and _self_eval["round"] '
                b'% SELF_EVAL_EVERY == 0:',
        "replace": b'if False and _self_eval["round"] % SELF_EVAL_EVERY == 0:',
        "count": 1,
    },
]


def run_suite(wt, suite):
    """Run one suite in the staging worktree. -B: no .pyc, so a stale cache
    never masks a mutation (mutation-driver rule). Returns (exit, output)."""
    env = dict(os.environ)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env.setdefault("PYTHONUTF8", "1")
    try:
        r = subprocess.run([sys.executable, "-B", suite],
                           cwd=wt, capture_output=True, text=True,
                           timeout=600, env=env)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as e:
        return 124, "TIMEOUT: %s" % e


def own_fail_lines(output):
    """Lines that look like a suite's OWN failed check, not a crash. The suites
    here print 'FAIL:' / '  FAIL ' for a failed check; a bare traceback is not
    one. This is how a NO RESULT is kept from reading as a catch."""
    out = []
    for ln in output.splitlines():
        s = ln.strip()
        if s.startswith("FAIL:") or s.startswith("FAIL ") or " FAIL:" in s \
                or s.startswith("x ") and "FAIL" in s:
            out.append(s[:120])
    return out


def has_traceback(output):
    return "Traceback (most recent call last)" in output


def git(args, cwd=ROOT):
    return subprocess.run(["git", "--no-optional-locks"] + args, cwd=cwd,
                          capture_output=True, text=True)


def main():
    verbose = "--verbose" in sys.argv[1:]
    stage = tempfile.mkdtemp(prefix="mutprobe_")
    wt = os.path.join(stage, "wt")
    print("mutation_probe: staging a worktree at HEAD in %s" % wt)
    add = git(["worktree", "add", "--detach", wt, "HEAD"])
    if add.returncode != 0:
        print("ABORT: could not create staging worktree:\n%s" % add.stderr)
        return 2

    results = []
    try:
        for t in TARGETS:
            r = probe_one(wt, t, verbose)
            results.append(r)
    finally:
        rm = git(["worktree", "remove", "--force", wt])
        if rm.returncode != 0:
            print("WARN: worktree not removed (%s); prune later: %s"
                  % (wt, rm.stderr.strip()))

    # Report
    print("\n" + "=" * 72)
    print("MUTATION PROBE -- %d targets" % len(results))
    print("=" * 72)
    caught = missed = indet = 0
    for r in results:
        print("\n[%s] %s" % (r["verdict"], r["id"]))
        print("   suite    : %s" % r["suite"])
        print("   subject  : %s (%s applied, expected %s)"
              % (r["subject"], r["applied"], r["count"]))
        print("   behaviour: %s" % r["behaviour"])
        print("   baseline : exit %s (%s)" % (r["base_exit"],
              "GREEN" if r["base_exit"] == 0 else "NOT GREEN"))
        if r["verdict"] != "INDETERMINATE" or r["mut_exit"] is not None:
            print("   mutant   : exit %s; own FAIL lines: %d"
                  % (r["mut_exit"], len(r["fails"])))
        if r["note"]:
            print("   note     : %s" % r["note"])
        for f in r["fails"][:4]:
            print("       %s" % f)
        if r["verdict"] == "CAUGHT":
            caught += 1
        elif r["verdict"] == "MISSED":
            missed += 1
        else:
            indet += 1

    print("\n" + "-" * 72)
    print("CAUGHT %d   MISSED %d   INDETERMINATE %d" % (caught, missed, indet))
    print("A CAUGHT is evidence for ONE mutation, never a clean suite.")
    print("A MISSED is a LEAD to prove by hand, never an auto-fix (rule 5/10).")
    print("An INDETERMINATE could not be measured and is not a pass (rule 9).")
    # Report-only on MISSED (operator's call). Fail only when something could
    # not be measured.
    return 2 if indet else 0


def probe_one(wt, t, verbose):
    r = {"id": t["id"], "suite": t["suite"], "subject": t["subject"],
         "behaviour": t["behaviour"], "count": t["count"], "applied": 0,
         "base_exit": None, "mut_exit": None, "fails": [], "note": "",
         "verdict": "INDETERMINATE"}
    subj = os.path.join(wt, t["subject"])
    rel = t["subject"]

    # 1. Baseline must be GREEN, or a catch cannot be proved.
    base_exit, base_out = run_suite(wt, t["suite"])
    r["base_exit"] = base_exit
    if base_exit != 0:
        r["note"] = ("baseline not green -- cannot prove a catch here. tail: %s"
                     % base_out.strip().splitlines()[-1:])
        return r

    # 2. Apply the mutation byte-for-byte; the count must match exactly.
    with open(subj, "rb") as fh:
        raw = fh.read()
    n = raw.count(t["find"])
    r["applied"] = n
    if n != t["count"]:
        r["note"] = ("mutation applied %d times, expected %d -- subject moved; "
                     "not mutating (rule 2/7)" % (n, t["count"]))
        return r
    mutated = raw.replace(t["find"], t["replace"])
    with open(subj, "wb") as fh:          # bytes, no newline translation
        fh.write(mutated)

    try:
        mut_exit, mut_out = run_suite(wt, t["suite"])
    finally:
        git(["checkout", "--", rel], cwd=wt)   # restore before next target

    r["mut_exit"] = mut_exit
    r["fails"] = own_fail_lines(mut_out)
    if verbose:
        print("\n--- %s mutant tail ---\n%s" % (t["id"],
              "\n".join(mut_out.strip().splitlines()[-12:])))

    # 3. Classify.
    if mut_exit == 0:
        r["verdict"] = "MISSED"
        r["note"] = "behaviour broken, suite stayed GREEN -- a lead to prove"
    elif r["fails"]:
        r["verdict"] = "CAUGHT"
        r["note"] = "suite went red on its own check(s)"
    elif has_traceback(mut_out):
        r["verdict"] = "INDETERMINATE"
        r["note"] = ("mutant died with a traceback and no own FAIL line -- a "
                     "crash is not a catch (NO RESULT is not a pass)")
    else:
        r["verdict"] = "INDETERMINATE"
        r["note"] = "non-zero exit but no own FAIL line found -- inspect by hand"
    return r


if __name__ == "__main__":
    raise SystemExit(main())
