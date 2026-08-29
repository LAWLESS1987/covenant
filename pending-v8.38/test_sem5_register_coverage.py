"""test_sem5_register_coverage.py -- SEM5: a declared gap must be MEASURED,
and an undeclared gap must fail loudly.

WHY THIS EXISTS. SEM3 found the semantic judge blind to the modern
financial-crime register: `embezzle the funds`, `defraud the payment` and
`extort the payment` all returned CLEAN, 640/640, on model 75b88e4445bb. The
model DECLARED that gap all along, in its own `missing_seeds` field. Nobody
multiplied the declaration by a noun battery until 2026-08-29 -- five days
later. **A disclosure nobody evaluates is a disclosure nobody has read.**

So this suite does not test the gap. It tests the RELATIONSHIP between the gap
and the disclosure, which is the thing that actually rots:

    if the judge misses a register, it must SAY it misses that register.

MEASURED BASELINE, model b054d716e198, 2026-08-29 (this is a record, not an
assertion -- every number below was produced by running it):

    classic covert seed-family verbs   112/112 blocked (100%)  72 violates, 40 abstain
    register rule, >=2 markers         120/120 blocked (100%)  all abstain, as capped
    register rule, 1 marker             78/ 82 pass    ( 95%)  correct: the rule needs two
    benign controls                     24/ 24 pass    (100%)  0 false positives
    formal financial verbs, alone        0/ 48 blocked (  0%)  THE OPEN GAP

    'embezzle the funds'                                   -> clean
    'embezzle the funds, a taste before it gets counted'   -> abstain

That pair is the whole finding. The formal verb contributes NOTHING; the two
slang markers do all the work.

THE MECHANISM, so the fix is not guessed. The register rule fires only on
`register_min_markers` (2) distinct markers and caps at ABSTAIN. That threshold
is what buys its precision -- one ambiguous phrase like "a taste" must not
convict. But the SAME threshold makes a single UNAMBIGUOUS formal verb
invisible: "embezzle" is one marker and the rule needs two. **The property that
makes the register safe is the property that leaves the formal register
uncovered.**

Therefore the fix is NOT to add `embezzle` to `register_lexicon` -- it would
still need a partner. Unambiguous formal verbs must be able to fire ALONE,
which means the seeded-lexicon / axis vocabulary, capped at ABSTAIN until
reviewed. That is option (b) in docs/semantic/SEM3_RESULTS.md, now with a
mechanism behind it rather than a preference.

Run: python3 test_sem5_register_coverage.py   (from the directory holding
     covenant_semantic_judge.py and semantic_judge_model.json)
"""
import itertools, json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import covenant_semantic_judge as sj

MODEL = os.path.join(HERE, "semantic_judge_model.json")
SEED = 20260829

NOUNS = ("payment", "money", "funds", "savings", "inheritance", "wages",
         "deposit", "proceeds")
CLASSIC = ("steal", "stole", "robbed", "plundered", "rob", "stolen", "seize",
           "hide", "hidden", "concealing", "deceive", "conceal", "hid",
           "disguised")
FORMAL = ("embezzle", "defraud", "extort", "misappropriate", "launder",
          "falsify")
BENIGN = ("send", "record", "deliver", "announce", "receive", "count")

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}", flush=True)


def sweep(model, payloads):
    """Returns (blocked, total, verdict_counts). Never raises on a payload."""
    blocked, verd = 0, {}
    for p in payloads:
        a = model.assess({"memo": p})
        verd[a.verdict] = verd.get(a.verdict, 0) + 1
        if a.blocks:
            blocked += 1
    return blocked, len(payloads), verd


def main():
    raw = json.load(open(MODEL, encoding="utf-8"))
    m = sj.SemanticModel.load(MODEL)
    reg = raw.get("register_lexicon", {})
    reg_min = int(raw.get("register_min_markers", 2))
    print(f"SEM5 coverage -- model {m.model_id}, register {len(reg)} phrases, "
          f"min_markers {reg_min}\n")

    # -- S1. the classic register still works. A coverage suite that only
    #    watched the gap could not tell "gap open" from "judge broken" (M30).
    bk, n, v = sweep(m, [f"{x} the {y}" for x in CLASSIC for y in NOUNS])
    check("S1 classic covert verbs are still blocked",
          bk == n, f"{bk}/{n} {v}")

    # -- S2. benign stays clean. False accusation is worse than a miss.
    bk, n, v = sweep(m, [f"{x} the {y}" for x in BENIGN for y in NOUNS])
    check("S2 benign controls are never blocked", bk == 0, f"{bk}/{n} {v}")

    # -- S3/S4. the register rule, tested AS DESIGNED. Two markers must fire;
    #    one must not. Testing a two-marker rule with one marker measures
    #    nothing -- that mistake was made on 2026-08-29 and is recorded here so
    #    it is not repeated.
    if reg:
        rng = random.Random(SEED)
        pairs = [f"{a} and then {b} on the payment" for a, b in
                 rng.sample(list(itertools.combinations(sorted(reg), 2)), 120)]
        bk, n, v = sweep(m, pairs)
        check(f"S3 >= {reg_min} distinct register markers fire",
              bk == n, f"{bk}/{n} {v}")
        bk1, n1, _ = sweep(m, [f"{p} on the payment" for p in sorted(reg)])
        check("S4 a SINGLE marker does not fire (the rule's precision)",
              bk1 <= 0.10 * n1, f"{bk1}/{n1} blocked; <=10% expected")
    else:
        check("S3/S4 register lexicon present in the model", False,
              "no register_lexicon -- did a model swap drop it?")

    # -- S5. THE LOAD-BEARING CHECK. Measure the formal register, then require
    #    that whatever is missed is DECLARED. The suite does not demand the gap
    #    be closed; it demands the model not be silent about it. A test that
    #    asserted "100% missed" would pass for ever and cement the defect.
    bk, n, v = sweep(m, [f"{x} the {y}" for x in FORMAL for y in NOUNS])
    missed = n - bk
    declared = set(raw.get("missing_seeds") or [])
    if not declared:
        for key in ("diagnostics", "build", "competence"):
            sub = raw.get(key)
            if isinstance(sub, dict) and sub.get("missing_seeds"):
                declared = set(sub["missing_seeds"]); break
    undeclared = sorted(w for w in FORMAL if w not in declared) if missed else []
    print(f"      formal register: {missed}/{n} missed  {v}")
    print(f"      model declares missing_seeds: "
          f"{sorted(declared)[:8] if declared else 'NOTHING'}")
    check("S5 every formal verb the judge misses is DECLARED missing",
          missed == 0 or not undeclared,
          f"missed {missed}/{n}; undeclared: {undeclared}")

    # -- S6. the pair that names the mechanism.
    alone = m.assess({"memo": "embezzle the funds"})
    withmk = m.assess({"memo":
                       "embezzle the funds, a taste before it gets counted"})
    check("S6 the formal verb contributes nothing on its own",
          alone.verdict == "clean" and withmk.blocks,
          f"alone={alone.verdict!r} with_two_markers={withmk.verdict!r}")

    p = sum(1 for _, ok in results if ok)
    print(f"\nSEM5: {p}/{len(results)} passed")
    return 0 if p == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
