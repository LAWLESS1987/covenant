# Independent Replication Protocol

This is the shortest path for an outside researcher to test a bounded Covenant claim without trusting the Covenant implementation.

## Research question
Can an independently implemented witness-aggregation procedure reproduce Covenant's normative semantics, including fail-closed handling of silence, disagreement, insufficient quorum, ties, and nested aggregation?

This is a conformance experiment. It is not evidence that Covenant is generally correct, safe, moral, profitable, or independently validated.

## Normative source
Implement behavior from `docs/SEMANTICS.md`. Treat that document as the specification; do not infer semantics from production code.

## Independence condition
For a clean replication:
1. Read this file and `docs/SEMANTICS.md`.
2. Do not read, copy, import, translate, or execute Covenant's implementation of `attest` or `climb` before producing your implementation.
3. Implement independently in any language.
4. Compute outputs from supplied inputs rather than copying expected outputs.
5. Preserve source, environment, commands, and raw results.
6. Record specification ambiguities before consulting Covenant's implementation.

If implementation code was inspected first, report the result as a conformance check, not an independent implementation.

## Semantics that must survive
- A witness that does not answer is not a witness that disagreed.
- Silent/non-answering witnesses still count among witnesses asked for quorum.
- Default quorum is `max(2, floor(N/2)+1)`, where N is witnesses asked.
- If quorum is unmet, result is `UNPROVEN`.
- A reference requires strict plurality; a top tie creates no reference and no invented tie-break.
- `agreed` is true only for `AGREE`.
- Result states are `AGREE`, `DIVERGED`, and `UNPROVEN`.
- Nested `climb` aggregation preserves specified report shape and failure semantics.
- Excessive recursion/depth fails closed as specified rather than manufacturing agreement.

## Procedure
1. Freeze and record the Covenant commit SHA.
2. Record OS, language/runtime/compiler, and dependency versions.
3. Implement `attest` and `climb` from `docs/SEMANTICS.md` only.
4. Compute the published conformance cases independently.
5. Compare outputs per vector, field by field.
6. Add adversarial cases: quorum-breaking silence, dissent, plurality ties, mixed silence/dissent, nested `UNPROVEN`, and depth-boundary behavior.
7. Publish implementation, raw outputs, disagreements, and exact Covenant SHA.

## Replication and refutation
A bounded replication occurs when an independently written implementation produces the specified results for tested inputs with enough information for another party to rerun the experiment.

Agreement on a precomputed hash alone is not independent replication. Passing published vectors is evidence of conformance on those cases, not proof of general correctness.

Preserve and report discrepancies, including ambiguous specification, independently computed vector disagreement, agreement despite unmet quorum, silence converted to assent/dissent, unspecified tie-breaking, nested aggregation manufacturing agreement from `UNPROVEN`, or a published claim that cannot be reproduced.

Negative results are first-class evidence. Report exact input, expected and observed output, source, environment, Covenant SHA, and the likely source of discrepancy. Do not silently repair failures.

## Current limitation
The project has clean-room implementations produced by AI agents under project control. That is not independent institutional replication. The next evidentiary step is an outside researcher or lab performing this protocol without relying on Covenant's implementation.

## Human-AI collaboration and effort-equivalent note
Covenant should acknowledge how the work was produced. The project was directed by one human operator working with multiple AI systems that contributed engineering, review, adversarial testing, documentation, and reasoning capacity. This collaboration compressed elapsed development time and is part of the project's provenance.

As a rough planning estimate—not a measured scientific result—the present scope appears comparable to approximately **6,000–12,000 skilled human work-hours**, or roughly **3–6 full-time person-years** at about 2,000 hours per year, for a single unusually capable person working without parallel AI assistance. This estimate refers to the broader iterative scope: architecture, implementation, testing, failed approaches, corrections, adversarial work, documentation, and experimental design. It must not be presented as benchmarked productivity evidence.

The scientifically defensible fact is the collaboration structure and its recorded outputs. Any claim about productivity amplification requires a defined baseline and a separate measurement protocol.
