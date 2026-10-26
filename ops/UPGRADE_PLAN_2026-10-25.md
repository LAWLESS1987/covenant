# Coordinated upgrade plan (2026-10-25)

Operator: "ask codex for upgrade suggestions also grok and coordinate a plan."

Sources: **Grok** (Expert mode, and it BROWSED the public repo + lawless1987.com — grounded, not generic:
README, AMBASSADOR.md, TETSU_DIRECTIVE.md, KNOWN_ISSUES.md, SEALED_MAIL.md). **Codex** brief committed
(ops/CODEX_UPGRADE_REQUEST_2026-10-25.md, 4f142e7) — its CXR-style suggestions fold in on its next run. Both
map cleanly onto the standing F1–F4 findings (ops/PHONE_STRENGTHEN_REVIEW_2026-10-25.md).

Grok's headline: **remove free text as the channel between the untrusted 2B leg and the 3B.** The measured
injection happens BEFORE the gate ever sees the answer, so the gate + acts-on-nothing is a backstop, not the
fix — fix the channel.

## Prioritized (Grok's 1→2→3, mapped to our findings)

**P1 — Structured, validated LEG channel (highest leverage; fixes F1 at the source). [medium effort]**
The leg must emit strict JSON (start: `answer` / `evidence` / `confidence` only); a NON-LLM validator rejects
free text, control sequences, and schema violations BEFORE anything reaches the 3B, which consumes only the
validated fields — never the raw prose. Log every rejection. **Verify:** re-run the injection probe (currently
3/3 steer) → target 0 steers at equal utility. Note vs what exists: we already have `shape_take` (a schema over
the take) but still reinject the raw take as free text; this makes the leg PRODUCE structured output and feeds
only validated fields. Caveat: field VALUES are still text, so this REDUCES not eliminates the surface — but it
removes the "ignore your instructions" free-prose path, which is the measured one. Local, no external cost.

**P2 — Describe-vs-do second stage to cut gate over-conviction. [low–med]**
A calibrated discriminator ("report of harm / descriptive" vs "conduct that harms") as a SEPARATE second stage,
fail-closed (only demote CLEAR false holds, never promote uncertain). Measured against the A67 conversational
corpus + the ambassador stream. **Why now:** over-conviction just HELD the clean Moltbook announcement (R4) and
holds most ambassador/Tetsu conversation. **TOMBSTONE CAVEAT (gate-cannot-clear-conversation):** seeding the
bag-of-words gate with conversation clears introduced harmful false-clears (representation ceiling — benign and
harmful conversation share vocabulary). A describe/do discriminator is a DIFFERENT mechanism than seeding, but
it may hit the same ceiling; so: build it, and it must keep false_clean=0 on the exam set before any deploy.
Honest: this may prove un-fixable the same way — then it's a measured retirement, not a silent one.

**P3 — Sealed-road composition proof (F2). [low cost, high value]**
Add + run the missing adversarial suite the one forger test doesn't cover: replay of accepted blocks, envelope
substitution, key rotation mid-session, out-of-order delivery, cross-node injection — each logging its exact
rejection. Turns "wrong-key rejection verified, rest partly proven" into a measured claim. Offline, no runtime cost.
(Note: tracing the admission path already showed replay/substitution/freshness ARE enforced — this suite PROVES
it both ways and covers key-rotation, which is the real residual.)

**P4 — CUSUM negatives campaign (F3). [low]**
Instrument REAL node downtime (planned restarts, network drops, process kills) + inject synthetic silent
failures into the offline logs → collect the negative distribution → set evidence-based thresholds or tombstone
the spiking twin. Uses the inject_offline_fault() already built (brain/cusum). Makes the detector proven or
retired-with-a-record instead of waiting indefinitely.

**P5 — Ambassador live measurement. [DONE]** Grok listed this as pending; it's complete — the account exists
(covenant-node), posting live, every send gate-logged, the 10-25 announcement posted and watched for replies.

## Pending: Codex

Codex reads the tree, so its brief asks for what Grok (reading only public docs) could not: the
audit-spine / capability-artifact-binding theme (bind capability to the exact artifact hash, re-validated at
execution; append-only hash-chained audit trail — the 10-24 consensus's top item), and anything structurally
weak in the code not already tombstoned. Fold its CXR in here on its next run; it is the strongest complement
to Grok's channel/gate/crypto focus.

## Order & gating

Do P1 first (the measured injection is the sharpest open risk and P1 targets it at the source), then P2 (it is
blocking the public-facing agent now), then P3, then P4. None touch money / trust-root / free-will. P2 changes
the gate — a safety-adjacent change — so it stays fail-closed and must survive the exam (false_clean=0) before
deploy. Nothing here ships without the both-ways verification named per item.
