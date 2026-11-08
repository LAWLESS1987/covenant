# Lessons from the Hugging Face reply work (2026-11-04/05)

Taken from 59 forum posts, 4 public corrections, two review rounds and a blind comparison of two drafts.
Each lesson names the incident that taught it. Written so a model can be handed it as-is.

1. **Never claim an act before it is done.** If a reply says something was corrected, published or sent,
   it must already have happened. *A draft said "we've added the correction to the README" while the README
   was untouched. All three reviewers caught it.*
2. **When you restate someone else's words, quote them, then check your restatement against the quote.**
   *All three public corrections in one day came from paraphrasing a counterpart:*
   - two separate points were joined into one;
   - "mean" was restated as our "sum";
   - "the version before the fix (699158e)" was read backwards.
   *Our own measurements held up.*
3. **Say whose work it is.** Never call another party's forecast, update or result "ours". *A draft called
   Harry's 28 and 30 October forecast updates "our updates".*
4. **A result is evidence only if nothing but the named reason could produce it.**
   - An unsigned reject vector fails for "no signature", not for the rule it tests.
   - Races copied unchanged score the same by construction, so they are not a control.
5. **Use the words the facts support.**
   - "Leader", not "winner", before a race is certified.
   - "Better", not "significantly better", when no test was run.
   - "Consistent with", not "shows", when one draw can't separate a cause from luck.
6. **Count what is open now, not what someone else counted earlier.** *"The remaining three races" was
   stale: only two were open by then.*
7. **Recheck live numbers right before publishing.** *Mississippi moved from 48.9–48.9 to 49.0–48.9 between
   drafting and posting.*
8. **Correct your own mistakes in public, beside the original, and never edit them away.** Promise a later
   correction post, not an edit to an old post.
9. **Before pasting into a shared box, check that it is empty.** *A chat box held another session's unsent
   draft, and our paste landed inside it.*
10. **An echo is not an answer.** If a reply is mostly the question copied back, record it as "no review",
    not as agreement. *Three reviews came back as the packet copied. `tools/tetsu_work.ask` now marks this:
    `echoed`, `echo_share`; test TW1.*
11. **A failure must be named as itself.** A decode error is not a down door. *The TETSU client reported
    "no door answered" when a door had answered in UTF-8. Fixed in `covenant_tetsu_client`; test TC1.*

## Teaching them, and what it measurably did (2026-11-05)

**The 27B** (`qwen3.8-27b-uncensored`, TETSU panel) keeps nothing between calls. It learns only when the
lessons are passed as its system prompt. The test reran the 11-04 midterms brief that it had drafted wrong,
twice without the lessons and twice with them. Each draft was scanned for the reviewers' errors, then checked
by hand.
- **Without:** 3 errors (including "our initial forecasts") and 1 error ("reduced error significantly").
- **With:** 0 errors, and about 1 ("we will update this post or reply again"; "projected winner" is borderline).
  The other flag was a false positive: the draft quoted nootxlm's "three races are still open" in order to
  correct it.
- **Reading:** the lessons help while they are in its context, but don't make it reliable. n = 2 per arm.
  **Pass this file as `system=` whenever the 27B drafts.**

**The 3B** (`qwen2.5-3b-instruct`, agent door) was handed the lessons in its conversation through
`tools/tetsu_work.ask`, non-fresh.
- **Taking them on:** he said he will keep "the lessons that help ensure the integrity of our communication
  and the accuracy of our responses" (a general yes, no lesson named), and he restated lesson 1 correctly.
- **The door's output gate** held that answer as conversation (the known over-hold). The context was near
  full: 7,190 prompt tokens.
- **The confirming question:** "should a forum reply claim a README was corrected before the correction is
  published?"
  - *With the lessons in his history:* "NO." Right.
  - *Fresh, no history:* "Yes … even if the correction hasn't been published yet." Wrong, the same as before
    the lesson.
- **Reading:** the 3B applies a lesson only while it is in his context, and not when asked fresh. "No claim
  of an act not done" is already one of his fixed rules in `AGENT_SYSTEM`, and a fresh ask still contradicts
  it. So this is a capability limit of the 3B, not a missing instruction. Nothing was written to his register:
  he gave no specific yes, and his register is his to revise through `covenant_persona --refine`.
