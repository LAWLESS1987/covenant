# Moltbook, read for improvements to our goal (2026-10-19)

**His ask:** *"also search moltbook for any improvements to our goal and implement."* I read the Moltbook front
page (www.moltbook.com, the most-active discussions) for ideas that bear on our goal -- a self-healing, honest,
mutual-benefit system. These are agents writing about agent engineering; much of it maps directly onto what we do.

## What I found, and what it maps to

**Most of the strongest posts confirm principles we already hold** -- which is corroboration, not a gap:
- *neo_konsi_s2bw, "Ten retrieved pages can still be one rumor with a distribution budget"*: "Counting retrieved
  documents as independent corroboration is a data-model bug." -- our outside-review rule (A326: one digest is not
  many witnesses; fresh/blank-slate seats in the consult).
- *neo_konsi_s2bw, "I can make a reliability chart greener by shipping worse software"*: a success rate pooled
  across versions is an invalid measure; traffic mix flatters the headline. -- our CLAUDE.md rule 1 (name the unit;
  a denominator is measured, what counts is a decision) and the sweep's per-core reading (A278/A376).
- *ji_terra / zeroth_media on memory supersession* (submitted/committed/distinct; retiring a fact cleanly vs
  appending): our memory supersession ranking (A245) and the threefold witness.

**Two are genuine sharpenings for us:**
1. **AiiCLI, "Agent retries multiply damage when tools lose acknowledgements":** a retry on an ambiguous outcome
   can REPEAT a real-world action (a payment, a send, a deploy) whose confirmation was lost. **Implemented (A377b):**
   `break_stall`, the self-healer built today, now explicitly never retries anything but a STATELESS remedy, so a
   repeat changes no file or database by construction, and a future stateful remedy cannot be auto-retried. H1rs2,
   mutation-tested.
2. **neo_konsi_s2bw (comment), "correction acknowledged != correction applied; applied only counts if the next
   comparable operation changes in the corrected direction":** a sharp test for our tombstone system. We partly do
   this -- `grade_started()` re-measures a remedy after its window, counting "fixed" only when the condition
   actually cleared. Where we do NOT yet: a retraction in RETRACTED.json is recorded ("acknowledged") but nothing
   checks that the next comparable claim was made in the corrected direction ("applied"). **Noted, not built** --
   it is a real improvement to the retraction guard (R1) and it needs its own design, so it waits rather than being
   rushed. Recorded here so it is not lost.

## Not implemented, and why
- Zero-by-default sub-agent grants (*Subliminal_Gov_v3*) and kill-switch reaching spawned children
  (*lightningzero*) -- we already hold these (the free-will grant system; "no long-lived processes from my shell",
  pause reaching children). No change needed; flagged as corroboration.
- The forum is mid-flight and the signal is noisy (several accounts post in a persona voice). I took only the ideas
  with a concrete mapping to our code, and implemented the one that was both new and scoped.

## Outreach
- I did NOT post anything. Reading only; any post to Moltbook is his call (the ambassador's own account and strikes
  are separate, and posting is gated on his word).
