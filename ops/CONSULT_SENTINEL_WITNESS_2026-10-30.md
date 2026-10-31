# Consult: improving the Sentinel-Witness witness (2026-10-30)

The operator's words: *"Sent8nel witness improvement? Ask the others"*.

Three seats, each on its own site in the operator's Edge, asked one identical
question (kept verbatim in the session scratchpad as `sw_consult_q.txt`):
ChatGPT (chatgpt.com, thinking effort High), Gemini (gemini.google.com, 4 Argon),
Grok (grok.com, Expert). The question was about the WITNESS architecture only, and
said so: not investment advice, not the strategy. It carried only facts already
public in the Sentinel-Witness README (caps, the waiver and the 7/30, 0/7, -6.13%
record at the waiver) plus the topology. No balances, no keys, no account names.

Nothing was changed in Sentinel-Witness. Every item below touches the money
path, and changes there are the operator's to approve (autonomy grant: approval
for money).

## What I checked in the code before writing this (rule 1, rule 7)

- `Sentinel-Witness-trading/trader/witness.py`: the boundary is a subprocess
  into covenant's folder, run as the same OS user on the same host. Its seal
  script hands covenant's `seal_decision_result` the **executor's own `cfg`**.
- `covenant/covenant_trader.py` `seal_decision_result`: reads `node_key` and
  `node_ports` from that cfg. `os.path.join(HERE, node_key)` returns `node_key`
  unchanged when it is absolute (measured: a join of `C:/cov` with
  `D:/elsewhere/k.pem` returned `D:/elsewhere/k.pem`).
- `Sentinel-Witness-trading/trader/covenant_trader.py`: whether a seal is
  needed at all is `cfg.get("seal_required")` from the executor's config, and so
  is every cap (`max_order_usd`, `max_daily_notional_usd`, `max_orders_per_day`).
  So is the Rule 5 waiver record.
- Today's values are benign: `node_ports [5000]`, a relative `node_key`,
  `seal_required` true, `armed` false.

**Finding (mine, verified; none of the three saw the code):** the party being
witnessed sets the witness's terms. Its config chooses which node seals, which
key signs, whether a seal is required, and the caps. A change to the
executor's config (an edited file, or a second executor with its own) could point
the seal at a node that always admits, or turn the seal off, and every check
downstream would still read green. This is the A392 grid shape again, where the
signer chose the class. The seal is real only while the executor's config is
honest, which is exactly what a witness is supposed to stop relying on.

## Where all three agree

1. **Same host, same user is not independent witnessing.** All three said the
   framing overstates it, each in its own words: Gemini called it "an elaborate
   compliance logger". It guards against logic bugs, not against a compromised or
   misconfigured executor.
2. **Move what can place an order out of the executor's reach.** ChatGPT: an
   authorization gateway that alone holds the exchange credentials and submits
   only what covenant approved. Gemini: "invert the topology", so covenant holds
   the keys under a separate OS user and the executor sends unsigned intents.
   Grok: covenant on a different host or user, reached by a narrow authenticated
   channel that cannot write the chain or clear a halt. The shared test: with the
   executor fully compromised, no order reaches the exchange.
3. **Seals anchored off-host**, so a rewritten or truncated local chain
   diverges from a record the executor's host cannot edit. Grok and Gemini name
   the attack it defeats: truncate and re-mine from genesis.
4. **Caps and halts owned by the witness, durable, keyed on the witness's
   honored time.** Restarts and clock moves must not reset the daily window or
   clear a halt. Unknown actions refused, class derived, never declared.
5. **Two executors block arming.** Covenant's older armed copy and Sentinel's
   copy can split-brain and double-count caps. (Gemini says delete it. Here that
   means retire it to `.trash/` with a record, which is the retire step he
   stopped on 10-06.)
6. **Do not arm as it stands.** It is already disarmed (`armed: false`), so this
   asks for nothing new. It names what would have to be true first.

## Where they differ

- **Deadman heartbeat:** Gemini says it does not transfer, because for a spot
  rebalancer a dead witness fails closed, and that is safe. Grok says heartbeats
  must be signed. ChatGPT says only if heartbeat freshness is made a condition of
  executing. My read: Gemini's point holds while every failure refuses, which
  `witness.py` claims and its tests drive.
- **Two-party vote:** ChatGPT and Grok say keep the principle (no unilateral
  class or timing control), not the grid's exact mechanism. Gemini was silent.
- **Verifier independence:** Gemini says stop importing the core's id
  derivation and hash a flat canonical string in the standard library alone.
  `verify_record.py` says on purpose that a reimplemented hash drifts and
  reports false tampering. Both are partly right. An off-host anchor
  (agreement 3) defeats the attack Gemini names whichever hash is used, so it
  comes first.
- **Bind the seal to the exact order** (ChatGPT only): the account, side,
  quantity, order type, plan hash and policy version, with a nonce and expiry,
  used once. Today `order_claims.py` checks that the note describes the order,
  not that the placed order equals the sealed one.
- **The waived gate** (Gemini, as a process blocker): overriding the gate after
  0/7 makes the human the bypass. It asks for either an explicit reframing as a
  paid infrastructure test, accepting total loss of the capped amounts, or a
  pre-committed walk-forward pass first. This is the operator's free will and
  money, recorded here as their view, not mine to decide.

## Ranked, for the operator (cost and the test that proves it)

1. **The witness owns its own terms.** Covenant reads `node_ports`, `node_key`,
   `seal_required` and the caps from ITS OWN file, never from the executor's
   cfg; the executor's cfg can only be stricter. Cost: small, in the seal path
   on both sides. Works: an executor cfg naming another port, an absolute key,
   or `seal_required: false` is refused or ignored. Fake: any of those three
   still changes where or whether the seal happens.
2. **Retire covenant's old armed copy**, so one executor exists. This is the
   10-06 retire step (`docs/SENTINEL_WITNESS.md`). Cost: move
   `seal_decision_result` first, since it has outside callers. Works: one
   scheduled task, one config with `armed`, both verified by listing.
3. **Credentials out of the executor's reach** (gateway or separate OS user)
   **plus an off-host seal anchor.** Cost: real infrastructure. It is also the
   same off-host trust root that `docs/TAKEOVER_RESISTANCE.md` already waits on.
   That step is his.

None of this makes a strategy pass. All three said a safety review cannot
validate an edge, and the standing result is that none has passed.
