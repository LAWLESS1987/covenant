# Standing method for this repository

Written 2026-09-17 on the operator's instruction: *"this must be used in every
applicable situation from the beginning."* It is here, rather than in a document
somebody has to remember to open, because this file loads at the start of every
session.

It exists because the same error was made four times in two days, each time
inside the correction for the previous one.

---

## 1. Find the data. Prose about data is not data.

Before counting, measuring or verifying anything, ask **which artifact is the
measurement** and which is a description of it.

- A markdown file is a description. `private/*/catalog.csv` is data.
- `docs/KNOWN_ISSUES.md` describes a defect. The code is the defect.
- `/health` is a report. The process is the thing.

*2026-09-16:* a media index was cross-checked against itself, found internally
consistent, and reported as accurate. It was superseded, its "new" finding was
eight days old, and the catalogues sat unread the whole time. **Internal
consistency is not accuracy.**

## 2. Enumerate by discovery, never by recall.

Walk the directory. Filter by **content** — does the header carry the column? —
never by a filename list and never by a name pattern.

A hardcoded list cannot find the file added after the list was written, which is
precisely the file a recount exists to catch. *2026-09-17:* a tool written to
fix rule 1 hardcoded five catalogue paths and missed a sixth.

## 3. Count in two ways that can disagree.

One route is a guess with a number attached. Rows in a catalogue and artifacts
on disk are independent; which one is short tells you whether the gap is in the
reading or in the record. Three patterns agreeing is evidence; one pattern is
not.

## 4. Say what unit you are counting.

FILES and POSTS are different. UPLOAD EVENTS, GRID IDS and RELEVANT items are
three different denominators. Most wrong numbers here were right numbers of the
wrong thing:

- "117 files" vs "108 posts" — nine multi-file posts.
- "114 of 114 read" — 114 files against 114 posts.
- "26 of 90 Facebook" — transcribed reels against *upload events including
  personal video*. My error, 2026-09-17.

## 5. A denominator can be measured. What COUNTS cannot.

Three automated passes produced 90, 69 and 47 for Facebook and no way to choose.
One sentence from the operator — *"47 relevant"* — settled it. Scope is his
call, not a measurement. When a number depends on relevance, **ask**; do not
compute and present the result as settled.

## 6. Before narrowing access, grep every consumer of the capability.

Not the call sites of the fix — the call sites of the thing being narrowed.
*2026-09-16:* closing A21 killed the teacher and the phone-build path. `token()`
had four callers; reasoning found two. `grep -rn "\.token()"` found all of them
in one call.

The dangerous shape is a tightening that returns empty rather than raising,
because callers read empty as "not available today" and carry on silently.

## 7. Cite only what you have opened.

A grep hit is a pointer, never a citation. `grep -o` strips the filename, so
text that looks like `path:N:` inside a match is content, not provenance. A
truncated match is not a fact — open the file rather than completing it.

A `Stop` hook (`.claude/hooks/verify_citations.py`) enforces this on `file:line`
claims. It cannot enforce the rest; that is what this file is for.

## 8. Break it to prove the green is earned.

A check that has only ever passed has never been observed. Drive every guard
both ways, and never move a check to make it pass. *A65:* 35 of 36 suspected
guards were fake because they grepped source text instead of running the code.

## 9. Report what was measured, and name what was not.

`UNDETERMINED` is a real answer. A tool that resolves everything is lying about
the part that needs a running node, a second machine, or a decision.

---

**Re-runnable, not remembered:** `python tools/corpus_reconcile.py`,
`python tools/audit_a1_a46_status.py`, `python covenant_one.py`.
