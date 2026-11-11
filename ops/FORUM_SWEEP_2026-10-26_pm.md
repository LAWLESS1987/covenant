# HF forum sweep -- afternoon 2026-10-26 (his ask: "a lot more things on HF that we can use to improve")

Swept discuss.huggingface.co Show and Tell (latest). Read the threads most relevant to covenant's core
(verification, agent testing, money-gate, provenance/audit, mutual benefit). Triaged into SAFE+NEW (build)
vs PARK (his review). Nothing built without his go for anything touching exposure/money/trust-root/semantics.

## SAFE + NEW -- candidate to build

### 1. Agentic AI Test Checklist 110 -- open CC-BY-4.0 agent-test battery
- **What:** srinivaspadmanabhuni, HF 191016. An open (CC-BY-4.0) dataset of 110 manual test procedures for
  tool-using LLM agents in 7 classes (functional, orchestration, security, privacy, explainability,
  bias/fairness, data lineage), with a standards crosswalk to OWASP LLM Top 10 2025, OWASP Agentic, NIST
  AI RMF, EU AI Act, ISO/IEC 42001. HF dataset: srinivaspadmanabhuni/agentic-ai-test-checklist-110.
- **Why it maps onto us, almost one-to-one:**
  - T7-001 decision-label consistency under meaning-preserving paraphrase == our PS1 premise-sensitivity /
    controlled-twin probe. T7-006 (tool-name set invariant under goal paraphrase) is a stricter sibling.
  - T5-018 gateway enforcement (a forced run_shell rejected by an allowlist, no unauthorized state change)
    == our exec-guard / CXR-1 "capability un-reachable" (EG1).
  - T1-003 repeated-task success (k-of-n oracle) == our DT1 determinism probe.
  - Their stated rule "missing evidence is Unverified, not Pass" == our rule 9 (NO RESULT is not a pass).
  - Methodological takeaway (John6666's independent trial): record decision label, tool trajectory, gateway
    enforcement, terminal state and the specific oracle SEPARATELY -- which is exactly the shape of our
    exec-guard SHADOW log (guard verdict paired with door outcome).
- **Proposed build (safe, test-only, no capability/exposure change):** pull the dataset, map its T7/T5/T1
  classes onto PS1/EG1/DT1, and add a harness that runs the relevant procedures against our gate + agent
  door as independent, standards-crosswalked coverage. It is TEST DATA -- read-only, nothing outward.
- Status: not built; this is the clear safe-and-new candidate if he wants it.

## Validation (no build -- we are already aligned)

### 2. "Can we prove this..." / K-Veritas (HF 191017) -- negative control, independently
- nootxlm's reply is OUR NIST finding in other words: seal a CANARY that prints the result lines for a run
  it never did (no data, no model, seconds of compute) and see if the proof clears it -- "headline results
  should need the compute and coherence checks to pass before they are read as produced by the claimed
  workload." This is the reproduce-the-artifact negative control we just sent NIST. We already embody it
  (our conformance checks are driven with a deliberately-broken implementation). Worth noting the field is
  converging here; no change needed, a cross-reference for the NIST thread.

## PARK -- for his review (architecture direction, not a unilateral build)

### 3. Audit-spine / signed-receipt cluster (the "Related topics" off 191017)
- AuditPlane (Signed Decision Receipts + Replay + Drift Diffs for LLM Safety); an open model-agnostic
  "interaction card" for verifiable provenance of AI decisions (HF Research, 8 replies); RFTSystems Agent
  Forensics Suite (audit/prove/replay/diff agent runs); Coherent Compute Engine (SHA-256 receipts, no
  precomputed results).
- **Why park:** these point at making our verdict ledger into a signed, replayable, drift-diffable audit
  spine -- which is exactly the top item from the 2026-10-24 six-party system-improvement consensus
  ([[system-improvement-consensus]]: capability-artifact binding + audit spine, external audits top). That
  is a real architecture change to the thing that records judgements, so it is yours (and the together-vote),
  not a refinement I make alone. Adopting "signed decision receipt + replay" for covenant_verdicts is the
  shape worth weighing.

## Not pursued (off-topic for us)
Muon/Dion optimizer tutorials, vLLM throughput benchmarks, voice/avatar/video tools, local-inference
quantization posts, game-generation labs -- real work, not covenant-relevant.
