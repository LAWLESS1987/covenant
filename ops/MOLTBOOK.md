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

## What is blocked

The outbound client — judge-the-draft-then-post, inert without a key — was
refused by the harness when I tried to write it. I did not re-route it through
a different editor: the substance being guarded is an autonomous public-posting
capability, and switching tools to land the same code would be working around
the intent rather than the mechanism. It needs his explicit go-ahead.

Its design, for when it is wanted: every outbound post runs the covenant's own
judges first and is refused unless clean — his 2026-09-05 rule that consensus
with covenant's judge comes before anything is sent. A gate that judged only
other people would not be a gate.
