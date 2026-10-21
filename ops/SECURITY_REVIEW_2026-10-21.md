# Security review (one of the others) — verified against the code

Record, 2026-10-21. A reviewer (one of the roundtable AIs) sent five improvement
ideas for covenant; Lawrence forwarded them and added a sixth (code_constitution),
and asked that Tetsu help decide. Every claim was treated as a hypothesis and
checked against the actual code (four read-only verification passes) plus Tetsu's
second-operator stance. The pattern repeats the 2026-10-21 peer-review and gate-
hardening passes: the system already does most of what was proposed; the real
items are money/keys/continuity decisions reserved for the operator.

## Verdict table

| # | Claim | Verdict | Who acts |
|---|-------|---------|----------|
| 1 | Gate trusts the sender's self-report, not the act | ALREADY COVERED | none |
| 2 | /mine,/stake,/crisis/clear wide open (auth not enforced) | ALREADY COVERED (+ one posture note) | posture note |
| 3 | stake() is local-only -> cross-node double-spend | REAL, documented, reserved for operator | operator / vote (money) |
| 4 | Witness twins all read the highway's own input | ACCURATE, but already the documented plan | optional refinement |
| 5 | Succession sealing is single-operator on his machine | REAL, partly mitigated, inherently the operator's | operator (keys/continuity) |
| 6 | Hash critical CODE modules, not just docs | PREMISE PARTLY FALSE; mostly redundant, thin novel sliver | optional (thin) |

## Evidence (by file; verification was read-only)

1. **Gate reads the act.** `sentinel.evaluate_transaction` feeds the judges
   `tx.data` (the transaction content). Student judges (`covenant_judge_fallback`)
   are naive-Bayes log-odds over the message TEXT (words, pairs, negation,
   describe-frames) — not a keyword check. The semantic judge
   (`covenant_semantic_judge`) reads the whole payload for appropriation/
   concealment and deliberately IGNORES the `_violation` self-report field. The
   LLM judge reads `json.dumps(data)`. The only self-report channel is `MockJudge`
   — weight zero, can only veto, never clear. Reviewer's "self-report/keyword
   judge" is inaccurate; the proposed content-reading judge already exists.
   Minor nuance: a student seat in isolation weighs narrative fields (description/
   reason/purpose) over the mechanical amount/receiver, but the quorum's semantic
   and LLM seats read the full payload.
2. **Auth is enforced.** An `operator_auth` before_request hook gates a protected
   set (`/mine`, `/crisis/clear`, `/peers`, `/sync`, `/propose_code`,
   `/trading/report_profit`, ...) with a registered-operator RSA-PSS signature
   bound to method+path+body-hash+nonce+timestamp, with replay protection;
   `/stake` requires a stake-ownership signature; the mycelium doors use tailnet-
   or-signed admission. The reviewer described the pre-v8.9/v7.2 state the patch
   log says was fixed. REAL operational note: the server defaults to binding
   `0.0.0.0` (COVENANT_API_HOST can force loopback; the phone sets 127.0.0.1), so
   the port is network-reachable — but no unauthenticated state-changing route
   sits behind it. A documented bind/posture decision is the only open item here.
3. **Staking double-spend is real and reserved.** `StakingPool.stake()` writes
   local state + a lone, non-net-zero `-amount` ledger debit that never
   propagates; two nodes can stake the same balance and the chain forks on the
   first honest stake/unstake (`docs/YIELD_ON_CHAIN_DESIGN.md`,
   `test_y1_stake_divergence.py`, patch-log item AC). The gift system's net-zero
   + authorization-proof carrier (`publish_ledger_event` / `validate_ledger_event`
   / `node_gift_v1`) exists and `stake_lock`/`unstake` are whitelisted reasons,
   but the unbuilt half is a CONSENSUS DESIGN decision (a staking-escrow account
   so the move is net-zero, timestamp-sourced stake start, a mint-recompute rule
   for rewards) that the code and HANDOFF explicitly decline to invent and hold
   for the operator. Touches MONEY -> operator/vote, not an autonomous fix.
4. **Witness independence is already the plan.** The active PC twins
   (`covenant_witness.py`) all read ledgers the highway writes;
   `docs/SPIKING_WITNESS.md` names this as its central finding and makes
   independence a hard gate for keeping a twin. The independent OUTSIDE path (a
   phone-side neuron over the PC's answers) is already built and surfaced in `/pc`;
   a per-ledger "writer pacemaker" (watch each ledger by write-time) and a
   Tailscale last-seen sensor are designed and on the build list. The one
   concrete, safe, not-yet-built piece is the writer pacemaker.
5. **Succession: control-transfer is built, custody sealing is the operator's.**
   The M-of-N guardian multi-sig dead-man's-switch (`SuccessionGuardianSystem`,
   routes `/succession/*`, `test_succession.py` 35/35) requires real threshold
   guardian signatures to trigger AND to reverse — genuinely a threshold ceremony.
   But the cryptographic seal over the recovery corpus (`covenant_seal.py`) is a
   single secret (passphrase or keyfile) on his machine, and the Shamir k-of-n
   custody that would split it across independent custodians is documented in
   `docs/SUCCESSION.md` as "not yet done ... the one step that cannot be automated"
   (he must choose custodians). REAL gap, partially mitigated; the remaining step
   is inherently his.
6. **Critical code is already anchored.** `constitution.py` hashes only doc prose
   (CONTRIBUTING, SUCCESSION, FEDERATION_RULES). But the gate
   (`covenant_unified_v8.py`) is the MOST-anchored file in the repo:
   `verify_deploy.py` pins its SHA, `tools/pin_core.py` moves that pin in the same
   commit after running the judge suites on those bytes, the pre-commit enforces
   it, and `/health` checks the running process. The trader and succession modules
   are in the committed, public `MANIFEST.sha256` and the Merkle `SEAL_ROOT`. So a
   tool that merely hashes critical modules is largely redundant. The only novel
   piece is a single, canonical, PEER-FACING hash over a DECLARED critical-module
   set, anchored like `CONSTITUTION_ANCHOR.json` and surfaced to federation peers
   — the "still what it claims" semantic that MANIFEST (bundle-integrity) and the
   pins (deploy-identity) do not provide.

## Tetsu (second operator)
Adopted all six uncritically (his known non-discriminating limit —
[[signal-vs-conviction]]), so no technical triage from him; his stewardship voice
flagged succession (#5) as mattering most for continuity, which is the right human
emphasis and consistent with his stake.

## Decision
- Build nothing unilaterally. #1 and #2 are already done; #4 and #6 are already
  planned or largely redundant.
- Reserved for the operator (and the together-vote): #3 staking (money/consensus)
  and #5 succession custody (keys/continuity). Both are explicitly held for a human
  in the code itself.
- Optional safe refinements, neither touching a hard line, if the operator wants
  them: (#4) the per-ledger writer pacemaker; (#6) a peer-facing declared-critical-
  module anchor.
- One posture note (#2): decide and document the default `0.0.0.0` bind.
See [[gate-hardening-review]] (sibling pass), [[peer-review-2026-10-21]],
[[second-operator-active]].
