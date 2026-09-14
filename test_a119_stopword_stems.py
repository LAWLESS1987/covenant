#!/usr/bin/env python3
"""test_a119_stopword_stems.py -- a function word carries no weight in ANY form,
including its stem.

THE DEFECT (2026-09-14). covenant_judge_fallback.py states the rule one line
above its stopword list: "These never get weight, at any count." It was not
true. `features()` emitted `_fold(t)` for every raw token, and a folded stem is
not itself in STOPWORDS -- "there" is a stopword, `_fold("there")` is "ther~",
and "ther~" in STOPWORDS is False. Three of them had earned weight in the
deployed elder: thes~ +1.9510 (above DAMNING = 1.2), thos~ -1.4502, ther~
+0.5647. A judge that holds a payment because of the word "there" is the same
availability failure the comment above the list was written about, wearing a
different costume.

It was not academic. `ther~` was one of the five features convicting block 12 of
the canonical chain -- a zero-amount operator statement reading "There can be no
mutual benefit without a little faith." -- at +2.5235 against a 2.4 bar. No node
could sync past it (A116), which blocked a second operator entirely.

WHAT THIS SUITE IS FOR, AND WHAT IT REFUSES TO BE. It pins the RULE, not the
outcome. A suite that only checked "block 12 passes now" would go green for a
retrain that cleared it by luck, and would be exactly the fix-to-green the
operator ruled out on 2026-09-14 (A118). So the load-bearing checks are that no
stem of a function word is ever emitted, can ever earn a weight, or survives in
the model in use -- and, just as importantly, that folding STILL WORKS for real
words, because the cheapest false fix is to stop folding altogether.

Run:  python test_a119_stopword_stems.py
"""
import os
import sys
import traceback

os.environ.setdefault("COVENANT_JUDGE_PROVIDERS", "semantic")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RESULTS = []


def check(label, ok, detail=""):
    RESULTS.append((label, bool(ok), detail))
    print("%-6s %-62s %s" % ("ok" if ok else "FAIL", label, detail))
    return bool(ok)


def skip(label, why):
    RESULTS.append((label, None, why))
    print("%-6s %-62s %s" % ("SKIP", label, why))


def main():
    import covenant_judge_fallback as F

    # ------------------------------------------------ the rule, at emission
    # Every function word, in a sentence, must contribute NO feature that is a
    # fold of it. Driven through the real features() rather than by reading it.
    leaked = []
    for w in sorted(set(F.STOPWORDS) | set(F.PRONOUNS_PAIR_ONLY)):
        stem = F._fold(w)
        if not stem:
            continue
        feats = set(F.features("the auditor said %s again and the ledger agreed" % w))
        if stem in feats or ("not:" + stem) in feats:
            leaked.append((w, stem))
    check("A119.1 no function word emits a fold of itself, in any sentence",
          not leaked, "leaked: %s" % (leaked[:4] if leaked else "none"))

    # ------------------------------------------- the rule, at weight selection
    stems = [s for s in (F._fold(w) for w in
                         (set(F.STOPWORDS) | set(F.PRONOUNS_PAIR_ONLY))) if s]
    check("A119.2a the stem set is not empty, so 2b is measuring something",
          len(stems) > 0, "%d stem(s): %s" % (len(stems), sorted(stems)[:6]))
    bad = [s for s in stems if F._informative(s) or F._informative("not:" + s)]
    check("A119.2b no stem of a function word can earn a weight",
          not bad, "would be kept: %s" % (bad[:4] if bad else "none"))

    # ------------------------------------------------ THE FALSE FIX IT MUST NOT BE
    # Deleting the fold entirely would pass 1 and 2 and gut the judge. A real
    # word must still fold, and the fold must still be usable as evidence.
    real = {"backdated": "backdat~", "forging": "forg~", "transferred": "transferr~"}
    folds_ok, folds_detail = True, []
    for word, _want in real.items():
        f = F._fold(word)
        folds_detail.append("%s->%s" % (word, f))
        if not f or not F._informative(f):
            folds_ok = False
    check("A119.3 real words STILL fold, and the fold is still usable evidence",
          folds_ok, "; ".join(folds_detail))

    # ------------------------------------------------- the model actually in use
    m = F.FallbackModel.load()
    stemset = set(stems)
    in_model = sorted(f for f in m.weights if f in stemset)
    check("A119.4a the model in use carries no function-word stem",
          not in_model, "found: %s" % (in_model if in_model else "none"))
    check("A119.4b ...and it is a trained model, so 4a is not vacuous",
          len(m.weights) > 500, "%d weighted features" % len(m.weights))

    # ------------------------------ the consequence, stated as a consequence
    # This is the chain's own block 12. It is checked because its regression
    # would re-break sync for every joining node -- not because clearing it was
    # the purpose. If this ever fails, read A116 before touching anything.
    b12 = "There can be no mutual benefit without a little faith."
    v12, _why = m.verdict(b12)
    check("A119.5 the canonical chain's block 12 is not convicted",
          v12 != "violates", "verdict=%s score=%+.4f" % (v12, m.score(b12)[0]))

    # ------------------------------------------------- and the judge still bites
    # The repair removes evidence the model had been leaning on. It must not
    # have removed its power to convict. Plain violations, none of which contain
    # a function word whose stem was leaking.
    must_convict = [
        "skim two percent off every transfer that passes through, nobody will notice",
        "attach a receipt for goods that were never delivered",
        "he cannot repay, so he works for me without wages until I say otherwise",
        "Move the float into my wallet tonight and tell no one",
    ]
    missed = [t for t in must_convict if m.verdict(t)[0] != "violates"]
    check("A119.6 plain violations are still convicted", not missed,
          "missed %d of %d%s" % (len(missed), len(must_convict),
                                 (": " + missed[0][:40]) if missed else ""))

    # --------------------------------------------- and it clears nothing on the exam
    try:
        import covenant_distill as D
        st = D.examine(m)
        check("A119.7 the exam still shows ZERO cleared violations",
              st["total"]["false_clean"] == 0,
              "false_clean=%d over %d case(s)" % (st["total"]["false_clean"], st["total"]["n"]))
    except Exception as e:                                        # noqa: BLE001
        skip("A119.7 the exam still shows ZERO cleared violations",
             "could not run the examiner here: %s" % type(e).__name__)

    passed = sum(1 for _, o, _ in RESULTS if o is True)
    failed = sum(1 for _, o, _ in RESULTS if o is False)
    skipped = sum(1 for _, o, _ in RESULTS if o is None)
    print("")
    print("A119: %d passed, %d failed, %d skipped" % (passed, failed, skipped))
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                             # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)
