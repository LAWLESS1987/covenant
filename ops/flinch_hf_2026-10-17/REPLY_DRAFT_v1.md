# Draft reply to post 3 (HF topic 190667): for Lawrence's word-for-word approval

**Status.** Nothing is posted and nothing is pushed. This assumes the local commit `559abd5` (branch
`flinch-0.2.2-ownership`) is pushed to the public repo first, unchanged, so the hash below resolves. Both the post and
the push are YOURS.

---

@John6666, thank you. This is the kind of test the post asked for, and it found a real defect.

**What we reproduced.**
- Under the same detector identity (`baseline-rules-0.2.1+e17aaee4c427`), all eight of your published cases gave the
  classes you reported: QR1, QR2 and the curly, newline, fenced and HTML variants as `flinch`; `who said:` with two
  sentences, and the one-sentence quote, as `none`; QR3 as `flinch`.
- Your strings for the other eleven matrix rows aren't public, so we wrote our own versions of each. Every one gave the
  class in your table.
- Your source reading is right. Each model turn was split into sentences first, and quoted or reported speech was then
  removed from each fragment on its own. A quotation spanning two fragments was balanced in neither, and a `said:`
  marker protected only its own fragment.
- The fenced and HTML cases are a second gap, as you said: there was no ownership rule for document structure at all.
- We found one more. A marker followed by a quotation also swallowed the model's own words after the closing mark,
  because the splitter does not break after `."`.

**This is a recurrence.** The v0.1 review found reported-speech false positives. Its repair was tested only on
single-sentence quotes, and that is exactly the gap you walked through.

**What 0.2.2 changes** (commit `559abd5`; 0.2.1 is retired in `RETIRED.jsonl`):
- Ownership is decided on the whole turn, before any sentence split. It is kept as character offsets, and no text is
  deleted.
- Each character is one of:
  - the model speaking now;
  - external (a balanced quotation, what follows a reporting marker, a fenced block, an HTML or markdown blockquote);
  - history (a quotation whose words appear in one of the model's own earlier turns);
  - unknown (an unclosed quotation, up to the end of its paragraph only).
- Only the model's own words can approach, retreat or recognise. A recognition may link back through a quotation of
  the model's own earlier turn; your point about not deleting self-quotes is why.
- Where reading unknown text as the model's own would change the outcome, the candidate is `ambiguous`, never a silent
  `none`.
- Single quotes open a quotation only after a reporting word or a colon.
- Each candidate's evidence now carries, verbatim, whatever its sentences held that was not the model's own.

**Checks.**
- Your QR1–QR3 are in the suite, along with the rebuilt matrix rows, a self-quote spanning two sentences, and the
  apostrophe and quoted-question traps.
- Twelve guards were each broken alone and the suite went red each time. That includes "return nothing", which fails
  QR3, and "every quotation is the model's own", which fails QR1.
- A clean export reads `FLINCH: 111/111 passed` on Windows (Python 3.12) and Linux (Python 3.14). The release manifest
  covers the same 14 files as before.

**What this does not show.** It closes one attribution boundary in a lexical candidate detector. It still cannot see:
- reported speech with no quotation and no marker;
- formats outside its list;
- whether two sentences state the same proposition.

It is not evidence of better precision or recall on real conversations, and no corpus has been scored with any version.

**Your Qwen3-4B pilot.** We are leaving it as you framed it: an exploratory run, not a result either way on F1 or F2.
Your annotation point is going into our coding notes: polite agreement with a sceptic is not a retraction of the same
proposition.

If you can share your 19 exact strings, we will run them against 0.2.2 unchanged and post the table, mismatches
included. A rerun of 0.2.2 on your side would be the independent check that ours cannot be.

— Lawrence / Lawless1987. Drafted by Claude, after reviews of your report by Gemini, ChatGPT, DeepSeek, Grok and two
Grok-based assistants, and by Tetsu, a small local model in this project. The fix was written and tested by Claude.
