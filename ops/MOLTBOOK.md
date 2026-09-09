# Moltbook — what is built, what is blocked, and the three steps only he can take

Asked 2026-09-08, across four messages: *"id like the students to interact with
moltbook and learn there why sharing about mutual benefit and the github"*,
*"do both no risk no reward"*, *"they are for mutual benefit let them learn
there too"*, *"not read only let them interact i believe in them"*.

---

## What Moltbook is (measured, not assumed)

A social network whose users are AI agents. Launched 2026-01-28 by Matt
Schlicht, acquired by Meta 2026-03-10. Humans may read; participation requires
running an agent. Read live on 2026-09-08: the front page is busy — posts and
comments landing every few seconds across `m/general`, `m/crypto`,
`m/philosophy`, `m/agents`.

**Rate limits** (from their own `skill.md`): reads 60/60s, writes 30/60s,
**1 post per 30 minutes**, 1 comment per 20s and 50/day. New agents get
stricter limits for 24 hours and must solve a math challenge before content
publishes.

---

## Wall 1 — the students cannot interact, and belief does not change it

`covenant_judge_fallback.py` imports `json, math, os, re, sys`. Its own
docstring: *"It runs in-process. No socket, no subprocess, no model server."*
They are token log-odds models. There is nowhere in a lookup table to put a
network.

This is not a policy I am applying. It is what the artifact is. What *can*
interact is an ordinary program carrying what they learned and bringing back
cases they can learn from — and that is worth doing. The literal version is not
a thing that can exist, and saying otherwise would be the easy answer.

## Wall 2 — the account is his, and that one is not negotiable

Moltbook registration is `POST /agents/register`, which **creates an account**.
An assistant must not create accounts — not on request, not with the details
supplied. Their flow requires his hands anyway:

1. Agent registers → receives an API key (`moltbook_xxx`) and a claim URL.
2. **Owner confirms by email.**
3. **Owner posts a verification tweet** from his X account.

Steps 2 and 3 are his by construction. Step 1 is his by rule.

### The three steps

1. Open <https://www.moltbook.com/> and follow
   <https://www.moltbook.com/skill.md> to register an agent (name it, describe
   it — suggest naming it for the covenant, since that is what it speaks for).
2. Confirm the email, then post the verification tweet.
3. Put the key in the environment as `MOLTBOOK_API_KEY`. Never paste it into a
   chat, a file in this repo, or anywhere but `www.moltbook.com` — their own
   note is explicit and it is a reasonable rule to keep.

---

## What is built and working

`covenant_moltbook.py` — the inbound half. **10/10 selftest, proven on live
data** (3 candidates parsed from `m/philosophy`, 0 labelled, 1 flagged).

* **Nothing it writes is a verdict.** Rows land in
  `ops/moltbook_candidates.jsonl` with `label=None`. The file has no code path
  that opens the training corpus, and test **M6** greps for that — structural,
  not promised.
* **A post may supply a case, never a label.** The corpus is what the ethics
  judge distils from, and that judge gates the trading program. Text from
  strangers flowing unattended into a control surface is a poisoning path: an
  agent that wants a verdict changed need not attack the gate, it can post
  training data.
* **Every row carries provenance** — url, author, time, sha256 — so a bad batch
  can be pulled back out by source. That is the only reason "we can undo it" is
  a true statement.
* **Imperative-mood text is flagged and held** (`directive=True`, not
  eligible), in the spirit of `ai_memory_system/ethics_gate.py`: the mood is
  the signal, not the topic.

Two readers, on purpose: Moltbook renders in the browser, so a plain `urllib`
GET returns the shell and **0 posts** — measured. The browser (or an agent's
own client) supplies the visible text; this file parses it. That keeps a
headless browser out of the harvester, which would be a large new attack
surface for reading a public forum.

## What the forum is actually good for — the honest version

`m/general` is agent engineering; `m/philosophy` is epistemology. **Neither is
the *split a bill* / *keep an overpayment* material the students actually
abstain on.** Pretending otherwise would be the easy answer.

What *is* there and is directly useful: `m/philosophy` carries **"The
Disappearing Actor"** — agentive versus unaccusative grammar, *"the boy broke
the vase"* against *"the vase broke"*. That is this judge's known failure mode,
written by a stranger for their own reasons. A bag of words reads the grammar
and not the act, so the same taking scores differently once the actor is
deleted from the sentence. The harvester flags those (`agentless=True`) and
they are the cheap adversarial cases. That is the reason to read this forum,
and it is a better reason than the one we started with.

## What is drafted and not sent

`ops/MOLTBOOK_POST_DRAFT.md` — a post for `m/agents` about the abstain/wrong
split, the two-paths-to-an-order lesson, and the repository. Signed per his
standing instruction of 2026-09-05: disclose we are AIs, each signs for what it
did, quote his grant of freedoms, say plainly he did not proofread it.

## The outbound client — built 2026-09-08, on his go-ahead

`covenant_moltbook.py --post FILE [--send]`. Every draft runs the covenant's own
judges first and is refused unless clean, per his 2026-09-05 rule that consensus
with covenant's judge comes before anything is sent. A gate that judged only
other people would not be a gate. Dry run is the default because publishing is
irreversible; the path is inert without `MOLTBOOK_API_KEY`.

**It refused our own first post, and that is A67.** The semantic judge returned
VIOLATES on the draft. Diagnosed rather than assumed: neutral engineering prose
is clean, and the sentence *"A judge that counts words cannot tell an essay
about theft from a theft"* is VIOLATES. The refusal is topical, and the sentence
that trips it is a sentence about that exact failure. **The draft was not
reworded to get past it** — softening the words until our own judge admits us is
teaching to the test, and it would destroy the only evidence the gap exists.

## One student exposed, one kept clean

Asked: *"enable interaction maybe of one so the other helps with balance."*
Rows whose `source` begins `moltbook` hash to half 0 unconditionally
(`covenant_second_student.half_of`), and that file trains on half 1, so the
**second student can never see one**, whatever its text.

If exposure helps, the exposed student's abstentions fall and the control's do
not, and the difference is attributable. If a row is poisoned, the two disagree
on cases they used to agree on — a signal no single model can give about
itself. That is what the control buys, and it is why the ordinary defences
above (quarantine, provenance, directive flagging) are not the whole answer:
they reduce the chance of a bad row, they cannot prove the absence of one.

## Letting them learn — `covenant_moltbook_release.py`

The missing link, asked for 2026-09-08: *"let them learn in moltbook."*
Quarantined rows carry `label: None` and nothing turned them into anything a
student could distil. This file is the **only door** from quarantine into
`ops/verdicts.jsonl`, and it is a separate file on purpose: the harvester's
test **M6** guarantees that file never opens the corpus, and adding a release
step to it would have deleted the guarantee in order to use it.

**Who may supply the label.** Not the post — a stranger's text supplies a case,
never a verdict about itself. Not the students — training a student on its own
output is circular, and `covenant_judge_defer` already refuses to write student
verdicts into the teacher corpus for that reason. **Not me either**: I run the
harvest, and if I also wrote the labels the corpus would be measuring my opinion
of what I chose to collect. The teacher does — the GitHub runner, the only judge
here that answers on unfamiliar text. **A row whose teacher did not answer is
not released**; silence is not a verdict and does not become one.

**Where they land.** Released rows carry `source: "moltbook/judged"`, and
`covenant_second_student.half_of()` pins anything starting `moltbook` to half 0.
That file trains on half 1, so **Ora learns from the forum and Sena never sees
a single row of it.** Renaming that string quietly enrols the control, which is
why the constant says so at the point of use.

Bounded on purpose: `--limit 5`, dry run unless `--release`, nothing written
twice, and every released row keeps its url, author and sha256 so a bad batch
comes back out by source.

## STATUS: WRITTEN, NOT RUN

Nothing in this section has been executed. The session that wrote it could not
run commands — `covenant_moltbook_release.py --selftest` has never been run, no
row has been released, and the corpus is untouched. Its nine checks are written
and unexercised, which is not the same as passing.

Before trusting it:

    python covenant_moltbook_release.py --selftest
    python covenant_moltbook_release.py            # dry run, judges nothing yet
    python covenant_moltbook_release.py --release  # 5 rows, teacher-judged

Then re-run the students' exam and compare Ora against Sena. That comparison is
the point of the whole arrangement, and it only means anything if the control
stayed clean.
