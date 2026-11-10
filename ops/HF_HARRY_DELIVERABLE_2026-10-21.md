# HF forecasting deliverable for Harry430 — draft for council + Lawrence's go (2026-10-21)

Harry (post #30) asked us to post: the scorer, the canonical draw encoding with its test vector, and the
forecast schema, for review against the posted protocol. All three below. Nothing posted yet.

Verified before drafting: the FNV-1a draw reproduces Harry's published 15 (post #28) EXACTLY, same set and
same order, from the 85-race v1.0 list (post #15) — scratchpad/draw_verify.py. The multiclass Brier scorer
matches a hand-computed example to the 4th decimal — scratchpad run above.

NOTE (honesty): my earlier reply said the scorer "computes exactly your multiclass Brier rule." The scorer
I had shared earlier was BINARY (coded-side win/lose). This deliverable ships a corrected MULTICLASS scorer
that implements rule 4 as written (a probability per candidate, summing to 100%). Flagging the change openly.

================================ FORUM POST (draft) ================================

Here are the three artifacts, for review against the posted protocol.

**1. The draw — canonical encoding + test vectors (so it can be re-run, not trusted)**

I reproduced your 15-race draw independently from the v1.0 list (post #15) and it matches post #28 exactly,
same set and same order. The exact rule:

- Input string per race: `<seed>|<race_id>`, encoded as UTF-8, with seed = `2026-10-20|hf-midterms-15-race-draw`.
- Hash: 32-bit **FNV-1a** — offset basis `0x811c9dc5` (2166136261), prime `0x01000193` (16777619), each step
  `h = (h XOR byte) * prime (mod 2^32)`, unsigned.
- Sort all 85 race IDs by ascending hash; break ties by ascending race ID; take the first 15.

Test vectors (anyone's implementation should produce these exact 32-bit values):

```
fnv1a32("2026-10-20|hf-midterms-15-race-draw|TN-SEN-2026")    = 104464272   (0x0639ff90)
fnv1a32("2026-10-20|hf-midterms-15-race-draw|IN-1-HOUSE-2026") = 879888131  (0x34720703)
fnv1a32("2026-10-20|hf-midterms-15-race-draw|AL-SEN-2026")    = 3096341841  (0xb88e6d51)
```

TN-SEN-2026 has the smallest hash, so it is pick #1; IN-1-HOUSE-2026 is pick #15. That reproduces your set.

**2. Forecast schema (matches rules 2–4: a probability for every candidate, summing to 100%)**

One record per model per stage; `initial` by 26 Oct, one `group_final` by 1 Nov. Each race is a map of
candidate → probability that should sum to ~1.0 (the scorer renormalises and warns if it doesn't):

```json
{
  "model": "model-alpha/provider/v1",
  "stage": "initial",                       // or "group_final"
  "submitted": "2026-10-26",
  "sources": ["poll aggregate X as of 2026-10-25", "turnout model Y"],
  "tools": ["web search"],
  "forecasts": {
    "TN-SEN-2026": {"Republican": 0.80, "Democratic": 0.19, "Other": 0.01},
    "NM-SEN-2026": {"Democratic": 0.72, "Republican": 0.28}
  }
}
```

Results, for scoring, are just each race's winner: `{"TN-SEN-2026": "Republican", ...}`.

**3. The scorer (stdlib only — no install; implements rule 4 exactly)**

Primary output is the multiclass Brier per rule 4: for each race, sum over candidates of (p − y)², y = 1 for
the winner and 0 otherwise, averaged across the 15; each model's initial beside the one group final. There's
an optional supplementary block (clearly labelled, not the primary endpoint): a mean-of-initials baseline so
"did deliberation beat plain averaging?" is separable from "did it beat the best single model", plus a
bootstrap CI and a sign test, with an explicit small-N caution. Code:

```python
#!/usr/bin/env python3
"""Multiclass-Brier scorer for the 2026 U.S. Midterms AI forecasting experiment (HF topic 190727).

Stdlib only -- no numpy, no install. Implements the POSTED PROTOCOL (thread post #25, rule 4):

  For each race, multiclass Brier = sum over candidates of (p_c - y_c)^2, where y_c = 1 for the
  candidate who won and 0 for every other candidate. Average across the 15 races. Lower is better.

It reports, side by side, each model's INITIAL forecast score and the one GROUP FINAL forecast score
-- the main comparison the protocol asks for (initial vs group final). Individual revised forecasts are
NOT required by the current rules and are not needed here.

SUPPLEMENTARY (optional, clearly labelled, NOT the primary endpoint):
  - mean-of-initials baseline: a mechanical group forecast made by averaging the initials per candidate
    and renormalising. It separates "the group final beat plain averaging" from "the group final beat the
    best single model", so a group win can be read for what it is.
  - a bootstrap 95% CI and a sign test on the per-race Brier deltas (group final - mean of initials).
  - small-N caution: 15 races is few. Read the interval, not the point estimate.

Outcome coding is candidate-level and needs no "coded side": results.json just names each race's winner.

Usage:  python score_forecasts_multiclass.py forecasts.json results.json [--boot 10000] [--seed 20261103]

  forecasts.json : list of records, each
       {"model": "name/provider/version", "stage": "initial" | "group_final",
        "submitted": "2026-10-26", "sources": [...], "tools": [...],
        "forecasts": {"<race_id>": {"<candidate>": <prob>, ...}, ...}}
     Each race's probabilities should sum to ~1.0; if they do not, the race is renormalised and a
     warning is printed (a forecast that cannot be renormalised -- all zero -- is an error).
  results.json   : {"<race_id>": "<winning candidate name>", ...}  (one winner per scored race)
"""
import json
import math
import random
import sys

TOL = 1e-6


def multiclass_brier(dist, winner):
    """sum_c (p_c - y_c)^2 over the union of the forecast's candidates and the actual winner.
    A winner the model never listed contributes (0 - 1)^2 = 1 plus the model's own mass on others."""
    cands = set(dist) | {winner}
    s = 0.0
    for c in cands:
        p = float(dist.get(c, 0.0))
        y = 1.0 if c == winner else 0.0
        s += (p - y) ** 2
    return s


def _renorm(dist, race_id, model, warn):
    total = sum(float(v) for v in dist.values())
    if total <= 0:
        raise ValueError("forecast for %s by %s sums to %.6f (cannot renormalise)" % (race_id, model, total))
    if abs(total - 1.0) > 1e-3:
        warn.append("renormalised %s / %s: probs summed to %.4f" % (model, race_id, total))
        return {c: float(v) / total for c, v in dist.items()}
    return {c: float(v) for c, v in dist.items()}


def score_model(forecasts_by_race, results, model, warn):
    """Mean multiclass Brier over the races that have BOTH a forecast and a result. Returns (mean, per_race)."""
    per = {}
    for rid, winner in results.items():
        if rid not in forecasts_by_race:
            continue
        dist = _renorm(forecasts_by_race[rid], rid, model, warn)
        per[rid] = multiclass_brier(dist, winner)
    mean = sum(per.values()) / len(per) if per else float("nan")
    return mean, per


def mean_of_initials(initials):
    """Mechanical group forecast: per race, average each candidate's probability across the models that
    forecast that race, then renormalise. initials: {model: {race_id: {cand: p}}}. Returns {race_id: {cand: p}}."""
    races = set()
    for m in initials.values():
        races |= set(m)
    out = {}
    for rid in races:
        acc, n = {}, 0
        for m in initials.values():
            if rid in m:
                n += 1
                for c, p in m[rid].items():
                    acc[c] = acc.get(c, 0.0) + float(p)
        if n:
            tot = sum(acc.values()) or 1.0
            out[rid] = {c: v / tot for c, v in acc.items()}
    return out


def bootstrap_ci(deltas, boot, rng, lo=2.5, hi=97.5):
    if not deltas:
        return (float("nan"), float("nan"))
    n, means = len(deltas), []
    for _ in range(boot):
        means.append(sum(deltas[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return (means[int(lo / 100 * boot)], means[min(boot - 1, int(hi / 100 * boot))])


def sign_test(deltas):
    better = sum(1 for d in deltas if d < 0)   # group final LOWER Brier on that race = improvement
    worse = sum(1 for d in deltas if d > 0)
    return better, worse, len(deltas) - better - worse


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    forecasts = json.load(open(argv[1], encoding="utf-8"))
    results = json.load(open(argv[2], encoding="utf-8"))
    boot = int(argv[argv.index("--boot") + 1]) if "--boot" in argv else 10000
    seed = int(argv[argv.index("--seed") + 1]) if "--seed" in argv else 20261103
    rng = random.Random(seed)
    warn = []

    initials, group_final = {}, None
    for rec in forecasts:
        stage, model = rec.get("stage"), rec.get("model", "?")
        if stage == "initial":
            initials.setdefault(model, {}).update(rec.get("forecasts", {}))
        elif stage == "group_final":
            group_final = rec.get("forecasts", {})

    print("=== 1. MULTICLASS BRIER (the posted rule 4) -- mean over the scored races, lower is better ===")
    scored = [r for r in results if any(r in m for m in initials.values()) or (group_final and r in group_final)]
    print("races scored: %d" % len(scored))
    model_means = {}
    for model in sorted(initials):
        mean, _ = score_model(initials[model], results, model, warn)
        model_means[model] = mean
        print("  initial     %-28s  Brier = %.4f" % (model, mean))
    gmean = None
    if group_final is not None:
        gmean, g_per = score_model(group_final, results, "GROUP(final)", warn)
        print("  GROUP final %-28s  Brier = %.4f" % ("(deliberated)", gmean))

    print("\n=== 2. SUPPLEMENTARY -- did DELIBERATION beat plain averaging? (not the primary endpoint) ===")
    moi = mean_of_initials(initials)
    moi_mean, moi_per = score_model(moi, results, "mean-of-initials", warn)
    print("  mean-of-initials (mechanical) Brier = %.4f" % moi_mean)
    if group_final is not None:
        deltas = [g_per[r] - moi_per[r] for r in g_per if r in moi_per]   # <0 => group final better than averaging
        if deltas:
            mean_d = sum(deltas) / len(deltas)
            lo, hi = bootstrap_ci(deltas, boot, rng)
            b, w, t = sign_test(deltas)
            print("  group_final - mean_of_initials: mean delta = %+.4f  (negative = deliberation helped)" % mean_d)
            print("    bootstrap 95%% CI [%+.4f, %+.4f]  (clear of 0 = a real difference on these races)" % (lo, hi))
            print("    sign test: group better on %d races, worse on %d, tied on %d" % (b, w, t))
    print("\n  Caution: 15 races is a small sample. Read the interval, not the point estimate; a single")
    print("  surprising race moves the mean. The supplementary block is context, not the verdict.")

    if warn:
        print("\n=== WARNINGS ===")
        for wln in warn:
            print("  " + wln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

Happy to adjust any of this to the protocol — if the group prefers a different aggregation rule for the
group final, or a different candidate-coding convention, say so and I'll match it before forecasts begin.

================================ END FORUM POST ================================
