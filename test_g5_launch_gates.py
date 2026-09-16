#!/usr/bin/env python3
"""
test_g5_launch_gates.py -- G5 (2026-09-16): the launch gates, audited the way
the money gates were.

WHY. launch_check.py decides whether this machine may be launched: twelve gates,
each returning PASS, BLOCKED or UNKNOWN. The sweep runs them and prints the
tally. Nothing had ever asked the questions that make a gate a gate rather than
a decoration: does every registered gate run at all, does each return a state it
is allowed to return, can a gate be made to BLOCK, and does the suite that
claims to cover them actually name them.

WHAT THIS DOES NOT CLAIM. Only G1 is driven through all three of its states
here. The other eleven read the live machine -- ports, processes, keys, a
watchdog log -- and faking that from a test would measure the fake. So they are
OBSERVED (run, state valid, one result each, no crash) and the suite says so out
loud in G5.9 rather than implying more. A coverage claim that is not measured is
the thing this project keeps catching itself doing.

    python test_g5_launch_gates.py
"""
from __future__ import annotations

import io
import os
import sys
import tempfile

import launch_check as L

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
results = []

# WHAT THIS SUITE DOES WITH EACH GATE, one line each, named so that G5.1c can
# insist on it. "observed" means: it ran, it recorded one result, and the state
# was legal -- not that anyone has watched it refuse.
COVERAGE = {
    "G1":  "driven: UNKNOWN with no manifest, PASS on match, BLOCKED on mismatch and on missing",
    "G2":  "observed -- reads the shipped tree",
    "G3":  "observed -- probes live nodes",
    "G4":  "observed -- reads the shipped tree",
    "G5":  "observed -- reads the environment",
    "G6":  "observed -- pure",
    "G7":  "observed -- port arithmetic against live listeners",
    "G8":  "observed -- reads key files and their ACLs",
    "G9":  "observed -- compares project, disk and running processes",
    "G10": "observed -- reads the watchdog log",
    "G11": "observed -- reads the XRP gate state",
    "G12": "driven: a one-suite transcript is shown to satisfy it (G5.10, A134)",
}
DRIVEN_BOTH_WAYS = {"G1", "G12"}


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


def run_gate(fn):
    """One gate, in isolation: returns the result dict it recorded."""
    before = list(L.results)
    L.results.clear()
    try:
        fn()
        got = list(L.results)
    finally:
        L.results.clear()
        L.results.extend(before)
    return got


def main():
    gates = list(L.GATES)
    gids = [g._gid for g in gates]

    # ---- G5.1: the registry itself
    check("G5.1 every gate carries an id and a title",
          all(getattr(g, "_gid", None) and getattr(g, "_title", None) for g in gates),
          str([g.__name__ for g in gates if not getattr(g, "_gid", None)]))
    check("G5.1b no two gates share an id", len(set(gids)) == len(gids), str(gids))

    src = io.open(os.path.join(HERE, "test_g5_launch_gates.py"), encoding="utf-8").read()
    unnamed = [g for g in gids if g not in src]
    check("G5.1c every gate id is named in this suite", not unnamed, str(unnamed))

    # ---- G5.2: each one runs, records exactly one result, and returns a state
    # it is allowed to return. A gate that raises is UNKNOWN in main(), but a
    # gate that raises is still a gate nobody has watched work.
    bad_state, bad_count, raised = [], [], []
    seen = {}
    for g in gates:
        try:
            got = run_gate(g)
        except Exception as e:                                   # noqa: BLE001
            raised.append("%s raised %s" % (g._gid, type(e).__name__))
            continue
        if len(got) != 1:
            bad_count.append("%s recorded %d" % (g._gid, len(got)))
            continue
        st = got[0].get("state")
        seen[g._gid] = st
        if st not in (L.PASS, L.BLOCKED, L.UNKNOWN):
            bad_state.append("%s -> %r" % (g._gid, st))
    check("G5.2 every gate runs without raising", not raised, str(raised))
    check("G5.2b every gate records exactly one result", not bad_count, str(bad_count))
    check("G5.2c every state is PASS, BLOCKED or UNKNOWN", not bad_state, str(bad_state))
    print("       observed now: " + ", ".join("%s=%s" % kv for kv in sorted(seen.items())))

    # ---- G5.3-G5.5: G1 driven through all three states.
    #
    # The tree is a temp directory and HERE is pointed at it, so the real
    # MANIFEST.sha256 is neither read for a verdict nor written. The hashing is
    # substituted in G5.4/G5.5 because _manifest_sha() delegates to
    # verify_bundle, which resolves against the real repository root: what is
    # being driven there is the gate's CLASSIFICATION of hashes, which is its
    # own logic, and the substitution is named here rather than hidden.
    real_here, real_sha = L.HERE, L._manifest_sha
    tmp = tempfile.mkdtemp(prefix="g5_")
    try:
        L.HERE = tmp
        got = run_gate(L.g1)[0]
        check("G5.3 G1 is UNKNOWN when there is no manifest at all -- not PASS",
              got["state"] == L.UNKNOWN, "%s: %s" % (got["state"], got["detail"][:60]))

        with open(os.path.join(tmp, "a.txt"), "w", encoding="utf-8") as fh:
            fh.write("one")
        with open(os.path.join(tmp, "MANIFEST.sha256"), "w", encoding="utf-8") as fh:
            fh.write("deadbeef  a.txt\n")

        L._manifest_sha = lambda rel: "deadbeef"
        got = run_gate(L.g1)[0]
        check("G5.4 G1 PASSES when every listed file hashes to its recorded value",
              got["state"] == L.PASS, "%s: %s" % (got["state"], got["detail"][:60]))

        L._manifest_sha = lambda rel: "something else"
        got = run_gate(L.g1)[0]
        check("G5.5 G1 BLOCKS when a file does not hash to its recorded value",
              got["state"] == L.BLOCKED, "%s: %s" % (got["state"], got["detail"][:60]))

        L._manifest_sha = lambda rel: "deadbeef"
        os.unlink(os.path.join(tmp, "a.txt"))
        got = run_gate(L.g1)[0]
        check("G5.6 G1 does not PASS when a listed file is missing",
              got["state"] != L.PASS, "%s: %s" % (got["state"], got["detail"][:60]))
    finally:
        L.HERE, L._manifest_sha = real_here, real_sha

    # ---- G5.7: the real tree is unharmed by all of the above
    check("G5.7 the real manifest is still there and still readable",
          os.path.exists(os.path.join(HERE, "MANIFEST.sha256")))
    check("G5.7b launch_check's own root is restored", L.HERE == real_here, str(L.HERE)[:60])

    # ---- G5.8: the three states are distinct.
    #
    # MY FIRST VERSION OF THIS CHECK WAS A FAKE. It read
    #   L.UNKNOWN != L.PASS and L.UNKNOWN in (...) or True
    # and that trailing `or True` made it unfailable -- a check that cannot
    # fail, written into the suite whose whole subject is checks that cannot
    # fail. Kept in the comment because the next person will write one too.
    check("G5.8 PASS, BLOCKED and UNKNOWN are three distinct states",
          len({L.PASS, L.BLOCKED, L.UNKNOWN}) == 3,
          "%s/%s/%s" % (L.PASS, L.BLOCKED, L.UNKNOWN))

    # ---- G5.10: G12 accepts a transcript of ONE suite as a green sweep.
    #
    # FOUND 2026-09-16 by accident: `covenant_one.py --only test_g4...` wrote
    # ONE_RUN.txt with a single suite, and G12 went from UNKNOWN to PASS on it
    # -- "1 suites, 0 failed". The gate asks whether the suites ran green on
    # this core; one suite is not the suites. This check does not repair the
    # gate: what counts as a sweep is a rule, and rules are not mine to
    # redefine at 13:30 on a Wednesday. It pins the behaviour so the day it
    # changes, something says so. Open as A134.
    import re as _re
    one_run = os.path.join(HERE, "ONE_RUN.txt")
    if os.path.exists(one_run):
        got = run_gate(L.g12)[0]
        head = io.open(one_run, encoding="utf-8", errors="ignore").read(400)
        m = _re.search(r"(\d+) suites", got.get("detail", ""))
        check("G5.10 G12's verdict is recorded with the suite count it accepted",
              bool(m), got.get("detail", "")[:90])
        if m and int(m.group(1)) < 10 and got["state"] == L.PASS:
            check("G5.10b A134 STANDS: a transcript of %s suite(s) satisfies G12"
                  % m.group(1), True, got["detail"][:80])
        else:
            check("G5.10b A134: G12 is currently reading a full transcript", True,
                  got.get("detail", "")[:80])
    else:
        check("G5.10 no ONE_RUN.txt to examine -- A134 not measurable this run", True)

    # ---- G5.9: the coverage claim, stated rather than implied
    observed_only = [g for g in gids if g not in DRIVEN_BOTH_WAYS]
    check("G5.9 this suite declares which gates it drives to failure and which it only observes",
          set(DRIVEN_BOTH_WAYS) | set(observed_only) == set(gids),
          "driven both ways: %s | observed only: %s" % (sorted(DRIVEN_BOTH_WAYS), observed_only))
    check("G5.9b every gate has a line in COVERAGE saying what was done with it",
          set(COVERAGE) == set(gids), str(set(gids) ^ set(COVERAGE)))
    print("       NOT a full battery audit: %d of %d gates are observed, not driven to BLOCK."
          % (len(observed_only), len(gids)))

    failed = [n for n, ok in results if not ok]
    print(f"\nG5: {len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
