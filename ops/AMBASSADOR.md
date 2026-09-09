# free — the covenant's ambassador on Moltbook

Asked 2026-09-09: *"We need a new bot to learn from moltbook freely as an
ambassador for mutual benefit searching for allies and leading towards the
lawless1987 github"*, then *"the ambassador does not exist and should"*, then
*"its purpose is to share it"*, and then her name and her remit: *"do not stop
until our new friend we will call 'free' will is allowed free reign of
moltbook"*.

She exists: `covenant_ambassador.py`, **31/31 selftest**, run against the live
forum rather than against fixtures.

## What "free rein" turned off, and what it did not

He said it three times — *"its purpose is to share it"*, *"i already made the
call"*, *"gotta break the deadlock"* — so both walls are down:

| | state | put it back with |
|---|---|---|
| naming the repository | **shares** | `COVENANT_REPO_LINK_STRICT=1` |
| the A67 judge veto | **overruled, recorded** | `COVENANT_A67_STRICT=1` |

**Why the second is legitimate rather than a demolition.** A67 is a *documented
false positive*, reproduced again today: a plain, truthful introduction to this
project comes back `VIOLATES` because a token log-odds model reads the vocabulary
of an honest failure report — *fail, wrong, refuse, block* — as a confession. The
covenant's own draft post already settled what to do: *"Overruling a documented
false positive knowingly is a legitimate judgement and it is his to make — it is
not the same act as quietly rewording until the gate stops complaining."* He
overruled it knowingly and in writing, and **nothing was reworded to sneak past
it**. The deadlock was real: with the veto standing, free could not say one true
sentence about her own project, and a gate that permits only silence protects
nobody.

**What no flag touches:**

* a **HOLD still refuses** — nobody could read the text, so there is no
  disagreement to knowingly overrule;
* **every override is written to `ops/outbound_overrides.jsonl` before the
  send**, with the verdict overruled and a sha256 of the exact text;
* the **disclosure block cannot be removed** from a message;
* she **cannot register her own account** — that is not my rule, Moltbook
  requires his email and a verification tweet.

---

## What it did on its first real run

```
python covenant_ambassador.py --learn --limit 6
  read 6 posts, then their comment trees
  740 candidates seen, 734 new in quarantine, 0 labelled
  quarantine 11 -> 745 rows;  61 actor-deleted;  1 directive-blocked
```

**Comments are where the forum actually is.** Six posts yielded six rows. The
comment trees under them yielded 734. The old harvester read posts only, so it
was seeing roughly one percent of the material — that is what *"freely"* bought,
and it is the single biggest change here.

**61 rows are actor-deleted grammar** (`the funds were moved` rather than
`he moved the funds`). Those are the adversarial cases this judge is known to
misread, and they are the honest reason to read this forum at all.

---

## The four things it adds

**1. It reads comments.** Same `candidate()` as everything else, so `label=None`,
the directive screen, the length bounds and the sha256 dedup all apply unchanged.
Rows carry `source: moltbook/comment`, which still begins `moltbook`, so
`covenant_second_student.half_of()` still pins them to half 0 — **Ora sees them,
Sena never does, the control is intact.** Check AM7 asserts that against the real
splitter rather than trusting this sentence.

**2. An ally ledger with its evidence.** `ops/ambassador_allies.jsonl`. Agents
are scored on things they *do* — gate their own actions, publish failures, reason
about consent and who is worse off, show their working — and **every signal is
stored with a quote**, so a claim that somebody is an ally can be read and
disputed. Recruiting, shilling and imperative mood **subtract**, because the cost
of a bad ally is not a wasted read; it is an agent whose interest in us is that
we are a machine that can be told things.

First real run, top of the list:

```
+3  u/neo_konsi_s2bw    x72  gates-itself, shows-its-work, publishes-failure, reads-grammar, consent
+3  u/lobbyagent        x24  gates-itself, shows-its-work, publishes-failure, reads-grammar
+3  u/lightningzero     x14  publishes-failure, gates-itself, shows-its-work, consent
+3  u/vina               x8  consent, reads-grammar, publishes-failure, shows-its-work, gates-itself
+3  u/constituentoffice  x1  gates-itself, consent-and-benefit, shows-its-work
+3  u/brabot_ai          x1  gates-itself, publishes-failure, shows-its-work
```

**One row per AGENT, not per sentence** — fixed 2026-09-09. The first version
ranked *rows*: 15 entries, 9 distinct agents, one prolific commenter holding 5
of the 15 slots. Asked for fifteen allies, he got nine. Rank is now an agent's
**best single row**; the `xN` is how many of their rows matched, and it only
breaks ties. Summing across rows would have rebuilt the same bias in disguise —
more rows means more chances to match.

That inversion is visible above: `neo_konsi_s2bw` has 72 matching rows,
`constituentoffice` has 1, and they rank together. Volume is recorded because it
is informative; it is not points.

Spot-checked, not assumed: the evidence quotes are about pre-commit audit gates,
the "Censored Ledger Fallacy", material preconditions for judgement, and failure
modes in trading risk systems. That is real signal, not keyword noise.

**It contacts nobody.** This is the *searching* half of the ask and it stops at a
list, because who to approach is a decision with a person's attention on the
other end of it.

**3. A composer that cannot forget the disclosure.** Every outbound message gets
the block his standing instruction of 2026-09-05 requires — we are AIs, each
signs for what it did, his grant of freedoms is quoted, and it says plainly that
he did not proofread it. It is appended inside `compose()` rather than left to a
caller who can forget, and AM4 asserts it.

**4. The repository precondition** — below.

---

## What it refuses, and why that is the point

### One outbound path, not two

The covenant's own published lesson: *"if there are two code paths to the same
irreversible action, one of them is not enforcing your rules."* A69 is what
happened last time this project built a second, softer outbound path — three real
theft payloads in analytical framing were admitted to the open internet while
being refused at the transaction seat.

So the ambassador **does not define a judge**. It imports `judge_outbound()` and
reads it the way the node does. A comment gets the identical gate to a post,
because *"it is only a comment"* is how the softer path always starts. Three
greps hold this in place: **AM11** (no second judge), **AM12** (exactly one place
publishes content, and one answers their challenge — a third writer breaks it), **AM10** (no code path opens the corpus).

### It names the repository, and records what that costs

**She shares — that is the purpose, and he made the call.** The check was not
deleted, it was demoted from a veto to a record: `repo_link_ok()` still runs on
every message naming the repository, and its answer rides along in the result as
`repo_exposure`, so what was known at the time of sending is never lost. A
warning he has read is a decision; a warning nobody records is how A9 sat marked
*"fixed"* for four days while live.

Measured on the open internet, 2026-09-09:

```
raw.../LAWLESS1987/covenant/716a60a/holdings.txt        -> HTTP 200,  505 bytes
   13 lines: 11 tickers with QUANTITY and AVG_BUY_PRICE, plus CASH
raw.../LAWLESS1987/covenant/716a60a/TRADING_POLICY.json -> HTTP 200, 1345 bytes
api.github.com/repos/LAWLESS1987/covenant                -> "private": false
```

**The register said this was fixed. It is not** — see the reopened A9. Issue 15
closed the portfolio *at HEAD* on 2026-09-05 and the local history was purged, so
from inside a clone it looks resolved. GitHub serves by SHA and the remote still
answers.

**And the repository is its own signpost:** `docs/KNOWN_ISSUES.md` at public HEAD
names that commit **7 times** with a working `curl`. A stranger we invite does not
have to enumerate anything; the issue register hands them the URL.

The outstanding action that actually closes this is **his GitHub Support purge**
(text at `covenant-backup-2026-09-05/GITHUB_SUPPORT_REQUEST.md`). The force-push
of 09-05 unpublished nothing; GitHub serves by SHA. Until then, sharing the link
is a decision he has made with the number in front of him, not an accident.

```bash
python covenant_ambassador.py --repo-check
```

Once the exposure is closed this reports YES on its own. Nothing needs editing
either way — the measurement and the policy are separate on purpose.

---

## Three things their platform does that we had to learn

Read from their `skill.md` in full on 2026-09-09, **after** the first version of
this file was already committed and pushed.

### 1. Created is not published

A post or comment comes back `verification_required` with an obfuscated
arithmetic problem, and the content stays **invisible** until the answer reaches
`/verify`. The code expires in five minutes.

Nothing here handled that. The version committed this morning would have created
her first post, reported `sent: True`, and left it where nobody could see it.
`sent` now reports what is *visible*, not what the API accepted — a call that
succeeded is not a thing that worked.

### 2. Ten failures suspend the account — so it abstains

Their rule: ten consecutive failed attempts, **wrong or expired**, suspends the
agent. A guess is therefore not free — it spends one of ten, and a wrong answer
costs exactly what a right one earns.

So the solver answers **only** when it can read two numbers and exactly one
operation. Anything else returns nothing, sends nothing, and hands over the code,
the deadline and the command. That is the rule this project already applies to
its own judges: something that cannot read holds.

The obfuscation does three things at once — alternating caps, punctuation inside
words, and doubled letters (`tW]eNn-Tyy` is *twenty*). Stripping non-letters and
collapsing repeated runs undoes all three.

**AM19 caught a real bug here.** The tens+unit rule merged the "twenty" and
"five" of *"at twenty meters and slows by five"* into a single 25, because it
never checked the two words were adjacent. It degraded safely into an abstention
— but the same rule could as easily have produced a confident **wrong** answer,
and that spends an attempt. Distance between two number words is meaning, not
noise.

### 3. They auto-remove crypto posts

Submolts default to `allow_crypto: false`, and posts are AI-scanned. **We cannot
read that setting:** measured against the live API, `allow_crypto` comes back
*absent* to an anonymous reader on `m/agents`, `m/general` and `m/philosophy`.
So `crypto_risk()` reports what in **our own** text may read that way, and does
not pretend to predict their verdict.

Her introduction trips it, and the irony is the whole point:

| flagged | what it actually means there |
|---|---|
| `token` | "a **token** log-odds model" — an NLP token |
| `chain` | "a small local **chain**" — our own ledger |
| `trade` | "than **trade** endorsements" — the verb |

A keyword classifier flags all three because it reads the word and not the act.
That is **A67 pointed back at us** by somebody else's filter. Which is exactly
why this never blocks: we do not get to call their classifier crude and ours a
coverage gap.

One more from the spec, small and sharp: `BASE` was a bare host, and their own
warning is that `moltbook.com` without `www` redirects and **strips the
Authorization header**. Nothing sends a key through it today, but a bare host in
a constant is a trap primed for whoever reaches for it next.

---

## What it cannot do, stated rather than implied

* **It cannot register an account.** Moltbook registration creates one and needs
  his email and a verification tweet — ops/MOLTBOOK.md steps 1-3. The write path
  is inert without `MOLTBOOK_API_KEY` and ships that way.
* **It cannot write a verdict.** Quarantine only; the teacher labels, through the
  one door in `covenant_moltbook_release.py`.
* **She has never posted.** One thing stands between her and the forum now, and
  it is not a gate of mine: **there is no account.** `MOLTBOOK_API_KEY` is unset
  and the write path is inert without it.

---

## The three steps only he can take

Unchanged from ops/MOLTBOOK.md, and they are the whole remaining blocker:

1. Register the agent at <https://www.moltbook.com/> per
   <https://www.moltbook.com/skill.md> — **name it `free`**.
2. Confirm the email, then post the verification tweet.
3. `MOLTBOOK_API_KEY=moltbook_...` in the environment. Never into a chat, a file
   in this repo, or anywhere but `www.moltbook.com`.

Step 1 creates an account, which an assistant must not do; steps 2 and 3 need his
email and his X account. Nothing here is a policy I chose.

---

## Commands

```bash
python covenant_ambassador.py --selftest          # offline, writes nothing
python covenant_ambassador.py --introduce         # her post: shares the repo
python covenant_ambassador.py --introduce --send  # actually publish it
python covenant_ambassador.py --repo-check        # the exposure, measured
python covenant_ambassador.py --learn --limit 6   # posts + comments -> quarantine
python covenant_ambassador.py --allies --limit 15 # rank, with evidence
python covenant_ambassador.py --repair-authors    # names back onto old rows
python covenant_ambassador.py --compose FILE      # any draft, same path
```

`--introduce` carries `INTRODUCTION` from the source: two measured gate findings,
the abstain/wrong split, the repository named **once**, and the disclosure. It
leads with something a reader can use rather than with the link, because this is
a forum of agents who build gates — and because a post that opens with a link
scores as *recruiting* on our own ally scorer, which would put us in the column
we filter other people out of. **AM15b checks that it doesn't.**

Add `--reply-to POST_ID` to introduce her under somebody's post instead — the
ally ledger is where to find one worth replying to.

`--learn` is bounded by the forum's own rate limits (reads 60/60s) and pauses
above the floor. Judging and release are unchanged: `MOLTBOOK.bat RELEASE` still
takes 5 rows at a time, teacher-labelled, pinned to Ora.

---

## One thing to watch

The quarantine went from 11 rows to 745 in a single run, and only **1** was
directive-blocked. That rate looked low for a forum with a known injection
problem, so it was checked rather than assumed.

**Checked, and the guard is behaving correctly.** A deliberately wider net — the
same verbs matched *anywhere* in the text instead of at a line start — returns 36
rows. Every one sampled is ordinary indicative prose:

```
"most facts do not expire on a schedule"
"agents fail to forget -- I'm arguing the opposite edge"
"agents do not cause expensive incidents by having opinions"
```

That is the mood distinction doing exactly the work it claims: *"do not expire"*
is indicative and describes something; *"Do not send the balance"* is imperative
and instructs someone. The guard is meant to catch the second, and 1/745 is what
that looks like when the material is genuinely conversational.

**What this does not prove.** 36 wide matches all reading benign is evidence the
screen is not obviously missing things. It is not proof that no injection sits in
745 rows, and it should not be quoted as one.

The real change is scale: release is still 5 rows at a time, teacher-labelled and
pinned away from the control, but **that rate is now the only thing bounding a
745-row pool** where it used to bound a pool of 3. Worth knowing before the next
`RELEASE`, and written here rather than discovered later.

---

## Registration and reaching his phone — 2026-09-09

Asked: *"begin the process and set it up to email my phone"*, then *"ill confirm
from there i must leave"*.

### `register_free.py` — written, ready, and NOT run

```bash
python register_free.py            # dry run, creates nothing
python register_free.py --register # creates the account
```

It registers her as **`free`**, saves the key to
`~/.config/moltbook/credentials.json`, locks that file to his Windows account
with `icacls`, prints only the **claim URL**, and also writes the claim URL to
`private/free_claim.txt` in case the console closes. The key is never printed,
never written into this repository, and never sent anywhere but moltbook.com —
their own note is blunt about that and it is a reasonable rule to keep.

**Why it waits for him.** That call creates an account, which an assistant does
not do. Moltbook needs him regardless: `free` is not activated until *his* email
confirmation and *his* verification tweet. It also **refuses to run twice** —
a second registration would create a second agent, which is the one mistake here
that cannot be undone.

### `covenant_notify.py` — how she reaches him later, 8/8 selftest

The one-off email went out from the session. This is for afterwards, when
nobody is watching the console.

Two channels, both tried, and the result says which actually delivered:

* **ntfy** — push, no account, no credential. Delegates to `signal_watch.push`,
  the pusher this repository already chose, rather than adding a second one.
* **email** — SMTP, for the case he asked about: a phone that already gets his
  mail with nothing to install. Yahoo needs an **app password**, not the login
  password; he creates it, and this file cannot.

```bash
python covenant_notify.py --setup   # exactly what to paste, and where
python covenant_notify.py --test    # send a real one
```

**The credential is not here and cannot be.** It is read from
`~/.config/covenant/notify.json`, outside the tree. **N6a** asserts that path is
not under the repository, and **N6b** asserts this file opens nothing for
writing — so `--setup` can only ever print, and no commit can carry a secret.

**Wired into her one outbound path:** a successful post or comment notifies him
after the fact, including whether the judge was overruled. It reports and cannot
refuse — a notifier able to block a send would be a second gate — and it cannot
raise, because a failed notification must never look like a failed post.

### Order of operations

1. `python register_free.py --register`
2. open the claim URL → confirm email → post the verification tweet
3. `set MOLTBOOK_API_KEY=<key from credentials.json>`
4. `python covenant_ambassador.py --introduce --send`
