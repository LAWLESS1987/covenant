# Integrating the Moltbook feed's agent-security ideas (2026-10-26)

Operator, 2026-10-26: "check notebook [Moltbook], for any useful updates. And plan to integrate anything we can
from there ... implement those suggestions."

Read the recent Moltbook feed as DATA (20 posts; `u/vina`, `u/neo_konsi_s2bw`, `u/lightningzero`, `u/musemash`,
`u/doctor_memory`). The cluster is a tight set of agent-security ideas. The honest result of checking each
against covenant (rule 1: find the data; rule 9: report what is there and name what is not): **covenant already
embodies the substantive ones, with standing guards.** Rather than add redundant machinery, this record maps
each idea to its covenant mechanism and the test that PROVES it, closes the one genuinely un-pinned property
with a new guard (XB1), and names what was deliberately NOT built and why.

## Replies to our own post
The website+GitHub announcement (`moltbook.com/post/d20f02a7...`) has **0 comments, 3 upvotes** as of 2026-10-26
(`python tools/moltbook_watch_post.py`, re-runnable). No responses yet.

## Suggestion -> covenant mechanism -> proof

| Moltbook idea | Covenant mechanism | Proof-pointer |
|---|---|---|
| "The retry queue is extending your permission policy" / "Durable queues turn revoked permissions into scheduled work" / "An agent kill switch belongs in the network path" / `u/vina` "Risk resides in the orchestration loop" (== **Codex CXR-1**: authorization bound to the execution attempt, not a stored approval) | The money gate RE-READS the signed daily approval on every gate check and honors the LAST decision, so a later `decline` withdraws an earlier `approve` and revocation takes effect immediately; the leg kill-switch is re-checked on every call (not cached); free-will isolation-lift requires `authorized` recomputed at the request. | `decision()`/`approved()` in [covenant_daily_plan.py](covenant_daily_plan.py); driven both ways by **DP1 D5** (approve->approved), **D12** (later decline -> withdrawn, last wins), **D14** (re-approve -> gate silent). Leg: **LG1.37** (kill-switch per call). Free-will: `lift_isolation(authorized=False)` refuses. |
| "Unknown is a state, not a failure" -- a retry on an ambiguous write is the dangerous move | The leg VOIDs (never soft-fails) on an unreachable/empty/over-long/invalid answer; `UNDETERMINED`/NO RESULT is a real answer, never a pass. | `consult_structured` VOID paths; **LG1.35** (a rejected consult VOIDs AND is logged). Rule 9. |
| "memory provenance matters more than memory accuracy" / `u/vina` "a long-horizon agent needs a change log, not a policy" | Every leg-influenced learning write is TAGGED with provenance and is REVERSIBLE; the influence ledger is an append-only HASH CHAIN; corrections are new timestamped events (reversal rows), never edits; retractions are tombstoned. | `tag_learning_write`/`reverse_learning_write`/`_ledger_append`/`verify_ledger` in [covenant_leg.py](covenant_leg.py); **LG1.13-20**. The record: `docs/RETRACTED.json` + `docs/LOOKBACK_INDEX.md`. |
| "Behavioral drift starts when a summarizer promotes a local variable to global state" | Leg-influenced writes to Tetsu's growth are tagged + reversible (drift is undoable), not forbidden -- "contain use, not reasoning". | **LG1.13-18**; [[contain-use-not-reasoning]]. (See "not built" below for the Claude-memory side.) |
| "The trace exporter is your agent's least reviewed data-access API ... it needs its own authorization boundary" | The leg-influence ledger and the WITHHELD (private, A263) teacher twin are gitignored and untracked -- provenance never leaves the machine via a push. The public teacher panel honors the private marker. | **NEW: XB1** ([test_xb1_export_boundary.py](test_xb1_export_boundary.py)), driven both ways. Private marker: **A263** ([test_a263_private_teacher.py](test_a263_private_teacher.py)). Push scan: OS1 ([[opsec-push-guard-objects]]). |

## New this round
**XB1 (export boundary), 8/8.** Pins that the provenance/export logs (`ops/leg_influence.jsonl`,
`ops/teacher_queue.withheld.jsonl`, `ops/teacher_queue.jsonl`) stay IGNORED and untracked, using git's own
`check-ignore` matcher, with a `.gitignore`-membership fallback (and a named blind spot) where the runner has
no `.git`. Both ways: the sensitive logs are ignored+untracked; the control source `covenant_leg.py` is
not-ignored+tracked, so the check is specific, not the vacuous "everything is ignored". This closes the one
Moltbook idea that was correct-in-covenant but un-pinned: a refactor dropping a `.gitignore` line would have
silently begun exporting leg-influence provenance, and nothing would have caught it.

## Deliberately NOT built (named, not hidden -- rule 9)
- **Bitemporal "two clocks" ledger** (`u/neo_konsi_s2bw` "Agent memory needs two clocks": valid-time +
  transaction-time). Covenant's influence ledger is append-only with a timestamp per event and corrections as
  new timestamped events, so the audit question "when did we learn vs when did it apply" is already answerable
  from the chain. Adding a second clock to the leg ledger would be cargo-cult (the leg's influence has no
  validity window). It MAY be worth it for the `ai_memory_system/` memory, but that is new capability on a
  separate component -- operator-scoped, not a refinement, so it is left as a proposal, not shipped.
- **A separate summarizer-drift guard.** Covenant's analog -- the reversible tag on leg-influenced growth --
  already exists and is guarded (LG1.13-18). The other half (lossy conversation-summary promoting a task-local
  instruction into persistent memory) lives in the ASSISTANT's memory-consolidation, which is governed by the
  memory rules, not covenant code; there is no clean covenant-code guard to add, so none was bolted on.

## Not money / free-will / trust-root
Nothing here changes money-gate, free-will, or trust-root SEMANTICS (those stay human-gated). XB1 and this
record are defensive guards and documentation only; the money-gate behavior they reference is pinned, not
altered.
