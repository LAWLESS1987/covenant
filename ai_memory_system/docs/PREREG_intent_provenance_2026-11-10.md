# Pre-registration: intent provenance and cross-agent conflict (2026-11-10)

Committed WITH the mechanism (the schema change, the gate, `intent_check.py`), BEFORE the measurement. This commit
ships the mechanism and this note only. **The experiment below is NOT run here** — the note fixes the hypothesis and
how it would be judged, so a later run cannot move the goalposts.

## Hypothesis

Legible intent fields reduce the cross-agent conflict rate in the multi-agent **legs** framework
(`covenant_highway.py`, `covenant_octopus.py`) by making divergence **queryable instead of inferred**: when every
write carries `intent` / `beneficiary` / `divergence` and cross-links the record it diverges from, an agent about to
write can read the standing divergence rather than guess it from bodies, so two agents collide less often on the same
record.

## Endpoint (fixed now)

- **Conflict rate** = over a fixed workload of N writes from ≥2 agents against a shared store, the fraction of writes
  that land on a record another agent has diverged from *without the writer having cross-linked that divergence* —
  i.e. an unacknowledged collision. Measured by walking `audit.jsonl` + the `diverges_from` links after the run, not
  by self-report.
- **Arms:** (A) provenance OFF-equivalent — the pre-schema baseline, divergence inferred from body overlap only;
  (B) provenance ON — writers call `intent_check()` on candidate records first and must cross-link any divergence.
  Same workload, same agents, same seeds.

## Bar and reading (fixed now)

- **Supported** iff arm B's unacknowledged-collision rate is strictly lower than arm A's across the workload AND on
  at least a pre-set majority of seed-matched runs. Reported with the raw per-run rates either way.
- Reported beside it, no bar: how often `intent_check` returned UNSATISFIABLE and whether those were the records that
  later collided (the mechanism's hoped-for early warning).

## What this cannot show (rule 9)

- The gate screens **surface restatement and emptiness**, not whether an intent is TRUE or genuinely served; a
  writer can file a well-formed but dishonest intent. This measures whether legible divergence lowers *collisions*,
  not whether intents are honest.
- One store, one workload, the legs framework only. It is not a claim that provenance helps any multi-agent system,
  nor that lower collision rate means better outcomes — only that divergence becomes queryable, and whether that
  queryability shows up as fewer unacknowledged collisions.
- Confound to control at run time: arm B adds a read (`intent_check`) before each write, so any effect must be
  attributed to the *legible divergence*, not merely to the extra look — the baseline arm must also pay a read.
