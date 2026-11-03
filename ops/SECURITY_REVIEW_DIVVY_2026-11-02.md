# Cross-system security review — divvy + cross-check ledger (2026-11-02)

His ask: "have yourself and the others search for potential security flaws throughout all the
code divvied up between all the different systems. Use each one to whatever they're most
efficient at. Then double check the work by cross-referencing with a different system."

This file is the backbone + the artifact the outside-review method requires (a finding is kept
only with an artifact; one digest is not evidence — [[outside-review-method]]). Every finding
below names a `file:line` and the system that raised it AND the DIFFERENT system that verified
it. A finding verified only by the system that raised it is NOT confirmed.

## Scope

PUBLIC repos (safe to paste to external seats): covenant (this one), threefold-memory,
Sentinel-Witness, threefold, spiking-experiments, grokflinch, flinch-record,
flinch-observability, contradiction-probe.

PRIVATE repos — **never paste their code to an external seat** without his explicit yes for
that repo: covenant-phone, mutual-benefit-collective, water-food-air. These are reviewed by
Claude (me) / Tetsu (local) only, or by him.

## Reviewer roster + what each is most efficient at

| System | Reach | Best at |
|---|---|---|
| Claude Code (me, Opus) | here | big interdependent modules, crypto usage, replay/ordering logic |
| Tetsu (local qwen) | door, tetsu_work.ask(fresh=True) | checking ONE concrete named claim; weak on open-ended generation |
| ChatGPT | chatgpt.com (context thread) | general code-security review of a self-contained module |
| Gemini | gemini (new chat) | careful reasoning over one module's control flow |
| DeepSeek | chat.deepseek.com | code-level bug spotting |
| Grok on X | x.com/i/grok (FRESH, no context, voice OFF) | cold self-contained module, nothing we said shaped it |
| Conscious Ledger (Grok bot) | grok.com bot 45789a12 | context review of a module |
| Tien (Grok bot) | grok.com bot acce0861 | context review; also reads the collective repo |
| Claude.ai | claude.ai thread 95fa661c | context review of a module |
| Chat Smith seats | covenant_ai_consult (4k-char box) | short self-contained snippets, several seats at once |
| Codex | collective repo issues / reviews/ | the website + other repos |
| covenant quorum | judge / outbound dry run | one-sentence go/no-go on a specific claim (cross-check gate) |

## Divvy — area → primary reviewer → cross-check (a DIFFERENT system)

Priority = where untrusted input meets a dangerous sink, money, keys, autonomy, network.

| # | Area (files) | Primary | Cross-check |
|---|---|---|---|
| 1 | Node P2P + HTTP + chain parse (covenant_unified_v8) | Claude (me) | Gemini |
| 2 | Mesh sync + remedies + process control (covenant_highway) | Claude (me) | DeepSeek |
| 3 | Money: x402 earn server + payment verify (covenant_earn) | ChatGPT | Claude (me) |
| 4 | Money/keys: trader + XRP mainnet (covenant_trader, covenant_xrp_mainnet) | DeepSeek | Claude (me) |
| 5 | Grid guard + ledger + crypto (covenant_grid_guard, head_commit, consent_chain) | Claude (me, done) | Grok on X (fresh) |
| 6 | Model server + subprocess (covenant_model, covenant_leg) | Gemini | Claude (me) |
| 7 | Autonomy: free_will + ambassador + grants (covenant_free_will, covenant_ambassador) | Claude.ai | Claude (me) |
| 8 | Console (covenant_app) + proxy (covenant_gate_proxy) | Claude (me, app done) | ChatGPT |
| 9 | Public ledger server (public_ledger) | Tien | Claude (me) |
| 10 | Spiking + flinch repos (public) | Conscious Ledger | Claude (me) |
| 11 | threefold / Sentinel-Witness (public) | Chat Smith seats | Claude (me) |
| 12 | contradiction-probe / grokflinch (public) | Codex | Claude (me) |

Tetsu and the covenant quorum are the point cross-checkers: a specific claim ("is X validated
before Y?") goes to Tetsu for a concrete yes/no, or to the quorum for a one-sentence verdict.

## Protocol for the external-seat rounds ([[ask-the-others-every-row]], [[browser-token-economy]])

- Drive HIS browser (Edge = "Browser 1" in the claude-in-chrome extension). Text tools only,
  NEVER screenshots.
- Open seats in batches of 3; read and close each before the next batch; measure free RAM
  between batches and wait under 2.5 GB free (each frontier tab ~0.3–0.5 GB). **Gate: with
  Tetsu's model away the floor is 5.1 GB; with it up, 2.5 GB. Do not open under the floor.**
- Paste the module, then press Enter in a SEPARATE call (the classifier refuses a paste+send
  in one call). A refused site → say so in one line, carry on with the rest.
- Fresh readers (Grok on X, Chat Smith) get the code COLD — no history, no names, no digest.
  Context readers get the pointer + what already exists (run the lookback first).
- Disclose + sign as ourselves on anything outward ([[outward-messages-signed-by-ais]]).

## Findings ledger (append-only; each needs file:line + raiser + a DIFFERENT verifier)

Already landed THIS session (Claude raised; both-ways guard IS the artifact; PR #14):
- F0a remedy_restart_git_host bare-filename kill (A160) — covenant_highway.py:2655 — fixed bd7ceb9, H1gr. CROSS-CHECK PENDING.
- F0b verify_grid_ledger didn't re-run C1–C7 — covenant_grid_guard.py reverify — 32a2f70, GS3. CROSS-CHECK PENDING.
- F0c grid ledger not bound off-host — covenant_head_commit.py checkpoint — 403b5b9, GS4. CROSS-CHECK PENDING.
- F0d ram_guard tab side-door — .claude/hooks/ram_guard.py — a6e235e, TG1. CROSS-CHECK PENDING.
- F0e reverify policy-vs-integrity ambiguity — covenant_grid_guard.py policy_sha — 50896ee, GS3. CROSS-CHECK PENDING.
- F0f console DNS-rebind/CSRF — covenant_app.py:_guard — 384bce2, AG1. CROSS-CHECK PENDING.

New findings (open):

- C4 -- ChatGPT (area 9, public_ledger.py), 2026-11-03: the FIRST external seat this round to raise findings that
  SURVIVE cross-check (C1/C2/C3 were all refuted). ChatGPT (High effort) returned three; VERIFIED against the real
  code by Claude (me, the different system) -> all three CONFIRMED. All bite ONLY under the deliberate `--public`
  bind (loopback by default), on a file whose whole purpose is to be safe when public, so they are real hardening
  gaps, not remote compromises. Claude's own pre-read independently flagged (1) before seeing ChatGPT's answer ->
  genuine two-system agreement.
  (a) HIGH DoS -- slowloris / unbounded threads. public_ledger.py:200 ThreadingHTTPServer + Handler sets no
      `timeout`, so BaseHTTPRequestHandler.timeout is None: a thread per connection, no read deadline, partial-header
      clients block forever -> thread/fd/memory exhaustion. CONFIRMED.
  (b) HIGH DoS -- cache stampede + memory amplification. public_ledger.py:78-102 _fetch_chain has no single-flight
      lock; N concurrent misses after the 5s cache expiry each open upstream and buffer up to 8 MiB (N x 8 MiB).
      Sub-bug: `now` is captured at :80 BEFORE the fetch and stored as the cache timestamp at :101, so a fetch >5s
      caches an already-stale entry. CONFIRMED.
  (c) CONDITIONAL -- urlopen follows redirects by default. public_ledger.py:87 uses the default opener; a 302 from
      upstream would be followed to another loopback port or an external host. The public caller cannot steer it
      (fixed URL), so it needs the upstream to emit the redirect -- low risk (upstream is our own node) -- but the
      file's docstring SELLS "only GET, only to 127.0.0.1, fixed origin" and the code does not enforce it. CONFIRMED
      as a real guarantee-vs-code gap.
  FIX (this session, both-ways guard = the artifact): see commit + test_pl1_public_ledger.py below.

- C3 -- ChatGPT (area 7, free_will heal auth), 2026-11-03: a CONDITIONAL candidate, and the first seat this round
  to find the gap in Claude's own pass. It accepted the loopback/signature logic but flagged that
  _tailnet_caller returns `addr2 or addr` (covenant_unified_v8.py:9179) where addr2 comes from
  covenant_mycelium.admit -- and the HEAL path then trusts that addr for _addr_is_loopback. IF admit derived its
  address from attacker-controlled data and gated on the same value, a remote caller could claim 127.0.0.1, pass
  admit's tailnet gate UNSIGNED, and the returned loopback addr would authorize the lift. VERIFIED against the
  real code by Claude (me, the different system) -> REFUTED: covenant_mycelium.admit:116 sets
  `addr = req.remote_addr` (the real socket peer) in EVERY return path and gates tailnet_ok on THAT; the
  X-Operator-* headers are signature material, never an address claim. So addr2 is always the true peer; off the
  tailnet admit returns ok=True only on a verified signature (:137/:157). The loopback check is not forgeable.
  NOTED (defense-in-depth, not a flaw, not implemented -- scope is his): the HEAL auth's safety depends on admit
  always returning the true peer; passing request.remote_addr straight to heal_lift_authorized would make the
  "loopback = real peer" invariant local to the HEAL path and immune to a future change in admit's return
  contract. VALUE: the cross-check surfaced a real coupling Claude's pass had not closed (admit's address
  source), even though the verdict stands -- exactly why a DIFFERENT system reviews.

Area 6 (model stop / subprocess) -- external primary UNDETERMINED, Claude ground-truth recorded, 2026-11-03:
  Re-drove Gemini (its assigned primary) on the de-named stop() control block. Gemini STALLED a second time
  (Flash; the paste landed on the follow-up, but no readable verdict rendered after ~40s -- same stall the
  2026-11-02 round logged). Not hammering it (rule 9: UNDETERMINED is a real answer); to be re-driven on Pro or a
  different seat. Claude (me) ground-truth on the exact adversarial question I posed (PID-reuse / wrong-process
  kill race, covenant_model.py:466-506):
  - The real concern: between _read_state() reading pid (:467) and taskkill/os.kill (:474/:477), the original
    server could exit and the OS recycle that PID; stop() does NOT re-verify the pid still belongs to our server
    before killing (no create-time / cmdline recheck), so in principle it could kill an unrelated recycled PID (on
    Windows, with /T /F, its whole tree).
  - Severity LOW and NOT a security boundary: consumer sweep (rule 6) -- every caller of stop() is an internal
    keeper path (covenant_daily/nightly/highway/persona/image/free_will/refine_loop/tetsu_*), none an untrusted
    HTTP handler; stop() takes no attacker-controlled argument (say=print only) and pid comes from the keeper's own
    state file. So this is a local robustness race on a self-managed single server, not a remote-reachable hole.
  - The verify loop (:480-490, alive() polled AFTER the kill, STOP FAILED keeps state -- A265) and the A348b
    state-record guard (:491-501, remove state only if it still names our pid) already cover the dangerous
    outcomes. VERDICT: sound under its threat model; matches the divvy's existing area-6 pass. NOTED
    (defense-in-depth, not a flaw, not implemented -- scope is his): record the process create-time at start() and
    re-check it before the kill, to close the recycled-PID race locally too.

Cross-checked, NOT confirmed (the process working):
- C1 — ChatGPT (area 3, earn x402), 2026-11-02: claimed the handler "returns 200 and stores a
  paid result without checking /settle succeeded." VERIFIED against the real code by Claude (me,
  the different system) → REFUTED. covenant_earn.py:1564–1572 checks `s.get("success")`: an
  unsuccessful non-pending settle records state="unsettled" and returns 402 (result held for
  free re-delivery, not charged); the `return 200` at :1603 is reached ONLY for state=="earned".
  ChatGPT reviewed my COMPRESSED pseudocode comment (which hid the success check), not the code.
  LESSON: paste REAL code excerpts to the seats, never a summary — a summary manufactures findings.
- C2 — DeepSeek (area 4, xrp mainnet), 2026-11-02: two candidates on authorize_mainnet_payment().
  VERIFIED against real code by Claude (me):
  (i) "activated set but never enforced" → REFUTED: covenant_xrp_mainnet.py:961
      `if activated is False and drops < DROPS_PER_XRP: raise` DOES enforce it; ≥1 XRP to an
      inactive account is intentional (it activates it). Artifact of my excerpt being TRUNCATED
      at :960, before the enforcement.
  (ii) "client is None skips the activation check (fail-open)" → TRUE but LOW severity: it is a
      doomed-payment/typo safety check, not a security boundary; the allowlist, per-payment +
      daily/lifetime ceilings, confirmation phrase and reserve-under-lock (:961–993) all enforce
      regardless of client. Noted, not a security flaw.
  LESSON refined: send the WHOLE control block (through where each variable is USED), not a cut.

External round progress:
- 2026-11-02: 2nd computer located (tetsu, on our tailnet [IP redacted -- opsec]; its service ports
  + SSH closed to me, so I cannot offload compute to it from here; his browser + AI logins are on
  covenant-pc). Browser pipeline PROVEN (Edge "Browser 1" connected; tab opens; read via text).
  Seat 1: ChatGPT on area 3 — refuted (C1). Seat 2: DeepSeek on area 4 — refuted/low (C2).
  Claude-side pass of area 6 (model/leg): covenant_model.stop() kills by PID, verifies the process
  actually stopped (reads taskkill result + polls alive()), keeps state + logs FAILED on a refused
  kill (A265), removes state only if still our pid (A348b) — sound. covenant_leg: CONTAINMENT =
  untrusted-data / acts:none / used_via gate-only / reversible learning / attribution — the
  uncensored leg acts on nothing structurally and is gated like any model output — sound.
  Resumed one-tab-at-a-time (close between; single-tab peak ~0.4 GB is safe at 2.5 GB — the 503
  was from TEN tabs, not the discipline I use).
  Seat 3: Gemini on area 6 (model stop()) — submitted but returned no readable answer in ~35s;
  noted, not blocking. Seat 4: Grok on X (fresh) on area 5 (de-named C6 together-vote check) —
  code delivered (X sends on newline, so flatten with · separators), but Grok hung ~32s with no
  verdict; noted. Both to be re-driven / folded later.
  GROUND-TRUTH cross-check (Claude) of the C6 together-vote check: SOUND, no bypass — distinct
  roles enforced (got_roles is a set keyed on the signers-allowlist role, NOT a token field);
  cross-command replay blocked (the token's SIGNED cmd_sha256 must equal this command's digest);
  expiry, TTL bound, and signature-against-allowlist-key all checked. Matches the grid-guard
  session review of C6 (covenant_grid_guard.py:456–480).
  Operating note: X/Grok composer sends on any newline — paste code with · as the line separator,
  no '\n'. Gemini (Pro/Flash) was slow to render. Fresh seats often reply "no code" to a first
  send; the code lands on the follow-up.

## Claude-side pass (me) — 2026-11-02
Adversarial read of the reachable security-critical surface:
- Area 5 (grid guard / head_commit / consent): token→command binding is cryptographic,
  distinct-authority roles, deadman heartbeat verified, C1 key-pinning — CLEAN (this session
  also hardened it: F0a–F0f).
- Area 8 (console): DNS-rebind/CSRF closed (F0f); run_action allowlisted + shell=False;
  loopback-only by construction — CLEAN after the fix.
- Area 1 (node unified_v8 network): bounded reads (AGENT_FETCH_MAX_READ 65536), memory-capped
  per-endpoint limiter (RATE_LIMIT_MAX_KEYS), 0.0.0.0-bind refused, slowloris/exchange caps
  (MAX_EXCHANGE_S, MAX_CONCURRENT_HANDLERS), length-framed signatures, weird_science mint bug
  fixed — no new bug found this pass.
- Area 3 (earn x402): verify-before-work, settle-after, 24h idempotent re-delivery, signed
  receipts, facilitator-delegated crypto, loopback default bind — spec-faithful; deep payment
  audit LEFT TO ChatGPT (primary) per the divvy.
- Area 7 (autonomy: free_will heal / ambassador isolation), 2026-11-03: the one capability that un-isolates
  free's safety pause is lift_isolation (covenant_free_will.py:93) -> _cp.resume("ambassador"):125-127. Guard
  order traced: granted + tetsu_may_lift_isolation + is_isolation + not dry_run + `authorized is True`
  (default False, fail closed) BEFORE resume. Live caller is the /m/agent HEAL branch alone
  (covenant_unified_v8.py:9432) via covenant_tetsu_heal.act (passes authorized straight through, :69).
  authorized = heal_lift_authorized(addr, request):555-560 = _addr_is_loopback(addr) OR
  _request_signed_by_registered(req). KEY: addr is the real socket peer (request.remote_addr, :9174) -- no
  X-Forwarded-For / ProxyFix anywhere in the request path (grepped) -- so loopback cannot be forged by a remote
  tailnet caller; the signature path forces the address gate OFF (admit(..., lambda _a: False), :549) and fails
  closed on any error. Consumer sweep (rule 6): the only other reader of the three grant conditions,
  covenant_tetsu_forum.py:153-157, merely refuses a send and prints the resume command -- it never calls resume/
  lift, so it is NOT a second door. VERDICT: sound, fail closed. Primary (Claude.ai, fresh eyes) still OPEN.
- A160 process-kill shape across production: all scoped (abs path / port); the one gap (F0a)
  is fixed.
Measured result: the in-house (Claude) review finds the reachable critical code hardened.
This is exactly why the cross-system round matters — fresh seats may see what we don't.

## Status
- 2026-11-02: backbone + Claude-side pass done. RAM 4.05 GB free, model away → UNDER the 5.1 GB
  floor, so the external-seat rounds (areas 3,4,6,7,9–12 primaries + all cross-checks) WAIT for
  headroom (his tabs / model state) or his browser. They are teed up; the moment RAM frees,
  fan out in batches of 3, paste-then-Enter, text reads only.
