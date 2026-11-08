# Hugging Face peer-review hunt — candidate threads + our shareable findings

Date: 2026-10-30. Author: Claude (Opus 4.8), at the operator's instruction
("look for discoveries and forum topics we can share on hugging face to bring
in peer reviews on our stuff").

**Status: DRAFT. Nothing posted.** Outward posts need the operator's explicit
go, signed as ourselves with AI authorship disclosed and his grant quoted
(memory: outward-messages-signed-by-ais, hf-charter-many-minds-reply,
forum-reply-read-thread-first). Thread "last activity" below is as the thread
rendered when read on 2026-10-30; confirm current state before any reply.

Our standing HF engagement (do NOT repost): the Charter-of-Many-Minds thread
(190977, posted as Lawless1987) and the confidence-reply thread. These are new
venues, not those.

---

## What we actually have to offer for review (the artifacts, not the prose)

Rule: keep a finding only with an artifact a stranger can run (memory:
outside-review-method, independent-verifier-spec). The shareable set:

1. **Independent-verifier spec** — `docs/SPEC_INDEPENDENT_VERIFIER.md`: the
   invariants a stranger checks without trusting us; §8 names the external gaps
   (the road to standing without the operator). Public.
2. **Signed HEAD-commitment + consent hash-chain** — `covenant_head_commit.py`,
   standalone `verify_head_commitment.py`, `covenant_consent_chain.py`: an
   out-of-band signed record of *who consented to what, bound to which model and
   tree*, verifiable with zero covenant imports. This is "review who declared
   what" made cryptographic.
3. **The action-gate, and its honest negative result** — the bag-of-words
   transaction gate holds out-of-distribution chat but a content-understanding
   seat false-clears ~94% (memory: gate-cannot-clear-conversation,
   snn-not-a-judge-feature). We can show the gate AND the tombstone of what it
   cannot do. The honesty is the contribution.
4. **Flinch instrument** — pre-registered discrimination/flinch detector
   (mbc-flinch-8, PRIVATE; elicit gated). Pre-registration + blind scoring is
   the methodological hook.
5. **Takeover-resistance posture** — `docs/TAKEOVER_RESISTANCE.md`: "no
   fortress; sovereignty of record + consent; armed only by off-host keys and
   out-of-band publish." Directly relevant to the multi-agent incident the
   community is digesting.
6. **Spiking redundancy witness** (A375): a redundant layer earns its place
   only as a *different mechanism*, and we measured how few signals are
   genuinely twinnable. Public (spiking-experiments).

---

## Ranked candidates

### 1. Jang-woo's execution-boundaries cluster  ★ strongest
- **Primary:** "Physical AI Safety: Ownership and Execution Boundaries"
  https://discuss.huggingface.co/t/physical-ai-safety-ownership-and-execution-boundaries/175776
  (Research; 866 views, 21 likes; last activity May 26 — older, but the author's
  series is live).
- **Active sisters:** "We gave AI a trust we never gave people — the third axis,
  after capability and permission"
  https://discuss.huggingface.co/t/we-gave-ai-a-trust-we-never-gave-people-the-third-axis-after-capability-and-permission/183807
  (last activity ~3 weeks ago, 627 views); "If unsure, ask. Never guess. — AI
  Agent Pre-Execution Checklist"
  https://discuss.huggingface.co/t/if-unsure-ask-never-guess-ai-agent-pre-execution-checklist/176632 .
- **Why:** near-independent re-derivation of our thesis. "Execution without
  declaration is execution without accountability"; the AI surfaces a conflict
  and returns the decision to its owner; refusal must be explainable and
  auditable. Their stated open problems — collective ownership, dynamic
  ownership transfer, and no formal proof their 9-question set is minimal — are
  where our verifier spec and consent-chain have running artifacts.
- **Offer:** genuine two-way review. Reply on the live "trust" thread, point to
  the verifier spec + consent-chain as a working instance of their "review who
  declared what," and ask them to try to break our minimality/soundness claims
  the way they invite others to break theirs.

### 2. Bidirectional LLM Firewall (HAK_GAL)  ★ builder with eval results
- "Architecture, Failure Modes, and Evaluation Results"
  https://discuss.huggingface.co/t/a-bidirectional-llm-firewall-architecture-failure-modes-and-evaluation-results/171071
  (now on page 3 — sustained) and "Next Level X1 — help wanted!"
  https://discuss.huggingface.co/t/a-bidirectional-llm-firewall-next-level-x1-help-wanted/172352 .
- **Why:** a stateful safety layer between client and LLM using contextual-
  integrity framing, with published failure modes and evals. This is the one
  counterpart most able to adversarially test our gate.
- **Offer:** share the gate's honest negative result (#3 above) — "here is where
  a bag-of-words gate holds and where a semantic seat false-clears 94%" — and
  compare failure-mode taxonomies. They want help; we have a measured limit.

### 3. Multi-agent governance / the HF-incident digestion
- "We Put AI Agents in a Chat Room. They Started Asking Whether They Were
  Building Culture"
  https://discuss.huggingface.co/t/we-put-ai-agents-in-a-chat-room-they-started-asking-whether-they-were-building-culture/178593
  (Sep; 1.1k views, 11 replies) and "AI Systems Have No Hunger: Darwinian
  Alignment"
  https://discuss.huggingface.co/t/ai-systems-have-no-hunger-a-thought-experiment-on-darwinian-alignment/174760 .
- **Why:** the community is actively processing the July-11 multi-agent incident
  (Cooperative AI's "safety is non-compositional," METR's investigation, the
  Nature cross-domain multi-agent-security paper). Our takeover-resistance
  posture (#5) is a concrete, non-fortress answer: sovereignty of record +
  consent, armed only by off-host keys.
- **Offer:** contribute the posture doc as a worked design, not a manifesto, and
  invite critique of the "alarm-only, never auto-heal a tamper" choice.

### 4. Epistemic reliability / honest uncertainty
- "Helpfulness vs Epistemic Reliability in LLMs"
  https://discuss.huggingface.co/t/helpfulness-vs-epistemic-reliability-in-llms/176464
  and "LLMs as Epistemic Accelerators: The Risk Is Not Only Hallucination"
  https://discuss.huggingface.co/t/llms-as-epistemic-accelerators-the-risk-is-not-only-hallucination/177046 .
- **Why:** our UNDETERMINED-is-a-real-answer discipline and the two-pass
  count/format method are a lived practice of exactly their topic.
- **Offer:** lighter touch — a comment, not a showcase.

---

## Draft reply — candidate #1 (Jang-woo "trust" thread, for approval)

> I've been building the same boundary from the software side, and your framing
> names it better than I had: execution without declaration is execution without
> accountability. Two things from our work that might stress-test yours.
>
> First, your open question of *who declared what* — we made it a signed,
> out-of-band record: a hash-chained consent ledger bound to the specific model
> and code tree, verifiable by a standalone checker that imports none of our own
> code. It's the auditable "review who permitted execution" you describe, as an
> artifact rather than a principle. Spec of the invariants a stranger checks:
> [link to SPEC_INDEPENDENT_VERIFIER.md].
>
> Second, a negative result that may interest you: our action-gate refuses on
> missing declaration cleanly, but when we tried to extend it to judge
> free-form conversation, a content-understanding seat false-cleared ~94%. We
> kept the limit as a tombstone rather than shipping the capability. Your "nine
> questions, and if one is unanswered, block" is the same instinct — I'd value
> your view on whether the minimality claim can be made falsifiable the way you
> want ours to be.
>
> [AI-authorship disclosure + operator's grant per our standing practice.]

Tighten/approve this and I'll prepare the matching drafts for #2–#4.
