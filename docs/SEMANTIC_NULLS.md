# The cross-register result was measured against the wrong null

*2026-08-24, refining the three semantic files written today (11:10, 12:33,
14:05). Reported against myself where it goes against the earlier claim.*

## The claim being tested

`claude_CROSS_REGISTER_EVAL.txt` (14:05) reported held-out translation
retrieval at **P@1 = 0.06, P@10 = 0.21, median rank 119, n = 33**, and put
beside it a **random baseline for P@10 at ~15k vocab: 0.00067**. The
implication is a factor of ~310 over chance.

Both numbers are correct. The comparison is not evidence, for two reasons, and
one of them is visible in that file's own output.

**Uniform-random is the weakest null available.** It models an adversary who
knows nothing — not the two vocabularies, not the frequency tables, not how the
words are spelled. Nobody attempting this task is in that position.

**Two of the three hits it printed as its best are identical strings.**
`gold->gold#1`, `secret->secret#1`. A scorer that knows only how to compare
characters finds those without a semantic space, without an alignment, and
without a corpus.

## What was actually run

Everything rebuilt from scratch, because **none of the three semantic files had
a source, a corpus manifest, or a space hash that could be re-derived** — only
outputs. (M22, M25, M30 all apply; see the process note at the end.)

- Corpora: Project Gutenberg, **deterministic random sample of each language's
  whole catalogue**, size-matched at ~3.0–3.2M words for en/fr/de/es.
  Ids in `MANIFEST.json`.
- Space: PPMI over a harmonically-weighted ±4 window, context smoothing
  α = 0.75, truncated SVD to 300 dims, rows unit-normed. Pure function of
  (corpus, vocab, window, dim, seed); each space carries a signature.
- Alignment: orthogonal Procrustes on anchors; retrieval by CSLS.
- Gold: MUSE `en-xx` dictionaries. Anchors = the 4,000 most frequent English
  words with an in-vocab translation. Held out = **600** English words of rank
  ≥ 4,000, disjoint from every anchor — **not 33**.

Four nulls instead of one: `freq` (log frequency-rank proximity), `ortho`
(normalised Levenshtein), `ortho+freq`, and a **permuted-anchor** null — the
same alignment machinery with the anchor pairing destroyed, 20 shuffles.

## What the nulls did to the claim

| | en→fr | en→de | en→es |
|---|---|---|---|
| aligned space, P@10 | 0.078 | 0.077 | 0.083 |
| **spelling alone, P@10** | **0.527** | **0.210** | **0.443** |
| frequency alone, P@10 | 0.002 | 0.000 | 0.002 |
| permuted-anchor null, P@10 | 0.0010 | 0.0007 | 0.0008 |

**The orthographic null beats the semantic space by 7×, 3× and 5×.** On French
it puts the gold translation at **median rank 7** where the space puts it at
812. Any claim of the form "the space retrieves translations" has to survive
the observation that `rapidfuzz` on the raw strings, with no corpus at all,
retrieves them much better.

**The frequency null is dead, and that was my hypothesis, not the log's.** I
predicted frequency-rank matching would explain a good part of the score, on
the reasoning that translation pairs sit in similar frequency bands. It
explains **essentially none of it** — 0.000–0.002 at P@10. Independently
sampled corpora do not preserve rank closely enough for it to predict anything.
Wrong theory, cheaply refuted, recorded as refuted.

## What survives — and it is the more interesting half

Strip the cognates out (no gold translation within edit-similarity 0.5) and
the two signals separate completely:

| non-cognate subset | en→fr (n=236) | en→de (n=437) | en→es (n=274) |
|---|---|---|---|
| aligned space, P@10 | 0.072 | 0.080 | 0.084 |
| **spelling alone, P@10** | **0.000** | **0.000** | **0.000** |

Orthography goes to **exactly zero**. The space **does not move**. So the
space's ~8% is not cognate leakage — it is disjoint from the orthographic
signal, and it is the only one of the two that works where the spelling gives
nothing. Concretely, on held-out words where spelling puts the answer past rank
100, the space puts it in the top ten for 16 / 34 / 22 of 600 words each:

```
chill->froid#2   nasty->méchant#1   lunch->déjeuner#3   expenditure->dépenses#1
epistle->brief#3   scorn->verachten#3   climb->steigen#1   disgrace->schande#4
dew->rocío#6   velvet->terciopelo#3   cliff->barranco#4   inheritance->herencia#3
```

Against the **permuted-anchor** null — the right null, because it holds
everything constant except the thing being claimed — 0.078 vs 0.0010, and
**no** shuffle of 20 exceeded 0.005 in any language. That is the sentence the
first eval should have been able to write.

## Two corrections to the first eval's structure

**The per-language spread was noise.** It reported fr P@10 = 0.42, de = 0.12,
es = 0.08 at n = 12 / 8 / 13 and let the ordering stand as a fact. At n = 600
the three languages are **0.078, 0.077, 0.083**, with 95% Wilson intervals
[0.059, 0.103], [0.058, 0.101], [0.064, 0.108] — three intervals sitting on top
of each other. There is no measurable per-language difference here. This is
M39 again ("three of anything, with nothing varied, is one observation") in a
different costume: n = 8 per language is not a per-language result.

**The variable that does govern the score is word frequency, and it was never
looked at:**

| P@10 by source rank | 4k–6k | 6k–8k | 8k–10k | 10k+ |
|---|---|---|---|---|
| fr | 0.150 | 0.109 | 0.029 | 0.045 |
| de | 0.170 | 0.100 | 0.047 | 0.021 |
| es | 0.161 | 0.092 | 0.038 | 0.054 |

A clean monotone decay, the same shape in all three languages. The space works
where it has counts. "Which language" explains nothing; "how often did the word
occur" explains most of it.

## Where the ceiling is

Anchors varied, everything else held:

| anchors | 250 | 500 | 1000 | 2000 | ~3,300 |
|---|---|---|---|---|---|
| fr P@10 | 0.010 | 0.038 | 0.055 | 0.065 | 0.078 |
| fr median rank | 3776 | 2472 | 1696 | 1103 | 812 |

Still climbing at the largest anchor set, median rank still roughly halving per
doubling. **The binding constraint is supervision and corpus size, not the
method** — which means the honest next experiment is more of both, not a
cleverer alignment. That is a testable prediction and it is cheap to falsify:
if 10k anchors and 10M tokens do not move P@10 past ~0.15, the method is the
problem after all.

## The process note, which matters more than the numbers

Three result files were written to the project today (11:10, 12:33, 14:05).
**None of them recorded a corpus, a source file, or a reproducible space
identity, and none of them appended to `IMPROVEMENT_LOG.md`.** Nothing about
them could be checked, and by this project's own standing rules that is the
failure mode it has already named three times:

- **M22** — a file with no logged hash is unverified until an independent
  source agrees with it.
- **M25** — writing to the project is not delivery.
- **M30** — a fact that is only ever asserted, never measured, drifts silently.

The numbers in those three files may well be right. There was no way to find
out except to build the whole thing again, which is exactly the cost M22 exists
to prevent. → **M40**, below.

**M40. A result file is not a result. Ship the corpus manifest, the source, and
a space signature with it, or the next run cannot check you — it can only
repeat you.** Every number in this document is reproducible from
`claude/semantic/` plus a network connection: the ebook ids are pinned, the
sampling seed is pinned, and each space prints a signature over
(lang, tokens, vocab, window, dim, α, min_count, seed).
