# SEM2 closed: the prediction passes 3× over — and the curve was never an anchor curve

**Run:** 2026-08-29 ~01:40Z, scheduled, unattended. Every number below was
produced twice; both sweep outputs and both non-cognate outputs are
byte-identical (run1 = run2 sha256 `55bb8b850d90…` for the sweep).

## The prediction, as filed (08-24, IMPROVEMENT_LOG §SEM2)

> the anchor curve has not flattened (fr P@10 .010/.038/.055/.065/.078 at
> 250/500/1k/2k/3.2k, median rank halving per doubling). If 10k anchors and
> 10M tokens do not pass P@10 ~0.15, I am wrong and the method is the problem.

## Setup

- Corpora: same deterministic Gutenberg sampling as 08-24 (seed 20260824,
  shuffle of the whole per-language catalogue), extended from ~3M to **11.1M
  (en) / 12.6M (fr) / 11.2M (de) / 11.1M (es) tokenized tokens**. Ids in
  `CORPUS_MANIFEST_10M.json`. en 185 books, fr 170, de 167, es 162.
- Spaces: `sem_core.build_space` untouched — V=20000, min_count=10, window=4,
  dim=300, alpha=0.75, seed=0 (the exact knobs of the 08-24 cache). Sigs:
  en `85e88a9650a6`, fr `bde3c79c41f1`, de `7e9dc8f5e949`, es `adf0ac3aa32b`.
- Scoring: embed-only CSLS (`anchor_sweep.py`'s path), MUSE gold dicts,
  test cap 600. Permutation null: 20 anchor shuffles.
- In-vocab gold source words grew with the corpus: fr 10,340 / de 10,604 /
  es 10,132 (the 10k-anchor regime exists at all *because* the corpus grew).

## Protocol A — token axis alone (08-24 protocol verbatim: anchors < rank
## 4000, test ≥ 4000, cap 600)

| anchors | fr 3M (08-24) | fr 11M+ | de 11M+ | es 11M+ |
|---|---|---|---|---|
| 250 | .010 | **.063** | .052 | .038 |
| 500 | .038 | **.158** | .122 | .128 |
| 1000 | .055 | **.300** | .222 | .245 |
| 2000 | .065 | **.385** | .282 | .332 |
| ~3.2k (max) | .078 | **.428** (med 19) | .318 | .377 |

Quadrupling tokens at FIXED anchors multiplied P@10 by ~5.5 (fr, 3.2k). At
11M tokens, **500 anchors already beat the entire 08-24 curve's best point**
(.158 > .078 — and clears the prediction's 0.15 bar on its own).

## Protocol C — the prediction's letter: 10k anchors, the same test band

10k anchors sampled uniformly from all in-vocab gold pairs; test = 600
left-out pairs at rank ≥ 4000 (the 08-24 band); two seeds.

| lang | anchors | P@10 seed0 [wilson95] | P@10 seed1 | perm null (max of 20) |
|---|---|---|---|---|
| fr | 9,740 | **.509** [.460,.558] | .463 | .0026 |
| de | 10,000 | **.458** [.409,.508] | .414 | .0026 |
| es | 9,532 | **.461** [.411,.511] | .441 | .0026 |

**The prediction asked for 0.15. The measurement is 0.41–0.51 — passed 3×
over, in all three languages, both seeds.** Median rank 9–21 over a 20,000
word vocabulary.

SEM1's discipline applied (spelling must not be the story): on the
cognate-free subset (every gold translation < 0.5 normalised Levenshtein):
fr **.475** (n=158), de **.469** (n=271), es **.461** (n=180) — statistically
indistinguishable from the full-set numbers. The space is doing the work
where spelling scores zero.

## Protocol B — anchor axis at fixed band (the uncontaminated version)

Anchors can't grow past rank 4000 while the test band stays ≥ 4000 without
eating it, so the honest anchor-axis grid uses anchors < 15000 and tests on
rank ≥ 15000 — a strictly harder band (SEM1: P@10 decays with rank).

| anchors | fr | de | es |
|---|---|---|---|
| 3.2–3.5k (rank<4000, same band) | .233 | .165 | .202 |
| 2000 | .183 | .122 | .170 |
| 4000 | .248 | .173 | .225 |
| 6000 | .287 | .203 | .245 |
| 8000 | .293 | .220 | .265 |
| ~9–10k (max) | .297 | .237 | .257 |

Still rising at ~9–10k, but flattening: the last doubling (4k→8k) buys +4.5pp
(fr), where a token quadrupling bought +35pp on the easier band.

## What SEM2 actually taught

**The 08-24 "supervision curve" was a starvation curve.** It varied anchors
at fixed tokens and read the rise as "supervision pays"; the governing
variable was the corpus. At 3M tokens the vectors were too noisy for ANY
amount of anchor supervision to align well; at 11M the same method with the
same knobs is ~5× better everywhere, and supervision beyond ~4k anchors is
a second-order refinement. Consistent with SEM1's correction (frequency
governs P@10): more tokens move every word up the effective-frequency scale.

Prediction verdict: **PASS. The method is not the problem; the corpus was.**

## Caveats, stated rather than smoothed

- Protocol A's test WORDS differ from 08-24's (same protocol, but vocabulary
  composition shifted with the corpus). The comparison is protocol-identical,
  not test-set-identical; the 3M cache pickles no longer exist here to rerun
  the old corpus (the sandbox is fresh each run — M13's cousin).
- Protocol C's test n is 380–406 after anchor removal, not 600. Wilson
  intervals are printed against exactly that n.
- es Gutenberg depth: 162 of 885 catalogue texts consumed for 11M words —
  one further doubling is likely possible, two are not (DE5's family).
- The `+0.15` bar is passed on the ORIGINAL band (protocol C). On the harder
  ≥15000 band the max is .237–.297 — also past 0.15, for every language.

## Files

- `docs/semantic/fetch10.py`, `build10.py` — corpus + spaces (deterministic)
- `docs/semantic/sem2_sweep.py` — protocols A/B/C + permutation null
- `docs/semantic/sem2_noncognate.py` — SEM1-style cognate split
- `docs/semantic/CORPUS_MANIFEST_10M.json` — the 684 book ids
- `docs/semantic/SEM2_RESULT.txt` — raw sweep output (run 1 = run 2)

Nothing here touches the node, the judge, the sweep/publish files, or
anything the two concurrent sessions of 08-28/29 were writing. No file in
`C:\Users\Lawre\covenant` needed to change for this item — which is exactly
why it had never been saved here until the 08-29 rescue.
