# Assembly + recursive-security pass — findings

Combined the project's modules into one runnable system, re-ran the suites in a
clean sandbox, then found and **fixed** a real propagation defect. Method:
empirical — observed by running, not inferred. Findings continue the project's
letter convention (last recorded was AU).

## Verified green (after the fix)
- Core + all bridges import (`COVENANT_VERSION = v8.9-merged`).
- `test_security_audit.py` **127/127**, `test_adversarial_suite.py` **21/21**,
  `test_e2e_gift.py` **11/11**, `test_xrp_signer.py` **22/22**,
  `test_xrp_mainnet.py` **69/69**, `quant/test_backtest_guardrails.py` **16/16**
  (266 checks total — matches HANDOFF).
- `probe_final_pass.py` **0 findings**; `sim_order_independence.py` all invariants held.
- `test_multinode_live.py` **21/21, four consecutive runs** (was 19/21).
- `preflight.py` 0 blocking.

## Finding AV (HIGH) — real-time push relay was a dead end on any pull path — **FIXED**

**Symptom.** `test_multinode_live.py` was a deterministic 19/21: a block mined on
A reached direct peer B but not the 2-hop node C in real time; C converged only
via the periodic bootstrap pull.

**Root cause, traced with a 3-process line A–B–C and debug instrumentation.** The
push relay itself is sound — `_fetch_announced` and the `BLOCK_PROPAGATE` accept
path both re-announce onward, so with startup bootstrap settled the chain
propagates A→B→C in ~2s. The failure was a **race**: `test_multinode_live` mines
*immediately*, while nodes are still inside their startup-bootstrap window. When
a block is applied via the bootstrap / gap-fill path (`_apply_fetched_blocks`),
that path **never re-announced it onward** — so whenever the pull path won the
race against the announce/fetch push (recorded as a `block_rejected_persist`
anomaly on the losing fetch, an `sqlite` IntegrityError at `save_block`), the
block reached the node and stopped. The relay to the far side died.

**Fix (`covenant_unified_v8.py`, `_apply_fetched_blocks`).** Every block this
path applies is now re-announced onward — the same address-event
(`announce_block`) the other two accept paths already emit — excluding the peer
it was pulled from. Loop-safe by the same argument the other paths rely on:
`_accept_block_common` admits a given height at most once, and an announced block
a peer already holds is inhibited (no fetch, no forward), so the flood dies where
it lands. `bootstrap_chain` now threads the source peer id through so the pull
source is excluded from the re-announce.

**Verification.** `test_multinode_live.py` now passes 21/21 across four
consecutive runs, with "block RELAYED to C" and three-way tip agreement holding
every time — C reaches the new height in ~2s by push, not by the bootstrap
interval. Full adversarial regression (security 127, adversarial 21, e2e 11, xrp
91, probe 0-findings, order-independence) re-run after the change: **no
regression.** This satisfies the project's own rule that a propagation-layer
change gets its own adversarial pass, not just a green regression run.

## Finding AW (LOW) — height-only propagation assertions hide push failure
The multi-node test asserts propagation by polling *height*, which the bootstrap
pull also satisfies, so a total push-relay failure could still pass the
direct-peer check and only surface at the 2-hop node. The AV fix makes this moot
in practice, but any future propagation assertion should pin the *mechanism*
(received via push before a bootstrap cycle elapses), not just the resulting
height. Not fixed in code — noted for the next test-hardening pass.

## Semantic gate (the "semantic improvements" ask)
Everything ran under `COVENANT_INSECURE_MOCK_JUDGE=1` (keyword matching —
adversarial transactions pass it). The real semantic quorum
(`build_semantic_quorum` / `QuorumJudge`) needs a provider API key and was not
exercised. Before gating real value on ethics judgment: set `ANTHROPIC_API_KEY`
(ideally a second provider too, for genuine reasoning diversity — the QuorumJudge
docstring is explicit that two mock judges are the same logic under different
labels, i.e. label diversity, not reasoning diversity).

## Housekeeping
- `COVENANT_VERSION` is `v8.9-merged` while HANDOFF/MANIFEST say v8.18 — the
  constant was not bumped. Cosmetic, but preflight prints it.
- `run_all_tests.sh` references helper suites not present in the current project
  export (`verify_*`, `test_ethics_judge`, `test_golden_ratio`,
  `test_judge_individuality`, `test_multi_provider_quorum`, `test_v86_*`,
  `test_path_pattern`, `test_succession_seal`, `verify_tx_aer`). It skips them
  cleanly; the total-check count reads low until they are re-added.
