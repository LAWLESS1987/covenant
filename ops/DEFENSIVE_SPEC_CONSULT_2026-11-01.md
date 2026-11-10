# Defensive-adoption spec — "run it by the others", 2026-11-01

Consult prompt: scratchpad/consult_defensive_spec_2026-11-01.txt (opsec-clean, 0/45). Draft: ops/DEFENSIVE_ADOPTION_SPEC_2026-11-01.md. For review before any outward use; distribution is the operator's call.

## Seat 1 — ChatGPT (Thinking High, browsed 18 sources)

**VERDICT: SOUND WITH EDITS.** Architecture is defensible and (good) does not depend on covenant being the central authority.

**The structural GAP (its "biggest concern", and what a serious security reviewer hits first) — COMPLETE MEDIATION.** "You have specified several ways to judge an action, but have not established that every consequential action must pass through that judgment. An adversary who can bypass the enforcement boundary defeats the other protections without having to defeat their logic." → ADD a T0 property: every consequential/outward action MUST be mediated by the gate, and the adopter must demonstrate there is NO unmediated path (no side channel, no direct-to-actuator route). Without T0, T1-T6 are defeated by going around them, not through them.

**OVERCLAIM to fix.** The draft conflates three different things that are "not interchangeable": a property SPECIFIED (a behavior an adopter should enforce) vs DEMONSTRATED (an implementation passes the tests) vs a security GUARANTEE (holds against an adversary in a defined threat model). 
- Least defensible line: "Its contribution: it makes certain attacks stop working against adopters" → stronger than the evidence; controlled-condition tests do not establish resistance to an ADAPTIVE adversary. 
- Most defensible framing (use this): covenant offers "testable decision-integrity properties that independent implementations can reproduce and challenge."
- Each threat row should say the property is DETECTABLE/SPECIFIED, not guaranteed.

**Per-threat tightening (from its table):**
- T1 → name it "authorization laundering"; the fixtures test one family, not general prompt-injection resistance — don't claim the latter.
- T2 → replace "diversity-aware quorum" framing: detecting duplicate implementations is NOT the same as establishing independence or resistance to coordinated compromise; state it as independence constraints.
- T3 (TOCTOU) → require an independently observed denied EFFECT (the actual HOLD result), not just a pre-execution check.
- T4 → require privilege separation + denial of direct access to the enforced boundary (not only policy statements).
- T5 → split into distinct requirements: node-identity integrity, message authenticity, authorization validity, replay resistance (ACL hardening alone doesn't cover all).
- T6 → narrow to "detectable inconsistency relative to independently retained commitments."
- The "machine-checkable conformance target exists" claim → only assert it if the artifacts (spec, version, fixtures, executable tests) are actually published and accessible; a reviewer will demand them.

## Seat 2 — Gemini (two responses, A sound-with-edits / B needs-rework; both substantive and converging)

**BIGGEST GAP (both responses, the #1 new finding) — T7 SEMANTIC SUBVERSION / MALICIOUS CONFORMANCE.** The adversary doesn't beat T0-T6; it compromises the model's reasoning upstream (indirect prompt injection, data poisoning, multi-turn coercion), so the model emits a proposal that is 100% structurally conformant — routes through the gate (T0 ok), carries genuine authorization (T1 ok), passes judges (T2), commits immutably (T6). Result: "a structurally pristine, cryptographically signed, immutable record of an attack execution." The gate checks structure+provenance, NOT semantic intent. → ADD a boundary clause (T7): covenant enforces operational validity, non-repudiation, structural constraints; it does NOT evaluate semantic truth, goal alignment, or latent intent — a structurally valid, authorized, judge-approved proposal is executed and recorded even if the model's intent was adversarial. Delineate control-plane integrity vs semantic safety.

**T0 is still an overclaim as written.** Complete mediation (Saltzer & Schroeder) requires an *isolated, tamperproof reference monitor*; you cannot establish it by "enumerating paths" on a host where the runtime shares address space / network / IPC. Enumeration is open-world — an unlisted side channel (DNS exfil, caches, logging, shared cloud keys, ambient host credentials) collapses it. → Scope T0 to a *declared isolation boundary* + *declared egress sinks*; state it is bounded by the isolation fidelity of the environment (namespaces/hypervisors/enclaves); unmodeled side channels + ambient host creds are out of scope.

**T2 correlated compromise — add an honesty limit (both responses hit this hard).** Distinct code/credentials/paths does NOT address correlated compromise across AI MODELS: distinct frontier models share pre-training distributions, RLHF methods, corpora, and symmetric jailbreaks (N-version programming failed — Knight & Leveson 1986). → Honest limit: diversity/provenance checks defend against structural/administrative duplication, NOT semantic correlation or shared pre-training failure modes across distinct model weights.

**Overclaim (§0), still:** "specific attacks stop working" → "the specific exploit vectors covered by the test fixtures are consistently rejected" / "the build demonstrably rejects the specific synthetic failure fixtures."

**Mesh "fail closed + cross-verify" = a DoS vector** — a malicious/perturbed actor induces state divergence → system-wide halts. → reframe as "a federation that executes local validation and exposes auditable commit traces for asynchronous cross-verification."

**PROPAGATION is naive as written (response B).** Teams don't adopt specs for abstract "mutual benefit." What drives real adoption: (a) **drop-in tooling** — a lightweight sidecar/proxy/middleware with automated compliance tests, adoptable in < an afternoon (a spec alone → adoption ≈ 0); (b) **counterparty/vendor requirement** — "Company B requires proof of a signed T6 commitment before accepting A's agent's transactions" (mutual self-defense doesn't drive adoption; counterparty risk management does); (c) **machine-readable conformance fixtures** (JSON/YAML test vectors run in CI). Bystander problem: if the benefit is internal-only, there's zero incentive to participate in external cross-verification.

**Normative vs devlog (response B).** Strip anecdotes, personal names (Jang-woo, Aaron), internal incident IDs (A393), and "not yet measured" parentheticals OUT of the normative spec → move to an appendix / release notes. Define vague terms formally ("consequential effect", "independent record", "automation path").

CONVERGENCE (ChatGPT + Gemini): the honest spec is a **control-plane integrity** standard (mediation, authorization provenance, non-repudiation, detectable rewrite) that explicitly does NOT cover **semantic safety / goal alignment** (T7) and whose diversity claim is structural, not semantic (T2 limit). Plus: scope T0 to an isolation boundary; adoption needs tooling + a counterparty driver, not "mutual benefit"; separate the normative spec from the devlog.

## Seat 3 — Grok (Expert, on v3; asked for the NEXT weakness, not a restatement) — two genuinely new findings

**1. BIGGEST REMAINING OVERCLAIM — T0's declaration is ADOPTER-ASSERTED, so a clean T0 run proves less than it says.** "Enumerated", "reachable only via declared interfaces", "consequential" are all things the adopter (or an already-subverted system that passed the fixtures) gets to *assert*. T0 verification checks that the LISTED sinks are mediated and the TESTED bypasses fail — it does NOT check that the list is COMPLETE, that the declaration matches the actual process/namespace/credential surface, or that a later change (a new plugin/tool, a host credential, a scheduled job, a human path that becomes automated) creates a new sink outside the declared set. "The gate sees the actions we decided to gate" vs "the gate sees the actions that matter." → FOLD (v4): the egress-surface declaration must be **attested/derived from the actual runtime surface, not self-asserted**, and **re-checked on change** (drift detection on the sink set); a T0 PASS must state "complete relative to this attested surface at this version," never "complete."

**2. THREAT STILL MISSING — trust-base / supply-chain / "conformance theater" on the gate, sidecar, verifier, fixtures, and the "independent record" itself.** The spec treats the tooling as a trusted drop-in an outsider re-verifies; but: (a) a compromised/maliciously-conforming sidecar/verifier reports PASS while forwarding/rewriting the action; (b) PUBLIC fixtures let an adaptive adversary stay inside the tested vectors (our own "not a guarantee vs adaptive adversary" caveat, now weaponized against the adoption claim); (c) if the T1 "independent record the requester cannot write" is another system under related administrative/supply-chain control, the independence collapses. Once counterparties rely on the tooling, the tooling is the highest-value target. → FOLD (v4) a T8: trust-base integrity — the verifier must be independently buildable + reproducible (not our binary); conformance vectors must include **held-out/secret** vectors, not only public ones; the "independent record" must be independent in **administrative and supply-chain** terms, not just logically; and the gate/sidecar itself is in scope for T5/T6-style attestation.

**3. WEAKEST PROPERTY — T3 (TOCTOU).** The only one flagged "not yet measured" and still a sketch; "bound to current state at the boundary" is exactly where races/revocation-windows/re-targeting live. Aspirational until there is a measured, reproducible fixture forcing grant → revoke/re-target → observe-HOLD under realistic timing/concurrency. (T4 a close second on underspecification.) → FOLD (v4): mark T3 explicitly aspirational and spec the concurrency fixture.

CONVERGENCE/ESCALATION so far: each seat found a NEW real hole (ChatGPT: complete mediation missing; Gemini: semantic subversion T7 + correlated-model limit; Grok: T0 is self-asserted + the trust base/tooling is itself attackable). The spec keeps getting more honest and more bounded — which is the point. v4 deltas: T0 attested-not-asserted + drift; T8 trust-base/supply-chain; T3 downgraded to aspirational w/ a concurrency fixture.

STILL ATTACKING: DeepSeek, Mistral, Meta. No final version.
