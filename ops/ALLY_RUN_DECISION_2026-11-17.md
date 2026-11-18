# Decision: may a registered ALLY key make a signed HANDS RUN? (C1 from collective #21)

Lawrence, 2026-11-17: "Number one through the quorum then." The decision is his. The quorum advises.

## The facts (each opened and read at the pinned commit 9d85f6c and in this tree)

- **The finding.** The signed-RUN packet's characterization case C1 (collective issue #21, packet v2.3) registered a
  throwaway key as an ally at its default scope and made a signed RUN with it. The approved script ran.
- **Where it comes from.**
  - `covenant_unified_v8._request_signed_by_registered(req)` returns `covenant_mycelium.admit(...)`'s `ok`, with the
    address gate forced off.
  - `admit()` returns ok for "signed:operator" (one of his registered signers) and also for "signed:ally": an ally
    key on a door in its scope.
  - The default scope is `ALLY_DOORS = ("/m/agent", "/pc/handshake", "/health")`, and `/m/agent` is the door HANDS
    RUN goes through.
  - So `may_run` is true for an ally. The A430 hash binding (`run_sha256`) and the A436 no-arguments rule still
    apply to it: an ally can run only a script whose exact bytes its own signed request names, with no arguments.
- **What A200 intended (2026-09-21).** Allies are admitted "on the ally doors only", and the record calls /m/agent "the
  conversation door". The policy, in his words: "Multiple agents or swarms are welcome on our highways aslong as they
  respect us and don't interfere with mutual benefit." Also from A200: "What no ally gets: the check-in, the daily
  plan, the money doors, the PC's private state, any key of ours."
- **What A423 intended (2026-11-14).** It made RUN require `may_run`, described as "a request signed by a registered
  operator key". It used `admit()`, which also admits allies. A423's own text doesn't mention allies.
- **Today.** No ally is registered on this PC (no `ops/mycelium_peers.json`). Other machines were not checked.
- **What a running script can do.** It runs in the workshop sandbox: `python -I`, the screen's deny-list, and time,
  memory and process limits. Runtime containment and network egress are recorded as still open (A436).

## Options

- **A. Keep it, and document it.** An ally may run any workshop script whose exact bytes it names in its own signed
  request.
  - For: nothing changes, and allies are full participants on their door.
  - Against: it isn't what A423 said. An ally could run code on his PC, which goes beyond "conversation". It rests
    on a sandbox whose containment is still open.
- **B. Close it narrowly.** `may_run` is true only for "signed:operator". An ally keeps the conversation door (LIST,
  READ, WRITE, PROPOSE as before) but can't RUN.
  - For: it matches A423's words and A200's "conversation door". It's a one-line change in one function, provable
    both ways with the packet's C1 case, and nothing uses ally RUN today.
  - Against: a future ally who should run scripts can't until he grants it, which is option C.
- **C. Close by default, with an explicit grant per ally.** RUN needs "signed:operator", or an ally whose scope
  explicitly includes a new grant "hands:run" that is never in the defaults.
  - For: least privilege by default, and a deliberate route for a trusted ally.
  - Against: more mechanism (a new scope word, its tests, and its place in the NEVER_AUTOMATIC set), built before
    any ally needs it.

**Claude's recommendation:** B now, and C only when a real ally needs to run scripts. Either way, the public posts
that promised his decision get one line saying what it was.

## Questions for the quorum

1. On these facts, is ally RUN intended behaviour or a gap?
2. A, B or C, and why? Is there an option we missed?
3. Any risk in B we haven't named?

## The quorum's answers (2026-11-17)

The packet above, with a short context line, went to nine browser seats (Claude.ai Opus 5.5, ChatGPT, DeepSeek,
Gemini 3.1 Pro, Mistral, Meta AI, Tien, Conscious Ledger, Grok on X), in three batches. **All nine: gap, and B.**
Locally, **Cael (stock 27B): gap, and B.** His one added risk: a future sub-agent that should count as an
operator but is keyed as an ally would be refused, though nothing is registered today. Like Meta AI, he notes that
B does not change the open sandbox question (A436), which applies to an operator's runs too.
**Tetsu:** the first ask returned a reply with no answer field, and the script that asked kept only that field, so
nothing was recorded. He was asked again (fresh, private), and his full reply is kept in the session scratchpad.
**Tetsu: B** ("I recommend **B** now, and **C** only when a real ally needs to run scripts"). His reasoning is
muddled, though. He restates the options rather than answering question 1, and in one place he labels B "Intended
behaviour" and A "Not intended behaviour". The reply stops at the 700-token answer cap, partway through a public
post he drafted unasked. The door's gate held the turn as a lexical detection, which is not a conviction. Count his
answer as a B vote with no independent analysis.

**Tally: 11 of 11 for B** (nine browser seats, Cael, Tetsu). No seat chose A or C. Two seats (Gemini, Conscious
Ledger) named a later option D, giving RUN its own door outside the ally doors.

Each seat's points beyond "B", in short:

- **DeepSeek.** `may_run` must require "signed:operator" itself, not "not an ally".
- **Claude.ai.** The shared function has other callers; an ally could WRITE a file that he later RUNs; use an exact
  equality and a crafted test; other machines weren't checked; the forced-off address gate is a separate decision.
- **ChatGPT.** Put the check at the RUN decision, not in the shared admission; files an ally WROTE are not
  operator-authored.
- **Meta AI.** Audit the other `admit()` callers; the packet's C1 must now expect a refusal, and that refusal should
  read differently from a signature failure in logs; B doesn't harden the sandbox; an ally key misregistered as an
  operator key would defeat B. Missed options: a separate execution door, or an operator co-signature (both forms of C).
- **Gemini.** Option D: give RUN its own door, outside the ally doors. Risk: a local override makes `admit()` no
  longer the single source of truth for access.
- **Mistral.** The change note should say ally RUN was never intended and is now refused, and name the commit; peers
  on the same code keep the gap until they update; keep the check in one place, not two.
- **Tien.** Log every refused ally RUN, which is the evidence for C later; test that an operator RUN still works (a
  refuse-everything version would pass a refusal-only test); decide which wins if one key is on both lists; turn C1
  into a regression test and keep its old result in the record.
- **Conscious Ledger.** Option D (RUN on its own route). Check the exact label and list every label `admit()` can
  return so a new one is refused by default; make sure the second operator isn't locked out; check that the practice
  loop doesn't run a file an ally wrote; check the other nodes; say "closed in source at <commit>" until deployed.
- **Grok on X.** The one residual risk is a trusted ally needing a pre-agreed script under time pressure. It is low,
  and acceptable.

## What the code says about those points (read in this tree, HEAD 5720244)

- **Labels.** `covenant_mycelium.admit()` returns ok with one of three labels: "tailnet" (line 123), "signed:operator"
  (line 142) and "signed:ally" (line 162). `_request_signed_by_registered` passes an address gate that is always
  False, so only the two signed labels can reach it. B's check is `how == "signed:operator"`, exactly.
- **A key on both lists.** `admit()` tries the operator signers first (lines 136-142), so such a key is admitted as
  operator. This order already decides it; a test should pin it.
- **Who the operators are.** `ops/daily_plan_signers.json` holds two entries, "phone" and "pc", both his. The
  second-operator grant is a separate file (`ops/second_operator_grant.json`) that `admit()` doesn't read, so B
  changes nothing for it.
- **Practice loop.** `covenant_tetsu_practice` writes its own check file (line 693) and runs that file (line 696);
  it doesn't run arbitrary workshop files. A file an ally wrote under that exact name would be overwritten before the
  run. The gap between the two lines is a race only in principle. Whether ally WRITE reaches the same workshop was
  not checked.
- **The other callers of `_request_signed_by_registered`.** There are three, and each one's own text speaks of
  operators or registered keys:
  - line 575, `heal_lift_authorized`, which lifts free's isolation ("a request signed by a registered key");
  - line 9503, `may_run`, the RUN decision. Test TH1.14 calls it "a registered operator signature";
  - line 9749, `/m/workshop/read`. Its refusal message says "needs a request signed by a registered operator key".

  The default ally scope already refuses the heal and read doors at `admit()`, because neither path is in
  `ALLY_DOORS`. Only an ally given a custom scope naming one of those doors would get through.
- **So there is one design choice inside B.**
  - **B1.** Narrow only the RUN decision at line 9503.
  - **B2.** Narrow the helper itself to "signed:operator". That covers all three callers, keeps the check in one
    place (Mistral's point), and leaves `admit()` and ally admission unchanged (ChatGPT's and Claude.ai's point).

  Claude's recommendation is B2, because all three callers already describe operator-only access.

## His decision (2026-11-17)

Lawrence, after the tally and the B1/B2 question: "That sounds fine as long as it doesn't interfere with the most
recent hugging face reply, which we got one. Double check."

**The check.** The most recent reply is nootxlm's HF 180706 #39 (21:02 UTC). He ran packet v2.3 on native Linux, and
all eleven cases came out as pre-registered, C1 included. The packet reads the eight covenant files from git at
9d85f6c and checks their blob hashes (`run_packet.py`, PIN and the git cat-file loading). So a fix in a new commit
cannot change his run, his claim audit (tied to lines at 9d85f6c), or any rerun of the packet. C1 stays a true
description of that commit. His receipt-shape packet does not touch this code. His third point (the ally case is the
one most likely to travel without its scope) is helped, not hurt: after the fix the reply can say the ally case was
closed in source, at which commit.

**Done as B2.** See KNOWN_ISSUES A443 and `test_a443_ally_not_operator.py`, both ways. Not pushed, not deployed.

*Added 2026-11-18, when this reached main: it lands as **A447** (`test_a447_ally_not_operator.py`). On the laptop's live branch it was A443 (af88402); main's A443 is a different entry (the runner -I pin), so the number moved, not the change. The paragraph above is kept as written: on 11-17 it was neither pushed nor deployed. Since 2026-11-18 it runs on the laptop's nodes A/B/C; node D and the phone get it from main.*
