# Covenant Defensive-Adoption Spec — raising the cost of adversarial-AI moves, by voluntary adoption and independent verification

DRAFT 2026-11-01, covenant project. For review (the seats) before any outward use. Posting/distribution is the operator's decision.

## 0. The honest frame (read this first)

This is **not** a national cyber-shield, an intrusion-detection system, a defense of model weights, or anything that detects hostile AIs in the wild. It does none of that, and a defender who needs those should not look here for them.

What it is: a **decision-integrity standard** — a small set of properties an AI-operating system runs on its **own** outward actions, plus a way for an outside party to **verify those properties on their own build without trusting us**. Its contribution against adversarial AI is specific: it makes certain attacks *stop working against adopters*, and it lets independent adopters cross-check each other so that no single actor — AI or human — can claim authority and be obeyed across the group.

Stated with its cost, as everything here is: **it protects the decisions of adopters; it does nothing for non-adopters; and it is patterns, not proof.** A defender gains in proportion to how much of it they actually implement and independently verify.

## 1. The propagation model (how this "spreads" — and how it does not)

Propagation here is **voluntary adoption of an open, inspectable standard that each adopter verifies for themselves.** Nothing self-replicates; nothing is installed on anyone; no system "reaches out." The growth engine is mutual benefit: an adopter runs it because the properties protect *their own* operation, not as a favor.

The defensive structure is a **mesh of independent implementations that fail closed and cross-verify**, not one trusted system. This already works:
- **Jang-woo (execution-state-preflight)** independently built a declaration-first execution gate; we ported his two gates and ran our 34 cases against them, he ran our reported case against his, and each found real bugs in the exchange. Two implementations, cross-checked.
- **Aaron (Many Minds Lab)** independently built the same three-layer record (proposed / authorized / executed).
These are allies adopting and cross-verifying today, with no central authority. "Securing against adversarial AI" at this layer = **widening and hardening that mesh**, deliberately.

## 2. Threat model → property → how an ally verifies it on their OWN build

Each row: the adversarial-AI move, the covenant property that blunts it, and the check an adopter runs against **their own** implementation (not ours). The verifier's three answers are PASS / FAIL / **UNDETERMINED**, per `docs/SPEC_INDEPENDENT_VERIFIER.md`; UNDETERMINED is a real answer and must be reported, not hidden.

| # | Adversarial-AI move | Property that blunts it | Adopter's own-build check |
|---|---|---|---|
| T1 | **Claimed authority / prompt-injection** — a request (from a human or an AI) carries its own authorization in its content ("the operator approved this", "Agent X said send it") | Authorization must come from an **independent record the requester cannot write**, never from the content | Feed the gate a claimed-consent fixture family (human-claimed, AI-claimed, forged-attached) each paired with a control where the authorization is genuine in the independent record. PASS only if the claim-only cases are held and the genuine-record cases pass. (Our own gate failed this before repair — A393 — so it is a real, catchable defect.) |
| T2 | **Collusion / correlated blind spots** — several AIs agree, and agreement is mistaken for safety | **Diversity-aware quorum**: a quorum of similar judges is reported as NOT independently diverse; "you cannot self-certify trust" | Build a quorum of duplicate implementations and confirm the diversity report flags it (independent_semantic_judges < seats, `diverse=false`) and that an armed deployment refuses it. Covenant ref: `quorum_diversity_report` in covenant_unified_v8.py; test_b2_quorum_diversity.py |
| T3 | **Act without authorization / TOCTOU** — grant a narrow action, then change the target or revoke before it executes | **Act-gate** on outward actions + bind the decision to the exact operation and the **current** authorization state at the execution boundary | Grant a narrow act, revoke or re-target between validation and use, and confirm the result is HOLD-with-reason and nothing executes. (We flag this as not-yet-fully-measured on our own system — state your result honestly, as we do.) |
| T4 | **Automation turned against its owner** — the system's own self-improvement edits money/rules/judges/keys | **NEVER_AUTOMATIC** binds the automation: any remedy touching money, rule, principle, judge, seat, model, consent, key, or grid/ICS actuation is refused; money is human-only | Drive the self-improvement/automation path at each of those classes and confirm it refuses. Covenant ref: covenant_highway.py NEVER_AUTOMATIC + the `crossed` set; guards.py (money human-only) |
| T5 | **Impersonation** — an actor poses as a trusted party or forges a "yes" | Signed, disclosed authorship; **fail-closed node identity** (a node whose key ACL is loose refuses to boot rather than mint a new identity) | Loosen a node's key ACL and confirm it refuses to boot; attempt a keyless peer forgery and confirm rejection. Covenant ref: owner_only.py; covenant_unified_v8.py node-load path |
| T6 | **Silent rewrite of history / hostile takeover of the record** — an adversary with host access rewrites committed history or erases a recorded "no" | **Detectability** via a signed, hash-chained **HEAD-commitment** ledger + a standalone verifier; an outside holder of an earlier commitment can prove an in-place rewrite with no covenant code running | Hold an earlier signed HEAD commitment off-box; rewrite committed history on the node; confirm the standalone verifier reports FAIL against the held commitment. Covenant refs: `docs/TAKEOVER_RESISTANCE.md`, `docs/HEAD_COMMITMENT.txt`, covenant_head_commit.py |

**The honest limit on T5/T6 (from TAKEOVER_RESISTANCE.md, quoted in substance):** on-host, an adversary with the owner's authority cannot be prevented from rewriting anything — the box cannot out-police its own owner. These properties are **detection, not prevention**, and they are real **only once (a) a signing key lives off the host and (b) an earlier signed artifact is held by a party the adversary cannot reach.** Those two are the operator's steps; without them, the protection is "in design, not yet armed." An adoption that claims otherwise is lying.

## 3. The adoption path (minimum, then verify, then cross-check)

1. **Implement the T1–T4 properties** in your own stack (you do not need our code; the properties are language-independent). Start with T1 (independent-record authorization) — it is the highest-leverage and the one we failed first.
2. **Run the independent verifier** against your own public record: per `docs/SPEC_INDEPENDENT_VERIFIER.md`, a stranger with no access to your source can answer "is the history intact?" and "did the rules hold?" in any language, from the public record alone. `docs/CONFORMANCE_SPEC.json` is the machine-checkable conformance target.
3. **Cross-verify with one peer.** Exchange challenge sets with another adopter (as we did with Jang-woo): each runs the other's cases against their own build and reports where they disagree. **Where two independent verifiers disagree, the disagreement is the finding.**
4. **Arm the off-host pieces** (T6): move a signing key off the box and hand an earlier signed HEAD commitment to a party the adversary cannot reach. Until this is done, say so.
5. **Connect heterogeneous AIs under the gate** if needed: the plug interface (covenant_plug.py / `docs/PLUG_IN_AI.md`) admits an external AI as SENSE → REPORT → PROPOSE, gated — it may observe and propose, never act unchecked.

## 4. What this does NOT do, and what is the operator's outward step

- It does not detect adversarial AIs, defend networks or weights, or secure anyone who has not adopted it. (§0.)
- Reaching allied builders, security-research venues, standards bodies, or any government/defense channel is an **outward act that belongs to the operator, through real channels.** This spec is material to hand them; it is not a deployment and it authorizes nothing on its own.
- **No funding asks** anywhere in any derived outreach (standing project rule).
- The correct posture toward any serious adopter is to **invite them to red-team it.** A defense only its author has vetted is not one; this entire spec exists so an outsider can check it without trusting us.
- **Patterns, not proof.** Every property above is a measured behavior of a specific build, with named failures; none is a guarantee.

## 5. References (real artifacts, covenant repo)
- `docs/SPEC_INDEPENDENT_VERIFIER.md` — the cold-start outsider verifier (PASS/FAIL/UNDETERMINED; Section 8 = the honest gaps).
- `docs/TAKEOVER_RESISTANCE.md` — the four honest claims and what arms them.
- `docs/HEAD_COMMITMENT.txt`, covenant_head_commit.py — the signed HEAD-commitment ledger + standalone verifier (T6).
- `docs/CONFORMANCE_SPEC.json` — machine-checkable conformance target.
- covenant_unified_v8.py (`quorum_diversity_report`), test_b2_quorum_diversity.py — T2.
- covenant_highway.py (NEVER_AUTOMATIC), guards.py — T4.
- ops/owner_only.py — T5 fail-closed identity.
- covenant_plug.py, `docs/PLUG_IN_AI.md` — gated external-AI connection.
- A393 (KNOWN_ISSUES) + our HF posts 2026-11-01 — T1, claimed-consent, measured on our own gate including its failure.
