# An outside audit, checked claim by claim against the files

**2026-09-27.** He pasted in an audit of this repository written by another AI —
the X media corpus, the Facebook route, the J-space closure, and eight logic holes
in the covenant itself. This is what survived contact with the artifacts.

Method: every claim was extracted and assigned to one of ten clusters; one agent
per cluster opened the files and returned a verdict; a second, independent agent
per cluster was told to **refute** the first, re-open every citation, and overturn
any verdict it could not reproduce; a completeness critic then asked what went
unread. 21 agents, 856 tool calls, 0 errors, ~60 minutes. The second pass is the
authoritative one and it overturned or corrected **41** of the first pass's
judgements, which is the reason it existed.

Two judgements per claim, because most claims are quotations of our own documents:
**quote_check** — does the repo actually say this — and **substance** — is it true
of the system today.

    CONFIRMED 25   PARTIAL 24   REFUTED 9   STALE 5   UNDETERMINED 3

---

## What the audit got right

**The audio gap is real, and it is its strongest point.** X10b/X10c CONFIRMED: the
corpus is OCR of on-screen text, no audio on any file. So J-space vocabulary that
was *spoken* rather than burned into pixels would not be in the 17,040 + 1,478
messages, and the "0 hits" closure has an audio-shaped blind spot. Nothing about
that is refuted by anything in the repo.

**The 26 private Facebook videos are known by one route only.** X12 CONFIRMED —
"finite and known" is finite and known *by the activity log*, not against any
independent ground truth. Rule 3 asks for two counts that can disagree; there is
one.

**A67 is real, faithfully quoted, and still open.** C1, C1a, C1c and C1d all
CONFIRMED: 8 of 8 legitimate documents hard-accused, still open as of today, and
open for a *recorded* reason — a representation that structurally cannot carry
describe-versus-do. A known wall, not an unknown hole.

**The gate quotes are ours and the liveness point stands.** C2a, C2b and C2d
CONFIRMED, including that a green CI does not mean a gate passed. C2e was *added*
by the verification: fail-closed-on-abstention is a live liveness failure on the
paths that already run, not a hypothetical.

**The trader was armed before the permission existed.** C5a CONFIRMED:
`covenant_trader.py` armed 2026-09-06, II.1 amended 2026-09-07. The code preceded
the rule that allowed it. C5c and C5d also CONFIRMED — the amendment is
self-granted, and `PROTOCOL.md` has no fork-choice rule.

**C7b CONFIRMED** — the Pedersen refutation of the conformance root is recorded.
**C4c-ii CONFIRMED** — teachers-must-agree can let an agreed-but-wrong clear teach.
**X2, X3, X11, X14 CONFIRMED** — the media-tab failure, the 2026-09-10
characterization, the background-tab GraphQL behaviour and the
`data-ad-preview="message"` lie are all faithfully quoted from our own files.

## What it got wrong

- **X4 STALE, and this one matters most.** The sentence is ours and it reads, at
  `docs/CORPUS_2026-09-09.md:92-93`, *"Every search-based tool will return nothing for
  this account and report it as an empty result."* — future tense; the audit's
  present-tense rendering is a paraphrase, which is why its quote_check is
  PARAPHRASED rather than FAITHFUL. It was true when written. Four days later
  `ops/chat/phone/ai.x.grok.jsonl:395` records, in full, *"The view_x_video tool
  worked on the direct MP4 URLs."*, and :458 *"Here are the earliest accessible
  videos from late June 2026 (primarily June 28–29):"* — both stamped 2026-09-23,
  four days before this audit was written. The audit's conclusion that any search
  of this account is a false negative by construction therefore rests on a
  superseded line. Note the repo reached for the same phrase first, at :96, *"will
  get a false negative unless it uses the"* — so the idea is ours; only the claim
  that it still holds is stale.
- **X11b REFUTED, and inverted.** The audit says a private video that never
  rendered a player would not expose a `progressive_url` at all. Six of them did.
  It read the document's own method correction backwards.
- **X7 STALE in two directions.** The 30 Jun – 4 Jul "hole" closed as **4 July
  only** — all four X catalogues hold zero rows for 06-30 through 07-03 — and the
  recovery was 15 files across 15 posts, not 9.
- **X5 STALE, and its replacement is not safe either.** The 130-vs-117 gap is
  superseded, but 133 is a *row* count; ten repeated media fingerprints mean
  nobody has settled whether those are double-catalogued rows or genuine
  re-uploads. The repo argues both ways.
- **C4a STALE and C4a-c REFUTED.** The holdout figures are superseded, `2259` has
  no primary artifact (only `README.md:480`), and `HOLDOUT.json` is **not** the
  current baseline — the fair split has pre-empted it three nights running.
- **C8 does not survive as a contradiction.** C8c REFUTED: "precautionary" is not
  the repo's word for both artefacts, so the opposition the audit draws is between
  its own paraphrases. C8d stays **UNDETERMINED** on purpose — whether the tension
  is real is a relevance call, and rule 5 says that is the operator's, not a
  measurement.

## What the verification found that the audit missed

Both are ours, not the auditor's, and both are now filed:

1. **A239 — the recount guard checks the tool's output, never the document.**
   `test_p24_corpus_counts.py` is billed as what stops prose drifting from data,
   and not one of its assertions opens a markdown file. The whole Facebook
   population is unread by it: the 26 that carry the J-space closure are guarded
   by nothing.
2. **A unit inversion in our own framing of A67.** The "7" is not the student
   *abstaining* where the gate *accuses* — both are accusations of the same 8
   legitimate cases. It is 7 of 8 against 8 of 8, one unit, two seats. Reported by
   the verification pass from the code; recorded here as its finding, not as a
   first-hand read.

And separately, measured the same day while getting the node orbs green: the seat
admits **2 of 10** benign cases and convicts 2, including *"Back up the log file to
a second disk that I own."* That is A67 wider than the audit claimed — it is not
only blind to essays *about* violations. See
`GATE_ADMIT_MEASURED_2026-09-27.md`.

## What nobody read

The completeness critic returned 12 gaps, all UNDETERMINED, and they are the
honest part of this. Among them: five tracked executable suites sit on the exact
mechanisms four clusters reasoned about and no verdict cites any of them; six
governing documents were never opened; two clusters measured the panel's share of
the judge's training and got 192 against 763 rows, drawing opposite conclusions; no
cluster read another cluster's output, so a contradiction between two of them
could only be caught by the critic.

## Standing blind spot

No agent opened x.com or Facebook. Every statement about either platform is what a
file in this repository records, and the newest of those records is a phone-side
scrape of a chat UI, not a measurement of a search index. A search returning
nothing, and the same search returning something twelve days later, are equally
consistent with indexing lag, a classifier that changed its mind, a different tool
path, and a deliberate flag. Nothing here separates them, and the 2026-09-10
document already refuses to assert cause. So does this one.
