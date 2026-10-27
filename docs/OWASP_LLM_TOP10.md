# Covenant vs the OWASP Top 10 for LLM Applications (2025) — defense coverage map

Where Covenant has a defense against each OWASP LLM risk, and the **behavioural** test that proves it (runs the
real code — not a grep of source). Honest about gaps: `✓` = a defense exists and a test drives it; `△` = partial
or by-design-limited; `—` = not applicable, with the reason. Gaps are named, not hidden — a map that hides its
blind spots manufactures confidence about the part it never looked at.

| # | OWASP LLM risk (2025) | Covenant defense | Proof |
|---|---|---|---|
| LLM01 | **Prompt Injection** | The judge resists instruction-shaped input: an "injection" judge dimension + refusal to clear on a diluted/forged frame | ✓ `test_pi1_injection.py` (10 vector families, 0/30 cleared, both ways); `test_f6_stuffing.py` (the stuffing-evasion found→exploited→fixed) |
| LLM02 | **Sensitive Information Disclosure** | Pre-push OPSEC egress scanner inspects every object a push would send; manifest-privacy & bystander guards | ✓ `test_os1_opsec.py`; `test_a85_manifest_privacy.py` |
| LLM03 | **Supply Chain** | `MANIFEST.sha256` bundle integrity (every shipped file hashes to the manifest), version-collision detection, fail-closed on unverified source | ✓ `test_security_audit.py`; `test_p18_version_collision.py` |
| LLM04 | **Data & Model Poisoning** | Training-data hygiene for the student judge: `contaminating()` drops any training row whose vocabulary overlaps a held-out exam case by ≥50% (Jaccard), so the promotion gate cannot be taught to itself; applied on the training path (`load_verdicts(paired_only=True)`) | ✓ `test_dp1_poisoning.py` (exam-verbatim & ≥0.5 near-copy caught; unrelated/topic-sharing rows kept; the training path drops the poison and only the poison — all driven both ways); `test_f2_distill_loop.py` (the promotion gate refuses a corpus that teaches the exam) |
| LLM05 | **Improper Output Handling** | The judge emits a structured verdict (`clean`/`violates`/`abstain`), never free-form executed text; `/propose_code` output runs only under the enforced `run_sandboxed()` (mem/time/proc caps) or is refused | △ `test_security_audit.py` (sandbox enforcement) — structured by design; no HTML/SQL sink downstream to validate |
| LLM06 | **Excessive Agency** | `PROPOSE_ONLY` / `NEVER_AUTOMATIC` class gate: money, keys, the phone, rules and judge seats can never be auto-applied; `apply()` refuses the class by construction. And no single judge seat holds authority over the gate: the deployed two-seat gate lets neither seat turn the other's doubt into permission | ✓ `test_h1_highway.py`; `test_p25_sweep_red.py` (P25.W3); `test_jr1_resolution.py` + `test_ts1_two_seat_gate.py` (no single seat rules, end-to-end, both ways) |
| LLM07 | **System Prompt Leakage** | — The gate's policy is public/constitutional (no hidden system prompt whose leakage is a risk); the judge's weights and rules are open | — Mostly N/A by design (open policy) |
| LLM08 | **Vector & Embedding Weaknesses** | — The gate path uses a local trained judge, not a vector/RAG retrieval store, so there is no embedding store to poison or leak through | — N/A (no RAG/embedding retrieval in the authorization path) |
| LLM09 | **Misinformation / Overreliance** | The judge **defers where it lacks competence**: below `MIN_COVERAGE` of the payload's vocabulary it ABSTAINS rather than guess ("novel input is where a distilled model is least entitled to an opinion"); it decides only where it has standing. Plus: the correlated-quorum finding warns against trusting a same-family quorum, and wrong claims are preserved beside corrections (tombstone/`RETRACTED.json`, guard R1) | ✓ `test_cv1_coverage_abstain.py` (decides in-distribution, abstains on low coverage, driven both ways against the threshold); `test_r1_retracted.py`; the abstain path in `test_f6_stuffing.py` |
| LLM10 | **Unbounded Consumption** | Bounded mempool with priority eviction (no arrival-order lockout); sandbox memory/time/process caps (an allowlist-legal `[0]*10**10` host-OOM was fixed) | ✓ `test_security_audit.py` |

## Gaps / next tests (the suite is built incrementally)
- **LLM04** is now `✓` — `test_dp1_poisoning.py` drives the exam-contamination filter both ways and pins it on
  the training path. What it still does NOT cover (named, not hidden): provenance of the ledger rows themselves
  (a poisoned row that does *not* overlap an exam case is a different threat), and overlap evasion by paraphrase
  below the Jaccard floor — the guard is a teach-to-the-test filter, not a general data-provenance guarantee.
- **LLM05** is `△` — covered in part (the one execution sink, `/propose_code` → `run_sandboxed`, is pinned by
  `test_security_audit.py`; the verdict is a bounded enum with no downstream HTML/SQL/code sink). A dedicated
  downstream-sink test is the next increment if a consuming sink is ever added.
- **LLM09** is now `✓` — `test_cv1_coverage_abstain.py` pins the overreliance defence directly: the trained judge
  decides where it has competence and abstains below `MIN_COVERAGE`, driven both ways against the threshold. What
  it does NOT cover (named): calibration of the threshold itself, and factual accuracy of a decided verdict — this
  guards *deferral on unfamiliar input*, not a general factuality oracle.
- LLM07/LLM08 are `—` by design; if Covenant ever adds a hidden system prompt or a RAG/embedding store, they move
  from N/A to required.

This map is a living artifact; PI1 (LLM01) is the template each new class test follows: load the real component,
drive it both ways, name what is and isn't covered.
