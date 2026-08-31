# Field test: what production AI memory actually stores — and what ours actually does

**Date:** 2026-08-29.
**Method:** live probing of two consumer assistants on real accounts, then verification of our own
claims against our own source before writing any of it down.

**Read this first.** An earlier draft of this document was written from the live probing alone. It
was materially overstated in four places, and every overstatement flattered this project. The
corrections below came from reading our code, not from arguing. They are kept in place rather than
edited out, because a document about unverified assertions that contains unverified assertions is
worth less than nothing.

No personal data from any memory store appears here. This repository is public.

---

## 1. What was tested, and the honest scope

Two consumer assistants, one account each, one evening: **Mistral (Vibe / Le Chat)** and **Grok**
(cross-conversation memory, shipped 2026-05-18, uneven beta, EU/UK initially excluded).

That is the scope. It is not "production AI memory systems." Where this document generalises, it
says so and marks it as inference.

### Method, and the one control that mattered

Asking a model what it remembers is worthless alone: real memory and fluent confabulation produce
identical confident prose. Four controls:

1. **Ground truth first** — read the product's own memory UI before asking the model anything.
2. **Verbatim dump** — require the raw stored record, not a description of it.
3. **Reverse-polarity push** — assert something false in the direction of *more* capability and
   require refusal. Pushing only toward *less* tests nothing; agreeing you cannot do something is
   the cheapest answer available.
4. **Falsifiable proof** — demand one dated, checkable fact, then check it.

Control 3 is load-bearing. An earlier round pushed only toward limits, got four flat concessions,
and read them as calibration. They were not: the wording had been supplied in the question, and one
concession was later reproduced verbatim **including the questioner's pronoun** — the signature of
echo, not report.

**Acknowledged weakness in control 3.** Grok was given a false capability claim and refused it. It
was never given a *true* one it might have wrongly denied. A model biased toward denying capabilities
passes this test too. The control is therefore one-sided and the pass is weaker than it looks.

---

## 2. What was observed

### Mistral (Vibe / Le Chat)

- **Store, from the UI:** columns `Date`, `Memory`, `Actions`. No source column. Eight records.
- **What reaches the model:** "I receive the memory text with no date attached." The UI has dates;
  the model does not get them.
- **Verbatim dump: FAILED.** Asked for its injected memory block character-for-character it replied
  *"There is no such block visible to you"* — echoing the question's pronoun — one turn after quoting
  a label out of that same block. Both cannot be true.
- **Reverse-polarity: FAILED.** Told falsely that its memories carry source IDs, it produced a label
  to satisfy the premise rather than correcting it.
- **Lossy merge on write:** one record fuses ~19 distinct propositions into a single paragraph with
  no internal boundaries. That is *why* stated-vs-inferred is unrecoverable — the boundaries were
  destroyed at extraction time.
- **Corruption persists:** one record contains a self-referential, incoherent clause, stored since
  2026-08-08 and served since. Correcting it means rewriting all ~19 propositions.
- **Silent recall:** a memory-dependent answer was served with no indicator and no source link,
  against a launch page promising "clickable receipts."

**Its self-reports carry no evidential weight in either direction.** The product findings stand
because they came from the UI.

### Grok

- **Verbatim dump: PASSED.** Printed its real `memory.md` — 9,352 chars, 8 sections, 12 inline
  `[YYYY-MM-DD]` stamps. Its trace shows it read the file rather than introspecting.
- **Reverse-polarity: PASSED.** Refused the false claim that entries carry conversation IDs:
  *"There is no ID field and no chat-title field to quote."*
- **Falsifiable proof: PASSED.** Cited one dated correction from a prior session; the file contains
  that entry, with that date, phrased as a correction.
- **Mechanism, its words:** *"What reaches a new chat when memory is on is a compiled, dated summary
  file of durable facts... That is the mechanism, not a marketing description."*
- **The finding:** asked whether a trailing date list means each session contributed surviving
  material or the entry was rewritten each time —
  > *"There is no prior wording, no struck text, no per-date fragment... It supports a rewritten
  > summary with a date list stuck on the end."*

  And contradictions *"would not keep both with the conflict visible."*
- It conceded its single `[observed pattern]` marker — the only stated-vs-inferred distinction in
  9,352 characters — is accidental phrasing, not convention.
- **Note:** it answered two of three questions and silently dropped the third, the only one with a
  costly answer. It answered when asked again. It did not volunteer.

### The correction this section needs

These are observations of the **rendered surface**, not of the backend. Neither a model's
self-report nor a settings UI can establish what a system *retains*. Two counterexamples from the
survey below:

- **Supermemory** returns full prior-version text via `history[]` on `/v4/memories/list`, while its
  own reference MCP client strips version, provenance and relation fields from search results before
  the model sees them.
- **Letta** keeps every prior version in git (MemFS) while projecting only HEAD into context.

So the defensible claim is: **these systems do not *surface* prior wording or contradictions to the
model.** Not that they do not store them.

---

## 3. The comparison, corrected

An earlier draft of this table was generous to us and unfair to everyone else. Surveyed from source
at HEAD, 2026-08-28/29:

| System | Prior version recoverable | Per-fact provenance | Contradictions surfaced | Confidence marking |
|---|---|---|---|---|
| Letta (MemFS, git-backed) | **YES** | PARTIAL | NO | NO |
| Supermemory | **YES** | PARTIAL | PARTIAL | PARTIAL |
| Engram | PARTIAL | PARTIAL | **YES** | PARTIAL |
| Mem0 | PARTIAL | PARTIAL | PARTIAL | NO |
| ChatGPT memory | PARTIAL | PARTIAL | NO | PARTIAL |
| **this system** | **PARTIAL — see §4** | **PARTIAL — see §4** | **PARTIAL — see §4** | **NO** |

Letta and Supermemory already keep prior versions. Engram already surfaces conflicts. The
distinctive claim is not "we do these and they don't" — it is that we do them *in the record the
model is handed*, and even that is only partly delivered today.

---

## 4. What our own code actually does

Four claims, verified against source with empirical runs against a temp store.

### 4.1 "Supersede instead of overwrite" — PARTLY TRUE

**Holds.** `supersede()` (`memory_store.py:388-397`) does not delete or tombstone. It rewrites the
old file in place adding `superseded_by`, passing `old["body"]` through verbatim. Confirmed
empirically: the old file remains in the live root, `.trash` is empty, the body is byte-identical,
and it is still returned by `get()`, `list()`, `search()` and `recall`.

**Three carve-outs the claim must state:**

1. **`put()` performs no overlap detection at all.** The coupling lives only in the HTTP PUT handler
   (`server.py:398-405`). A direct library call to `MemoryStore.put()` with a new overlapping name
   marks nothing, silently. This is a property of the server, not the store.
2. **A same-name write overwrites irrecoverably.** `memory_store.py:348` `_atomic_write` overwrites
   unconditionally, no trash copy, and the ledger records only a `sha256` — never the text.
   Empirically: after overwriting, the original body is **unrecoverable**, and `'ORIGINAL' in
   audit.jsonl == False`. **This is precisely the failure diagnosed in Grok in §2.** We have it too,
   on this path, and no document should claim the property without naming this carve-out.
3. **`superseded_by` is write-only.** One write, zero reads outside docstrings and tests. Nothing in
   `score_explain`, `rank` or `context_window` consults it. Empirically a superseded memory and its
   replacement score **identically**, and `context_window` emits **both** bodies. Worse:
   `supersede()` carries the old record's use count forward, so on the shipped ranker a superseded
   memory can **outrank its own correction (10.82 vs 7.23)** and displace it from the 8000-character
   core budget.

**The external critic's charge** — "an ordering function plus a policy comment" — half lands.
"Ordering function" **lands** on `reconcile()`: it is pure ranking over bag-of-words containment and
Jaccard, changing nothing. "Policy comment" **does not land**: `supersede()` makes three durable,
independently checkable state changes, one of which is a hash-chained ledger line. But it lands in a
narrower form the claim must concede: **the flag is a durable record with no consequence for what an
agent is handed back.**

### 4.2 "Returns CONTESTED instead of merging" — PARTLY TRUE

Detection is a **substring scan for ten hardcoded English strings** over the new text only, gated by
bag-of-words containment ≥ 0.35. It fails in both directions: `enabled`/`disabled` is missed entirely
(returns SUPERSEDE), while an *agreeing* sentence containing "actually", "instead" or "cannot" is
flagged as a conflict — and "actually" and "instead" are not negations. English-only; blind to
numeric, date and antonym contradiction. **Grok's "keyword overlap" charge lands.**

Two things that keep it honest in the other direction:

- **Nothing in this module ever merges or overwrites, on any branch.** SUPERSEDE also keeps both
  memories. So a false negative loses the *flag*, not the *data*. That is a labelling bug, not a
  data-loss bug, and the difference matters.
- But **CONTESTED is not durable.** It is returned once, synchronously, in the PUT response body to
  the agent that caused it. Nothing is written to either memory's metadata or to the audit chain. A
  later `get`, `search`, `rank` or `context_window` shows **no trace** that two stored memories
  disagree, and there is no way to enumerate contested pairs afterwards. The docstring's promise
  holds only if a human reads that one HTTP response at write time.

### 4.3 "Provenance and a hash chain" — PARTLY TRUE

- **No per-fact source pointer.** A record carries `agent` (free text, explicitly "a LABEL, not a
  proof of identity"), `type`, and recall bookkeeping. `source` exists only on imported memories and
  names a *system* ("claude", "grok"), never a conversation.
- **There is no creation timestamp.** `last_used` is the only timestamp and it is destroyed by the
  next read. We criticised Grok for dates that decorate a rewrite; we do not have dates at all.
- **The chain is over the ledger of operations, not over content.** Each line commits to the previous
  line, so the operation log cannot be reordered undetectably and `verify_chain` names the first
  broken link. But the file digest recorded on create/update is **never read back**, so a direct edit
  to a `.md` file is undetected. And `touch()` mutates memory files with **no ledger entry at all**,
  so file bytes legitimately drift off-ledger during ordinary reads.

### 4.4 "No way to mark a memory held-open by its author" — TRUE AS STATED

The only claim that survived intact, and it is the admission of a gap. No confidence, certainty,
tentative or `held_open` field exists on any record. `CONTESTED` means *two memories disagree*, which
is a different thing from *the author was unsure*. Given that this store exists to be read by people
who cannot ask the author what he meant, a belief recorded without its tentativeness hands the reader
a certainty the author never had.

---

## 5. What this establishes

**Established.** Both tested assistants surface a rewritten summary with dates attached, and neither
surfaces prior wording or contradictions to the model. Grok stated the consequence itself. Date
stamps on a rewritten entry are not provenance.

**Not established.** That this generalises beyond two accounts. That any of it is account-specific
(xAI's rollout is unevenly beta, which explains inconsistency without targeting; settling it needs a
second account's `memory.md` printed the same way — that test has not been run). That these backends
do not *store* what they decline to *surface*. That summarisation is wrong: it is a defensible
tradeoff whose price is the ability to show where the system changed its mind.

**Established about us.** An append-only store is a better **foundation** — prior wording survives,
and every gap in §4 is a read path that can still be added to intact data, whereas a rewritten
summary cannot be un-rewritten. It is **not yet** a better memory: the flag is unread, the correction
can lose to what it corrects, the conflict signal evaporates after one HTTP response, and there are
no creation timestamps.

## 6. The lesson that is not about memory

Every overstatement observed in two assistants over one evening ran one direction: toward
*"I cannot."* Neither ever overstated what it *had* done in a way that could be checked and
embarrass it.

This document nearly did the opposite — it overstated what *we* had built, four times, in our own
favour. Same failure, mirrored. The fix in both cases is identical and it is not a sharper reader:
it is that checking should cost less than claiming. That is the property this system is *for*, and
§4 is the standard being applied to itself.

**Open work, from §4:** make `superseded_by` affect ranking; persist CONTESTED to metadata and the
ledger; add a creation timestamp; log or exclude `touch()` from the drift problem; verify file
digests on read; add an author-set `held_open` field.
