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

---

# Draft v2 (2026-11-06, after review)

The same reviewers as the Branden v2. These facts were checked at 4c73858 after the review:
- **The A98 docstring** (`validate_block`, from line 2915) says the student's words were "6 content word(s)
  here were never seen in training [...] It has made NO finding and is NOT alleging anything." It also says
  "One non-finding vetoed two clears."
- **"WHAT `sync` CHANGES"** is at line 2932: a refusal that alleges nothing stops vetoing a block the node is
  fetching to catch up, and a genuine dissent still refuses.

**What changed from v1, and why:**
- **The colon that read as "the quote is the six words" is fixed.** Claude.ai and Mistral. The six were
  different words, and the quote is the model's own output.
- **The route-to-a-bigger-model point is now ours, not his.** Claude.ai, DeepSeek and Mistral: his
  underspecified result supports only the ask-back half.
- **The echo check is now said to be local and not yet public.** All reviewers.
- **The third overlap is now "not computed".** All reviewers.
- **The link is a permalink** at 4c73858 with a line anchor.
- **About a third shorter.**

LuzCommand, your split of "said IDK" from "ran out of tokens" matches something we ran into. Two notes from our
side.

**1. A third non-answer: the echo.** Given long structured input, our small model (a 3B) sometimes returns
the input copied back. That isn't an IDK and it isn't truncation, but accuracy scores it as wrong and
abstention scoring counts it as a commit. Three review requests came back that way. The two we measured had
8-gram overlaps with the prompt of 1.000 and 0.985. We now flag anything at 0.5 or above as "echoed" and don't
count it as an answer. That check is local; it isn't in our public repo yet.

**2. An abstention should carry its reason.** Our gate keeps its two non-commits, "Held, not judged" and
"Blocked, not proven", separate from an actual finding. Before that difference decided anything, a node catching up on our chain stalled
at height 2 while its peer was at 17. Our small model held an old transaction because six of its words were
never in training. It said so itself ("It has made NO finding and is NOT alleging anything"), and that one
non-finding vetoed two clean verdicts. Now a hold that alleges nothing no longer blocks catch-up, and a real
objection still does.

Your underspecified result looks like the same shape. An IDK that should have been a question back is a
different signal from an IDK that's right. If this ends up in the cascade you described, we'd guess "ask back"
and "pass up" want to be separate outputs.

Code for the second note: [validate_block, A98](https://github.com/LAWLESS1987/covenant/blob/4c73858749c4d9e464ad9afbf8adc5eab4abe88f/covenant_unified_v8.py#L2915).
These are offline observations from a small project, not a benchmark.
