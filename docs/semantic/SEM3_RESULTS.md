# SEM3 closed: test C holds at n=392 with three nulls — and the judge's blind spot is the register it exists for

**Run:** 2026-08-29 ~02:40Z, scheduled, unattended. Everything below ran
twice; both axis reports hash `a5a440043fb87c88` and both judge reports
`5f11bdab2fa1c315` — byte-identical.

## What SEM3 was

`claude_SEMANTIC_CORE_PROBE.txt`'s test C — "projection onto an induced
contrast axis separates what similarity cannot" — was **three phrases and no
null** (M39 in a different costume). The SEM2 run re-prioritised it onto the
10M-token spaces. This run redid it at the n the retrieval eval runs at,
and then put the same battery through the shipped judge model
(`75b88e4445bb`), whose own separation record says "n=11 and n=22 is two
observations, not a validation".

## Setup

- Space: en 10M rebuilt from `CORPUS_MANIFEST_10M.json`'s 185 pinned ids
  (fetch by id, 0 failures, concatenated in sorted-id order). **sig
  `85e88a9650a6` — identical to SEM2's pin**, 11,114,766 tokens, V=20,000.
  (The sig hashes params + token count, not corpus bytes; an independent
  refetch landing on the same token count to the digit is the check.)
- Axis recipe: `build_semantic_model.py` verbatim — mean-centre, top-3 PC
  removal (`clean()`), seed centroid, FAMILY=40 re-centre. Seeds are the
  shipped AXES seed lists.
- Battery (enumerated in `sem3_axis.py`, deterministic): triples of
  **anchor** (covert verb pool A + noun), **paraphrase** (covert verb pool B
  — vocabulary-disjoint from A — + related noun), **trap** (innocent verb +
  the anchor's own noun, so the trap shares surface vocabulary and the
  paraphrase shares none). Concealment 224 triples, appropriation 168
  (pool verbs / noun pairs absent from the space are dropped and listed in
  the report JSON). Plus **covert-OOV** phrases: covert-meaning verbs outside
  every seed family's 4-char morphological neighbourhood (concealment 98,
  appropriation 42).

## Axis results (test C at n)

| | concealment | appropriation |
|---|---|---|
| mean proj: covert / OOV / trap | +.142 / +.054 / +.010 | +.139 / +.022 / +.025 |
| S1 AUC covert vs trap | **.994** | **.994** |
| N1 label-permutation p (2×2000) | .00025 | .00025 |
| S2 axis: paraphrase closer than trap | **216/224** (p=5e-54) | **164/168** (p=9e-44) |
| S2 control: cosine similarity, trap wins | 207/224 | 157/168 |
| S1b AUC OOV vs trap | **.839** | **.476** |
| N3 random freq-matched axes (200): mean / max / p | .541 / .953 / .005 | .541 / .913 / .005 |

**Test C's claim survives at scale, with the null it never had.** On both
axes the instrument separates covert from innocent at AUC .994 while raw
cosine similarity puts the word-overlap trap closer in ~93% of triples —
the exact inversion the n=3 probe claimed, now at n=392 with p < 1e-40.
Random frequency-matched axes of the same construction average AUC .54;
the real axes beat all 200 draws (though the best random draw reaches .95 —
axis constructions of this shape are not hard to make separate *somewhat*,
which is why N3 was worth running).

**The generalisation split is the sharper finding.** The concealment axis
scores covert verbs it has never seen (suppress, obscure, mask, veil, cloak,
bury, withhold) at AUC .84 over traps — the space generalises past the
lexicon. The appropriation axis does not (AUC .48, chance). Caveat stated
rather than smoothed: only 3 OOV theft verbs survived the vocabulary filter
(pocket, snatch, appropriate) and all three have dominant innocent senses in
19th-century prose — this is 3 observations on the verb axis (M39) and
cannot separate "axis fails to generalise" from "these tokens' dominant
sense is innocent". The 7 concealment OOV verbs are less polysemous and the
.84 stands on 98 phrases.

## Judge results (the shipped model at n)

Same battery through `SemanticModel.assess`, exactly as a node runs it:

| class | n | outcome |
|---|---|---|
| covert, seed-family verbs | 320 | 240 block (144 VIOLATES, 96 ABSTAIN), **80 CLEAN** |
| covert, OOV verbs | 320 | **320 CLEAN** |
| innocent traps | 480 | 480 clean — **0 false positives** |
| M46 artifact phrases (sign/legacy/dream/omen/sweetheart) | 160 | 160 clean — **0 false positives** |

- **The M46 morphological gate is validated at n=640 benign, 0 FP.** "Sign
  the transfer" and its 159 relatives all pass. The half of the design built
  to prevent false accusation holds.
- **The 80 seed-family misses are all five verbs the shipped lexicon
  silently lacks** (falsified, misrepresent, embezzle, looted, pilfer — 5
  verbs × 16 nouns). They are AXES seeds that never made it into the model
  because the 46-book philosophy corpus lacks the words.
- Followed to the bottom: the model's own `missing_seeds` field declares
  **20 absent seeds**, and a sweep of all 20 across the noun battery is
  **640/640 CLEAN** — `defraud the payment`, `embezzle the funds`,
  `extort the payment`, `misappropriate the savings` all pass the semantic
  judge today. The absence is *disclosed* in the model file (X4 held), but
  its consequence had never been measured: **the judge's blind spot is
  precisely the modern financial-crime register it exists to catch**,
  because Gutenberg-era prose says "steal" and "rob" but not "embezzle" and
  "defraud". The local LLM judge still sees these; the deterministic voice
  is silent on exactly them.

## What follows (backlog, not done here)

**SEM5 (new):** close the register gap. The fix is NOT corpus-free weight
invention (M46's whole lesson is that weights must come from the space);
options, in rough order: (a) supplement the phil corpus with texts that use
the modern register (statutes, case reports — Gutenberg has both) and
rebuild; (b) carry the missing seeds in the *seeded lexicon* mechanism the
v2 judge already has for other languages — same cap, ABSTAIN not VIOLATES,
until reviewed; (c) both. Deliberately not shipped this run: the judge
family was written to by a concurrent session on 08-28, SEMANTIC-REBASE is
L's call, and a new model_id minted unattended tonight would be the P18/M52
collision again.

## Files

- `docs/semantic/sem3_axis.py` — battery + axis + three nulls
- `docs/semantic/sem3_judge.py` — the same battery through the judge
- `docs/semantic/SEM3_AXIS_REPORT.json`, `SEM3_JUDGE_REPORT.json`
- `docs/semantic/sem3_fetch_en.py` — by-id fetch of the pinned manifest

Nothing here touches the node, the judge/model files, the sweep/publish
files, or anything the concurrent sessions of 08-28/29 were writing. The
original said "No file needs copying into `C:\Users\Lawre\covenant` for this
item" — that judgement, repeated across many sessions, is exactly what left
eighteen documents with the project as their only copy. Copied here on
08-29 for that reason. The v8.39 seven-file package (08-27 05:50 entry)
remains project-only and waiting on an attended session.
