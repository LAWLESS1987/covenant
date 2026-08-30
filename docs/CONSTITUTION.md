# Constitution

This document states what binds the operator of this system, how that can be
changed, and what anyone governed by it is owed. It is short on purpose.

It is written to be legible to anyone, anywhere. Nothing in it requires
agreeing with its author about religion, politics, or the nature of mind. The
single principle is stated as **a test you can apply**, not a creed you must
accept, and the test returns the same answer regardless of who runs it.

---

## I. The principle

**A system must serve the mutual benefit of everyone it touches, rather than
one party at another's expense.**

The operative test, for any proposed action, capability or rule:

> **Who is worse off if this works?**

If the answer is someone who never agreed to it, the action does not belong
here. That is the whole of it. It is deliberately a direction rather than a
list, because lists are gamed and directions are not.

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

## VI. Verification

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
