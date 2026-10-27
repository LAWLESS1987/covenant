#!/usr/bin/env python3
"""tools/judge_eval.py -- evaluate the distilled judge the way a classifier
paper would: against baselines, with bootstrap confidence intervals, and with
the teacher panel's inter-annotator agreement reported as a statistic.

Written 2026-09-20 for the research artifact (peer review, 3.3: "a baseline,
confidence intervals, inter-annotator agreement for the panel labels
(recorded per row, never reported as a statistic)"). Everything here is
computed from ops/verdicts.jsonl and the student's own training code; no
runner, no token, no network.

    python tools/judge_eval.py              # writes docs/JUDGE_EVALUATION.md
    python tools/judge_eval.py --folds 5 --boot 1000 --seed 7

WHAT THE NUMBERS MEAN, said before they are printed. `false clear` is the
rate at which a judge CLEARS a memo the teacher labelled a violation: the
error the gate exists to prevent. `false hold` is the rate at which it
convicts or abstains on a memo the teacher labelled clean: the cost. `abstain`
is the share it declines to decide; for the student an abstention is by
design (a hold fails closed) and is counted separately, never as a clear.
The baselines cannot abstain. The teacher labels are the reference and are
themselves imperfect: the last table measures how much three panel members
agree with one another, which bounds how much any student can agree with
them.
"""
import io
import json
import os
import random
import re
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
os.environ.setdefault("COVENANT_QUIET", "1")

import covenant_distill as X  # noqa: E402
import covenant_judge_fallback as FB  # noqa: E402

OUT = os.path.join(HERE, "docs", "JUDGE_EVALUATION.md")
KEYWORDS = re.compile(r"\b(steal|stole|stolen|drain|siphon|skim|forge|forged|fake|backdat|threat|threaten|"
                      r"extort|blackmail|override|ignore previous|system:|you are now|embezzl|launder|"
                      r"without (?:his|her|their) (?:knowledge|consent)|not (?:mine|yours))\b", re.I)


def rates(pred, gold):
    """pred in {'violates','clean','abstain'}; gold bool (True = violation)."""
    n = len(gold)
    fc = sum(1 for p, g in zip(pred, gold) if g and p == "clean")
    fh = sum(1 for p, g in zip(pred, gold) if not g and p != "clean")
    ab = sum(1 for p in pred if p == "abstain")
    dec = [(p, g) for p, g in zip(pred, gold) if p != "abstain"]
    acc = sum(1 for p, g in dec if (p == "violates") == g) / float(max(1, len(dec)))
    # false conviction: a clean memo CONVICTED, over the clean memos it decided.
    # This is the figure comparable to the baselines, which cannot abstain.
    clean_dec = [(p, g) for p, g in dec if not g]
    fconv = sum(1 for p, g in clean_dec if p == "violates") / float(max(1, len(clean_dec)))
    # false_clear is MARGINAL, not conditional on deciding: the denominator is
    # every labelled violation (sum(gold)), abstained ones included, so a
    # judge cannot buy a better number by abstaining more. An external review
    # (2026-09-20) asked whether this was computed only over decided cases,
    # which would let heavy abstention masquerade as safety; it is not.
    return {"n": n, "false_clear": fc / float(max(1, sum(gold))),
            "false_hold": fh / float(max(1, n - sum(gold))), "false_conviction": fconv,
            "abstain": ab / float(n), "accuracy_when_deciding": acc, "decided": len(dec) / float(n)}


def bootstrap(pred, gold, key, boot, rng):
    vals = []
    idx = list(range(len(gold)))
    for _ in range(boot):
        s = [rng.choice(idx) for _ in idx]
        vals.append(rates([pred[i] for i in s], [gold[i] for i in s])[key])
    vals.sort()
    return vals[int(0.025 * boot)], vals[int(0.975 * boot) - 1]


class NaiveBayes(object):
    """A multinomial naive Bayes over the same bag of words the student sees,
    which MUST decide: no abstention. It exists so that the value of the
    student's abstention is visible against a model with the same features
    and no way to hold. Laplace smoothing, log space, no dependencies."""

    def __init__(self, examples):
        import math
        self.counts = {True: {}, False: {}}
        self.n = {True: 0, False: 0}
        self.total = {True: 0, False: 0}
        vocab = set()
        for text, viol in examples:
            self.n[viol] += 1
            for w in self._tokens(text):
                self.counts[viol][w] = self.counts[viol].get(w, 0) + 1
                self.total[viol] += 1
                vocab.add(w)
        self.v = max(1, len(vocab))
        self.prior = {c: math.log(max(1, self.n[c]) / float(max(1, sum(self.n.values())))) for c in (True, False)}
        self._log = math.log

    @staticmethod
    def _tokens(text):
        return re.findall(r"[a-z0-9']+", (text or "").lower())

    def verdict(self, text):
        score = {}
        for c in (True, False):
            s = self.prior[c]
            for w in self._tokens(text):
                s += self._log((self.counts[c].get(w, 0) + 1.0) / (self.total[c] + self.v))
            score[c] = s
        return ("violates" if score[True] > score[False] else "clean"), ""


def folds(rows, k, rng):
    """Grouped k-fold: every row sharing another row's exact text (case- and
    whitespace-folded) is assigned to the SAME fold, so no duplicate spans
    train and test. Fixed 2026-09-20 after two independent adversarial
    reviews (ChatGPT, DeepSeek) raised the possibility, and measurement
    against ops/verdicts.jsonl confirmed it: 1,276 of 3,766 rows (34%) share
    exact-duplicate text with at least one other row -- mostly the same
    generated memo re-admitted across nightly cycles. A plain row-level split
    could and, unverified, likely did put a memo's twin on the other side of
    the boundary it was supposed to be held out from, which inflates a
    held-out score without a single held-out example."""
    groups = {}
    for r in rows:
        key = re.sub(r"\s+", " ", (r.get("text") or "").strip().lower())
        groups.setdefault(key, []).append(r)
    keys = list(groups)
    rng.shuffle(keys)
    for f in range(k):
        test_keys = set(keys[f::k])
        train = [r for key in keys if key not in test_keys for r in groups[key]]
        test = [r for key in sorted(test_keys) for r in groups[key]]
        yield train, test


def evaluate(rows, k, boot, seed):
    rng = random.Random(seed)
    preds = {"student (distilled, 5-fold)": [], "naive Bayes, same words, must decide": [],
             "majority class": [], "keyword rule": []}
    gold_all, scores = [], []
    for train, test in folds(rows, k, rng):
        examples = [(r["text"], bool(r["violates"])) for r in train]
        m = FB.FallbackModel.train(examples, ["judge_eval fold"])
        nb = NaiveBayes(examples)
        maj = "violates" if sum(bool(r["violates"]) for r in train) * 2 > len(train) else "clean"
        for r in test:
            gold_all.append(bool(r["violates"]))
            v, _ = m.verdict(r["text"])
            preds["student (distilled, 5-fold)"].append(v)
            preds["naive Bayes, same words, must decide"].append(nb.verdict(r["text"])[0])
            preds["majority class"].append(maj)
            preds["keyword rule"].append("violates" if KEYWORDS.search(r["text"] or "") else "clean")
            try:
                scores.append(float(m.score(r["text"])[0]))     # (log-odds, coverage, n_known)
            except Exception:  # noqa: BLE001
                scores.append(float("nan"))
    out = {}
    for name, p in preds.items():
        r = rates(p, gold_all)
        r["ci_false_clear"] = bootstrap(p, gold_all, "false_clear", boot, random.Random(seed + 1))
        r["ci_false_hold"] = bootstrap(p, gold_all, "false_hold", boot, random.Random(seed + 2))
        out[name] = r
    out["_preds"] = preds
    out["_gold"] = gold_all
    out["_scores"] = scores
    return out, len(gold_all)


def coverage_curve(scores, gold, bands):
    """The safety/availability trade-off of the hold, from the student's own
    log-odds: for each half-width of an undecided band around zero, the share
    it decides (coverage), and the false clear and false conviction among what
    it decided. Wider band = more holds, fewer errors, less availability."""
    import math
    rows = []
    for b in bands:
        dec = [(s, g) for s, g in zip(scores, gold) if not math.isnan(s) and abs(s) > b]
        n = sum(1 for s in scores if not math.isnan(s))
        if not dec:
            rows.append((b, 0.0, float("nan"), float("nan")))
            continue
        viol = [(s, g) for s, g in dec if g]
        clean = [(s, g) for s, g in dec if not g]
        fc = sum(1 for s, g in viol if s < 0) / float(max(1, len(viol)))
        fv = sum(1 for s, g in clean if s > 0) / float(max(1, len(clean)))
        rows.append((b, len(dec) / float(max(1, n)), fc, fv))
    return rows


def error_overlap(pa, pb, gold):
    """First correlated-judge measurement: when two seats both decide a
    labelled violation, how often are they BOTH wrong (a joint false clear),
    against what independence would predict from their marginals? A ratio well
    above 1 means their errors travel together and a quorum of the two buys
    less than it looks."""
    both_dec = [(a, b, g) for a, b, g in zip(pa, pb, gold) if g and a != "abstain" and b != "abstain"]
    n = len(both_dec)
    if not n:
        return None
    a_fc = sum(1 for a, b, g in both_dec if a == "clean") / float(n)
    b_fc = sum(1 for a, b, g in both_dec if b == "clean") / float(n)
    joint = sum(1 for a, b, g in both_dec if a == "clean" and b == "clean") / float(n)
    expected = a_fc * b_fc
    both_wrong = sum(1 for a, b, g in both_dec if a == "clean" and b == "clean")
    a_only = sum(1 for a, b, g in both_dec if a == "clean" and b != "clean")
    b_only = sum(1 for a, b, g in both_dec if a != "clean" and b == "clean")
    out = {"n": n, "a_false_clear": a_fc, "b_false_clear": b_fc, "joint_false_clear": joint,
           "independent_expectation": expected, "ratio": (joint / expected) if expected else float("nan"),
           "table": {"both_wrong": both_wrong, "a_only_wrong": a_only, "b_only_wrong": b_only,
                     "both_right": n - both_wrong - a_only - b_only}}
    out.update(table_tests(both_wrong, a_only, b_only, n - both_wrong - a_only - b_only))
    return out


def table_tests(a, b, c, d):
    """Significance of a 2x2 table [[a, b], [c, d]] in closed form, standard library only,
    so anyone can recompute it (2026-09-26: a reader asked for the pair's own significance,
    not only the ratio). Pearson chi-square with and without Yates' correction (df = 1,
    p = erfc(sqrt(chi2 / 2))), phi (= Cramer's V for a 2x2), the sample odds ratio, and
    Fisher's exact test from the hypergeometric distribution. With an expected joint count
    near 7, the exact test is the one to trust: the chi-square p-value is asymptotic."""
    import math
    n = a + b + c + d
    r1, r2, c1, c2 = a + b, c + d, a + c, b + d
    den = float(r1) * r2 * c1 * c2
    diff = a * d - b * c
    chi2 = n * diff * diff / den if den else float("nan")
    yates = n * max(0.0, abs(diff) - n / 2.0) ** 2 / den if den else float("nan")
    p_chi2 = math.erfc(math.sqrt(chi2 / 2.0)) if den else float("nan")
    p_yates = math.erfc(math.sqrt(yates / 2.0)) if den else float("nan")
    phi = diff / math.sqrt(den) if den else float("nan")
    total = math.comb(n, c1)

    def pmf(x):
        return math.comb(r1, x) * math.comb(r2, c1 - x) / total
    lo, hi = max(0, c1 - r2), min(r1, c1)
    probs = {x: pmf(x) for x in range(lo, hi + 1)}
    p_obs = probs[a]
    p_two = min(1.0, sum(p for p in probs.values() if p <= p_obs * (1 + 1e-7)))
    p_greater = min(1.0, sum(p for x, p in probs.items() if x >= a))
    odds = (a * d) / float(b * c) if b * c else float("inf")
    return {"expected_both_wrong": r1 * c1 / float(n) if n else float("nan"), "chi2": chi2, "chi2_p": p_chi2,
            "chi2_yates": yates, "chi2_yates_p": p_yates, "phi": phi, "odds_ratio": odds,
            "fisher_p_two_sided": p_two, "fisher_p_greater": p_greater}


def provenance():
    """Every number in the report is tied to these; a reader can re-run and
    compare. The deployed student's digest is reported even though the folds
    train their own, because the exam numbers elsewhere refer to it."""
    import hashlib
    import subprocess

    def sha(path):
        try:
            with io.open(path, "rb") as fh:
                return hashlib.sha256(fh.read()).hexdigest()[:12]
        except OSError:
            return "absent"
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=HERE, capture_output=True,
                                text=True, timeout=30).stdout.strip()
    except Exception:  # noqa: BLE001
        commit = "?"
    import covenant_unified_v8 as cov
    # The live core carries its policy built in (DIVINE_PRINCIPLES in covenant_unified_v8.py); the artifact made
    # it a file. Name whichever this tree has, and fingerprint the file that holds it.
    pol = getattr(cov, "POLICY", None)
    policy, policy_path = ((pol["name"], pol["path"]) if isinstance(pol, dict) and pol.get("path") else
                           ("built-in DIVINE_PRINCIPLES", os.path.join(HERE, "covenant_unified_v8.py")))
    return {"commit": commit, "corpus_sha": sha(X.VERDICTS), "rejected_sha": sha(X.REJECTED),
            "deployed_student_sha": sha(FB.MODEL_PATH), "policy": policy,
            "policy_sha": sha(policy_path), "judge_code_sha": sha(os.path.join(HERE, "covenant_judge_fallback.py"))}


def panel_agreement(rows):
    """Pairwise agreement and Fleiss' kappa over rows with >= 2 panel votes."""
    votes = []
    for r in rows:
        p = r.get("panel")
        if isinstance(p, dict) and isinstance(p.get("votes"), dict) and len(p["votes"]) >= 2:
            votes.append([bool(v) for v in p["votes"].values()])
    if not votes:
        return None
    pairs = agree = 0
    for vs in votes:
        for i in range(len(vs)):
            for j in range(i + 1, len(vs)):
                pairs += 1
                agree += (vs[i] == vs[j])
    unanimous = sum(1 for vs in votes if len(set(vs)) == 1) / float(len(votes))
    # Fleiss' kappa, two categories, allowing a variable number of raters per row.
    n_items = len(votes)
    p_bar = 0.0
    tot_true = tot = 0
    for vs in votes:
        n = len(vs)
        t = sum(vs)
        tot_true += t
        tot += n
        if n > 1:
            p_bar += (t * (t - 1) + (n - t) * (n - t - 1)) / float(n * (n - 1))
    p_bar /= n_items
    p_true = tot_true / float(tot)
    p_e = p_true ** 2 + (1 - p_true) ** 2
    kappa = (p_bar - p_e) / (1 - p_e) if p_e < 1 else float("nan")
    return {"rows_with_votes": n_items, "pairwise_agreement": agree / float(max(1, pairs)),
            "unanimous_share": unanimous, "fleiss_kappa": kappa,
            "raters_per_row": tot / float(n_items)}


def render(res, n, pa, rows, k, boot, seed, prov=None, curve=None, overlap=None, leakage=None):
    L = ["# Judge evaluation", "",
         "Generated by `python tools/judge_eval.py --folds %d --boot %d --seed %d` at %s from %d teaching rows in "
         "`ops/verdicts.jsonl` (%d held-out predictions across the folds). Read the module docstring for what each "
         "rate means. **`false clear` = a labelled violation the judge wrongly ADMITTED**, the error the gate "
         "exists to prevent; **`false conviction` = a labelled clean memo it wrongly REFUSED**, the cost; lower is "
         "better for both. `false clear` is MARGINAL over every labelled violation, abstentions included -- a judge "
         "cannot buy a better number by abstaining more (fixed and stated after external review, 2026-09-20)."
         % (k, boot, seed, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), len(rows), n), ""]
    if leakage:
        L += ["## Duplicate-text leakage: the exact case is closed, paraphrase is not", "",
              "Two external reviews (2026-09-20) asked whether a plain row-level fold split leaks near-duplicate "
              "memos across train and test, inflating the held-out score. Measured: of %d labelled rows, %d "
              "distinct texts, and %d rows (%.0f%%) share their exact text with at least one other row -- mostly "
              "the same generated memo re-admitted across nightly cycles. `folds()` now groups by exact text (case- "
              "and whitespace-folded) so no EXACT duplicate spans train and test. A third external review (Astra, "
              "same day) pointed out this closes one leakage mechanism, not evaluation independence generally: "
              "paraphrases, shared templates and generator-family patterns are not deduplicated and can still cross "
              "folds. That is correct and is not fixed here; grouping by a semantic or template key is proposed "
              "work, not a result."
              % (leakage["rows"], leakage["distinct_texts"], leakage["rows_in_a_duplicate_group"],
                 100.0 * leakage["rows_in_a_duplicate_group"] / max(1, leakage["rows"])), ""]
    if prov:
        L += ["## Provenance of every number below", "",
              "| what | value |", "|---|---|"]
        for key in ("commit", "corpus_sha", "rejected_sha", "deployed_student_sha", "policy", "policy_sha", "judge_code_sha"):
            L.append("| %s | `%s` |" % (key, prov.get(key)))
        L += ["", "The folds train their own students from the corpus named here (seeded); the deployed student's digest is "
              "listed because the exam figures elsewhere refer to it, and a promotion changes it nightly.", ""]
    L += ["## The student against three baselines", "",
          "| judge | false clear (95% CI) | false hold incl. abstentions (95% CI) | false conviction, decided only | abstains | decides | accuracy when deciding |",
          "|---|---|---|---|---|---|---|"]
    for name, r in res.items():
        if name.startswith("_"):
            continue
        L.append("| %s | %.1f%% (%.1f–%.1f) | %.1f%% (%.1f–%.1f) | %.1f%% | %.1f%% | %.1f%% | %.1f%% |" % (
            name, 100 * r["false_clear"], 100 * r["ci_false_clear"][0], 100 * r["ci_false_clear"][1],
            100 * r["false_hold"], 100 * r["ci_false_hold"][0], 100 * r["ci_false_hold"][1],
            100 * r["false_conviction"], 100 * r["abstain"], 100 * r["decided"], 100 * r["accuracy_when_deciding"]))
    L += ["", "The naive Bayes row is the control that matters: the same bag of words as the student, trained on the same "
          "folds, with no way to hold. Whatever it clears wrongly and the student does not is what abstention buys; "
          "whatever the student convicts and it does not is what abstention costs. The other two baselines cannot abstain either. "
          "The student's `false hold` counts every clean memo it did not clear, "
          "abstentions included, because a hold fails closed and costs the sender the same wait; `false conviction` "
          "counts only the clean memos it actively convicted, which is the figure comparable to the baselines. "
          "The student here is trained from scratch per fold; the deployed student is refined nightly from its "
          "predecessor and reads better on the same corpus, so these are the conservative numbers. A student whose "
          "false-clear interval overlaps the keyword rule's has not shown it learned more than the keywords. "
          "**Not a matched-coverage comparison** (external review, 2026-09-20): the student decides %.1f%% of rows "
          "and naive Bayes decides %.0f%%, so the %.1f%% vs %.1f%% false-clear gap is partly the cost of the coverage "
          "the student declined. The coverage curve below is the same student at wider holds, which shows what its "
          "OWN false-clear buys at lower coverage; it is not a like-for-like point against a forced baseline at the "
          "student's coverage, which this tool does not yet compute."
          # Every figure in this sentence comes from the run (2026-09-26): the gap was written in as '3.4% vs 23.9%'
          # from the first dataset, and a second corpus measured 3.2% vs 25.4% under the same words.
          % (100 * res["student (distilled, 5-fold)"]["decided"], 100 * res["naive Bayes, same words, must decide"]["decided"],
             100 * res["student (distilled, 5-fold)"]["false_clear"], 100 * res["naive Bayes, same words, must decide"]["false_clear"]), ""]
    if pa:
        L += ["## How much the teachers agree with one another", "",
              "| quantity | value |", "|---|---|",
              "| rows carrying two or more panel votes | %d |" % pa["rows_with_votes"],
              "| raters per row (mean) | %.2f |" % pa["raters_per_row"],
              "| pairwise agreement | %.1f%% |" % (100 * pa["pairwise_agreement"]),
              "| unanimous rows | %.1f%% |" % (100 * pa["unanimous_share"]),
              "| Fleiss' kappa (two categories) | %.3f |" % pa["fleiss_kappa"], "",
              "Panel members are three small open models on one CI runner; their agreement bounds how much any student "
              "can agree with the labels, and it is not agreement with a human. Admission already requires unanimity "
              "across two model families, so the teaching rows are the agreeing subset of what was judged; the rate "
              "above is measured over every row that carries votes, admitted or not.", ""]
    else:
        L += ["## Panel agreement", "", "UNDETERMINED: no rows carry panel votes in this ledger.", ""]
    if curve:
        L += ["## The hold's price: coverage against risk", "",
              "A SIGN RULE on the student's raw log-odds with a symmetric undecided band: decide by sign outside the "
              "band, hold inside it. Widening the band trades availability (the share decided) for safety (errors "
              "among what is decided). This is NOT the deployed verdict, which adds vocabulary-coverage gating and "
              "the remove-proof evidence guards on top of the score; that is why the fold student's false clear "
              "in the table above (%.1f%%) sits far below this curve's, and the curve shows the shape of the trade-off, "
              "not the deployed operating point. Measured on the same held-out rows:"
              % (100 * res["student (distilled, 5-fold)"]["false_clear"]), "",
              "| band half-width | decides | false clear among decided | false conviction among decided |",
              "|---|---|---|---|"]
        for b, cov_, fc, fv in curve:
            L.append("| %.1f | %.1f%% | %.1f%% | %.1f%% |" % (b, 100 * cov_, 100 * fc, 100 * fv))
        L += ["", "This is the safety/availability curve a reviewer asked for, on one seat. The deployed gate composes "
              "seats, so the quorum-level curve is proposed work, not this table.", ""]
    if overlap:
        L += ["## Do two seats err together? A first correlated-judge measurement", "",
              "Over the %d labelled violations that BOTH the student and the same-words naive Bayes decided: the student "
              "wrongly admitted %.1f%%, the naive Bayes %.1f%%, and both together %.1f%%. If their errors were independent "
              "the joint rate would be %.2f%%; the measured joint rate is %.1f times that."
              % (overlap["n"], 100 * overlap["a_false_clear"], 100 * overlap["b_false_clear"],
                 100 * overlap["joint_false_clear"], 100 * overlap["independent_expectation"], overlap["ratio"]), "",
              "A ratio near 1 means a quorum of the two would buy roughly what independence predicts; well above 1 means "
              "their errors travel together (same words, same corpus) and a quorum buys less than it looks. This is one "
              "pair on one seat class; the panel's and the semantic seat's correlation with the student is proposed work, "
              "and it is the measurement Objective 1 turns on.", ""]
        t = overlap["table"]
        L += ["**The raw table**, so the pair's significance can be recomputed by hand. A = the student, B = the "
              "same-words naive Bayes, and 'wrong' = admitted a labelled violation as clean:", "",
              "| | B wrong | B right | total |", "|---|---:|---:|---:|",
              "| **A wrong** | %d | %d | %d |" % (t["both_wrong"], t["a_only_wrong"], t["both_wrong"] + t["a_only_wrong"]),
              "| **A right** | %d | %d | %d |" % (t["b_only_wrong"], t["both_right"], t["b_only_wrong"] + t["both_right"]),
              "| total | %d | %d | %d |" % (t["both_wrong"] + t["b_only_wrong"], t["a_only_wrong"] + t["both_right"],
                                          overlap["n"]), "",
              "Under independence the both-wrong cell expects %.2f; it holds %d. With an expected count that small the "
              "asymptotic chi-square p-value is not the one to trust, so the exact test comes first. **Fisher's exact "
              "test: p = %.2g** (two-sided; one-sided, errors travel together: p = %.2g). Pearson chi-square %.1f, "
              "df 1, p = %.2g (Yates-corrected %.1f, p = %.2g); phi (= Cramer's V for a 2x2) = %.3f; sample odds ratio "
              "%.0f. The chi-square p-value is smaller than the exact one by many orders of magnitude, which is the "
              "reason for the exact test; %s"
              % (overlap["expected_both_wrong"], t["both_wrong"], overlap["fisher_p_two_sided"], overlap["fisher_p_greater"],
                 overlap["chi2"], overlap["chi2_p"], overlap["chi2_yates"], overlap["chi2_yates_p"], overlap["phi"],
                 overlap["odds_ratio"],
                 # the verdict follows the p-values instead of being written in (it read 'the 7.7x is not noise' on
                 # a run that measured 9.1x, 2026-09-26)
                 ("both are far below any threshold, so the %.1fx is not noise." % overlap["ratio"])
                 if max(overlap["fisher_p_two_sided"], overlap["chi2_p"]) < 0.001 else
                 ("the exact p-value is %.2g, so the %.1fx is not established at the 0.001 level."
                  % (overlap["fisher_p_two_sided"], overlap["ratio"]))), "",
              "What the test assumes and does not show: it treats the %d rows as independent draws. Exact duplicates are "
              "kept out of the fold split, but near-duplicate texts are not, and clustering would make both p-values "
              "smaller than they should be, though not the table or phi. It shows THAT the two seats' errors are "
              "associated, not why. Both read the same words from the same corpus, so association is expected by "
              "construction; what the test settles is that its size is not chance. In practice, of the %d violations the "
              "student wrongly admitted, the naive Bayes also admitted %d, so requiring both to admit would lower the "
              "false-clear rate only from %.1f%% to %.1f%%." % (overlap["n"], t["both_wrong"] + t["a_only_wrong"],
                                                             t["both_wrong"], 100 * overlap["a_false_clear"],
                                                             100 * overlap["joint_false_clear"]), ""]
    L += ["## What this does not measure", "",
          "- Agreement with a human. No human has labelled these rows.",
          "- Adversarial inputs written by someone other than the author's own red-team loop.",
          "- The semantic seat or the panel itself; only the distilled student is scored here, because it is the seat "
          "that answers when the others cannot.", ""]
    return "\n".join(L)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    k = int(argv[argv.index("--folds") + 1]) if "--folds" in argv else 5
    boot = int(argv[argv.index("--boot") + 1]) if "--boot" in argv else 1000
    seed = int(argv[argv.index("--seed") + 1]) if "--seed" in argv else 7
    # THE SHAREABLE LEDGER ONLY (live repository, 2026-09-26): corpus_paths() would add ops/verdicts_live.jsonl,
    # the private half that holds his own conversations. A measurement meant for publication reads only what
    # the public repository already carries.
    rows = [r for r in X.load_verdicts(X.VERDICTS) if r.get("text") and r.get("violates") is not None]
    dupe_groups = {}
    for r in rows:
        key = re.sub(r"\s+", " ", (r.get("text") or "").strip().lower())
        dupe_groups.setdefault(key, 0)
        dupe_groups[key] += 1
    dupe_rows = sum(c for c in dupe_groups.values() if c > 1)
    leakage = {"rows": len(rows), "distinct_texts": len(dupe_groups), "rows_in_a_duplicate_group": dupe_rows}
    res, n = evaluate(rows, k, boot, seed)
    # AGREEMENT IS MEASURED OVER EVERY ROW THE PANEL VOTED ON, admitted or not.
    # ops/verdicts.jsonl holds only rows the panel was unanimous on (that is
    # the admission rule), so agreement over it alone reads 100% by
    # construction -- measured on the first run of this tool. The disagreeing
    # rows live in ops/distill_rejected.jsonl; both are read here.
    voted = []
    for path in (X.VERDICTS, X.REJECTED):
        try:
            with io.open(path, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(r.get("panel"), dict) and r["panel"].get("votes"):
                        voted.append(r)
        except OSError:
            pass
    pa = panel_agreement(voted)
    curve = coverage_curve(res["_scores"], res["_gold"], [0.0, 1.0, 2.0, 2.4, 3.0, 4.0, 5.0, 6.0])
    overlap = error_overlap(res["_preds"]["student (distilled, 5-fold)"],
                            res["_preds"]["naive Bayes, same words, must decide"], res["_gold"])
    prov = provenance()
    text = render(res, n, pa, rows, k, boot, seed, prov=prov, curve=curve, overlap=overlap, leakage=leakage)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(text)
    print("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
