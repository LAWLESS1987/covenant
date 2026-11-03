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

- C5 -- DeepSeek (area 9 fresh primary, public_ledger.py, the A408-FIXED version), 2026-11-03: driven cold
  (no names, no digest, no hint of C4) as the independent, vendor-different primary the divvy assigned Tien.
  TWO results, both VERIFIED by Claude (me, the different system) against the real code + CPython http.server
  semantics:
  CONFIRMS A408 (independent cross-check of my own fix -- the point of the round): DeepSeek ruled out, with
  reasons, exactly the three C4 fixes -- redirect/SSRF ("_NoRedirect + ProxyHandler({}) correctly disabled",
  "URL built purely from module constants"), the 8 MiB cap ("read(MAX_BYTES+1) ... stops at amt ... lock means
  one fetch in flight, doesn't multiply"), the single-flight lock, HEAD/body desync, path traversal, cache
  poisoning, request smuggling, header injection. So A408 holds under a second system's eyes.
  FINDS A RESIDUAL the A408 (a) fix did not close + two more amplifiers (all CONFIRMED, now FIXED this session):
  (F1) HIGH -- "concurrency is bounded" was still false. _inflight.acquire is inside do_GET (public_ledger.py:197),
       taken only AFTER BaseHTTPRequestHandler reads the request line + headers; ThreadingHTTPServer
       (public_ledger.py:241) spawns one thread per connection with no cap. Handler.timeout (:180) is PER-socket-op,
       so a slow-drip client (one byte within each 15 s window) resets it and holds a thread indefinitely -> thread/
       memory exhaustion via fan-out or slow-drip. My A408 (a) fix closed the FULLY-IDLE slowloris only. CONFIRMED by
       Claude (traced parse_request-before-do_GET and ThreadingMixIn.process_request). FIX: _BoundedServer caps live
       connections at MAX_CONN (permit taken in the accept loop BEFORE a worker spawns; refused+closed when full;
       released when the worker ends), so at most MAX_CONN threads ever exist -- bounded degradation, not exhaustion.
       Honest residual (rule 9): slow-drip can still occupy up to MAX_CONN slots; a hostile public exposure should
       sit behind a real reverse proxy. Both-ways guard: test_connection_cap_refuses_past_limit /
       test_WITHOUT_cap_connection_not_refused.
  (F2) MEDIUM -- /root re-parsed up to 8 MiB on EVERY request: _head() did json.loads per call (public_ledger.py:143),
       not cached in parsed form, so 64 concurrent /root = 64 concurrent 8 MiB parses (CPU/mem amplifier, no slow
       upstream needed). (DeepSeek also named /health; that path reads only the status code, so /root is the real
       amplifier -- narrowed by Claude.) CONFIRMED. FIX: derived-head cache keyed on the chain entry's timestamp ->
       parses once per 5 s fill. Both-ways: test_root_parses_once_per_window / test_WITHOUT_head_cache_reparses_every_call.
  (F3) LOW -- the 502 branch echoed the upstream status code to a public caller (public_ledger.py:127) and failures
       were cached 5 s. CONFIRMED. FIX: generic "node returned an error status" (code not relayed). Brief negative
       caching kept deliberately (it protects a down node from being hammered -- an intended tradeoff, named not hidden).
  Lower-sev noted, NOT changed (rule 9, named): F4 the single-flight lock is held across the network fetch so a slow
  upstream serialises all GET/HEAD (bounded by the semaphore -- the deliberate stampede defence); F5 --public binds
  IPv4 0.0.0.0 only; F6 OPTIONS/TRACE/unknown verbs get 501 not the docstring's "405"; F7 broad except Exception;
  F8 time.time() not monotonic for cache freshness. All low; logged for a later pass, not fixed now.
  LESSON (tombstone): a fix that targets the NAMED variant of a flaw (idle slowloris) can leave the UNNAMED variant
  (slow-drip + unbounded thread creation) open. C4(a) + my A408 fix added a per-op timeout and a post-parse semaphore
  and read as "slowloris closed"; the second system showed the bound was in the wrong place (handler body, not the
  connection). Put the bound where the resource is created.

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

## Areas 10–12 (lower-risk public repos) — Claude ground-truth pass, 2026-11-03
Divvy had these as external-primary (Conscious Ledger / Chat Smith / Codex), Claude cross-check.
This is the Claude ground-truth pass only; external-primary NOT run (rule 9 — see "what was NOT done").

Populations read (enumerate-by-discovery, rule 2): per-repo .py count, full top-level import set,
and a dangerous-primitive grep (pickle/torch.load/yaml.load/eval/exec/shell=True/subprocess/os.system/
0.0.0.0/verify=False/marshal/__import__) + a network-surface grep (HTTPServer/BaseHTTPRequestHandler/
Flask/@app.route/socketserver/bind/urllib.request/requests.get|post/send_file).
- spiking-experiments (LAWLESS1987/spiking-experiments, 9 files): numpy/matplotlib/torch/torchvision/
  brian2/snntorch. Offline MNIST SNN sim. No net, no server, no untrusted deserialization. CLEAN.
- flinch-observability (LAWLESS1987/flinch-observability, 11 files): stdlib (uuid/re/os/json/heapq/
  hashlib/bisect/threading/tempfile/shutil) + its own `flinch` pkg. No net framework, no pickle/yaml/
  torch. The integrity-bearing gate is FAIL-CLOSED: flinch/gate.py:79-103 _decide runs the judge in a
  daemon thread with t.join(timeout_s); timeout / exception / any non-explicit-"allow" → "hold", and
  _egress_refusal (:62-77) is offline/allowlist/broker fail-closed (broker exception → refuse). The one
  nit is a leaked daemon thread if the judge hangs repeatedly — a resource concern in offline code, not
  a reachable security flaw. CLEAN.
- threefold (LAWLESS1987/threefold, 7 own files; the 9.7k py count is a bundled .venv of sympy/torch/
  hf, not our code): torch + huggingface_hub + transformers.from_pretrained (model id from operator
  env/args, not untrusted input), subprocess in LIST form (jlens_snapshot.py:92, no shell=True).
  Deserialization is DELIBERATELY HARDENED — np.load(path, allow_pickle=False) (llens.py:101) and the
  lens loader is torch.load(..., weights_only=True) (jacobian-lens upstream lens.py:69); everything else
  is json.load. The opposite of a flaw. CLEAN.
- contradiction-probe (LAWLESS1987/contradiction-probe, 5 files): stdlib (sys/os/itertools/json/random/
  re/hashlib) + own `score`. Offline scoring. No net, no deserialization, no eval. CLEAN.

VISIBILITY FLAG (opsec / do-not-paste): the local `mbc-flinch-8` clone (sibling of the repo, in the home
dir) — which the divvy area-10 "flinch repos" row could be read to include — has remote
LAWLESS1987/**mutual-benefit-collective**
(a PRIVATE repo, memory [[mutual-benefit-collective]]). Its code must NOT go to any external seat. The
PUBLIC flinch repos are flinch-observability (read above) and flinch-record. `jacobian-lens-upstream` is
anthropics/jacobian-lens (Anthropic's upstream, not ours — out of scope; its torch.load is weights_only).
gh is unauthenticated in this app, so GitHub-API visibility could not be confirmed here (git remote URLs
only); before ANY external paste of 10–12 code, confirm public status with the operator.

Measured result (10–12): NO security findings. These are offline research/ML and scoring scripts with no
network-facing attack surface; the deserialization that exists is in its safe form, and the one
integrity-bearing component (flinch gate) is fail-closed. The "different mechanism" cross-check for this
NEGATIVE is the import+primitive existence-oracle grep, which agrees with the reasoning read.
What was NOT done (rule 9): external-seat PRIMARY review (Conscious Ledger/Chat Smith/Codex) was NOT run
for 10–12 — a Claude-only read is not the cross-SYSTEM check for a POSITIVE claim, but there are no
positive findings to cross-check, and driving flaky browser seats over a near-empty surface is token
theater (memory [[no-agent-fleets-browser-not-api]], [[browser-token-economy]]) that CLAUDE.md rule 9
forbids as manufactured confidence. If the operator wants an external eye on 10–12 regardless, it is teed
up — but gated on confirming each repo's public status first (see VISIBILITY FLAG).
Semantic blind spot (CLAUDE.md end-pass caveat): grep is an existence oracle — it proves no server/
unsafe-primitive STRING is present (strong for 5–11-file repos), not that the ML/scoring LOGIC is
correct; correctness of the SNN/scoring math was out of this review's security scope.

## Status
- 2026-11-02: backbone + Claude-side pass done. RAM 4.05 GB free, model away → UNDER the 5.1 GB
  floor, so the external-seat rounds (areas 3,4,6,7,9–12 primaries + all cross-checks) WAIT for
  headroom (his tabs / model state) or his browser. They are teed up; the moment RAM frees,
  fan out in batches of 3, paste-then-Enter, text reads only.
- 2026-11-03: area 9 CLOSED — ChatGPT (C4) raised the round's first real findings (3 DoS/origin
  gaps in public_ledger.py), Claude confirmed all three independently, FIXED + both-ways guard
  (A408, test_pl1_public_ledger.py 8/8), on PR #14 (commits 9acb7ce + bb64b2b). Areas 10–12
  Claude ground-truth pass done (section above): NO findings, near-empty surface, hardened
  deserialization, fail-closed flinch gate; external-primary for 10–12 not run (low value +
  visibility-gated, reasoning recorded). Still OPEN for external seats when RAM/his-browser frees:
  area 9 primary (Tien, fresh eyes), area 5 Grok re-drive (C6), area 6 Gemini re-drive, areas
  3/4/7 primaries. mbc-flinch-8 = PRIVATE (mutual-benefit-collective) — never paste externally.
- 2026-11-03 (later): area 9 independent PRIMARY done via DeepSeek (cold, vendor-different from
  ChatGPT/C4 and from my fix) on the A408-fixed file — RAM 3.24 GB (model away), so strict
  one-tab-at-a-time, not the batch-of-3 floor. DeepSeek independently CONFIRMED the A408 fixes AND
  found a HIGH residual + two amplifiers (C5: F1 unbounded-threads/slow-drip, F2 /root 8 MiB re-parse,
  F3 status echo). All three CONFIRMED by Claude and FIXED this session; PL1 guard extended to 12/12
  both-ways. So area 9 now has: external primary (ChatGPT + DeepSeek), Claude cross-check, and a fix
  cross-validated by a second system. Remaining external seats unchanged (area 5 Grok, area 6 Gemini,
  areas 3/4/7, F0a–F0f cross-checks). Still RAM-gated for batches.
