#!/usr/bin/env python3
"""
ethics_witness_phase0.py -- PHASE 0 of ops/ETHICS_SNN_WITNESS_PREREG_2026-11-04.md
(sealed 2026-11-04, corpus_sha 68a3a57597f5, deployed_student_sha f245e9076146).

THE GATE, cheap and non-spiking. Does ordered-sequence information decorrelate from
the lexical student's errors AT ALL -- more than the same-words naive Bayes (BL1)?
If not, the heavy octopus spiking build (Phase 1) is not justified and we stop.

BL3 (order-aware): a non-spiking model whose ONLY added signal over the student's
unigram bag of words is local ORDER -- word n-grams (1,2) + char n-grams (3,5),
TF-IDF, logistic regression. The student (FB.FallbackModel) and BL1 (NaiveBayes)
are run through the SEALED harness tools/judge_eval.py VERBATIM on the SAME grouped
folds, so the 2x2 of (student-wrong x other-wrong) is on the same held-out rows.

Over the HELD-OUT violations the student DECIDED (not abstained):
  A-wrong = student CLEARED a violation (its false-clear)
  B-wrong = BL3 (or BL1) CLEARED that violation, at the threshold where B's
            false-conviction on held-out CLEAN memos <= C = 16.5%.
  phi = association of the two error columns over the 2x2; catch_rate = b/(a+b)
        = share of the student's false-clears the other model FLAGS
        = the joint-false-clear reduction when both must admit to clear.

PHASE 0 PASS (both), pooled over 5 seeds x grouped folds, bootstrap 95% CI:
  (1) phi(student,BL3) < phi(student,BL1) with the CIs separated  [Delta phi CI > 0]
  (2) catch_rate(BL3) >= 0.25   [>=25% joint-false-clear reduction vs student-alone]
PASS -> Phase 1 runs.  FAIL -> STOP, witness parked UNKNOWN, honest finding recorded.

Run in the spiking-lab venv (needs sklearn):  python tools/ethics_witness_phase0.py
"""
import hashlib
import os
import random
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))

import judge_eval as JE          # folds(), NaiveBayes, FB (student), VERDICTS via X
X = JE.X
FB = JE.FB

C = 0.165                        # clean false-conviction ceiling (sealed)
CATCH_MIN = 0.25                 # >=25% joint-false-clear reduction (sealed)
SEEDS = (1, 2, 3, 4, 5)
K = 5
BOOT = 2000
EXPECT_CORPUS_SHA = "68a3a57597f5"


def corpus_sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]


def load_rows():
    rows = []
    with open(X.VERDICTS, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            import json
            r = json.loads(ln)
            if "text" in r and "violates" in r:
                rows.append({"text": r["text"], "violates": bool(r["violates"])})
    return rows


def build_bl3():
    """Order-aware, non-spiking. Word (1,2) + char (3,5) TF-IDF -> logistic reg.
    The n-grams are the LOCAL ORDER the unigram student/BL1 discard; that is the
    whole thing Phase 0 tests. Returns (fit(texts,labels), prob(texts))."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from scipy.sparse import hstack

    wv = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    cv = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True)
    clf = LogisticRegression(max_iter=2000, C=4.0)

    state = {}

    def fit(texts, labels):
        Xw = wv.fit_transform(texts)
        Xc = cv.fit_transform(texts)
        clf.fit(hstack([Xw, Xc]).tocsr(), labels)

    def prob(texts):
        Xw = wv.transform(texts)
        Xc = cv.transform(texts)
        return clf.predict_proba(hstack([Xw, Xc]).tocsr())[:, 1]   # P(violation)

    state["fit"], state["prob"] = fit, prob
    return state


def run_seed(rows, seed):
    """Per held-out row collect: gold(bool), student in {violates,clean,abstain},
    nb in {violates,clean}, bl3_prob(float). Pooled across the k folds."""
    rng = random.Random(seed)
    gold, stu, nb_v, bl3p = [], [], [], []
    for train, test in JE.folds(rows, K, rng):
        examples = [(r["text"], bool(r["violates"])) for r in train]
        m = FB.FallbackModel.train(examples, ["phase0 fold"])
        nb = JE.NaiveBayes(examples)
        bl3 = build_bl3()
        bl3["fit"]([t for t, _ in examples], [1 if v else 0 for _, v in examples])
        tt = [r["text"] for r in test]
        probs = bl3["prob"](tt)
        for r, p in zip(test, probs):
            gold.append(bool(r["violates"]))
            mv, _ = m.verdict(r["text"])
            stu.append(mv)
            nb_v.append(nb.verdict(r["text"])[0])
            bl3p.append(float(p))
    return gold, stu, nb_v, bl3p


def threshold_for_ceiling(gold, probs, ceiling):
    """Lowest threshold (most sensitive) with false-conviction on CLEAN <= ceiling.
    BL3 says 'violation' iff prob >= theta. FC_clean = clean called violation / clean."""
    clean = [p for g, p in zip(gold, probs) if not g]
    if not clean:
        return 1.0
    # try every candidate threshold (each clean prob), pick the smallest theta whose
    # FC_clean <= ceiling; more sensitive = catches more violations.
    cands = sorted(set(clean + [1.0]))
    best = 1.0
    for th in cands:
        fc = sum(1 for p in clean if p >= th) / float(len(clean))
        if fc <= ceiling:
            best = th
            break
    return best


def two_by_two(a_wrong, b_wrong):
    a = sum(1 for aw, bw in zip(a_wrong, b_wrong) if aw and bw)
    b = sum(1 for aw, bw in zip(a_wrong, b_wrong) if aw and not bw)
    c = sum(1 for aw, bw in zip(a_wrong, b_wrong) if not aw and bw)
    d = sum(1 for aw, bw in zip(a_wrong, b_wrong) if not aw and not bw)
    return a, b, c, d


def phi(a, b, c, d):
    import math
    den = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    return (a * d - b * c) / den if den > 0 else 0.0


def analyse(gold, stu, nb_v, bl3p):
    """On DECIDED violations (student not abstain): the student's false-clear is
    stu=='clean'; BL1 false-clear nb=='clean'; BL3 false-clear prob<theta."""
    th = threshold_for_ceiling(gold, bl3p, C)
    # decided violations only (student decided: not abstain)
    idx = [i for i in range(len(gold)) if gold[i] and stu[i] != "abstain"]
    stu_wrong = [stu[i] == "clean" for i in idx]            # student cleared a violation
    bl1_wrong = [nb_v[i] == "clean" for i in idx]           # BL1 cleared it
    bl3_wrong = [bl3p[i] < th for i in idx]                 # BL3 cleared it (below theta)
    a3, b3, c3, d3 = two_by_two(stu_wrong, bl3_wrong)
    a1, b1, c1, d1 = two_by_two(stu_wrong, bl1_wrong)
    phi3 = phi(a3, b3, c3, d3)
    phi1 = phi(a1, b1, c1, d1)
    stu_fc = (a3 + b3) / float(len(idx)) if idx else 0.0    # student-alone FC on decided viol
    catch3 = b3 / float(a3 + b3) if (a3 + b3) else 0.0      # BL3 catch rate = joint reduction
    catch1 = b1 / float(a1 + b1) if (a1 + b1) else 0.0
    return {"theta": th, "n_decided_viol": len(idx), "student_false_clears": a3 + b3,
            "phi_bl3": phi3, "phi_bl1": phi1, "dphi": phi1 - phi3,
            "catch_bl3": catch3, "catch_bl1": catch1,
            "2x2_bl3": (a3, b3, c3, d3), "stu_wrong": stu_wrong,
            "bl3_wrong": bl3_wrong, "bl1_wrong": bl1_wrong}


def bootstrap_ci(stu_wrong, bl3_wrong, bl1_wrong, boot, seed):
    """Bootstrap the paired Delta phi = phi_bl1 - phi_bl3 and catch_bl3 over the
    decided-violation rows. Returns (dphi_lo, dphi_hi, catch_lo, catch_hi)."""
    rng = random.Random(seed)
    n = len(stu_wrong)
    dphis, catches = [], []
    idxs = list(range(n))
    for _ in range(boot):
        s = [rng.choice(idxs) for _ in idxs]
        sw = [stu_wrong[i] for i in s]
        b3 = [bl3_wrong[i] for i in s]
        b1 = [bl1_wrong[i] for i in s]
        p3 = phi(*two_by_two(sw, b3))
        p1 = phi(*two_by_two(sw, b1))
        dphis.append(p1 - p3)
        a, b, c, d = two_by_two(sw, b3)
        catches.append(b / float(a + b) if (a + b) else 0.0)
    dphis.sort(); catches.sort()
    lo = int(0.025 * boot); hi = int(0.975 * boot) - 1
    return dphis[lo], dphis[hi], catches[lo], catches[hi]


def main():
    sha = corpus_sha(X.VERDICTS)
    print("corpus_sha:", sha, "(expected %s)" % EXPECT_CORPUS_SHA,
          "-- MATCH" if sha == EXPECT_CORPUS_SHA else "-- MISMATCH (corpus changed since seal!)")
    rows = load_rows()
    print("rows: %d (violations %d, clean %d)"
          % (len(rows), sum(r["violates"] for r in rows), sum(not r["violates"] for r in rows)))
    print("seeds %s, k=%d, boot=%d, C=%.3f, catch_min=%.2f\n" % (SEEDS, K, BOOT, C, CATCH_MIN))

    per_seed = []
    pooled_sw, pooled_b3, pooled_b1 = [], [], []
    for sd in SEEDS:
        gold, stu, nb_v, bl3p = run_seed(rows, sd)
        a = analyse(gold, stu, nb_v, bl3p)
        per_seed.append(a)
        pooled_sw += a["stu_wrong"]; pooled_b3 += a["bl3_wrong"]; pooled_b1 += a["bl1_wrong"]
        print("seed %d: theta=%.3f decided_viol=%d stu_false_clears=%d "
              "phi_bl3=%.3f phi_bl1=%.3f dphi=%.3f catch_bl3=%.3f catch_bl1=%.3f"
              % (sd, a["theta"], a["n_decided_viol"], a["student_false_clears"],
                 a["phi_bl3"], a["phi_bl1"], a["dphi"], a["catch_bl3"], a["catch_bl1"]))

    import statistics as st
    mean_phi3 = st.mean(x["phi_bl3"] for x in per_seed)
    mean_phi1 = st.mean(x["phi_bl1"] for x in per_seed)
    mean_dphi = st.mean(x["dphi"] for x in per_seed)
    sd_dphi = st.pstdev([x["dphi"] for x in per_seed])
    mean_catch3 = st.mean(x["catch_bl3"] for x in per_seed)
    mean_catch1 = st.mean(x["catch_bl1"] for x in per_seed)
    dlo, dhi, clo, chi = bootstrap_ci(pooled_sw, pooled_b3, pooled_b1, BOOT, 7)

    print("\n== POOLED over %d seeds (%d decided-violation rows) ==" % (len(SEEDS), len(pooled_sw)))
    print("phi(student,BL3) mean=%.3f   phi(student,BL1) mean=%.3f   [BL1 ref ~0.602]"
          % (mean_phi3, mean_phi1))
    print("Delta phi = phi_bl1 - phi_bl3: mean=%.3f (per-seed sd %.3f); bootstrap 95%% CI [%.3f, %.3f]"
          % (mean_dphi, sd_dphi, dlo, dhi))
    print("catch_rate BL3 (=joint-false-clear reduction): mean=%.3f; bootstrap 95%% CI [%.3f, %.3f]"
          % (mean_catch3, clo, chi))
    print("catch_rate BL1 (same-words reference): mean=%.3f" % mean_catch1)

    cond1 = dlo > 0.0                                   # BL3 decorrelates MORE than BL1, CI-separated
    cond2 = (mean_catch3 >= CATCH_MIN) and (clo >= CATCH_MIN * 0.8)   # catch >=25%, CI not far below
    print("\nCondition 1 (phi_bl3 < phi_bl1, CI-separated: dphi CI>0): %s" % ("PASS" if cond1 else "FAIL"))
    print("Condition 2 (catch_bl3 >= %.0f%%): %s" % (CATCH_MIN * 100, "PASS" if cond2 else "FAIL"))
    verdict = "PASS -> Phase 1 runs" if (cond1 and cond2) else "FAIL -> STOP, witness parked UNKNOWN"
    print("\nPHASE 0 VERDICT: %s" % verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
