# Owner's decision — the armed trader stands. 2026-09-07

**Decided by:** L, in session, asked directly and answered directly.
**Question put:** the trader is armed and places orders itself, which conflicts
with §0 / `CONSTITUTION.md` "no trades placed by automation" — leave it armed,
or disarm it?
**Answer:** **leave it armed.** *"and let the gates know i approved."*

Recorded here because `IMPROVEMENT_LOG.md` §0 says exactly what to do with this
situation: *"a run that finds itself reasoning toward an exception should stop
and write the reasoning into the log for a human instead."* The run stopped and
asked. The human ruled. This is that ruling, written down and dated so it is not
re-litigated by the next session and not resolved by default the next time
someone notices the conflict.

---

## What this decision does

- `covenant_trader.py` stays **armed**, on the **daily** `TRADER_TASK.bat` task
  — 09:00, repetition disabled, `--once` — with the caps as configured:
  $25/order, $50/day, 2 orders/day, $100/week fiat, 20% position cap, 10% cash
  floor.

  *(Corrected 2026-09-09: this said "the hourly ... loop". It fires once a day
  and is not a loop. TRADER_TASK.bat's own header gives the reason: the strategy
  reads daily closes and a 200-day line, so a second run in the same day decides
  on the same data. A governance record about arming a live trader should
  describe how often it can act, and this one doubled it twenty-four-fold.)*
- The governance ambiguity is **closed**: the automation is approved by the
  owner, knowingly, with the conflict stated to him in those words before he
  answered.

  *(Corrected 2026-09-09: this cited `claude/LIVE_STATE_2026-09-07.md` §2. There
  is no `claude/` directory and no such file anywhere on disk, so the single
  external anchor in a decision record about arming a live trader pointed at
  nothing. The decision itself stands on the record below and on
  CONSTITUTION.md III, which do exist.)*

## What this decision does NOT do

**It does not clear either gate, and neither was touched.**

- **Rule 5 — 1/30 settled signals.** This is an evidence gate, not a permission
  gate. `signal_ledger.py`'s own header names the failure mode it exists to
  prevent: *"it could not clear on evidence, only by someone lowering the
  number."* Approval is not evidence. `min_sealed_signals` stays at 30 and was
  not edited.
- **Cash floor — cash 0.0% below 10%.** A risk rule, untouched.
- `trader_config.json` was **not modified** by this session at all. It is read
  every cycle by a live task; a decision record belongs in a document, not in a
  file the running system parses.

So the trader remains blocked today, by arithmetic rather than by permission,
and will place its first order only when both gates clear on their own terms.

## What is now L's to do, and cannot be done for him

The deployed system and its founding text disagree on their face, and approval
in a chat does not fix a hashed document:

- `docs/CONSTITUTION.md` line 66 — *"No trades placed by automation. No
  credentials requested or stored."* — is described by `GOVERNANCE.md` as **what
  binds the operator**. It is anchored (`CONSTITUTION_ANCHOR.json`). If the rule
  is to permit a bounded, capped, gate-blocked automated trader, that is an
  **amendment**: edit the clause, say what it now permits and what it still
  forbids, and re-anchor. Deliberately, in daylight, by L.
- `IMPROVEMENT_LOG.md` §0 binds **runs**, not the owner, and says it *"may never
  be edited, weakened, reinterpreted, or moved — by any run, for any reason."*
  No run may touch it, including on the strength of this decision. If L wants §0
  to say something different, L edits §0.

**UPDATE, same day, after L said "edit 66 please":** `docs/CONSTITUTION.md`
clause 1 **has now been amended** — it splits credentials (absolute, unchanged)
from automated placement (permitted, bounded, gated), corrects the false
"the trader is disarmed" disclosure, and carries a dated amendment record in
section III. `constitution.py verify` reports `0f0b3162… UNCHANGED` before and
after, because this file is not in the anchored set. `test_g2_promised_commands`
62/62 and `test_g1_doc_consistency` 16/16 still pass.

**What is still open:** the *authoritative* text of clause 1 lives in
`CONTRIBUTING.md`'s protected block *What never changes*, which is anchored
(`8a761863…`) and still reads "No trades placed by automation". This document
and that block now disagree, deliberately and on the record. Resolving it is
L's: amend that block and re-anchor with `python constitution.py hash`, or
narrow the amendment. No run may touch it — it is inside §0's reach.

Until that happens, the honest description of the state is: **the owner has
approved automated placement, this document has been amended to say so, and the
hashed rule it restates has not.** A system whose deployed behaviour and whose founding document disagree
is the P11/P14 defect class one layer up — the thing that says what is running
no longer describes what is running.

## Boundary held by the run that wrote this

Nothing was armed, disarmed, edited, sized, prepared or placed. No config, no
gate, no cap, no key, no §0, no constitution. Read-only audit plus this file.
