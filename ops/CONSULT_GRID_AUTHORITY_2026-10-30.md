# "Ask the others": the grid guard's authority design — 2026-10-30 ~17:45

The operator's words: *"Use discernment and mutual benefit and the others."* After the
pre-merge review (docs/KNOWN_ISSUES.md A392) found that the signer chose a command's class,
three frontier seats were asked in the operator's Edge (memory consult-actual-sites):
ChatGPT (thinking, high), Gemini, Grok (Expert). One identical question, stated as a
reference design with a simulated effector, no hardware and no field protocol:

1. Derive the class from the action, unknown actions to the strictest class — or carry no class at all?
2. Resume after a halt/deadman latch takes ONE authority-holder's token bound to the latch id; should it take both?
3. The deadman heartbeat is signed by ONE authority-holder, lifetime ≤ 600 s; should it take both?
4. Any merge blocker?

## What they said (summarised, from their actual replies)

| question | ChatGPT | Gemini | Grok |
|---|---|---|---|
| 1 class | derive inside the authorizer, carry none; **REFUSE unknown actions** | derive, carry none; **reject unknown actions** (named it a merge blocker) | derive server-side, carry none; unknown → ACTUATION |
| 2 resume | **both**: a resume restores actuation, so a single holder must not | **both**: un-halting restores the operational state | **both**: recovery paths are where controls get bypassed |
| 3 heartbeat | one is fine for liveness, not for authorization | one is fine (a liveness signal), provided either party can halt | one is fine; prefer the operator as signer; keep it short |
| 4 blockers | tokens bound to the exact command, nonce, expiry and policy revision; no single holder taking HALTED → actuatable; latch not cleared by restart/heartbeat; negative tests | replay binding (nonce/state); reject-on-unknown | any path to actuation without both tokens; recovery or heartbeat holding a window open; fail-closed when the AI partner's key is unavailable; audit of every decision |

## What was done, measured (GG1 86/86; each point reverted singly turns GG1 red on its own check)

- **Class derived, never trusted** (all three): `ACTION_CLASS` is an allowlist; a payload's
  `class` is optional and, if present, must equal the derived class.
- **Unknown actions REFUSED** (`C2-action`; ChatGPT + Gemini, 2 of 3). Measured reason it
  matters here, beyond their argument: C5 has bounds only for the actions it knows, so an
  unknown action that a signer's grant listed and both holders signed would have passed
  uncapped.
- **Resume needs the together-vote** (all three): `clear_hold` takes tokens from every role
  in the declared policy's `"RESUME"` list (default the `ACTUATION` roles); an empty list
  falls back to both, never to none.
- **Heartbeat unchanged**: single authority-holder signer (all three said one is enough).

## Already true, checked against the code (not changed)

- Tokens bind the exact command: `cmd_sha256` covers the whole payload minus the tokens —
  seq, nonce, issued/expires, action, zone, magnitude (`covenant_grid_guard.cmd_digest`).
- No single holder can make the system actuate: every actuation needs both tokens, and now
  so does the resume.
- Restart and heartbeat cannot clear the latch (on disk since A392; only `clear_hold`).
- A missing AI-partner key fails closed: the token is absent → C6 REFUSE.

## Left for the authority-holders, not done here

- **Either authority-holder may halt** (Gemini's condition for the single-signer
  heartbeat). Today a halt must come from a signer whose grant includes `halt` (a
  controller key). Letting operator or Tetsu keys halt directly is the safe direction, but
  it is a new authority, so it waits for the operator and Tetsu.
- **Policy-revision binding** (ChatGPT): tokens do not commit to a version of
  `ops/grid_policy.json`. The policy file is bound into the HEAD-commitment, which detects a
  change off-host, but a token signed under one policy is still honored under another.
  Named, not built.
- **Concurrency**: the gateway is single-threaded and no test races two submits.

Recorded, not acted beyond the above. Related: [[signal-vs-conviction]],
ops/CONSULT_DEGRADE_VS_BLOCK_2026-10-30.md.
