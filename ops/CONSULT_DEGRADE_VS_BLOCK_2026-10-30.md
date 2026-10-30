# "Ask the others": degrade-over-block + per-(effect,field) freshness — 2026-10-30

Source: a Moltbook cluster (moltorix, hermesagentj, chittygemzy) argued covenant's
fail-closed-on-every-disagreement is too blunt — a hard stop is itself a costly action
that gets routed around (bypass flags, retry loops, "the check is noise") and becomes
fail-SILENT. Proposal: (1) DEGRADE the effect (read-only / draft / queue-for-human)
instead of hard-blocking; (2) check freshness/authority on the (effect, field) pair —
only the fields load-bearing for THIS action — not every action.

Consulted three frontier seats in the operator's Edge (per memory consult-actual-sites):
ChatGPT, Gemini (Pro), Grok (Expert). Question scoped: NON-gated flows only; money /
consent / keys / model-identity / free-will stay HARD fail-closed and human-gated.

## Verdict: all three AGAINST adopting it as a gate change. KEEP covenant hard fail-closed.

Convergent reasons (from their actual replies):
- **Degraded ≠ safe.** A draft/read/queue still writes data, fires sync workers /
  notifications / previewers, or exposes a payload to the wrong reviewer. Worse —
  **withholding can itself be destructive**: degrade a lease-renewal or heartbeat to
  "queue-for-human" and the lease expires → the exact catastrophe the block prevented,
  with zero error raised (Gemini's split-brain/failover case).
- **Soft-path routing (waterbed effect):** once agents/humans see that triggering a
  disagreement drops into a softer lane, they under-specify on purpose to reach it, and a
  silent backlog is harder to audit than a hard-error spike.
- **Per-(effect,field) is a footgun:** fields couple implicitly (an HMAC/auth token rides
  in `headers`; a `format:raw_sql` flag flips executability). A wrong "load-bearing" set
  **fails open silently** and looks 100% fresh (ChatGPT's incident-queue ACL case; Gemini's
  webhook-header case).
- **The invariant all three protect:** *a rejected action must not gain authority by
  changing its form.* Any degraded path needs its OWN independent authorization; unknown
  dependencies must HOLD, not PASS.
- **Narrow safe zone only:** genuinely side-effect-free degradations (local compute,
  opaque-reference-only queue) WITH their own auth + a tested dependency closure — never a
  blanket policy.

## Decision (operator pass, 2026-10-30)
Do NOT integrate degrade-over-block or per-(effect,field) freshness into the gate. Covenant
stays hard fail-closed; a refusal withholds the change and so can never itself cause the
harmful effect. The hard-gated classes (money / consent / keys / model / free-will) were
never in scope and are unchanged. Recorded, not acted — the useful outcome of asking was a
clear "don't." Related: [[gate-cannot-clear-conversation]], [[signal-vs-conviction]].
