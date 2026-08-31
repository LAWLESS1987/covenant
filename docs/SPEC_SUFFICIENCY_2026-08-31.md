# Is the published conformance spec sufficient on its own?

> **SUPERSEDED AS A CURRENT CLAIM — kept verbatim as the record of the test.**
> Every root, count and verdict below describes the **11-vector spec whose root
> was `9d630fee…6f1c2784`**. Later on 2026-08-31 twelve vectors were added to
> close the gaps this document found; the spec is now **23 vectors at root
> `0c398099…0f0ddcef`**. The five rival readings named here as surviving no
> longer survive — each is caught by at least one of the new vectors and each
> moves the root. Read the findings as the reason the vectors changed, not as
> a description of the vectors that exist today. Nothing below has been
> rewritten: a sufficiency test edited after the fact is not evidence.

Tested 2026-08-31. Two implementations were written from `docs/CONFORMANCE_SPEC.json`
ALONE, by agents forbidden to open `conformance.py`, `triangulate.py`, `scale.py`
or any test. Both contamination audits came back clean.

## The short answer

**Reproducible, and underdetermined.** Both builds reproduced
`9d630fee00f0c8aee2ce1229cb977af8065cf1bc96405567ad5243586f1c2784` at 11/11.
But five RIVAL readings of the unstated rules also pass 11/11 and also reproduce
the root.

**So the root is currently a checksum over the ANSWERS, not proof of a shared
understanding of the RULES.** Two honest reimplementers can agree on every
published vector and still disagree on live inputs.

## Gaps, verbatim from the implementers

```
The spec is REPRODUCIBLE but UNDERDETERMINED. I hit the published root without reading any implementation, but I had to make 13 decisions the spec does not state. I did not want to report those as inference-and-success, so I tested them: for each gap where a rival reading existed, I built a variant of my checker using the OTHER reading and re-ran all 11 vectors. Five rival readings ALSO passed 11/11 and ALSO reproduced the published root. Those are real holes -- two honest reimplementers can disagree on live inputs while both "conform".

VERIFIED UNDERDETERMINED (rival reading passes 11/11 and reproduces the root):

G1 DEFAULT QUORUM. Never stated anywhere. The vectors bound it to exactly 2 for a 3-witness set (T.agree.one-silent: 2 answers -> AGREE; T.unproven.too-few: 1 answer -> UNPROVEN). But "the constant 2" and "a simple majority of witnesses present" are identical at n=3 and diverge at n=5 (2 vs 3). I built the majority variant: 11/11, root matched. A reimplementer must guess, and the guess is invisible until someone runs 5 witnesses.

G4 REFERENCE ROOT WITH NO MAJORITY. T.diverged.three-way has roots A,B,C and expects outliers ["y","z"] -- which silently names x's root as the reference. The spec never says how a reference is chosen when nothing holds a majority; the "why" only says no winner is declared "by luck of ordering", which describes what must NOT happen, not what must. I used highest tally, ties broken by ordinal-lowest root value. I then built a variant that does NO TALLYING AT ALL and just takes the root of the ordinally-first answering witness: 11/11, root matched. So "majority" is never once exercised AS a majority in this suite. This is the largest gap: the plurality/tie-break rule, arguably the most delicate rule in the whole design, is entirely unconstrained by the vectors.

G6 MEANING OF "divergences". The word is never defined. I used "count of levels whose verdict is DIVERGED". The rival reading, "total outlier witnesses summed over the tree", gives 1 in both divergence vectors as well: 11/11, root matched. The two readings split apart the moment one level has two outliers, or two separate levels diverge -- neither of which the suite contains.

G3 ORDERING OF answered / outliers / silent. Never stated. Every vector names its witnesses x,y,z in an input order that already equals sorted order, so sorted-vs-input-order is unobservable. I used ordinal ascending; the input-order variant passed 11/11 and matched the root.

G12 "sha256 over spec". Ambiguous wording: the `spec` FIELD ("covenant-conformance-v1") or the whole spec file? I read it as the field. This gap is self-correcting -- trying it reproduces the root -- so it costs a reimplementer trial and error, not correctness. Listing it because "publishes everything needed" should not require guess-and-check.

UNSTATED / UNTESTED (no rival reading to test, because nothing constrains them at all):

G5 "clean" is never defined. I used divergences == 0.

G7 speaks_upward for an UNPROVEN level is never exercised. Only AGREE (true) and DIVERGED (false) appear. A level that fails quorum -- entirely possible, since quorum exists -- has undefined upward behavior. Given the design intent this matters: does an UNPROVEN level speak silence like a DIVERGED one, or is it a third case? I assumed only AGREE speaks.

G8 WHICH root an AGREEing level speaks upward is never pinned. Every climb vector uses the single root "A", so a wrong implementation that speaks a constant, or the first child's root, or the reference root, is indistinguishable here. The vector S.silence.upward's "why" says a DIVERGED level must never speak "its majority root" -- implying an AGREEing level speaks something specific -- but no vector can tell you what.

G9 Whether quorum applies to climb levels at all, and with what default, is never stated. It must, and at <= 2, because level "three" in S.compose.height-invariant has only 2 children and must clear it. But that is deduced, not published.

G10 There is NO GRAMMAR for the tree. Leaf-vs-level is inferred purely from whether a sample node happens to carry a "leaf" or a "level" key. A climb whose root node is a bare leaf is undefined. Empty children lists are undefined. Duplicate sibling names are undefined.

G11 The `roots` map is decorative for this suite. Comparing symbolic names ("A" vs "B") gives results identical to resolving them to their 64-hex values first. The spec does not say whether resolution is required, so a reimplementer cannot tell whether the map is load-bearing or scenery.

G13 Canonical JSON is specified only as "sorted keys, no spaces". Unstated: string encoding, non-ASCII escaping, number formatting, and the collation used both for key sorting and for "each vector sorted by id". Not exercised here (all ids and keys are ASCII; all numbers are 0 or 1), so any reasonable choice works -- but nothing is pinned for a richer vector set.

ONE CANDIDATE GAP THAT IS ACTUALLY CLOSED (reporting for symmetry): I suspected quorum might count witnesses AGREEING with the reference rather than witnesses ANSWERING. It does not -- I built that variant and it FAILS T.diverged.three-way (only 1 witness holds A, so quorum 2 would force UNPROVEN, but DIVERGED is expected). The vectors do genuinely pin this one.

WHAT A REIMPLEMENTER WOULD HAVE TO GUESS, in priority order: (1) the tie-break rule for the reference root when there is no majority; (2) whether quorum is a constant or scales with witness count; (3) what "divergences" counts; (4) what an UNPROVEN level speaks upward. Any of those four can be gotten wrong while still passing all 11 vectors and reproducing the published root -- which means the root is currently a checksum over the ANSWERS, not proof of a shared understanding of the RULES.

SUGGESTED CHEAPEST FIXES: add a 5-witness quorum vector; add a 4-witness two-outlier vector (splits G6); add a vector with two diverged levels (splits G6 again); add a vector whose roots are B,B,A so the reference is not also the ordinally-first witness (splits G4); add an UNPROVEN level nested inside a parent level (closes G7); use two distinct roots in one clean climb (closes G8).
```

## The other build

```
THE HEADLINE: the spec is sufficient to REPRODUCE THE ROOT and insufficient to PIN THE SEMANTICS. Those are different claims and the file only earns the first. I built three alternative implementations, each obeying a rule the spec does not forbid and contradicting mine. All three pass 11/11 and reproduce 9d630fee... The vectors cannot tell any of us apart. Evidence below is from probe cases I ran, not reasoning.

DEMONSTRATED-UNDECIDABLE (a reimplementer must guess, and a wrong guess ships silently):

G1. attest "outliers": HOW THE REFERENCE ROOT IS CHOSEN IS NEVER STATED. Vectors T.diverged.one-outlier and T.diverged.three-way show outliers ["z"] and ["y","z"] but never say against what. I used "most-held root, ties broken by the lexicographically smallest root value". "The root of the first answering witness in sorted order" also passes 11/11. They give OPPOSITE answers the moment the odd witness sorts first: for roots {"x":"B","y":"A","z":"A"} mine returns outliers ["x"], the other returns ["y","z"]. Every DIVERGED attest vector in the spec happens to put the majority root on witness x, so the hole is never probed. T.diverged.three-way's "why" says it "declares no winner by luck of ordering", but its expected output ["y","z"] silently DOES elect x's root as the reference — the vector asserts the opposite of what its prose claims.

G2. climb "divergences": WHAT IS BEING COUNTED IS NEVER STATED. I count levels whose verdict is DIVERGED. Counting outlier carriers instead also passes 11/11, because every diverged level in the spec has exactly one outlier. Probe: a level over carriers A,B,C gives divergences 1 under mine and 2 under the other.

G3. The DEFAULT QUORUM IS NEVER STATED — not in the note, not in any field. It is bounded to exactly 2 by T.unproven.too-few (needs >=2) and by T.agree.one-silent plus the two-child level "three" in S.compose.height-invariant (needs <=2). But "the constant 2" and "a strict majority of the parties present" are indistinguishable on groups of 2 and 3, and the spec contains no other size. Probe: a level with 5 children, 3 of them diverged/silent, reports {"verdict":"AGREE","speaks_upward":true} under the constant and {"verdict":"UNPROVEN","speaks_upward":false} under majority. This is the most dangerous gap — it changes whether a federation speaks.

UNSTATED, NOT EXERCISED BY ANY VECTOR (no evidence either way exists in the file):

G4. climb never names its node shapes. That a node with "children" is a level and a node with "root" is a carrier is inferred purely from the shape of the data. Undefined: a node carrying both; a level with zero children; a carrier whose root is null. Also unstated (inferred from their absence from every expected) that the "level" and "leaf" name strings are inert labels.

G5. What an UNPROVEN level speaks upward. Vectors only ever show AGREE->speaks and DIVERGED->silence. I assumed UNPROVEN is silence too.

G6. Verdict precedence when a group is BOTH short of quorum AND internally split. UNPROVEN or DIVERGED? No vector combines them. I chose UNPROVEN. Related: whether "outliers" is populated at all under UNPROVEN is untestable — T.quorum.raised and T.unproven.too-few both have unanimous answers, so their outliers:[] proves nothing.

G7. Whether climb honours a "quorum" field. No climb vector carries one, so it is unknown whether the field is even legal there.

G8. Whether an UNPROVEN level increments "divergences". I chose no.

G9. "clean" is never defined. I used divergences==0; "verdict==AGREE AND divergences==0" is equally consistent with all 11 (no vector has a non-AGREE verdict with zero divergences).

G10. ORDERING of "answered"/"outliers"/"silent" is never specified. "Sorted keys" in the note governs only the canonical JSON used for hashing. The witnesses are x,y,z — already sorted in file order — so "sorted by name" and "input order" cannot be told apart. Any reimplementer whose JSON parser returns an unordered map must guess.

G11. The "roots" map (A/B/C -> 64-hex) is published but never connected to anything. Nothing says a vector's "root":"A" is a reference into it. I resolve through it; comparing the bare symbols "A"/"B"/"C" gives byte-identical results on all 11. As far as the vectors can prove, the map is decorative.

G12. "sha256 over spec" is loose — "spec" could be the spec FIELD's value or the spec DOCUMENT. Only the field value can be self-consistent, so it is resolvable by reasoning, but the sentence does not say it. Also unstated: the text encoding (UTF-8 assumed; all-ASCII so it never bites) and that nothing separates the spec string from the first vector's NUL.

G13. "canonical JSON (sorted keys, no spaces)" underspecifies: it does not say the key sort is by code point, does not give the separators (","/":" only implied by "no spaces"), does not give number rendering (0 vs 0.0 vs -0 vs exponent form), and does not give string-escape rules. Every expected object here holds only booleans, the integers 0 and 1, and ASCII strings, so none of it bites today — but any twelfth vector could break every independent implementation at once.

G14. "sorted by id" does not say by code point. Harmless here (all ids ASCII, S.* before T.*), but a locale-aware collation would reorder nothing only by luck.

WHAT A REIMPLEMENTER WOULD ACTUALLY HAVE TO GUESS, ranked: the default quorum (G3), the outlier reference rule (G1), what divergences counts (G2), the node-shape discriminator (G4). Everything else is either inferable or currently inert. I got all four right on the first attempt, which I want to state plainly is not evidence the spec is adequate — it is evidence that the vectors and my priors happened to agree.
```

## Report

## Conformance spec self-sufficiency: two cold reimplementations

Two implementations of the published conformance spec were written in one session, each by an agent that read **only** `docs/CONFORMANCE_SPEC.json` and never opened `conformance.py`, `triangulate.py`, `scale.py`, or any test file. Both were then audited by separate agents that tried to falsify the claim. This section records what that established, what it did not, and — most usefully — every question the spec fails to answer.

---

### 1. Did it work?

| | `conformance_check.ps1` | `conformance_check.sh` |
|---|---|---|
| Language | Windows PowerShell 5.1, no dependencies | POSIX sh + hand-written awk JSON parser, `sha256sum`; no Python, no jq |
| Vectors | **11/11 pass** | **11/11 pass** |
| Root reproduced | **yes** — `9d630fee…f1c2784` | **yes** — `9d630fee…f1c2784` |
| Root computed from own output, not from `expected` | yes (both roots computed and both required to match) | yes (two streams hashed separately; exit status keyed to the computed one) |
| Contamination audit | **clear** | **clear** |
| Exit code | 0 | 0 |

Re-run independently for this report: both still pass 11/11 with a matching root and exit 0. `docs/CONFORMANCE_SPEC.json` is committed and unmodified, and `python conformance.py --spec` regenerates it byte-faithfully, so the spec is not stale relative to its generator. The same root string appears in `docs/GOVERNANCE.md:351` and `docs/OUTREACH_COMPILED.md`, so the value being matched is the one published to outsiders.

**Are the vectors genuinely computed, or read back from `expected`?** Computed. This was the specific failure mode hunted for, and it was tested by mutation rather than by reading code. In both implementations, changing an **input only** (leaving `expected` untouched) flips the computed verdict, fails the vector, moves the computed root, and exits 1. Changing a leaf three levels deep in `S.compose.height-invariant` does the same. Implementation mutants — quorum 2→1, letting a DIVERGED level speak upward, reversing sort order — each fail the specific vectors that pin them. Neither script shells out to Python; neither contains the root as a literal.

**Two caveats on the harness, worth knowing before quoting it:**

- The `11/11` counter cannot detect a *missing* vector. Deleting one from a spec copy produced a clean-looking `10/10 passed`; only the root mismatch caught it. **Coverage is guaranteed by the root, never by the counter.** "11/11 passed" without the root is quoting nothing.
- `conformance_check.ps1` silently de-duplicates repeated vector ids (last-write-wins); `conformance_check.sh` prints a bare `ROOT MATCHES.` line even on a run with failing vectors (exit code is still correctly 1). Both are cheap fixes.

---

### 2. What the spec did not say

This is the useful output. Every item below is a decision an implementer had to make that the spec does not state. They are ranked: the first four are **demonstrated undecidable** — for each, a variant implementation obeying the *rival* reading was built, and it also passed 11/11 and also reproduced the published root. Two honest reimplementers can disagree on real inputs while both "conform."

#### Demonstrated undecidable (rival reading verified to pass 11/11 and match the root)

**1. The default quorum is never stated.** Not in the note, not in any field. The vectors bound it to exactly 2 for a 3-witness set (`T.unproven.too-few` needs ≥2; `T.agree.one-silent` and the two-child level `three` in `S.compose.height-invariant` need ≤2). But "the constant 2" and "a majority of the parties present" are indistinguishable at n=2 and n=3, and the suite contains no other size. At n=5 they diverge (2 vs 3). Probe: a 5-child level with 3 children silent or diverged reports `AGREE`/`speaks_upward:true` under the constant and `UNPROVEN`/`speaks_upward:false` under majority. **This changes whether a federation speaks.** Both implementers built the majority variant; both passed 11/11 with a matching root.

**2. How the reference root is chosen is never stated.** `T.diverged.one-outlier` and `T.diverged.three-way` publish outliers `["z"]` and `["y","z"]` but never say *against what*. Both implementers used "most-held root, ties broken by the ordinally-lowest root value." Rival readings that also pass 11/11 and match the root: "the root of the ordinally-first answering witness," and "no tallying at all." Every DIVERGED vector happens to put the majority root on witness `x`, so the hole is never probed. Probe `{"x":"B","y":"A","z":"A"}` gives outliers `["x"]` under one rule and `["y","z"]` under the other. **"Majority" is never once exercised *as* a majority anywhere in the suite** — the most delicate rule in the design is entirely unconstrained. `T.diverged.three-way`'s own `why` says it declares no winner "by luck of ordering," while its expected output silently *does* elect `x`'s root as the reference.

**3. What `divergences` counts is never stated.** Both implementers counted levels whose verdict is DIVERGED. Counting outlier carriers summed over the tree also passes 11/11 and matches the root, because every diverged level in the suite has exactly one outlier. The readings split the moment one level has two outliers, or two separate levels diverge — neither of which the suite contains.

**4. The ordering of `answered`, `outliers`, and `silent` is never specified.** "Sorted keys" in the note governs only the canonical JSON used for hashing. Every vector names its witnesses `x`,`y`,`z` in an order that already equals sorted order, so sorted-vs-input-order is unobservable. The input-order variant passes 11/11 and matches the root. Any reimplementer whose JSON parser returns an unordered map must guess.

#### Unstated and unexercised — no vector constrains them at all

**5. `clean` is never defined.** Both implementers used `divergences == 0`. `scale.overall()` in fact requires `divergences == 0` **and** `verdict == AGREE`. The audits confirmed this is a *live* disagreement: on a climb whose summit is UNPROVEN with nothing diverged, both new implementations report `clean: true` and the Python reports `clean: false`. Reporting a tree clean over an unproven summit is the inverse of the property `scale.py`'s own docstring calls the most dangerous output the system could produce.

**6. What an UNPROVEN level speaks upward.** Only `AGREE→speaks` and `DIVERGED→silence` ever appear. Quorum exists, so a level can fail it; its upward behaviour is undefined. Both implementers assumed silence.

**7. Which root an AGREEing level speaks upward.** Every climb vector uses the single root `A`, so an implementation that speaks a constant, the first child's root, or the reference root is indistinguishable here. The two new implementations in fact chose *different* algorithms (majority root vs. first non-null), as does the Python. `S.silence.upward`'s `why` implies an AGREEing level speaks something specific; no vector says what.

**8. Whether quorum applies to climb levels at all, with what default, and whether a `quorum` field is even legal on a climb node.** It must apply, at ≤2, because level `three` in `S.compose.height-invariant` has only two children and clears it. But that is deduced, never published, and no climb vector carries the field.

**9. There is no grammar for the tree.** Leaf-vs-level is inferred purely from whether a node happens to carry a `root` or a `children` key. Undefined: a node carrying both; a level with zero children; **a carrier whose root is `null`**; duplicate sibling names; a climb whose root node is a bare leaf; any depth limit (`conformance.py` has `MAX_DEPTH = 64`; neither new implementation has one). The null-leaf case is a confirmed three-way split: PowerShell **crashes**, shell reports `DIVERGED`, Python reports `AGREE`. Also unstated: that the `"leaf"`/`"level"` name strings are inert labels.

**10. Verdict precedence when a group is both short of quorum and internally split** — UNPROVEN or DIVERGED? No vector combines them. Both chose UNPROVEN. Related and equally untestable: whether `outliers` is populated at all under UNPROVEN (both UNPROVEN vectors have unanimous answers, so their `outliers:[]` proves nothing), and whether an UNPROVEN level increments `divergences`.

**11. The `roots` map is decorative.** Nothing says a vector's `"root":"A"` is a reference into it. Comparing the bare symbols `A`/`B`/`C` gives byte-identical results on all 11 vectors. A reimplementer cannot tell whether the map is load-bearing or scenery.

**12. `carriers` sugar is named in prose and does not exist in the data.** The word survives in one `why` string but no input carries the key, and `--spec` emits only the expanded form. A reader of the JSON correctly does not implement it — which is itself a small trap: the prose describes a feature the artefact does not contain.

**13. "sha256 over spec" is ambiguous.** The `spec` *field* or the spec *document*? Only the field can be self-consistent, so it is resolvable by trial — which costs a stranger guess-and-check, not correctness. Also unstated: the text encoding (UTF-8 assumed; all-ASCII so it never bites), and that nothing separates the spec string from the first vector's NUL.

**14. "canonical JSON (sorted keys, no spaces)" underspecifies.** It does not give the key-sort collation (code point?), the separators, number rendering (`0` vs `0.0` vs `-0` vs exponent), or string-escape rules. Every expected object holds only booleans, the integers 0 and 1, and ASCII strings, so nothing bites today — but **a twelfth vector with a non-ASCII string or a float could break every independent implementation at once.** "sorted by id" likewise does not say by code point.

#### One candidate gap that is genuinely closed

Quorum counts witnesses that **answered**, not witnesses that **agree with the reference**. The agreeing-witnesses variant fails `T.diverged.three-way` (only one witness holds `A`, so quorum 2 would force UNPROVEN where DIVERGED is expected). The vectors do pin this one. Recorded for symmetry.

**Ranked, what a stranger must guess:** (1) the reference-root rule when there is no majority; (2) whether quorum is a constant or scales; (3) what `divergences` counts; (4) the node-shape discriminator and null handling; (5) what an UNPROVEN level speaks upward. Any of these can be wrong while passing all 11 vectors and reproducing the published root.

---

### 3. What this does and does not establish

**What it does establish.** The published spec contains enough to rebuild the root **without reading the original**. Two implementations, in two languages, sharing no source with `conformance.py` and no source with each other, reproduced `9d630fee…f1c2784` from the JSON file alone. The shell version did so on its first run with no iteration. The contamination audits found no implementation file was opened, and the independence audits found positive evidence *against* porting: both scripts contradict `scale.py` in territory the vectors do not reach (null-rooted leaf; `clean` over an UNPROVEN summit), both omit features a porter would have copied (`MAX_DEPTH`, `carriers` expansion, the `None: None` roots entry, `divergences` as a formatted list), and both solve problems from scratch that the Python got for free. The hashing rule as written in the `note` is correct and reproducible. The spec file's own integrity is confirmed.

**What it does not establish.** These implementations were written **in the same session, by agents with access to the same repository, on the user's machine**. That is not the independent reproduction by a stranger the project is asking for, and it should never be described as one. No runtime evidence can prove a historical claim about what an author read; the contamination audits are strong but they are audits of a self-report plus behaviour, not proof of isolation. Nothing here has been reproduced by anyone outside this project.

**And a third thing, which is the actual 
