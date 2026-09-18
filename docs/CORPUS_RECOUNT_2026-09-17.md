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

> **THE READER CANNOT CHECK THIS, and that is stated here rather than left to
> be discovered.** The data this rests on is in `private/`, which
> `docs/CONSTITUTION.md` II.4 never publishes -- it names people who did not
> consent to being recorded. Only its fingerprint is published, in
> `docs/SUCCESSION_ANCHORS.md`, so an outside reader can verify the data has not
> been ALTERED but cannot read it and cannot re-run this.
>
> Under II.6 ("what is not checked is not claimed") the status of every number
> below is therefore **observed by the operator, not independently verifiable**.
> It is not a refutation of the result; it is the honest ceiling on it, and it
> only lifts when the same test runs on data a reader can open.

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
| **H6** | Rows written down and artifacts produced are independent, so counting one is a single route | transcripts on disk may disagree with catalogue rows | exact agreement in every store — **which is what happened**, so both counts corroborate |

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

**Facebook, corrected the same day — my "64 unaccounted" was itself a units
error, and it is rule 4 of `CLAUDE.md` broken by the person who wrote it.** I
compared 26 transcribed reels against 90, which is *upload events including
ordinary personal video*. The operator reconciled the three Facebook counts on
2026-09-09 and the reconciliation was already in the record:

    90   video UPLOAD EVENTS in the activity log (includes personal video)
    69   reel ids exposed by the profile grid
    47   RELEVANT reels -- about AI, consciousness or this project

**The in-scope corpus is 47.** On disk: **26 transcribed** — the 20 pre-6-July
reels, SETTLED and read end to end, plus the 6 children of three multi-video
posts, which `CORPUS_2026-09-09.md` still lists as OPEN and which have since been
pulled. So the honest remaining gap is **21 relevant Facebook reels**, not 64.

Both OPEN items from 2026-09-09 are now closed on disk: the 6 multi-post children
are present, and the "9 X video posts missing from the catalogue" were taken up
by the `x_missing` and `x_missing2` sweeps.

**How that 47 was settled matters more than the number.** Three automated passes
produced three figures and no way to choose between them; one sentence from the
operator — *"47 relevant"* — resolved it. A denominator can be measured. What
COUNTS cannot. That is now rule 5 of the standing method, because no amount of
walking directories can decide which of a person's videos are about their work.

**X is complete against its own catalogue.** A second, independent count —
transcripts on disk rather than catalogue rows — agrees exactly in all five
stores: 109, 7, 8 for X and 20, 6 for Facebook, with no item catalogued-but-unread
and none read-but-uncatalogued. Three X ids that first appeared to be orphan
transcripts turned out to live in `catalog_new.csv`, which shares the same `text/`
directory; checked rather than reported.

## 5. Worked into the system

- `tools/corpus_reconcile.py` — the recount. Discovers catalogues by walking.
- `test_p24_corpus_counts.py` — fails when prose and data drift, so this cannot
  quietly rot back into a stale document. It **SKIPS, not fails, when `private/`
  is absent**, because the staged runner has no private data and a suite that
  fails for the wrong reason gets switched off.

## 6. What this does not establish

Nothing here opens a video, reads a transcript, or visits X or Facebook. It
counts rows and derives dates. It cannot confirm any claim about *content* —
J-SPACE, CONTAINMENT, re-uploads — all of which came from footage. It cannot
locate the **21 in-scope Facebook reels** that are not yet on disk, and it cannot
judge relevance, so it could not have produced the 47 itself. And it cannot
explain the four-post excess over the operator's 120; it can only show it.

An earlier version of this section said "the 64 missing FB uploads". That number
was retracted the same day — see §4. It counted transcribed reels against upload
events including personal video.
