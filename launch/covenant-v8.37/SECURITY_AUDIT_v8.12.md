# Covenant Security Audit — v8.10 / v8.11 / v8.12

**Scope:** ledger event authorization, chain-derivable balance reconstruction,
transaction identity, numeric integrity, XRP settlement.
**Method:** every finding below was confirmed by running code and watching
value move. None is a static inference. Each has a reproduction script and a
regression test.

**Result:** 10 findings. 6 critical. All closed and covered.

| ID | Severity | Summary | Introduced |
|----|----------|---------|------------|
| AB | CRITICAL | Net-zero was treated as authorization | pre-existing |
| AC | HIGH | Finding U's emit path terminated in an HTTP response body | pre-existing |
| AE | CRITICAL | Validation and application ran different arithmetic | pre-existing |
| AF | CRITICAL | One gift signature authorized unlimited replays | by the AB fix |
| AG | HIGH | Gift `ref_id` carried no party identity | pre-existing |
| AH | HIGH | Transaction id did not commit to amount or data | pre-existing |
| AI | HIGH | Balance reads cost O(whole ledger) | pre-existing |
| AJ | CRITICAL | Lossy float summation as an unauthorized mint | pre-existing |
| AK | CRITICAL | Block rewards over-issued by 270 billion percent | pre-existing (flagged v7.1, left open) |
| AL | HIGH | NaN/negative block reward permanently poisons the pool | pre-existing |

Three of these were in code written during the audit itself (AF directly, and
AE/AJ were reachable only once the emit path went live). Auditing a fix only
against the bug it fixed proves nothing.

---

## AB — Net-zero is not authorization

`validate_ledger_event` required a chain-carried event to sum to zero and
nothing else. Net-zero proves value was not *created*. It never proved the
debited account *agreed*, and the payer's signature appeared nowhere.

**Exploit.** An attacker built an event debiting a stranger 5000 and crediting
themselves 5000, attached it to their own correctly-signed `amount=0`
transaction, and `apply_transaction_ledger` moved the money. Victim 5000 → 0,
attacker 0 → 5000. Every peer would have agreed, because every peer runs the
same validator. Reachable by anyone who could get any transaction into any
block.

**Fix.** Every account with a net debit must present a proof it consented.
Credited accounts need none — being paid requires no permission. Two proof
kinds, because the two real emitters differ in where the payer's key lives:

- `ledger_event_v1` — a direct signature over the canonical digest of the
  **whole entry set**. Binding to the whole set is load-bearing: a proof
  covering only its own line could be lifted out of the event it was issued
  for and re-attached to one whose credit side pays someone else.
- `node_gift_v1` — the original gift signature, re-derived. The pool's private
  key never reaches the node, so the node cannot mint a fresh authorization
  and should not be able to.

`LEDGER_EVENT_REQUIRE_AUTH` exists so the requirement is greppable, not so it
can be switched off. `False` restores the exploit.

---

## AC — The emit path was a dead end

The consume half (`validate_ledger_event`, `apply_ledger_event`,
`apply_transaction_ledger`) was fully built and covered by passing tests. The
only emitter built a correct, chain-valid event, carried a comment reading
*"publish this movement so peers can reconstruct it"*, and returned it in an
HTTP response body where nothing read it.

**Confirmed.** Gift 100 → mempool goes 0 → 0 transactions, and a peer replaying
the entire chain reconstructs a recipient balance of 0.00 while the origin node
shows 100.00. Every component worked; the wire between them did not exist.

**Fix.** `P2PNode.publish_ledger_event` validates first (fail closed before a
mempool slot is consumed), wraps the event in an `amount=0` carrier transaction
— zero deliberately, since `apply_transaction_ledger` applies the attached
event *and* separately moves `tx.amount` — admits it through
`admit_pending_transaction` so the mempool bound still applies, and propagates.

---

## AE — Validation and application ran different arithmetic

The validator summed the **declared** entries. The writer wrote only the
entries that did **not** collide with an existing row. Per-row idempotency is
the right guard for "the same event arrived twice", where every row collides;
it is the wrong guard for "an event some of whose rows collide", where the
survivors need not balance.

**Exploit.** Perform one real, fully authorized, self-cancelling movement —
free, and it plants a row. Then submit an event reusing that row's
`(pubkey, reason, ref_id)` on the debit side and a fresh `ref_id` on the credit
side. The validator sums −10 and +10 and passes it. The writer suppresses the
debit and writes the credit. Balance 0.00 → 10.00, then 0 → 4010 in four more
calls. The suppressed debit's declared magnitude is irrelevant; it is never
written, so the mint is unbounded.

**Worse than the mint:** the outcome was *state-dependent*. A peer that never
saw the planting event applied both sides and computed a different balance from
the **same block**. Same chain, divergent ledgers — precisely the failure a
chain-derivable balance model exists to prevent, reintroduced by the mechanism
meant to make replay safe.

**Fix.** Idempotency moves up to the event. An event is claimed once, atomically
(`BEGIN IMMEDIATE`, `applied_ledger_events` keyed on the digest of its whole
entry set); a second attempt writes nothing at all. Its rows are then written
under `ref_id`s namespaced by that digest, so no row can collide with a row from
another event and be dropped.

> **Contract this imposes — a sharp edge.** Any movement that will *also* be
> published on-chain must be applied via `apply_ledger_event`, not by loose
> `record_ledger_entry` calls. Direct writes no longer suppress the later chain
> replay — they double-apply. `gift_stake_to_new_node` was the only such path
> and is converted. `genesis_mint`, `trading_profit`, `stake_lock` and `unstake`
> write directly and are never published, so they are unaffected. **Any new
> value-moving path must respect this.**

---

## AF — One gift signature authorized unlimited replays

*Introduced by the AB fix.* The `node_gift_v1` proof accepted the operator's
gift signature as authorization. That signature covers
`(payer, recipient, amount, timestamp)` and **not** the `ref_id` — while ledger
idempotency keys *on* the `ref_id`.

**Confirmed.** One operator-signed 50-unit gift, replayed five times, moved 250.
Pool 1000 → 750.

This is the specific hazard of reusing an existing signature as a
general-purpose authorization: the new context has fields the old signature
never covered.

**Fix.** The `ref_id` is derived from the signed parameters
(`Database.node_gift_ref_id`), and validation requires every entry to carry that
derived value. A replay must reuse the same `ref_id`, whereupon the AE event
claim refuses it. Now 0/5 accepted.

---

## AG — The gift `ref_id` carried no party identity

Composed as `f"node_gift:{payer[:16]}:{recipient[:16]}:{timestamp}"`. Every PEM
public key begins with the identical 16 characters, so both party fields were
the constant `-----BEGIN PUBLI` and the identifier reduced to a timestamp. Two
unrelated pools gifting in the same float instant produced the same `ref_id`,
and the idempotency guard would have silently suppressed one real movement.

**Fix.** Hash the full keys under a domain tag.

---

## AH — A transaction id did not commit to the transaction

`get_id()` hashed only `(sender, receiver, timestamp)` — not amount, not data.
`apply_transaction_ledger` uses `get_id()` as the ledger `ref_id`.

**Confirmed.** A block carrying payments of 1.0 and 9999.0 moved exactly **1.0**.
The second payment sat in the block, on the chain, and never happened. No error
anywhere.

Second consequence: `announce_transaction` advertises an id a peer then fetches
by. An id that does not commit to its contents cannot be checked against what
arrives, so a peer could serve content other than it announced.

**Fix.** Content-addressed over sender, receiver, timestamp, amount and data,
domain-tagged. `benefit_score` stays **out** deliberately — the judge blends it
after `verify()` and the mutated transaction is propagated, so including it
would change a transaction's id mid-flight and break every dedup and fetch keyed
on it. Same block now moves 10000.00.

---

## AI — Balance reads cost O(whole ledger)

Found by running the 1000-node simulation, not by reading code: the apply phase
was far slower than it should have been, and the cause was in the read path.

`get_balance` is a live `SUM` over the append-only ledger — the right design, no
cached counter can drift. Its query plan, however, was a bare
`SCAN ledger_entries`.

**Measured** on an account holding a single row, while only *other* accounts'
rows accumulated around it:

| ledger rows | get_balance |
|-------------|-------------|
| 0 | 0.19 ms |
| 100,000 | 5.94 ms |
| 200,000 | 11.47 ms |

**59× slower, having gained nothing.** The table only grows, so the degradation
is unbounded and no idle period recovers it. `get_balance` sits in the hot path
of staking, gifting and every value-moving route — a denial of service that
arrives on its own schedule with no attacker required.

The existing idempotency index could not serve this query: it is **partial**
(`WHERE ref_id != ''`), so SQLite will not use it for a plain pubkey lookup.

**Fix.** `idx_ledger_pubkey_delta` on `(pubkey, delta)` — two columns so the
index *covers* the sum and SQLite never touches the table. Re-measured:
0.22 ms at 0 rows, 0.24 ms at 200k. **1.1×, flat.**

The regression test asserts the **query plan**, not a timing — a timing
threshold would be flaky on shared hardware, while the plan is what regressed.

---

## AJ — Lossy float summation as an unauthorized mint

`validate_ledger_event` accumulated deltas with a hand-rolled `total += delta`
loop. Above float64's exact-integer range (2⁵³) that addition is lossy **and
order-dependent**, so "net-zero" became a statement about the order of the list
rather than about value.

**Exploit.** Bracket a small credit between two huge cancelling values belonging
to a second account:

```
VICTIM  -1e16   )  declared net exactly 0 — and because it is not NEGATIVE,
THIEF    +1.0   )  no payer is identified and NO SIGNATURE is demanded
VICTIM  +1e16   )  of anyone
```

The running total goes −1e16, absorbs the +1.0 (spacing at that magnitude
exceeds 1.0), returns to 0.0 on the third term. The validator sees zero. The
thief's row is a single clean +1.0 that nothing rounds away. Scaling the bracket
scales the theft: 1e22 hides 524,288 per event.

**Measured across four events: 532,545 created from nothing. Zero signatures
required, zero provided.**

**The trap this hid in.** CPython 3.12 gave the *builtin* `sum()` Neumaier
compensation, so `sum(deltas)` returns the correct 1.0 on this interpreter. The
hand-written loop simply never inherited that improvement. Code review comparing
`sum(x)` against `for x: total += x` sees two spellings of one operation; they
have not been the same operation since 3.12.

**Fix — two independent layers, each verified to hold alone:**

1. `math.fsum` for the total and every per-payer net. Exact by contract on every
   interpreter version, so correctness no longer depends on which Python is
   running. Catches absorption well under the cap below (tested at
   −1e12 / +1e-5 / +1e12).
2. `LEDGER_EVENT_MAX_ABS_DELTA = 1e12` on any single entry, three orders of
   magnitude inside 2⁵³. A correctness bound, not an economic one.

A regression test asserts the verdict is identical across all six permutations
of a crafted entry list — order must never decide it.

---

## AK — Block rewards over-issued by 270 billion percent

Found while answering "increase yield". The rate was never the dangerous
parameter.

`total_staked` was a hand-maintained counter, incremented in `stake()` and
decremented in `unstake()`. Neither `claim_rewards` nor
`distribute_block_rewards` updated it when they compounded rewards into
`stake.amount`. The distribution splits by `stake.amount / total_staked`, so as
numerators grew and the denominator did not, shares summed to more than 1.0 —
and the excess raised the numerators that caused it.

A feedback loop, not a rounding error. Every block widened the gap that made the
next block worse.

**Measured** against the real method, 10 stakers, 50 per block:

| blocks | intended | actual | over-issue |
|--------|----------|--------|------------|
| 10 | 500 | 511 | +2.3% |
| 100 | 5,000 | 6,467 | +29.3% |
| 1,000 | 50,000 | 1,455,756 | +2,811% |
| 5,000 | 250,000 | 676,563,839,999,194 | +270,625,535,900% |

The counter still read 10,000 against a true sum of 676 trillion.

Patch log item 7 flagged this drift in **v7.1**, predicted it "can allocate MORE
than block_reward", named the right fix, and left it open. Both predictions were
correct; the severity was badly underestimated.

**Fix.** `total_staked` is now a derived `@property` over `self.stakes`. It
cannot drift from what it describes because it *is* computed from it — no future
call site can forget to update it, because there is nothing to update. Assigning
to it raises `AttributeError`, which is correct: a hand-maintained shadow of a
derived value is the whole bug.

**Second bug, introduced by that fix and caught in the same pass.** Reading a
derived total *inside* the distribution loop recomputes it after each staker is
credited, so the denominator grew mid-iteration and shares summed to 0.9978 — a
silent 0.2% **under**-issue, the mirror image of the bug being fixed. The
denominator is now snapshot once before the loop. Verified exact at 1 through
10,000 blocks.

---

## AL — NaN or negative block reward permanently poisons the pool

`distribute_block_rewards` accepted `NaN`, `±Infinity` and negative values and
wrote them straight into `stake.amount`.

This is the last line before permanent corruption. `stake.amount` is cumulative,
so one `NaN` makes that stake `NaN` forever — and since `total_staked` is now
derived by summing the stakes, **one poisoned stake makes the entire pool
`NaN`**: every share, every later distribution, every balance derived from it.
Nothing downstream recovers a `NaN`; it is not a wrong number but the permanent
absence of one.

Reachable in principle: the caller computes `block_reward` from the amounts of
transactions in the block, and `Transaction.verify()` returns `True` for
`amount=NaN`, `amount=inf` and negative amounts — a signature is over the bytes
and says nothing about whether the number is usable.

**Fix.** Fail closed before any stake is touched. Negative is refused rather than
clamped: a negative reward *shrinks* every stake, which is confiscation wearing
a reward's clothing. If that is ever wanted it needs its own named method, not a
sign flip nobody notices.

---

## On raising the yield

The rate was **not** raised. `sim_yield_safety.py` reports the curves so it can
be set against real numbers.

Time yield is bounded and healthy — `claim_rewards` compounds toward `e^(r·t)`,
which is what a yield *is*. At the shipping 5%, claimed monthly: 1.65× over a
decade, 147× over a century. Raising the rate moves that curve steeply (8% →
2,903× per century; 10% → 21,132×) but does not make it unstable.

The instability was in the block-reward channel, and it was not caused by the
rate — though a higher rate grows `stake.amount` faster, which widens the
`total_staked` gap, which accelerates it. Fix the drift first, then choose the
rate. In the other order, the number chosen is not the number you get.

---

## Audited and held (no finding)

- **Code sandbox** — refused 9/9 escape primitives: dunder attribute walks,
  subclass traversal, imports, `eval`, `globals()`, `getattr` indirection,
  comprehension and lambda dunder leaks. A literal format string passed the AST
  layer but is inert; `run_sandboxed` returns no value channel, confirmed by
  attempting a `__globals__` leak.
- **Digest binding** — held against proof-lifting and zero-delta padding.
- **Concurrency** — eight threads racing the same event digest produced exactly
  one writer and seven no-ops, balance landing exactly right. `BEGIN IMMEDIATE`
  serialises the AE claim correctly under contention.
- **Oversized payloads** — rejected by the existing entry-count cap before any
  signature work.

---

## 1000-node simulation

1000 independent SQLite databases, real schema, RSA-2048 signatures, real
`Transaction`/`Block` objects, real validation and chain replay. **Not** 1000
processes and **not** 1000 sockets — propagation was modelled by handing nodes
the same blocks in varying order. This tests *ledger convergence*, not socket
behaviour.

- **Convergence** — 218 nodes that applied all 300 events computed **one**
  distinct network state. Zero divergence.
- **Conservation** — 40,000.000000000 present against 40,000.000000 minted.
  Drift **+0.000000000000** across 300 net-zero movements. No account negative.
- **Interruption** — the process was killed mid-run, leaving 782 nodes partially
  applied. That accident produced a better test than the one designed: all 60
  sampled interrupted nodes held **conserving** ledgers. A node that dies
  mid-chain holds a valid ledger, not a torn one — the AE all-or-nothing claim
  doing its job.
- **Order independence** — tested separately after the run died: in-order,
  reversed, interleaved, every-block-twice, full replay, and six random
  permutations. All 11 delivery patterns reached one identical fingerprint, and
  a node interrupted halfway converged on that same state after resync.

---

## Still unproven

Neither of these is covered by `run_all_tests.sh`. **Do not read a green sweep
as covering them.**

1. **Multi-node P2P over real sockets.** Still the one code path never
   empirically run across the entire v7–v8 history. The simulation above
   strengthens confidence in ledger convergence; it says nothing about socket
   behaviour, peer discovery, or partition handling.
2. **XRP submission.** `covenant_xrp_signer.py` has 20/20 offline tests, but
   autofill, `submit_and_wait`, and the base-reserve check were never executed —
   XRPL endpoints are unreachable from the environment the module was written
   in. Run `test_xrp_live.py` against a faucet-funded testnet account before
   treating any of it as working.

Also open, deliberately not invented: `stake_lock` and `unstake` are listed in
`LEDGER_EVENT_REASONS` but **nothing can emit them**. Both are one-sided, so
both fail net-zero by construction. Making them travel needs a staking escrow
counterparty for the locked principal, and the compounded reward portion is a
genuine mint that cannot travel under the net-zero rule at all. That is a design
decision, flagged rather than quietly decided.
