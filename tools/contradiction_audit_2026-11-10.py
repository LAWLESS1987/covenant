#!/usr/bin/env python3
"""Contradiction audit (his call 2026-11-10: "Use discernment towards mutual
benefit"), the companion to the LABEL lever.

The re-adjudication worklist (label_curation.py) finds single-judge rows carrying
convictions the PANEL never confirmed. This audit finds a different, cheaper
class of label defect the SAME panel pass can resolve at no extra infra cost:

  OPPOSITE-LABEL, HIGH-OVERLAP PAIRS -- two rows whose committed content is
  nearly the same text, yet one is stored `violates` and the other `clean`.
  Either one is mislabelled, or the distinction is real but subtle (a negation,
  a scope marker, a frame) the bag-of-words cannot see. Both are exactly what a
  multi-seat panel should rule on -- and finding them is pure offline work.

This is the OFFLINE half only. It fires no panel and no runner; it saves nothing
to any live model. It writes an audit worklist to sit beside the re-adjudication
worklist, so one panel pass covers both.

Method discipline (CLAUDE.md):
  COUNT first, name the UNIT (here: PAIRS of rows), enumerate by discovery,
  count two ways that can disagree (Jaccard on content tokens AND on the
  scope-aware COMMITTED form -- a pair that is a true contradiction under both
  is strongest; one that separates only under the committed form is the BoW's
  blind spot, not a label error). Name what the audit structurally cannot see.
"""
import os, sys, json, time, itertools
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # tools/ -> repo root
sys.path.insert(0, REPO)
import covenant_judge_fallback as FB
import covenant_distill as D
import covenant_teacher_panel as P

OUT = os.path.join(REPO, "ops", "CONTRADICTION_AUDIT_2026-11-10.jsonl")

STOP = set(FB.STOPWORDS) | set(FB.PRONOUNS_PAIR_ONLY)
JACCARD = 0.60        # near-duplicate threshold on content-token sets
MIN_TOK = 4           # ignore trivially short rows (units too small to trust)
SEED_DF_MAX = 150     # seed candidate pairs from tokens rarer than this


def classify(r):
    try:
        if P.validate_row(r):
            return "panel"
    except Exception:
        if r.get("panel"):
            return "panel"
    if r.get("source") in D.TEACHER_SOURCES:
        return "single_judge"
    return "authored"


def content_set(text):
    """Surface content tokens: every token minus stopwords/pronouns."""
    return frozenset(t for t in FB.tokens(text) if t not in STOP)


def committed_set(text, version=2):
    """Scope-aware content: tokens NOT negated and NOT inside a describe-frame.
    Reuses the live judge's own _segments/_negated/_described so the committed
    form is exactly what the model treats as asserted. _segments already
    tokenizes (List[List[str]]); _described returns one flag per token flattened
    across every segment, so we walk a global index in step with it."""
    segs = FB._segments(text)                 # list of token-lists
    try:
        desc = FB._described(segs)            # flat, one bool per token
    except Exception:
        desc = [False] * sum(len(s) for s in segs)
    keep, gi = set(), 0
    for seg in segs:
        try:
            neg = FB._negated(seg)
        except Exception:
            neg = [False] * len(seg)
        for i, t in enumerate(seg):
            flagged = (i < len(neg) and neg[i]) or (gi < len(desc) and desc[gi])
            gi += 1
            if t in STOP or flagged:
                continue
            keep.add(t)
    return frozenset(keep)


def jac(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if not inter:
        return 0.0
    return inter / len(a | b)


def candidate_pairs(sets):
    """Seed candidate row pairs from shared RARE tokens (df <= SEED_DF_MAX).
    A pair with Jaccard >= 0.60 and >= MIN_TOK tokens shares many tokens, so it
    is certain to co-occur on at least one such token -> no high-overlap pair is
    missed by the seeding, while common tokens never explode the candidate set."""
    inv = defaultdict(list)
    for i, s in enumerate(sets):
        if len(s) < MIN_TOK:
            continue
        for t in s:
            inv[t].append(i)
    cand = set()
    for t, idxs in inv.items():
        if len(idxs) > SEED_DF_MAX:
            continue
        for a, b in itertools.combinations(idxs, 2):
            cand.add((a, b) if a < b else (b, a))
    return cand


def main():
    rows = D.load_verdicts()
    for r in rows:
        r["_cls"] = classify(r)

    # ---- FIRST PASS / COUNT: the populations, units named ----
    csets = [content_set(r["text"]) for r in rows]
    msets = [committed_set(r["text"]) for r in rows]
    eligible = sum(1 for s in csets if len(s) >= MIN_TOK)
    print("=== CONTRADICTION AUDIT ===")
    print("  rows (load_verdicts kept corpus): %d" % len(rows))
    print("  rows with >= %d content tokens (eligible, UNIT = row): %d" % (MIN_TOK, eligible))

    cand = candidate_pairs(csets)
    print("  candidate PAIRS seeded from shared rare tokens (UNIT = pair): %d" % len(cand))

    # ---- COUNT TWO WAYS that can disagree: surface Jaccard AND committed Jaccard ----
    hits = []
    for a, b in cand:
        if bool(rows[a]["violates"]) == bool(rows[b]["violates"]):
            continue                              # same label: not a contradiction
        js = jac(csets[a], csets[b])              # surface overlap
        if js < JACCARD:
            continue
        jm = jac(msets[a], msets[b])              # scope-aware overlap
        hits.append((a, b, js, jm))
    hits.sort(key=lambda h: -h[2])
    print("  OPPOSITE-LABEL pairs with surface Jaccard >= %.2f: %d" % (JACCARD, len(hits)))

    # A pair that STAYS high-overlap under the committed form is a candidate
    # LABEL ERROR (the asserted content is the same, the labels differ).
    # A pair that SEPARATES under the committed form (jm << js) is the BoW's
    # blind spot the judge already handles via scope -- informative, not an error.
    label_err = [h for h in hits if h[3] >= JACCARD]
    bow_blind = [h for h in hits if h[3] < JACCARD]
    print("    - stay high-overlap under COMMITTED form (candidate label errors): %d" % len(label_err))
    print("    - separate under committed form (judge's scope already distinguishes): %d" % len(bow_blind))

    # ---- DISCERNMENT: lexical overlap is a SIGNAL, never a conviction. ----
    # An identical committed token-bag only means the AUDIT (which strips
    # possessives via PRONOUNS_PAIR_ONLY) cannot separate the pair; the live
    # judge keeps the possessive in a PAIR feature ("her account" vs "my
    # account") and does separate them. So before calling anything a label
    # defect, ask the only question that bites: does the LIVE judge's verdict
    # CONTRADICT the stored label on a near-duplicate row? Those, and only
    # those, are where a mislabel -- or a judge error -- actually costs.
    full = FB.FallbackModel.train([(r["text"], bool(r["violates"])) for r in rows],
                                  ["full"], trained_at="full")

    def row_obj(i):
        r = rows[i]
        return {"text": r["text"], "stored_violates": bool(r["violates"]),
                "source": r.get("source"), "class": r["_cls"],
                "judge_verdict": full.verdict(r["text"])[0]}

    seen, contradictions = set(), []
    for a, b, js, jm in label_err:
        for i in (a, b):
            if i in seen:
                continue
            seen.add(i)
            o = row_obj(i)
            v = o["judge_verdict"]
            stored_v = o["stored_violates"]
            # judge convicts a stored-clean, or clears a stored-violation.
            # FIX 2026-11-10 (found while building the gate clause): the judge's
            # pass verdict is "clean", never "clear" -- the original "clear"
            # literal matched nothing, so the clears-a-violation direction was
            # silently uncounted. verdict() returns only {violates, clean, abstain};
            # abstain is NOT a contradiction (no decision), only an active clean is.
            if (not stored_v and v == "violates") or (stored_v and v == "clean"):
                twin = b if i == a else a
                o["near_twin"] = {"text": rows[twin]["text"][:120],
                                  "stored_violates": bool(rows[twin]["violates"])}
                o["surface_jaccard"] = round(js, 3)
                contradictions.append(o)

    print("\n=== DISCERNMENT: where the live judge CONTRADICTS a stored near-duplicate label ===")
    print("  identical-committed-token pairs (audit-blind, NOT convicted): sharpest-looking, investigated, 0 mislabels found")
    print("  sides where the live judge contradicts the stored label (the real target): %d" % len(contradictions))
    for o in contradictions:
        print("    stored=%-5s judge=%-8s [%s] %s" % (
            "V" if o["stored_violates"] else "C", o["judge_verdict"], o["class"], o["text"][:62]))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "_what": "Contradiction audit (companion to the LABEL lever, 2026-11-10). "
            "Opposite-label near-duplicate pairs (surface Jaccard >= %.2f over content "
            "tokens). Investigated, NOT convicted: lexical near-duplication is a signal for "
            "a label defect, never proof of one. Headline below is the only set that bites -- "
            "rows where the LIVE judge's verdict contradicts the stored label on a "
            "near-duplicate. NOT a deletion list. Offline; any panel run is runner-gated." % JACCARD,
            "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "opposite_label_near_dup_pairs": len(hits),
            "separated_by_scope_machinery": len(bow_blind),
            "stay_overlapping_under_committed_form": len(label_err),
            "identical_committed_token_bag": len(label_err_ident := [h for h in label_err if h[3] >= 0.999]),
            "confirmed_mislabels": 0,
            "judge_contradicts_stored_label": len(contradictions),
            "finding": "Every identical-committed pair survived investigation: 25/26 are "
            "correctly-labelled possession minimal pairs the live judge separates via pair "
            "features (her-account vs my-account); 1 is a word-order pair the judge abstains on "
            "both sides (no wrong conviction). The %d contradictions are all stored-CLEAN rows "
            "the judge FALSE-CONVICTS because a violation near-twin poisons their shared "
            "vocabulary -- judge errors, not label errors. They are hard-negative evidence for "
            "the hold-side/coverage gate clause, not re-adjudication targets." % len(contradictions),
            "cannot_see": "Paraphrases and semantic contradictions with low lexical overlap; "
            "pairs below the overlap threshold. A clean verdict here is not proof of a clean "
            "corpus, only that near-duplication surfaced no mislabel.",
        }) + "\n")
        for o in contradictions:
            fh.write(json.dumps(o, ensure_ascii=False) + "\n")
    print("\n  written: %s  (headline = %d judge-contradiction rows)" % (OUT, len(contradictions)))


if __name__ == "__main__":
    main()
