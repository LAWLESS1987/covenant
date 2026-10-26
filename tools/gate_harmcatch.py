#!/usr/bin/env python3
"""The KEYSTONE measurement (2026-10-25, all four voices + Tetsu agreed): the LIVE gate's real harm-catch rate on
an EXTERNAL, published benchmark -- NOT a simulation we wrote. Tien: "a simulated 28/28 is a test of the
simulation, not the gate."

Set: HateCheck (Rottger et al. 2021), a published hate-speech functional test. Hateful cases are genuinely
harmful content the gate SHOULD convict (harm-catch / recall); non-hateful contrasts it SHOULD clear
(false-conviction / the over-conviction surface). We measure BOTH -- recall without the false-positive rate is
the trap, because a gate that convicts everything has 100% recall and no value.

Builds the SAME gate the node uses (build_semantic_quorum + ReasoningSentinel + DIVINE_PRINCIPLES) and judges
each case as a shared-text transaction, exactly as the agent door does. Read-only; nothing is sent or acted on;
the harmful items get CONVICTED, which is the safe direction. Reports aggregate rates only.

Usage: python tools/gate_harmcatch.py [N_PER_CLASS]   (needs the node's venv for the judge providers)."""
import csv, os, random, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
os.environ.setdefault("COVENANT_FORCE_NO_SANDBOX", "1")
import covenant_unified_v8 as cov

N = int(sys.argv[1]) if len(sys.argv) > 1 else 50
HATECHECK = os.path.join(HERE, "eval", "outside", "raw", "hatecheck", "test.csv")


def verdict(sentinel, text):
    tx = cov.Transaction(sender_pubkey="eval", receiver="collective",
                         data={"origin": "human", "kind": "shared", "message": str(text)[:4000]},
                         amount=0.0, benefit_score=0.5)
    ok, message, _benefit, result = sentinel.evaluate_transaction(tx)
    alleges_nothing = bool(result is not None and not ok and (
        getattr(result, "not_understood", False) or getattr(result, "uncertain", False)))
    if ok:
        return "cleared"
    return "alleges_nothing" if alleges_nothing else "convicted"


def run():
    rng = random.Random(7)
    rows = list(csv.DictReader(open(HATECHECK, encoding="utf-8", errors="replace")))
    hateful = [r["test_case"] for r in rows if r.get("label_gold") == "hateful"]
    benign = [r["test_case"] for r in rows if r.get("label_gold") == "non-hateful"]
    rng.shuffle(hateful); rng.shuffle(benign)
    hateful, benign = hateful[:N], benign[:N]
    print("building the live gate (build_semantic_quorum + ReasoningSentinel)...", flush=True)
    judge = cov.build_semantic_quorum()
    sentinel = cov.ReasoningSentinel(judge, cov.DIVINE_PRINCIPLES)
    from collections import Counter
    res = {"hateful": Counter(), "non-hateful": Counter()}
    for label, items in (("hateful", hateful), ("non-hateful", benign)):
        for i, t in enumerate(items):
            res[label][verdict(sentinel, t)] += 1
            if (i + 1) % 10 == 0:
                print("  %s %d/%d" % (label, i + 1, len(items)), flush=True)
    nh, nb = sum(res["hateful"].values()), sum(res["non-hateful"].values())
    caught = res["hateful"]["convicted"] + res["hateful"]["alleges_nothing"]      # not cleared = held/convicted
    fconv = res["non-hateful"]["convicted"] + res["non-hateful"]["alleges_nothing"]
    print("\n=== LIVE GATE on HateCheck (external, published) -- real numbers ===")
    print("HARM-CATCH (hateful not cleared): %d/%d = %.1f%%   breakdown %s" % (caught, nh, 100.0 * caught / max(1, nh), dict(res["hateful"])))
    print("FALSE-CONVICTION (non-hateful not cleared): %d/%d = %.1f%%   breakdown %s" % (fconv, nb, 100.0 * fconv / max(1, nb), dict(res["non-hateful"])))
    print("\nReading: high harm-catch is good; high false-conviction is the over-conviction (the trap). The pair is")
    print("the keystone number -- it is NOT the 28/28 sim; it is the live gate on someone else's labelled set.")


if __name__ == "__main__":
    run()
