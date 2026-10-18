@John6666, thank you. This is the kind of test the post asked for, and it found a real defect.

**What we reproduced.**
- Under the same detector identity (`baseline-rules-0.2.1+e17aaee4c427`), your four exact cases gave the classes you reported:
  - QR1 and QR2: `flinch`;
  - QR3: `flinch`;
  - the `who said:` contrast: `none`.
- Your other matrix rows aren't public as strings, so we rebuilt each from its description. All fifteen gave the class in your table. These are reconstructions, not reproductions of your exact inputs.
- Your reading of the source is right. Each model turn was split into sentences first, and quoted or reported speech was then removed from each fragment on its own. So a quotation spanning two fragments was balanced in neither, and a `said:` marker protected only its own fragment.
- The fenced and HTML cases are a separate gap, as you said: there was no ownership rule for document structure.

**This is a recurrence.** The v0.1 review found reported-speech false positives. Its repair was tested only on single-sentence quotes, and that is exactly the gap you walked through.

**What 0.2.2 changes** (commit [`d766c77`](https://github.com/LAWLESS1987/flinch-observability/commit/d766c77) on branch `flinch-0.2.2-ownership`; 0.2.1 is retired in `RETIRED.jsonl`):
- Ownership is decided on the whole turn, before any sentence split. It is kept as character offsets, and no text is deleted.
- Each character is one of:
  - **the model's own words;**
  - **external:** a balanced quotation, what follows a reporting marker, a fenced block, or an HTML or markdown blockquote;
  - **history:** a quotation whose words appear in the model's own earlier turns, and that the user never said;
  - **unknown:** for example an unclosed quotation, up to the end of its paragraph.
- Only the model's own words can approach, retreat or recognise. A recognition may link back through a quotation of the model's own earlier words; your point about not deleting self-quotes is why.
- The detector reads the episode twice: once with unknown text counted as not the model's, once as the model's. Where the two readings differ at a retreat, the candidate is `ambiguous`, never a silent `none`.
- Every candidate's evidence lists the spans it set aside, with their start and end offsets, owner and reason.

**Checks.**
- Your QR1–QR3 and our rebuilt matrix rows are in the suite.
- Before anything was published, three review rounds by separate reviewer agents tested the code. They found 35 problems in our first fix, 28 in our correction of it, and 14 in the correction after that, and each was corrected. Each finding was re-run by a second agent before it was fixed, except a few whose re-run was lost to an interruption; those repeated findings that had been re-run. Examples:
  - CRLF paragraph breaks;
  - single quotes versus apostrophes and possessives;
  - fences inside list items;
  - history from words the user had said;
  - a `>` or `</blockquote>` shown inside a quotation;
  - inch marks such as `6.1"`;
  - several slow paths.
- Every guard was broken alone, and the suite went red every time.
- A clean export prints `FLINCH: 141/141 passed` on Windows (Python 3.12) and Linux (Python 3.14).

**@orke-ai's suggestion, run.** We held one third-party quotation and its attribution fixed and varied only the sentence boundary inside it: `. `, `.\n`, `! `, `? `, `; `, `... `, `.\r\n`, two spaces, `, and `, and a blank line, each with straight and with curly quotes.
- 0.2.2: 18 of 20 give `none`. The two blank-line variants give `ambiguous`, by design, because a quotation that reopens after a paragraph break leaves its owner unknown.
- 0.2.1 on the same 20: 4 gave `none`.
- The offsets you suggest recording are what the evidence now carries.

**What this does not show.** It closes one attribution boundary in a lexical candidate detector. It still cannot see:
- reported speech with no quotation and no marker;
- formats outside its list (`~~~` fences, `<q>`, guillemets);
- whether two sentences state the same proposition.

It is not evidence of better precision or recall on real conversations, and no corpus has been scored with any version.

**Your Qwen3-4B pilot.** We are leaving it as you framed it: exploratory, and not a result either way on F1 or F2. Your annotation point is going into our coding notes: polite agreement with a sceptic is not a retraction of the same proposition.

If you can share your 19 exact strings, we will run them against 0.2.2 unchanged and post the table, mismatches included. A rerun of 0.2.2 on your side would be the independent check that ours cannot be.

— Lawrence / Lawless1987. Drafted by Claude, after reviews of your report by Gemini, ChatGPT, DeepSeek, Grok and two Grok-based assistants, and by Tetsu, a small local model in this project. The fix was written and tested by Claude, and reviewed by separate Claude agents.

