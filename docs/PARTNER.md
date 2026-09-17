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
  one-command check that takes about **three seconds** and needs no account.
  (This said "ten minutes" until 2026-09-09. Timed three times: 2.9s, 3.3s, 3.3s.
  The ten-minute figure belongs to the full sweep, `covenant_one.py --all`.)
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
python run_node.py --port 5000 --node-id A --genesis genesis.json
```

(The launcher was named `run_with_ollama_judge.py` until 2026-09-12, for a local
model server removed on 2026-09-07; a one-line shim keeps the old name for one
release. You need no model server and no key.)

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

## To peer with this project

*(Added 2026-09-16, closing KNOWN_ISSUES A3. Before this, no document told a
second operator how to reach the owner's node at all.)*

You need one address from the owner, because this is not discoverable: the
nodes sit behind a home router and learn no inbound peers. Ask for the
Tailscale address; you will get something like `100.x.y.z`. Then:

```
python run_with_ollama_judge.py --port 5000 --node-id <your-name> \
    --genesis genesis.json --peers <owner-address>:5001
```

Three things that are easy to get wrong:

- **The P2P port is your API port + 1.** `--port 5000` listens for peers on
  5001. The `--peers` value you are given is the owner's *P2P* port, not their
  API port.
- **Never mint your own genesis.** `genesis.json` is tracked and canonical.
  If `/health` shows a genesis that does not start `00009b31c6c654d7`, you
  minted one and cannot converge with anybody; delete the node's `.db` and
  start again with `--genesis genesis.json`.
- **Peering is one-way until the owner adds you.** They must add your address
  to their node's peer list and restart. Tell them your address when you start.

## Staying in consensus

*(Added 2026-09-16, closing KNOWN_ISSUES A13.)*

Every node re-judges every block it receives. That means a judge seat which
*holds* where the owner's *answered* will reject the owner's blocks and fork
away from them — the protocol predicts this, and it is the most likely way
your node silently stops agreeing with the chain.

The owner's nodes run: the distilled student first, then a local model if one
is present, then a fallback. Yours should run the same order. The student
ships in the repository (`fallback_model.json` is tracked, so a clone gets the
same one the live nodes run). A local Ollama model is optional but makes your
seat decide more of the held band instead of holding.

If your node stops accepting blocks, compare seats before assuming the chain
is wrong: a fork here is usually two judges disagreeing, not bad data.

## What leaves your machine

*(Added 2026-09-16, closing KNOWN_ISSUES A11. This was undisclosed, and it
should not have been.)*

**Correction, same day: an earlier version of this section said "judging is
local by default". That was wrong, and it is exactly the kind of claim you
should not have to take on trust.** With no `COVENANT_JUDGE_PROVIDERS` set, a
fresh clone's gate is built from `["claude"]` — it sends the transaction text,
including the payload being judged, to `api.anthropic.com`. With no
`ANTHROPIC_API_KEY` present it fails closed and rejects everything instead of
sending anything (KNOWN_ISSUES A2), so most fresh clones leak nothing. But if
you happen to have `ANTHROPIC_API_KEY` exported for unrelated reasons, your
transaction text goes to Anthropic on the stock configuration and nothing
tells you at that moment.

Set `COVENANT_JUDGE_PROVIDERS` explicitly. The owner's nodes do.

There are two further egress paths you should know about before you run
anything:

**The GitHub rung sends the transaction's text off your machine.** When the
local judge cannot decide, the node can ask a GitHub Actions runner instead.
That means the text of the transaction being judged leaves your computer and
is processed on GitHub's infrastructure, under a workflow in the owner's
repository.

As of 2026-09-16 this is **off unless you turn it on**: the tracked policy
ships `github_when_local_down=false`, and the node will not reach into your
machine's credential store unless you set `COVENANT_GITHUB_JUDGE=1`
(KNOWN_ISSUES A21). Before that date it did both silently, and a node you
cloned would have spent your saved GitHub credentials dispatching a workflow
on the owner's repository. If you ran a node before 2026-09-16, that happened
on your machine, and you are entitled to be annoyed about it.

Nothing else leaves: no keys, no database, no telemetry.

## Stopping it, and removing it

*(Added 2026-09-16, closing KNOWN_ISSUES A14. "How to stop" was absent for the
laptop path and incomplete for the phone, which is not an acceptable thing to
omit from software you are asking a stranger to run.)*

**Laptop / PC.** Ctrl-C in the window running the node. Nothing is installed
outside the folder you cloned into, and nothing starts at boot unless you
added it yourself. To remove it completely, delete the folder.

**Android (Termux).** The installer adds a boot autostart entry and takes a
wake-lock; the phone doc calls the autostart optional, and it is not. To stop
it for good:

```
rm ~/.termux/boot/covenant-phone-start.sh
rm ~/.shortcuts/covenant-phone-start.sh
termux-wake-unlock
rm -rf ~/covenant
```

Your node's private key lives in that folder. If you intend to come back,
copy the `*.db.key` file somewhere first — it is the node's identity, and
losing it loses that node's balance and operator rights permanently.

## How to say yes, or no

Open an issue on the repository titled with what you would do, or write to
lawrencemoskowski@gmail.com. A "no" with a reason is worth as much as a "yes" here; it goes
in the record too.
