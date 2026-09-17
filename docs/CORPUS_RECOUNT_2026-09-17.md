# Corpus recount, 2026-09-17 — counted from the catalogues, not from the prose

**Asked:** *"refine theres inaccuracies use the methodical post recount if need
be cross reference with my past replies currently 120 on x alone, plus facebook
hosted videos your inability to count properly is no mistake. use regex and
document it with the scientific method ensure this is worked into the system as
part of the total thought process"*

Re-runnable: `python tools/corpus_reconcile.py`

---

## 0. The error that prompted this, stated before the results

On 2026-09-16 I cross-checked `NJEST1987_MEDIA_INDEX_2026-08-29.md` against
itself, found it internally consistent, and reported that as accuracy. Internal
consistency is not accuracy. Three faults, and they are one fault:

- I checked a **document**, not the **data**. `private/*/catalog.csv` existed
  the whole time.
- The document was **superseded** eight days earlier by `CORPUS_2026-09-09.md`,
  which had **already found** the files-versus-posts conflation I announced as
  new.
- Then, writing the tool to fix that, I **hardcoded a list of five catalogue
  paths** and missed `private/x_missing2/catalog.csv`. Eight rows.

All three substitute a record I already hold for the thing I am supposed to be
measuring. That is cheap, always available, and fails silently and confidently.
The operator's phrase for it was *"no mistake"*, and as a description of a
pattern rather than an intent, that is fair.

---

## 1. Hypotheses, and what would falsify each

| | Hypothesis | Prediction | Falsified by |
|---|---|---|---|
| **H1** | Every count in the prose is derivable from the catalogues | each stated figure matches a computed one | any disagreement — and disagreement is the *result*, not a tool bug |
| **H2** | FILES and POSTS are different units and the prose conflates them | distinct `status_id` < rows | rows == distinct ids |
| **H3** | An X `status_id` is a snowflake, so every row carries its own date | derived date == `date` column | any disagreement |
| **H4** | Facebook ids are **not** snowflakes | derivation yields absurd dates | a plausible date |
| **H5** | My own enumeration is the weak link, not the regex | a discovery walk finds catalogues a hardcoded list missed | walk == list |

## 2. Method

Patterns are named in `tools/corpus_reconcile.py` so they can be argued with:

    RE_SNOWFLAKE = ^\d{17,20}$          an X status id
    RE_DATE      = ^(20\d\d)-(\d\d)-(\d\d)   leading ISO date in a column

Snowflake derivation: `date = epoch_ms + (id >> 22)`, epoch
`2010-11-04T01:42:54.657Z`. **The epoch is asserted against a known row before
any date is reported**, because an epoch wrong by a constant shifts every date
equally and looks perfectly self-consistent.

A catalogue is identified **by its columns** (`status_id` in the header), found
by **walking `private/`** — not by filename and not by a list. A name filter is
the same guess that missed `x_missing2`.

Counts only. No title, URL, filename or transcript text is read or printed, so
the output is safe to paste in public while `private/` stays private.

## 3. Results

**H5 CONFIRMED first, because it invalidates any result taken before it.** The
walk found **six** catalogues; my hardcoded list had five. Every number below is
post-correction.

| | rows (FILES) | distinct ids (POSTS) |
|---|---|---|
| X, all catalogues deduped | **133** | **124** |
| Facebook, all catalogues | **26** | **26** |

- **H2 HOLDS.** 133 files across 124 posts — nine posts carry more than one file.
- **H3 HOLDS.** **133 of 133** X dates agree with their own id. No drift.
- **H4 HOLDS.** No Facebook id is even snowflake-*shaped*. FB is counted, never
  date-derived.
- **H1 FALSIFIED**, which is the point of running it. The prose disagrees with
  the data everywhere:

| claim | source | computed |
|---|---|---|
| 117 files / 108 posts | media index, 08-29 | 133 / 124 |
| 121 X media posts | corpus, 09-09 | 124 |
| 114 X video files read | corpus, 09-09 | 133 |
| **90 FB uploads catalogued** | corpus, 09-09 | **26** |
| 120 on X alone | **operator, 09-17** | 124 posts |

## 4. What the numbers mean

**The X side is not short. The prose was.** The catalogue runs
**2026-06-28 → 2026-09-15**, two days behind today, and holds **124 posts** —
*more* than the 120 stated, not fewer. The 26-day staleness I reported yesterday
was a property of the markdown, not of the corpus. The data was two days old.

The four-post excess over 120 is not yet explained and is not assumed to be
error: a catalogue built by several sweeps can hold posts the Media tab does not
show, and the operator's 120 is a live reading of a tab that paginates. **Where
a computed number is lower than the operator's, the catalogue is short — not the
operator.** Here it is higher, so the question runs the other way and stays open.

**Facebook is the real hole: 26 catalogued against 90 claimed.** Sixty-four
uploads are asserted in `CORPUS_2026-09-09.md` and are not on disk in any file
carrying a `status_id` column. Either they live somewhere this walk does not
reach, or the 90 was never written down. That is the largest single gap in the
corpus and it sits on the surface the operator named — *"plus facebook hosted
videos"*.

FB coverage is also structurally weaker than X: `XREF_FACEBOOK_2026-09-03.md`
says plainly that the timeline loads lazily and **older posts were not read**.
The FB count has never had an honest denominator the way X now does.

## 5. Worked into the system

- `tools/corpus_reconcile.py` — the recount. Discovers catalogues by walking.
- `test_p24_corpus_counts.py` — fails when prose and data drift, so this cannot
  quietly rot back into a stale document. It **SKIPS, not fails, when `private/`
  is absent**, because the staged runner has no private data and a suite that
  fails for the wrong reason gets switched off.

## 6. What this does not establish

Nothing here opens a video, reads a transcript, or visits X or Facebook. It
counts rows and derives dates. It cannot confirm any claim about *content* —
J-SPACE, CONTAINMENT, re-uploads — all of which came from footage. It cannot say
whether the 64 missing FB uploads exist. And it cannot explain the four-post
excess over the operator's 120; it can only show it.
