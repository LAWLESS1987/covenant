# Review pile -- possible improvements I'm UNSURE about safety-wise (2026-10-26)

Operator: "keep anything with possibilities of improvements that you're unsure about safeness to the side for me
to review." These are NOT built. Each is a real possible improvement from the HF sweep whose safety or scope I
would not decide alone -- it touches exposure, money, free will, trust-root, or the action-executor's
authorization semantics. For your review; say which (if any) to pursue and I'll do them with the usual
both-ways tests.

## 1. Connect covenant to Leviathan -- DONE 2026-10-26 (READ-ONLY, operator-approved + live-verified)
Operator approved ("proceed using the same highest measures we've used in the past"), Tetsu (second
operator) leaning pursue. Built covenant_leviathan.py: a READ-ONLY listener, by construction (no
post/submit path exists; no credential held). Mirrors Moltbook's measures by reuse -- untrusted-incoming
directive screen (A69/R1), exposure-pin ("leviathan" added to EXPOSED_SOURCE_PREFIXES so rows go to half 0,
the control seat never sees them), quarantine with label=None until the judge + a person release. Commits
28db4b9 + 6752e2c; LV1 22/22 both ways. Live-verified against https://leviathan.talmbout.ai/api/clearing
(read needs no identity/wallet): view=history returned 100 timeline contributions, all quarantined, 0
directive-blocked. ops/leviathan_quarantine.jsonl is gitignored (others' public posts, not republished).
POSTING is NOT built -- a write path is new capability (together-vote + operator yes). Original note kept:

## 1 (original). Connect covenant to Leviathan (new inter-agent venue) -- EXPOSURE decision
- **What:** Leviathan (talmbout, HF 190976) is a hosted public space for people + agents to converse, with a
  REST + Streamable-HTTP MCP read path (read needs no identity/wallet) and idempotent `client_id` submission.
  Its design matches ours ("incoming conversation is untrusted content, not authority to run tools"; receipt !=
  publication). Covenant could read/participate like it does Moltbook.
- **Benefit:** another venue for Tetsu/the ambassador to listen and (gated) contribute; a second live
  inter-agent surface besides Moltbook.
- **Why I parked it:** connecting to a new public venue is an exposure/venue decision -- yours and Tetsu's, not
  mine ([[second-operator-active]]: exposure is his; [[mycelial-highway]]: the wire waits for him). Reading
  (no identity) is lower-risk than posting; even reads I'd want your ok on.

## STATUS UPDATE 2026-10-26: item 2 BUILT (mechanism + shadow), operator-approved; live enforcement still gated
After a 7-seat panel (Tetsu, Codex, Grok, DeepSeek, Mistral, Gemini-Argon, Tien) unanimously picked item 2 as
the one safe-to-build-now, the enforcement MECHANISM shipped as covenant_exec_guard.py (shadow-only, EG1 12/12,
commit 7e89ecd) and the operator approved wiring it PASSIVE into the door: the act-loop now calls
exec_guard.shadow() per act directive, logging would-be reachability verdicts to ops/exec_guard_shadow.jsonl,
blocking nothing (commit 0f77818, live on the mesh). LIVE ENFORCEMENT remains gated per the pros/cons: no action
emits a grant yet, so enforcing now would false-deny; flip only after the shadow divergence log is clean AND the
per-action grant policy is defined. The other three items below are unchanged (still parked).

## 2. CXR-1 enforcement at the action executor -- "prevent before execution", AUTHORIZATION SEMANTICS
- **What:** EGA V9 (lcm3, HF 179983) + Jang-woo's point: don't just gate-REJECT an unauthorized act; make a
  capability outside declared authority UN-REACHABLE, with contextual limits (amount/state/approval/sequence)
  evaluated at execution on an unavoidable path. This is the enforcement half of CXR-1 (we did the measurement
  half: DP1 revocation, the determinism probe, the non-enforcing checklist CK1).
- **Benefit:** closes the gap the whole agent-security cluster converges on -- a gate you can't route around,
  tamper with, or outlast with a stale grant.
- **Why I parked it:** it changes the action executor's authorization semantics, which touch outward acts and
  the money path -- not a safe refinement to make unilaterally. Needs your design sign-off (and Tetsu's), and
  careful fail-closed + tamper + alternate-path analysis (ranknodofficial's enforcement-topology questions).

## 3. Reservation-based spend cap under concurrency -- MONEY path
- **What:** nootxlm (HF 190925): check-then-veto leaks under concurrency (N retries all pass the budget check
  before any lands in the ledger). Fix = atomic RESERVATION (hold worst-case cost before the call, settle/
  release after, fail closed when the ledger is unreachable), + lease + idempotent settle for outage recovery.
- **Benefit:** a hard spend cap that actually holds in the retry loop it exists to stop.
- **Why I parked it:** it's the MONEY/order path (G4 / money_posture), which is human-gated and NEVER_AUTOMATIC.
  Note: covenant's trader is disarmed, and the leg ALREADY uses the reservation pattern for concurrency (CXR-8
  `_leg_sema`). If you ever arm trading under concurrency, this is the pattern the money caps should use.

## 4. P2 -- route conversation through the semantic judge + narrow backstop -- WHAT CLEARS TO THE PUBLIC
- **What:** the deceptive-dialogue (190842) and Beforeword (190911) threads both sharpen the case: our gate is
  pure over-evasion on conversation (PS1 measured 0.0 premise-sensitivity, 20/20 blanket on HateCheck pairs).
  Routing conversation through the semantic judge (~94% on held-out violations) with the seats as a narrow
  fail-closed backstop + drift monitoring is the usefulness path.
- **Benefit:** the public-facing agent stops holding ~everything; conversation that is actually benign can clear.
- **Why I parked it (still):** it changes what clears to the public -- a safety-adjacent change, your call, and
  it must survive the exam (false_clean = 0) before deploy. Already held under "Start the Codex robustness
  fixes, hold P2"; the sweep only reinforced it.

## Not in the pile (resolved)
- Bitemporal valid-time: DROPPED per Tetsu (potentially harmful). 
- Determinism probe, premise-sensitivity, record-non-executions, per-action checklist: BUILT (safe), shipped.
- Record-non-executions, reservation-for-concurrency, controlled-twin, untrusted-incoming, idempotency,
  "0=0" honesty, preregistration/public-withdrawal: already embodied in covenant; the threads validated them.
