# Everything I Claimed That Turned Out Wrong

A builder's inventory of his own claims that did not survive checking, in the order they were
made and unmade. This is not an apology and it is not asking anyone's forgiveness. It is the
record, volunteered, because the project's whole wager is that a claim is worth more once it has
been broken in public than it ever was while it stood unexamined.

The machinery behind this page: nothing wrong is edited away. The original wording stays where it
was written; the correction sits beside it; and a build-breaking test (`test_r1_retracted.py`)
refuses any reprint of a retracted claim that does not point back at its retraction. That is why
the entries below *describe* the old claims rather than re-print them — reprinting the exact
wording here, uncited, would turn this very file red, by design. Each item names the record entry
(`A…`) where the verbatim original and the pattern that now guards it are kept, in
[`RETRACTED.json`](RETRACTED.json) and [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md).

---

## 2026-09-09 — "35 of 36 guards protected what they named." (A74)

An audit put every suspected test-guard through mutation: break the exact property the guard
claims to protect, and watch whether the guard goes red. **35 of the 36 did not go red.** They had
been searching the *source text* for a word instead of running the code and seeing it fail — a
check that stays green while the thing it names is broken is not a guard at all. One (a reserve
clamp in `covenant_trader.plan()`) was fixed that day; the rest were logged open. This is now the canonical failure shape the
project watches for: a test that reads the source looking for words rather than exercising the
behaviour. **[A74]**

## 2026-09-09 — "Those pre-July videos were private." (catalogued; later A362)

The corpus catalogued that day described the 26 pre-6-July Facebook videos (across 23 upload
events) as visible only to the author ("Only me"). **That description was true when it was
written.** It is listed here because it was later retracted as a statement about the videos *today*
— see 2026-10-17. The lesson it eventually taught is the oldest one in the book: an audience
setting is a fact about a moment, not a permanent property of a file. **[A362]**

## 2026-09-11 — "The project has drawn contributions from outside institutions." (A121b)

Withdrawn by the author to NSF, unprompted — before any outside refutation, and reinforced by the one
that came four days later. It had not drawn outside-institutional contributions. The "outside
implementers" referred to were **AI agents run inside the project**. A claim of external, arm's-
length validation that was, on inspection, the project reviewing itself. **[A121b]**

## 2026-09-15 — "An independent build re-derived our number, so it did the computation." (A121)

The strongest claim on this list, and the emptiest. I held that if an independent build — sharing
none of this code, in any language — re-derived the published conformance number, that was proof
it had actually performed the governed computation. **Jens Egholm Pedersen (DTU)**, the author of
the idea I had borrowed, showed why it proved nothing: the published number is a SHA-256 taken
over the *expected outputs already printed inside the spec file*. Anything can re-derive it in
about nine lines without implementing a single one of the operations it was supposed to attest.
The real evidence is per-vector — compute each expected answer from its own input and compare — an
ordinary test-vector suite that pins the computation only where it happens to sample. Replaced the
same day by `docs/SEMANTICS.md`, which states the rules independently of any implementation, with
an exhaustively enumerated check. Sixteen days of outreach had been aimed at an event that could
be satisfied by reading a file. **[A121]**

## 2026-09-24 → 2026-09-27 — A forum-post title that asserted intent. (A236)

I posted to a Hugging Face forum under a title that said AI systems are trained *on purpose* —
with intent — to sound certain when they are wrong. Three days later the post's own body refuted
its own title: what the body actually describes is an incentive artifact of RLHF (raters tend to
score confident answers higher), which needs no one to intend it to be true — weaker in one way
(nobody chose it), stronger in another (nobody had to). The word asserting intent was retracted;
the operator conceded it that same morning ("I concede it."). The underlying finding is defended
neither way here, because **nothing in this project ever measured rater preference or
calibration** — so the honest position is to claim neither the mechanism nor its denial. The
original post stays up, unedited, with the correction beside it. **[A236]**

## 2026-10-17 — "The catalogue doesn't say whether those videos are public." (A362)

Returning to the pre-July videos. On this day I claimed the record left their public/private
status unstated. The operator corrected me on the spot: he had made them public after the
cataloguing date. Measured the same day, **all 20 reels in the catalogue read "Public"** to a
logged-out browser. So two things were put right at once: the 2026-09-09 "Only me" description was
retracted as a statement about the videos *now* (not as an error then — they did change), and my
own claim that the status was unstated was simply wrong — it *was* stated, and I had catalogued it
myself. "private/" in the repository is a gitignored local folder; it was never a claim about a
Facebook audience. **[A362]**

---

## What the list has in common

Read together, these are not six unrelated slips. Four of the six are the **same error wearing
different clothes**: treating a check that *resembles* evidence as though it *were* evidence. A
guard that greps for a word resembles a test. A hash over outputs printed beside it resembles an
independent reproduction. An AI agent inside the project resembles an outside implementer. A
confident forum title resembles a measured finding. In every case the resemblance was mistaken for
the thing. The project's method — count the real population before reasoning, name the unit, drive
every green both ways, and keep the broken claim beside its correction forever — is the scar tissue
from exactly these. The point of publishing the list is not absolution. It is that a reader can now
check whether the method actually holds, against the record of the times it did not.

*Sources: the verbatim originals and the regex patterns that guard each reprint live in
[`RETRACTED.json`](RETRACTED.json) (A121, A236, A362) and [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md)
(A74, A121b). This page paraphrases; the record quotes.*
