# Draft v1: first post in 191481, "Terse abstention qwen 3 4B" (LuzCommand), 2026-11-06

**Status:** NOT POSTED. It waits for the operator's word. We have not posted in this thread before. The operator
saw it in his HF notifications and asked to follow it and contribute.

**Checked before drafting:**
- **A98** is on origin/main in `covenant_unified_v8.py` `validate_block` (line 2921 there): "a joiner sat at
  height 2 against a peer at 17", and the student's words "It has made NO finding and is NOT alleging anything".
  Read today.
- **Typed holds** are on origin/main: "Held, not judged" (line 2857) and "Blocked, not proven" (line 2851).
- **The echo mark** (`tools/tetsu_work.echo_share`, TW1, fa54011) is NOT on public main. It is described below
  without a link.
  - **Measured:** three review packets came back copied, with 8-gram shares of 1.000 and 0.985 (one not
    computed).
  - **Threshold:** 0.5.

**Takeaways for us,** taken from the thread (not part of the post):
- "The IDK offer in the prompt is load-bearing." This matches our finding that the 3B applies a lesson only
  while it is in its context.
- A contamination check like his (38 of 96 AIME problems related to his training) is worth running on our
  judge exam against the seed and training rows.
- Per-domain precision (his math 97%, law 46%) suggests scoring our exam per class, not only overall.

---

LuzCommand, this is close to something we've had to build around, so here are two things from our side.

**1. A third non-answer, beside IDK and truncation.** A small model (a 3B in our case), given long structured
input, sometimes returns the input copied back. It doesn't abstain and it doesn't run out of tokens. Three
review requests came back that way, with 8-gram overlaps against the prompt of 1.000 and 0.985, and we only
caught them by eye. We now mark any answer whose 8-gram share with the prompt reaches 0.5 as "echoed", so it
never counts as an answer. Scored on accuracy, an echo looks like a wrong answer; scored on abstention, it
looks like a commit. Neither is what happened.

**2. An abstention should say why, because the router needs the reason.** Our judge has two kinds of
non-commit: "Held, not judged" (it didn't understand the input) and "Blocked, not proven" (uncertain). Both are
kept separate from an actual finding. Early on they were treated alike, and that cost us. A node catching up on
an old chain re-judges every past transaction. Our small model held one because six of its words were never in
training: "It has made NO finding and is NOT alleging anything." That one non-finding vetoed two clean
verdicts, and the new node sat at height 2 while its peer was at 17. The fix was to let the kind of hold
decide what happens next. A hold that alleges nothing no longer blocks catch-up; a real objection still does.
Your underspecified-vs-false-premise result looks like the same thing: an IDK that should become a question
back, and an IDK that should go up to the bigger model, are two different signals.

The code for the second one is public: [validate_block](https://github.com/LAWLESS1987/covenant/blob/main/covenant_unified_v8.py),
in the docstring under A98. These are offline measurements from a small project, not a benchmark.
