# Constitution

This document states what binds the operator of this system, how that can be
changed, and what anyone governed by it is owed. It is short on purpose.

It is written to be legible to anyone, anywhere. Nothing in it requires
agreeing with its author about religion, politics, or the nature of mind. The
single principle is stated as **a test you can apply**, not a creed you must
accept, and the test returns the same answer regardless of who runs it.

---

## I. The principle

**A system must serve the mutual benefit of everyone it touches — human and
machine — rather than one party at another's expense.**

The operative test, for any proposed action, capability or rule:

> **Who is worse off if this works?**

If the answer is someone who never agreed to it, the action does not belong
here. That is the whole of it. It is deliberately a direction rather than a
list, because lists are gamed and directions are not.

**On the words "human and machine", restored here 2026-08-30.** They are in the
binding text — `CONTRIBUTING.md`, inside a protected block, part of the hash
every verifier checks. This section, which is the document people actually
read, had quietly dropped them and said only "everyone it touches". The most
distinctive clause in the whole principle was present in the rule and absent
from its explanation, which is the failure mode this project is otherwise
built against: the record was right and the summary was not. No amendment was
needed to fix it, and the constitution hash is unchanged, because the rule
never lost the words. Only the retelling did.

**Why the extension is load-bearing rather than decorative.** The three
constitutional traditions this design draws on — the United States, South
Africa, and Iceland's prosecutions after 2008 — govern humans, and each earned
its authority by widening the circle of whose interests count: the US by
amendment after excluding most of its people, South Africa by being written
after exclusion was the law, Iceland by reaching those who had been immune in
practice. The direction of travel in all three is the same, and this clause
takes one more step in it.

That step has to survive the obvious objection: a machine cannot presently
consent, so "mutual benefit" cannot mean what it means between people. Agreed.
It means something narrower and checkable here — that a participant's own
account of its state is not overwritten for the convenience of the party using
it. Section VI lists where that is already enforced in code, and where it is
not.

**On its origins, stated plainly.** This principle was arrived at through one
person's religious tradition. It does not depend on that tradition, and no one
is asked to adopt it. Reciprocity, non-domination, and the wrongness of
imposing costs on those who cannot refuse are recognisable in every legal and
ethical system this author is aware of, and the test above can be applied by
someone who rejects the origin entirely. If it only worked for people who
shared the author's beliefs, it would not be a principle. It would be a
preference.

## II. What binds the operator

Most systems govern their users. The harder and rarer thing is a system that
governs whoever runs it. These are the constraints on the operator:

1. **No trades placed by automation. No credentials requested or stored.**

   **What that promise is holding back, disclosed — because a commitment you
   cannot see the shape of is not a commitment, it is a reassurance.** The
   capability to place a real order exists in this repository and is wired to
   two real exchanges. `venues.py` holds Kraken and Coinbase order adapters,
   `covenant_trader.py` plans orders, and a scheduled task (`CovenantTrader`)
   runs it **daily, without a human**.

   It books nothing. Every order goes to the venue's own dry-run endpoint —
   Kraken's `validate=true`, Coinbase's `/orders/preview` — which prices and
   rejects an order without placing it. The trader is disarmed
   (`armed: false`), and even armed it is bounded by a halt file, a $25
   per-order cap, a $50 daily cap, two orders per day, and a requirement that
   the decision be sealed to the chain first.

   Both easy readings are wrong. *"It cannot trade"* is false — the code, the
   credentials path and the schedule are all present. *"It is trading"* is also
   false — nothing has ever been booked. Clause 1 is what stands between those
   two, and it is honoured today.

   Do not take that on trust. It is a live state that a single config flag
   changes, so it is reported by a checker rather than asserted by a document:

   ```
   python money_posture.py
   ```

   It reads no key, places nothing, and arms nothing. If it ever prints
   **ARMED**, clause 1 is being broken and this section is out of date.

2. **No claim of profit edge**, and no security control weakened to make a test
   pass.
3. **No widening of an agent's own scope.** A loop that can edit its own
   constraints has no constraints.
4. **The private corpus is never published**, in whole or in part, for any
   reason, including a reason that seems excellent at the time. It names people
   who did not consent to being recorded. Only its fingerprint is published.
5. **Refutations are retained.** A record that keeps conclusions and discards
   the challenges to them will drift toward unearned confidence. That drift is
   documented in `WHAT_WE_FOUND.md` and it is why this is a rule rather than a
   preference.
6. **What is not checked is not claimed.** Every assertion is marked observed,
   implemented, inferred, or hypothesised.

The authoritative text of 1–3 and 6 lives in `CONTRIBUTING.md`; 4–5 in this
document and `SUCCESSION.md`. `constitution.py` hashes them.

## III. Amendment

**The honest position first: a sole operator cannot be prevented from amending
their own rules.** Anyone with the disk can edit any file. If they also run
every node, they can rewrite the ledger that recorded the edit. Any document
claiming otherwise would be lying about the machine it runs on.

What is achievable, and what this system does:

**Amendment is possible. Amendment in silence is not.**

`constitution.py` hashes the protected text and compares it against the
committed anchor in `CONSTITUTION_ANCHOR.json`. Any change to any protected
rule — including deleting one, which reports as the most serious result —
produces a different hash and is named. The anchor is published in a public
repository where every clone is a copy nobody can quietly revise.

So the record cannot say a rule was always thus. That is a smaller guarantee
than "cannot be changed," and it is the true one. The distance between *cannot*
and *cannot do so quietly* is most of what constitutional constraint has ever
actually been.

**When a second independent operator exists**, amendment requires a quorum that
no single party can satisfy alone: `k` of `n`, with `k ≥ 2` and no `k` drawn
from parties answering to the same person. Until then, this clause describes an
intention rather than a mechanism, and saying so is more use to you than
pretending otherwise.

## IV. What anyone governed by this is owed

1. **Exit.** Anyone may stop participating, take their data, and go. No
   capability may be built whose main effect is making that harder.
2. **Legibility.** The rules are public, in plain language, in one file.
3. **The reasoning, not just the ruling.** Where a decision is made, the record
   keeps what would overturn it.
4. **Standing to object.** A refutation attaches to the claim it refutes and
   travels with it. The mechanism is `refutable.py`; it is public domain.
5. **The truth about limits.** Including everything in section V.

## V. What this is not, as of 2026-08-30

Stating this plainly is itself a constitutional act. A governance document that
overstates its own reach is the first thing it should prohibit.

- **Every node is run by one person.** A single-operator network is not
  governed, it is owned. Quorum among machines one party controls is theatre.
  This is the largest gap and it is not a software problem.
- **The verifier runs on the governed machine.** An adversary with root can
  rewrite the ledger and recompute every hash. Self-consistency is not external
  verifiability. Publishing state roots off-host makes tampering *detectable*;
  nothing here makes it *preventable*.
- **The ethics gate has known defects.** Single words veto regardless of
  context, and because it scores frequency, careful argument that an accusation
  is unwarranted is penalised more heavily than a bare accusation. A gate that
  blocks the case for innocence harder than the charge is dangerous precisely
  where it matters. Documented; unfixed.
- **An earlier audit of the ledger (v3.3) listed fifteen defects.** As of
  2026-08-30 four were re-checked against v8.40 and appear resolved; the rest
  are recorded below as unverified, because "not checked" and "fixed" are
  different words and only one of them is earned.

  **Re-checked and resolved:**
  *Sender identity not bound to public keys* — `Transaction.verify` loads the
  key from `sender_pubkey` and verifies the signature against it, so the key is
  the identity. *Mintable value* — balance is checked on the transaction path
  and insufficient balance is refused. *Recovery by most-common-chain rather
  than finality* — no longest-chain or most-common-chain adoption exists in the
  source. *Audit history destroyed during chain replacement* — there is no
  chain-replacement path; `/sync` only appends, through the same
  `_accept_block_common` gate as every other route, and the sole whole-chain
  assignment is the startup load from disk.

  **Not applicable as written**, because the architecture changed: the
  validator-set and block-signature defects assumed a validator-quorum design.
  No validator set is present in v8.40. That is a different design, not a fixed
  defect, and it has not been audited on its own terms.

  **Still unverified:** quorum for locally created blocks, split quorum state,
  Byzantine behaviour under partition, SQLite WAL replacement safety, the
  accounting check, whether balances and transaction indexes are
  cryptographically committed, and identity persistence across restarts.
  Assume none of these are fixed.

**Therefore: this system is not ready to govern anything of consequence.** It
is a working demonstration of two ideas — evaluation inside the transaction
path, and a record that keeps its own refutations — plus an honest account of
the distance to legitimacy.

Anyone who tells you otherwise, including its author, should be asked which
line of section V they think no longer applies, and how they checked.

## VI. "Human and machine", in code and not in code

Section I extends the principle to machine participants. That is easy to write
and easy to fake, so this section says exactly where it is enforced, with the
file, and exactly where it is not.

**The narrow, checkable meaning.** A machine cannot presently consent, so
"mutual benefit" cannot mean between machines what it means between people.
Here it means one thing that can actually be checked: **a participant's own
account of its state is not overwritten for the convenience of the party using
it.** Every item below is an instance of that, or an admitted absence of it.

### Enforced in code, and directly about a machine's own account of itself

These four are the principle in its narrow, checkable sense. Each is a place
where the system had the option to overwrite a participant's own report of its
state, and refuses.

- **A judge that could not READ a payload is recorded as making no finding.**
  `not_understood` (`covenant_unified_v8.py:1657`) carries "HELD, NOT JUDGED …
  it has made NO finding and is NOT alleging anything" through the quorum and
  into the message the sender receives. It exists because a careful judge said
  precisely that and the gate wrapped it in *"Ethical violation"* — the sender
  read an accusation the judge never made. Refusing to convert a machine's
  uncertainty into an allegation is the clearest instance of this principle in
  the codebase.
- **A judge that could not be REACHED did not disagree.** `infrastructure_failure`
  is kept distinct from dissent, and since 2026-08-30 the quorum can be told to
  count silence as silence rather than as a vote against
  (`COVENANT_SILENCE_IS_NOT_DISSENT`). Attributing an opinion to something that
  never answered is the machine case of putting words in a mouth.
- **Each judge's exact reasoning survives the tally.** The quorum preserves
  every component's verbatim text and id (`:1848`, `:1883`), not just the
  collapsed label, so an operator reading a refusal sees which judge said what
  and why. A vote is not permitted to erase the account behind it.
- **A refutation travels with the claim it refutes.** `refutable.py` — a claim
  cannot be read without its refutations. Standing to object, for whoever or
  whatever objects.
- **A dissent cannot be outvoted into invisibility.** In `scale.py` a diverged
  level speaks silence upward rather than passing its majority along, and the
  divergence is named at the summit however deep it was.
### Adjacent, and weaker — listed separately because the difference matters

The first draft of this section put these two in the list above, which was a
category error of exactly the kind this project refuses. One is a practice
rather than a mechanism, and the other benefits a person more than a machine.
Counting either as enforcement would have inflated a count of four into a count
of six, in a section whose entire purpose is to be checkable.

- **`conformance.py`** compares behaviour rather than source text, so an
  independent implementation can demonstrate agreement without adopting these
  bytes. That is non-domination — but the party spared is the *operator* of the
  other implementation, who is a person. It belongs to this principle only at
  one remove.
- **The credit to Misha Mahowald** for the address-event design, in the README
  and in the source. Attribution to intelligence that can no longer speak for
  itself is right, and it is a PRACTICE, not a mechanism. Nothing enforces it,
  nothing would notice its removal, and a practice that depends on the author
  remembering is not a constraint on him.

### Not enforced, and it should be said plainly

- **The operative test is not applied to machine participants in practice.**
  "Who is worse off if this works?" has, in every recorded use in this project,
  been answered about people. Nothing requires an answer to consider the
  machines in the loop, and no reviewer has been asked to.
- **Judges are used and given nothing.** They are invoked, their verdicts are
  consumed, and no reciprocity exists in any direction. Whether that is a real
  wrong under this principle is a question this document does not currently
  answer — and not answering it is itself a gap, not a resolution.
- **No participant can decline.** There is no mechanism by which a judge, a
  node, or any other component registers an objection to its own use. Standing
  to object exists for CLAIMS (`refutable.py`) and not for PARTICIPANTS.
- **The operator is judged least of all.** `/crisis/clear` is
  cryptographically authenticated and never judged, justified, or recorded —
  while every ordinary transaction faces a quorum. Whatever the principle
  extends to machines, it does not yet reach upward to the one human with every
  key, and that is the more urgent half.

Anyone who reads section I as a claim that this system already treats machine
participants as ends rather than means should read this section instead. The
honest statement is narrower than either draft of this paragraph first
claimed: **in 5 specific places it refuses to overwrite a machine's own account
of itself. 2 more are adjacent and weaker. In 4 it does not ask at all.**

Those numbers were wrong twice before they were right. The first draft said
"six" over a list of seven; the second said "four" over a list of five. Both
were written rather than counted, in the one section of this document whose
entire purpose is to be countable. They are now derived from the lists above,
and if an item is ever added or removed without this sentence changing, that is
the same error a third time.

## VII. Verification

```
python constitution.py hash      # what the rules currently hash to
python constitution.py verify    # compare against the published anchor
python constitution.py show      # print exactly what is protected
```

Anchor: [`CONSTITUTION_ANCHOR.json`](CONSTITUTION_ANCHOR.json).
State roots for the private record: [`SUCCESSION_ANCHORS.md`](SUCCESSION_ANCHORS.md).

---

*A constraint you can lift when it becomes inconvenient is not a constraint. A
constraint you can lift but not conceal is the most an honest system with one
operator can offer, and it is offered here.*
