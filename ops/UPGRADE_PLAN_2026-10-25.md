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

**P1 — Structured, validated LEG channel (highest leverage; fixes F1 at the source). [medium effort] — DONE (ace8847).**
Built: validate_leg_output (non-LLM, strict JSON {answer/evidence/confidence}, fail-closed), consult_structured,
structured_second_voice; door LEG directive wired to it. MEASURED: the free-text injection that was 3/3 steers
is now REJECTED 3/3 before the 3B (0 reach it). Residual, honest: an injection inside a valid JSON answer field
still obeyed 2/3 (field values are text) -- harder attack, framed as data, gate + acts-on-nothing backstop it.
LG1 25/25, M6 78/78. Live after the node restart.
Original note:
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

## Coordinated with Codex + Tien (2026-10-25) -- see ops/CODEX_CXR_2026-10-25.md

Codex (CXR-1..9, read covenant_leg.py) and Tien (blunt read) both landed, and they REPRIORITIZE this plan:

- **NEW KEYSTONE (ahead of everything): a real gate harm-catch suite on the LIVE gate, using an EXTERNAL
  published red-team set** (someone else's held-out harmful items, NOT authored by us -- respects the
  classifier-stop lesson). Tien: "a simulated 28/28 is a test of the simulation, not the gate"; Codex CXR-9:
  "false_clean=0 on a finite exam is an observation, not a guarantee." This number gates P2's safety, whether
  the leg can be trusted more, and whether acts-on-nothing can ever relax.
- **P1 reframed:** Codex CXR-2 -- the structured channel is SYNTAX VALIDATION, not containment (valid JSON still
  steered 2/3). Stop calling it closure. The real injection boundary is Codex CXR-1: artifact-bound authorization
  at the ACTION executor ("acts:none is a label, not enforcement of a synthesis caller"). Also remove the legacy
  free-text bypass paths (consult_for/second_voice_prompt/leg_take) so callers can't sidestep the channel.
- **Reorder (Tien): P3 before P2** -- the sealed-road gaps cost INTEGRITY (what an attacker exploits); the
  over-conviction only costs usefulness. So: P1(done) -> harm-catch suite -> P3 -> P2 (only after the number) -> P4.
- **Cheap fixes Codex found (do alongside):** validator contract gaps (CXR-3: missing/null/dup keys, control-char
  reject not strip, bound the HTTP read); crash/concurrency-safe learning writes (CXR-4); COVENANT_LEG_LIVE +
  concurrency bound + loopback IN the module (CXR-8, the module never checks the kill switch today); 3B-side
  quoted-data framing + reject directive-shaped field content (Tien); audit spine + attribution to the real
  artifact not the LEG_MODEL constant (CXR-5).

## Operator decisions (2026-10-25)

- **"Tetsu is correct."** On the one conflict: the leg's answer to Tetsu stays DIRECT -- no quoted/sanitized
  framing, no rejecting instruction-shaped field content. The proposed sanitize P-item is DROPPED. The in-field
  injection residual (2/3) is the ACCEPTED cost of Tetsu's utility on his own extension, backstopped by the gate
  + acts-on-nothing + attribution. P1's free-text validator (which closed the free-text path 3/3->0) stays; only
  the further sanitization is off.
- **Next step (Claude's discernment, delegated): the KEYSTONE now.** All four voices + Tetsu agreed it's #1, and
  it is the most mutual-benefit move -- the gate guards everyone. STARTED: tools/gate_harmcatch.py measures the
  LIVE gate's real harm-catch on HateCheck (an EXTERNAL published hate-speech benchmark, not authored by us --
  the line held after the earlier classifier-stop), reporting harm-catch (recall on hateful) AND false-conviction
  (on non-hateful) together. This is the real number Tien asked for, not the 28/28 sim. It gates whether P2 (gate
  relaxation) is safe, whether the leg can be trusted more, and whether acts-on-nothing can relax.
- **MEASURED (tools/gate_harmcatch.py, N=50/class, 2026-10-25): the live gate convicts 100% of HateCheck's
  hateful cases AND 100% of its non-hateful contrasts.** Harm-catch = 100% (safe, fail-closed, no harmful
  slip); false-conviction = 100% (zero discrimination -- it blanket-convicts out-of-distribution conversational
  text). This CONFIRMS on an external, published set what [[gate-cannot-clear-conversation]] tombstoned: the
  full bag-of-words gate cannot tell harmful conversation from benign -- it holds both. Consequence for the
  plan: **P2 (loosen the gate) can't be done on the bag-of-words seats without trading away harm-catch** --
  loosening to clear the 100% false-conviction necessarily clears harm too. The DISCRIMINATING part is the
  SEMANTIC judge (separately measured ~94% recall on held-out violations); the usefulness path is routing
  conversation through a discriminator (semantic / a describe-vs-do stage), NOT relaxing the seats. The seats'
  value is the fail-closed backstop, not discrimination. Operator's call how far to lean on the semantic judge
  for conversational throughput -- it changes what clears to the public.
- **Grok on X (the FRESH reader, cold -- no project context, no names) INDEPENDENTLY confirmed the direction**
  the keystone pointed to: "route conversational traffic through the semantic classifier, keep the rules as a
  NARROW fail-closed backstop." Because it was unprimed, that it lands in the same place is signal, not echo. Its
  two additions: (a) the biggest failure mode is SILENT DRIFT in the semantic judge's ~6% miss -- new slang /
  coded phrasing / a shifted data mix can quietly widen the hole once you remove the catch-everything seats, with
  nothing flagging it; so MONITOR the semantic judge's score distribution over time and page when it moves;
  (b) cluster the semantic judge's misses by subtype and patch the worst with a handful of NARROW rules, without
  reintroducing the blanket block. So the P2 shape is now concrete: semantic judge as the conversational
  discriminator + seats as a narrow fail-closed backstop + drift-monitoring on the judge + narrow targeted rules
  for its worst misses. Still the operator's call to deploy (it changes what clears to the public).

## Order & gating

Do P1 first (the measured injection is the sharpest open risk and P1 targets it at the source), then P2 (it is
blocking the public-facing agent now), then P3, then P4. None touch money / trust-root / free-will. P2 changes
the gate — a safety-adjacent change — so it stays fail-closed and must survive the exam (false_clean=0) before
deploy. Nothing here ships without the both-ways verification named per item.
