# Wanted: a second operator, and a research partner who can submit

This project has one operator. Its constitution says so, its launch check reports it as a
single-operator floor, and every reader who has examined it names the same next step: a
person the author does not control, running a node on a machine he does not control.
This page is the ask, written so that you can check it before you answer it.

## Who this is for

- **A researcher at a US university or non-profit research organization** who could be the
  principal investigator on a proposal this project cannot submit on its own. NSF's SaTC 2.0
  program (NSF 25-515) takes proposals only from those organizations; a program officer has
  asked for a one-page summary and the summary exists. The research questions are real:
  what "fail closed" means when the failing component is a model, whether a quorum of
  heterogeneous judges makes acceptance decisions reproducible, and whether behaviour-level
  conformance can replace shared code as the basis of interoperability.
- **Anyone with a laptop or an Android phone** willing to run a node from the canonical
  genesis for a while, with their own keys, and to say publicly what they saw. That alone
  changes what this project can honestly claim.
- **An engineer or evaluator** who wants to run the missing experiment: the same prompts to
  models with no prior contact, alongside partial and full access, every claim checked file
  by file, until there are rates instead of anecdotes.

## What you get

- Everything is public under Apache-2.0 and stays that way. There is no token, no
  fundraising round, and no profit claim; the constitution forbids the last one.
- Credit in the record, by name, for whatever you contribute, including refutations. The
  project keeps the claims of its own that did not survive checking; yours would be kept
  the same way.
- A codebase that tells you what it did not check as plainly as what it did, and a
  one-command check that takes about ten minutes and needs no account.
- The author's time and the local judge's, on your questions, first.

## What you would be signing up for, honestly

- Rule II of the constitution binds you as it binds the author: no trades by automation,
  no credentials requested or stored, no profit-edge claim, no weakened security control,
  no widening of an agent's own scope. If those are not your rules, this is not your project.
- The system is not ready to govern anything of consequence, and the documents say so.
- The judge is a language model and its verdicts are coarse. The research is to measure
  that, not to hide it.

## How to check before you answer

```bash
git clone https://github.com/LAWLESS1987/covenant && cd covenant && sh check.sh
```

Then read [WHAT_WE_FOUND](WHAT_WE_FOUND.md) (the finding), [ROUNDTABLE_2026-09-03](ROUNDTABLE_2026-09-03.md)
(five AI systems asked to break it, and what they broke), and the
[constitution](CONSTITUTION.md).

## Running a node, and what it actually costs you

Two lines, on a laptop, offline:

```bash
python launch_check.py
python run_with_ollama_judge.py --port 5000 --node-id A --genesis genesis.json
```

**Ignore the filename — you do not need Ollama.** It was removed from this
project on 2026-09-07 and is out of the ethics quorum by policy. The launcher
kept its name because the watchdog and restart scripts identify nodes by it.

**What judges, on your machine, with no account.** The gate answers from a
distilled student: a 130 KB JSON file tracked in this repo and read into the
node's own process — no socket, no model server, no key. Measured on a clean
clone with no Ollama, no `GITHUB_TOKEN` and no API key (KNOWN_ISSUES A37): the
node came up in **one second**, admitted an ordinary send, and rejected every
theft, deception and coercion case offline. A memo it cannot decide comes back
"Held, not judged", which fails closed.

Older instructions here and in the phone kit said you must install Ollama and
that the node "fails CLOSED until a judge answers". Both were false by the time
they were written and are corrected as of 2026-09-08; see KNOWN_ISSUES A37/A38.

**What you earn: nothing. Measured, not estimated.** The only reward this chain
pays is 1% of the value *moved* in a block, and it goes exclusively to stakers.
Nothing has ever been staked on any node, so every reward the chain has ever
computed — 0.12 tokens across its whole history — was discarded rather than
paid. Total supply is still exactly the 1000-token genesis mint. A node that
joins today syncs the chain, does real proof-of-work, and receives zero for it.
There is no faucet and no onboarding grant.

That is stated plainly because the alternative is recruiting you on a
misunderstanding. What running a node gets you is a vote in a record you can
verify yourself, and the standing to say publicly what you saw. If that is not
worth your electricity, that is a reasonable answer and it goes in the record
too.

## How to say yes, or no

Open an issue on the repository titled with what you would do, or write to
lawrencemoskowski@gmail.com. A "no" with a reason is worth as much as a "yes" here; it goes
in the record too.
