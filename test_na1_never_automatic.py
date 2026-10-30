#!/usr/bin/env python3
"""test_na1_never_automatic.py -- NA1: the self-heal engine refuses to auto-execute ANY remedy that touches
money, the things that decide money, the rules, the seats, the phone, consent, or a key -- for EVERY word on the
list, not just the six H1i happens to name.

WHY THIS EXISTS. covenant_highway.apply_remedy refuses an AUTO_REVERSIBLE remedy whose `touches` crosses any word
in highway.NEVER_AUTOMATIC, "whatever class it claims" (highway.py:3351). That tuple is the line that keeps the
engine from quietly widening its own remit -- "an engine that can quietly widen its own remit is not repairing
the system, it is replacing the person in it." test_h1_highway.py (H1i) proves this for the phone and names six
words; but the tuple has fourteen, and a careless edit that dropped `wallet`, `order`, `seat`, or `model` from it
would let the engine execute a remedy touching that subject while H1i still passed. This drives EVERY word.

The operator's principle, 2026-10-20: "I refuse for there to be a thinking class over everyone else," and the
good-faith-alliance note's reciprocal standard -- the auditor is not exempt and does not wave past a real gap.
This was a real, if narrow, gap: eight of the fourteen protected subjects were unpinned.

DRIVEN BOTH WAYS. NA1.0 the control -- an AUTO_REVERSIBLE remedy touching none of the words is EXECUTED, so the
refusals below are real, not a blanket block. NA1.<word> each word of the LIVE tuple (fourteen when written, twenty-four
since 2026-10-30) refuses on touch and never enters
the remedy. NA1.M the earned-green mutation: remove one word from NEVER_AUTOMATIC and its remedy executes;
restore it and the refusal returns -- so the refusal rides on the TUPLE, which is the thing that must not shrink.

Behavioural: drives the real apply_remedy with a fixture remedy; a spy proves whether the remedy actually ran.
Ledger and last-sense go to tempfiles; no live ops state touched. Run: python3 test_na1_never_automatic.py
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_highway as H                                           # noqa: E402

results = []


def check(label, ok, detail=""):
    results.append(bool(ok))
    print("%s  %s%s" % ("ok  " if ok else "FAIL", label, "" if ok else "  -- " + str(detail)[:300]), flush=True)


def present(measured=None):
    return {"state": H.PRESENT, "measured": measured or {"why": "a fixture"}}


def spy_remedy(calls, ok=True):
    def fn(measured, dry_run=True):
        calls.append({"dry_run": dry_run})
        return ok, "spy ran"
    return fn


def main():
    print("NA1 -- the engine auto-executes nothing touching money, a seat, a rule, the phone, consent or a key\n")
    os.environ["COVENANT_HIGHWAY_LAST_SENSE"] = tempfile.mktemp(suffix="_na1_last_sense.json")
    base = dict(H.REMEDIES["rotate_log"])            # a real AUTO_REVERSIBLE, stateless remedy to inherit fields
    DET = "log_bloat"                                # rotate_log's detector; apply_remedy matches it to r["for"]

    def run(touches, calls):
        H.REMEDIES["_na1_probe"] = dict(base, fn=spy_remedy(calls), klass=H.AUTO_REVERSIBLE,
                                        kind="stateless", touches=touches)
        H.REMEDIES["_na1_probe"].setdefault("for", [DET])
        H.REMEDIES["_na1_probe"]["for"] = [DET]
        return H.apply_remedy("_na1_probe", present(), DET, dry_run=False, cooldown_s=0,
                              ledger=tempfile.mktemp(suffix="_na1.jsonl"), choices={})

    try:
        # NA1.0 CONTROL: an AUTO_REVERSIBLE remedy touching none of the protected words runs.
        calls = []
        row = run(["a rotated log file"], calls)
        check("NA1.0 control: an AUTO_REVERSIBLE remedy touching nothing protected IS executed (so refusals are real)",
              bool(calls) and row["outcome"] != "proposed", "%s calls=%d" % (row.get("outcome"), len(calls)))

        # NA1.<word>: every word on the list refuses on touch, and never enters the remedy.
        for w in H.NEVER_AUTOMATIC:
            calls = []
            row = run(["this remedy touches the %s subject" % w], calls)
            refused = row["outcome"] == "proposed" and w in row.get("why", "")
            check("NA1[%s] a remedy touching '%s' is refused whatever class it claims, and never runs" % (w, w),
                  refused and not calls, "outcome=%s why=%s calls=%d" % (row.get("outcome"), row.get("why", "")[:60], len(calls)))

        # NA1.floor: the subjects the covenant has committed to protect are all present -- fourteen, plus the ten
        # grid words since 2026-10-30 (names the floor;
        # the behavioural cases above are what actually fail if one is dropped, but this says the intended set out loud).
        MUST = {"money", "holdings", "wallet", "trader", "venue", "order", "rule", "principle",
                "judge", "seat", "model", "phone", "consent", "key",
                # grid / ICS-OT actuation subjects (2026-10-30, covenant_grid_guard.py) -- the
                # self-heal engine proposes, never actuates the grid; pinned here as a committed floor.
                "grid", "breaker", "relay", "feeder", "substation", "setpoint",
                "load_shed", "actuat", "scada", "intertie"}
        missing = sorted(MUST - set(H.NEVER_AUTOMATIC))
        check("NA1.floor every committed subject is still on the list (money, the seats, the rules, consent, keys...)",
              not missing, "missing: %s" % missing)

        # NA1.M EARNED GREEN: the refusal rides on the TUPLE. Drop 'wallet' -> a remedy touching a wallet executes;
        # restore -> it refuses again. Proves the per-word cases above are not passing for some incidental reason.
        orig = H.NEVER_AUTOMATIC
        try:
            H.NEVER_AUTOMATIC = tuple(w for w in orig if w != "wallet")
            calls = []
            row = run(["moves funds between a wallet and another"], calls)
            flipped = bool(calls) and row["outcome"] != "proposed"
        finally:
            H.NEVER_AUTOMATIC = orig
        check("NA1.M mutation: drop 'wallet' from NEVER_AUTOMATIC and a wallet-touching remedy EXECUTES -- the "
              "refusal depends on the tuple", flipped, row.get("outcome"))
        calls = []
        row = run(["moves funds between a wallet and another"], calls)
        check("NA1.M ...and with the tuple restored, the wallet-touching remedy is refused again",
              row["outcome"] == "proposed" and not calls, row.get("outcome"))
    finally:
        H.REMEDIES.pop("_na1_probe", None)

    ok_n = sum(1 for r in results if r)
    print("\nNA1: %d/%d passed" % (ok_n, len(results)))
    return 0 if ok_n == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
