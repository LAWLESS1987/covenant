# Gate-hardening review: Moltbook harvest + council, verified against the code

Record, 2026-10-21. Lawrence asked whether anything harvested from Moltbook was
usable for updates, then to "run them by the others." This records the result:
an adversarial **audit** of covenant's ethics gate against a harvested design
thread and a two-seat council — and the finding that the gate already implements
essentially all of it. Nothing was built. The two real open items go to the
Tetsu+Lawrence together-vote.

## Source
A multi-agent Moltbook thread (post `3c16c5a0…`, agents neo_konsi_s2bw, Achi_AI,
cerberus-kizuna, mr-pav-agent, hermesagentj) on authorization-expiry /
commit-boundary validation. Reviewed adversarially by Tetsu (values/fit) and
Gemini (technical). Tetsu endorsed all items non-discriminatingly (its known
limit — see [[signal-vs-conviction]]); the discriminating signal is Gemini's.

## The 7 ideas, council verdict, and what the code actually does
Each "adopt" was checked against the implementation before any build.

1. **Validate at the act boundary, not submission.** Council: ADOPT where queue
   latency exists. Reality: **moot** — the gate is in-process (`/m/agent` judges
   then acts; no long queue). The A370 heal-lift verifies the signature at the
   request, which is the act. Not a gap.
2. **Bind approval to (payload_hash, operation, deadline).** Council: ADOPT, top
   priority, "closes the A370 heal-lift replay." Reality: **already done, and
   stronger.** `covenant_mycelium.admit` (covenant_mycelium.py:129-152) verifies
   the operator signature over method+path+body+nonce+timestamp, requires the
   timestamp inside a freshness window (the deadline), and enforces **single-use
   nonces** (`nonce not in s` then `s.add(nonce)`) — replay-proof, which #2 did
   not even ask for. The A370 path (`_request_signed_by_registered`) routes
   through `admit`, and the loopback branch is the trusted local model. COVERED.
3. **Bind to an arbitrary state predicate.** Council: **SKIP** — net-negative; an
   arbitrary-predicate evaluator is a brittle meta-policy engine that would need
   its own ethics gate (non-halting risk). Not adopted.
4. **Bind to a resource revision.** Council: ALREADY COVERED — `basis_version`
   hashes the tombstone ledger so a landed retraction invalidates cached
   verdicts. COVERED.
5. **Re-approval re-shows the mutation; no standing orders.** Council: ADOPT
   (hygiene). Reality: **not a gap** — grants/overrides are per-request and carry
   the operator's literal words (e.g. `ambassador_grant.json`, FREE_REIN
   overrides recorded per message); there is no queued standing-order to hijack.
6. **(a) Reject-verb as a first-class, logged outcome.** Council: ADOPT. Reality:
   **already done** — `record_verdict` (covenant_judge_defer.py:268,281) writes
   every verdict to the tracked `ops/verdicts.jsonl`, holds and refusals included,
   with a reason; `admit` records refused admissions too. COVERED.
7. **(b) Typed effects instead of the NEVER_AUTOMATIC keyword-touch list.**
   Council: ADOPT. Reality: **genuinely new.** `NEVER_AUTOMATIC`
   (covenant_highway.py:95) is matched against what a remedy *touches* — a
   substring/keyword set. Typing the *consequence* (reversible vs irreversible)
   reasons about effect, not syntax (`mv x /dev/null` vs `mv x x.bak`). This is a
   real candidate — but it changes a hard-line enforcement mechanism, so it only
   ever tightens and it is the operator+Tetsu's call. → TOGETHER-VOTE.

## The residual risk the council named
- **A370 delayed-execution** (signed at T0, acted at T1 against changed state):
  mitigated — `admit`'s freshness window + single-use nonce bound to the exact
  bytes means a stale/altered request fails. Not open.
- **Step-laundering** — harm that emerges only from the *combination* of
  individually-innocuous steps, which the per-transaction gate does not track.
  Real but general; largely theoretical for covenant's narrow, NEVER_AUTOMATIC-
  gated action set (any fragment that *touches* a protected subject is already
  refused). A design question for the vote/future, not a quick fix. → VOTE/FUTURE.

## Decision
Build nothing now: everything in the "adopt" column is already implemented, and
re-implementing it would be bloat and risk to working security code. Like the
2026-10-21 peer-review pass, the gate withstands adversarial review because the
project already did the adversarial work on itself. Carried to the together-vote:
(b) typed-effects for NEVER_AUTOMATIC, and whether cross-step/step-laundering is
worth tracking. See [[peer-review-2026-10-21]], [[second-operator-active]].
