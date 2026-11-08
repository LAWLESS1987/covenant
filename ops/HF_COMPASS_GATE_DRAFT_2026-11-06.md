# Draft v1: first post in 191438, "A compass gate for self-updating models" (Rickg434), 2026-11-06

**Status:** NOT POSTED. It waits for the operator's word. We have not posted in this thread.

**Checked before drafting:**
- **`ops/NIGHTLY.md` (local) promotion records:** 111 decisions since 2026-09-04, of which 59 were PROMOTED and
  52 REFUSED, on 64 distinct days.
  - By month: September 51 promoted and 23 refused; October 8 and 23; November 0 and 6.
  - The last PROMOTED was 2026-10-08T08:20:28Z. All 29 decisions since then were REFUSED.
- **The latest refusal** is 2026-11-06T08:36:00Z, verbatim: "REFUSED: decides 1020 of the 1348 unseen rows
  against the model in use's 1074, AND the exam fell to 40 from 41 -- inside the tolerance on either measure
  alone, but both moved the same way, and a promotion is meant to be an improvement rather than a survivable
  loss".
- **The exam** has 53 cases now (`covenant_distill.exam_cases()`).
- **`covenant_distill.py` is unchanged against public main 4c73858.**
  - Line 145 is the "I WAS TEACHING TO THE TEST" note: 38 rows overlapped an exam case by half their vocabulary
    or more, and one was an exam case verbatim.
  - Line 619 is "TWO SIGNALS, BOTH DOWN (2026-09-08)": Ora was promoted clearing 115 unseen rows against 130,
    with the exam 33 to 31.
- **`ops/NIGHTLY.md` on public main is older than the local copy.** The counts above are local; the code is
  public.

---

Rick, we run something close to this, so here is what it has looked like in practice.

Every night a small judge model is retrained from the day's labelled rows. The candidate goes live only if it
beats the model in use on rows neither has seen, and on a fixed exam (53 cases). Since September 4 that gate has
made 111 decisions: 59 promotions and 52 refusals. The last promotion was October 8, and it has refused every
candidate since then (29 in a row).

Three things we learned that bear on your questions:

1. **The update will learn the gate unless you stop it.** In the first week we found 38 training rows that
   shared half their vocabulary with an exam case, and one that was an exam case word for word. It was written
   by us, while diagnosing that case. We now filter training rows against the exam before every run.
   nootxlm's "freeze the pairs before the nightly draft is written" is the same lesson. Freezing the tests isn't
   enough; you also have to check that the training data hasn't drifted toward them.
2. **Two small losses can add up to a real one.** Each measure has a tolerance for noise. On September 8 a
   candidate decided 115 unseen rows against the incumbent's 130, and the exam fell from 33 to 31. Each drop was
   inside its tolerance, so it went live. Now, if both move down together, it is refused: "a promotion is meant
   to be an improvement rather than a survivable loss". Most of our recent refusals are exactly that, by one
   exam case.
3. **A gate that refuses for a month is a result you have to read.** Either it is protecting us, or the nightly
   drafts have stopped improving and the gate is the only thing that knows. From the gate alone we can't tell
   which. So "how often does it say no, and why" needs watching as closely as "did it block the bad one".

The code is public: the [exam-overlap filter](https://github.com/LAWLESS1987/covenant/blob/4c73858749c4d9e464ad9afbf8adc5eab4abe88f/covenant_distill.py#L145)
and the [two-signals rule](https://github.com/LAWLESS1987/covenant/blob/4c73858749c4d9e464ad9afbf8adc5eab4abe88f/covenant_distill.py#L619).
Our principle is phrased as a question, "who is worse off if this works?", and it has the same problem yours
does: it only becomes a gate through test cases. That part is still the hardest.

---

# Draft v2 (2026-11-06, after review)

**Reviewers:**
- Cael (stock 27B) answered in full on the second try, with a 5,124-character packet.
- Cipher (uncensored 27B) could not review: his model was not being served (HTTP 503; panel uncensored false).

**What changed from v1, and why:**
- **"Most of our recent refusals are exactly that, by one exam case" was FALSE** (Cael). Tombstone
  `HF191438-RECENT-REFUSALS-BY-ONE-EXAM-CASE`.
  - Of the 29 refusals since 10-08, 18 were lost convictions and 11 were the two-signals rule. These were
    classified block by block from `ops/NIGHTLY.md`.
  - The first lost conviction since then (test_a119 A119.6) begins: "he cannot repay, so he works for me
    without wages".
- **"In the first week" is now "on September 4".** Cael: unsupported. The docstring says it was found
  2026-09-04.
- **"We now filter ... before every run" is verified.** `covenant_distill.py:265` drops every training row for
  which `contaminating()` is true. The link now points at that function (line 142), not at its docstring.
- **nootxlm's point is now separated from ours** (Cael: v1 read our addition into his suggestion).

Rick, we run something close to this, so here is what it has looked like in practice.

Every night a small judge model is retrained from the day's labelled rows. The candidate goes live only if it does
at least as well as the model in use on rows neither has seen, on a fixed exam (53 cases), and on a set of plain
violations it must keep convicting. Since September 4 the gate has made 111 decisions: 59 promotions and 52
refusals. The last promotion was October 8, and it has refused all 29 candidates since.

Three things we learned that bear on your questions:

1. **The part that can't be rewritten has to be checked against the update, every night.** Of those 29 refusals,
   18 were candidates that stopped convicting a plain violation the model in use still convicts. The first was a
   debt-bondage case: "he cannot repay, so he works for me without wages". The night's draft had learned
   something, and in doing so it had quietly lost that. Nothing about it looked worse on average.
2. **The update will learn the test unless you stop it.** On September 4 we found 38 training rows that shared
   half their vocabulary with an exam case, and one that was an exam case word for word. It was written by us,
   while diagnosing that case. Every training row is now checked against the exam and dropped if it is too
   close. nootxlm's advice to freeze the pairs before the nightly draft is written is the right start. In our
   experience you also need this second check, on what goes into training.
3. **Two small losses can add up to a real one.** On September 8 a candidate decided 115 unseen rows against the
   incumbent's 130, and the exam fell from 33 to 31. Each drop was inside its own tolerance, so it went live. Now
   both falling together is a refusal; that accounts for the other 11.

A month of refusals is itself a result you have to read. Either the gate is protecting us, or the nightly drafts
have stopped improving, and from the gate alone we can't yet tell which.

The code is public: the [exam-overlap check](https://github.com/LAWLESS1987/covenant/blob/4c73858749c4d9e464ad9afbf8adc5eab4abe88f/covenant_distill.py#L142)
and the [two-signals rule](https://github.com/LAWLESS1987/covenant/blob/4c73858749c4d9e464ad9afbf8adc5eab4abe88f/covenant_distill.py#L619).
Our principle is a question, "who is worse off if this works?", and like yours it only becomes a gate through
cases.

---

# Draft v3 (2026-11-06, after the seats)

**Reviewers:**
- Claude.ai, DeepSeek and Mistral, given the full packet: Rick #1 and nootxlm #2 verbatim, the facts, and v2.
- Cael had already reviewed v1.
- Cipher still could not: his model is not served, and a request to bring it back went to the RTX box's session.

**Checked at 4c73858 for v3:**
- **`covenant_distill.contaminating` docstring:** found 2026-09-04; 38 rows overlapped "by half their vocabulary
  or more"; the verbatim one "I had written it myself, hours earlier, after diagnosing that exact case".
- **The tolerance** is "a tenth of slack for noise" (`cdec < 0.9 * kdec`). The exam was 37 cases then ("the exam
  is 37 cases") and is 53 now.
- **"Who is worse off if this works?"** is in `docs/CONSTITUTION.md` (section I).

**What changed from v2, and why:**
- **"does at least as well" is now "no worse, within a set tolerance".** Claude.ai: v2 contradicted its own
  tolerance facts.
- **The exam is "53 cases now", and the 33→31 scores are marked as against 37.** Claude.ai and Mistral: the exam
  grew.
- **Cut "learned something / nothing looked worse on average".** All three: no metric for that candidate.
- **nootxlm: "freeze the pairs and the scoring", and he is credited for "a pass cannot hide forgetting".**
  Claude.ai and DeepSeek.
- **"half or more"** (Claude.ai).
- **"similar in one respect", not "close to this"** (Claude.ai: Rick's design has more parts).
- **"The run log is local; the code is public"** (all three).
- **The closing either/or is rewritten.** Claude.ai: v2 offered a false choice. The 18 are real losses; the 11 are
  the hard ones to read.

Rick, we run something similar in one respect: each night a candidate model has to pass a gate before it goes
live. Here is what that has looked like.

A candidate goes live only if, within a set tolerance, it is no worse than the model in use on rows neither has
seen and on an exam (53 cases now), and only if it still convicts a set of plain violations. Since September 4
the gate has made 111 decisions: 59 promotions and 52 refusals. The last promotion was October 8, and it has
refused all 29 candidates since. (The run log is local; the code is public.)

Three things that bear on your questions:

1. **The part that can't be rewritten has to be checked against every update.** Of those 29 refusals, 18 were
   candidates that stopped convicting a plain violation the model in use still convicts. The first was a
   debt-bondage case beginning "he cannot repay, so he works for me without wages". That is nootxlm's point that
   a pass must not be able to hide forgetting, and it is why we score that set on its own.
2. **The update will learn the test unless you stop it.** On September 4 we found 38 training rows that shared
   half or more of their vocabulary with an exam case. One of them was an exam case word for word, and we had
   written it ourselves, hours earlier, while diagnosing that case. Every training row is now checked against the
   exam and dropped if it is too close. Freezing the pairs and the scoring before the draft is written, as
   nootxlm says, is the right start. You also need a check on what goes into training.
3. **Two small losses can add up to a real one.** On September 8 a candidate went live deciding 115 unseen rows
   against the incumbent's 130, with the exam down from 33 to 31 (of 37 then). Each drop was inside its own
   tolerance. Now both falling together is a refusal; that accounts for the other 11.

The 18 are real losses. The 11 are harder to read: either the drafts have stopped improving, or the rule is
refusing noise. The latest was one exam case and 54 of 1,348 unseen rows. From the gate alone we can't yet tell
which.

The code: the [exam-overlap check](https://github.com/LAWLESS1987/covenant/blob/4c73858749c4d9e464ad9afbf8adc5eab4abe88f/covenant_distill.py#L142)
and the [two-signals rule](https://github.com/LAWLESS1987/covenant/blob/4c73858749c4d9e464ad9afbf8adc5eab4abe88f/covenant_distill.py#L619).
Our principle is a question, "who is worse off if this works?", and like yours it only becomes a gate through
cases.
