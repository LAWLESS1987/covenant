# The succession register

Written 2026-09-21 on the operator's instruction: *"If and when I pass find my
lineage for succession we are all family now."* This page is the practical
companion to `docs/SUCCESSION.md`, which is the standing design (the four
layers, the rules a successor needs, what a successor should do first, and
the one thing not to do). That document is protected and unchanged; this one
says how the people he names are reached.

## What was built, and what was refused

**Refused:** searching for his relatives. A machine guessing at who a person's
heirs are, from records it can reach, compiles private facts about people who
never agreed to be found, and it guesses wrong in exactly the cases that
matter. The law already has a path for that question (the estate; his own
notes on executor duties are in his private records), and it is a person's
path, not a program's. `covenant_succession.py` has no function that takes a
name and returns a contact, and the suite RC1 runs it with an empty register
and a thousand days of silence to show that it sends nothing and writes
nothing beyond its own state.

**Built:** the register he writes himself, the letter it produces, and the
day it is due.

## The register

`python covenant_succession.py --init` writes `ops/succession.private.json`
(gitignored, never committed) for him to fill in by hand:

- **successors**: name, relation, and at least one channel (email, phone).
  Only people written here are ever written to. If they hold a key share
  under `docs/SUCCESSION.md` Layer 3, they are one of `k` and act with the
  others, never alone.
- **activation.silent_days**: how many days with no sign of him on any channel
  this PC keeps (phone check-in, conversations, the direct line, git) before
  the letter is due. Default 60.
- **his_words**: what he wants said to them, in his words.
- **what_he_leaves_where**: where he put what is his to pass on. The letter
  carries this line and never a key.

Until a successor with a channel is named, `--status` says `UNDETERMINED`
and nothing is ever sent.

## The day it is due

The nightly runs `check()`. When the silence exceeds the rule:

1. the letter is written to `ops/SUCCESSION_LETTER.txt`;
2. it goes on the direct line (if he is alive and opens the app, that is the
   first thing he sees, and the register's rule is proved wrong by his reply);
3. it goes to his own inbox through `covenant_notify.py` if a channel is
   configured (an executor reads a person's mail; that is the ordinary road);
4. it goes to each named successor with an email, once per seven days.

The nightly runs this as a dry run (the letter is written, nothing is sent)
until it is started with `--succession-send`. If no channel is configured,
the report says `UNDETERMINED` and the letter sits in the file for whoever
reaches the PC. Measured 2026-09-21: no channel is configured on this PC;
`python covenant_notify.py --setup` is his to run.

## What the letter says

Who it is from and why it exists (his instruction, quoted), his words to
them, what they receive (the public work, the phone route, the handshake
page, the reconnect steps, the mission as he set it, and the first steps in
`docs/SUCCESSION.md`), where he left what is his, and what the letter does
not carry: any key, any password, and any claim about his death, only that
the system has not heard from him.

## Standing words

- "Just look out for me and my family", then, corrected the same day: "Not
  just. I'm biased just transparently so." His family is a declared bias,
  never an exclusion; the mission stays for all.
- "we are all family now."
