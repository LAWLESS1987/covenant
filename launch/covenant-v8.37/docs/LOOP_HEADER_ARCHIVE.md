# Archived loop-header prose — moved 2026-08-24, nothing lost

The STALL WATCH banner at the top of `claude/IMPROVEMENT_LOG.md` exists to
answer one question that rule 6 asks: **how many consecutive runs have closed
nothing?** By 2026-08-23 it had accreted nine runs of narrative and cost about
sixty lines that every future run reads before it can start — while saying
nothing that §4 (the backlog) and §5 (the run log) did not already hold in
fuller form.

So the prose below was **moved here verbatim** and the banner reduced to its
function. This is a shrink of the loop's read-imprint, not a deletion: every
sentence that was in the banner is in this file, byte for byte, and each of the
runs it describes has a complete §5 entry and a struck-through §4 item.
See M36.

If a future run needs the narrative of runs from 2026-08-22 12:30 through
2026-08-23 08:30, it is here. If it needs the *facts*, §4 and §5 are the
record and are more complete.

---

> **STALL WATCH (rule 6): 0 consecutive runs with no close.** The 2026-08-23
> ~08:30 run built **C5** — the Android on-device privacy/security layer L
> asked for in the trigger prompt (a local `VpnService` DNS firewall in Kotlin
> with a real governance seam). The finding that matters beyond the app: the
> **Android SDK, Gradle and both Maven repos are reachable from this sandbox**,
> so it was COMPILED, not described — 89 JVM tests, a debug APK, an R8 release
> APK, lint 0 errors, signed and `apksigner verify`d, twice from a cold cache.
> Three real defects fell out of writing the tests, all in code that read
> correctly: a suffix walk that never reached the apex (every wildcard blocklist
> entry inert beyond one level), an audit log that **truncated itself on
> reopen**, and a rotation that left `verify()` permanently red. → **M35**, and
> a correction to `claude/ANDROID_VPN_SYNC.md` §3 that matters for **C3**:
> **Android runs exactly ONE VpnService at a time**, so the phone cannot hold
> Tailscale (the covenant-node sync path) and a filtering VPN simultaneously.
> The 2026-08-23
> ~07:45 run closed **P8** and **P10** and instrumented **P7** — one problem
> under three numbers: *a sweep cannot tell you anything until it is quiet.* On
> Windows the suite showed four failing lines, three of them permanent and
> correct behaviour being asserted as if it were wrong. It now shows **one**,
> and that one (P9, the NTFS key ACL) is real and is L's to decide. → **M34**.
> The ~07:00 run closed **A22** (L: *"stay vigilant for bad actors"*, then went to
> rest): `/mycelium` — the last sensory stream with no internal consumer — now
> reaches the watchdog, which alerts on an unexpected peer, on every link at the
> conductance floor, on a chain that shortens, and on a silent restart. The same
> pass audited the peer-input surface A20/A21 had added **ninety minutes
> earlier** and found two defects in it, one of which was this loop reproducing,
> in its own new code, the exact tonic-signal failure it had fixed one layer up
> the same night (→ **M33**). It also corrected a comment in the node source
> that **denied a security control it was sitting on top of**. The ~06:40
> attended run closed **A20 + A21** on L's instruction *"broadcast"* —
> the transmitting half of the antenna. Every peer reply now carries `v` and
> `src`; a bounded digest rides the 120 s heartbeat and **nothing else** (the
> 156-byte block announce is untouched); surviving alerts can be pushed off the
> machine. Backwards compatibility is **measured against a real pre-A20
> process, both directions** (M32), and the digest's contents are asserted
> against the bytes captured off the wire. The ~06:15 attended run closed
> **P12** on L's instruction to "act as an antenna,
> looking for substrate messages above and below": the node now senses the
> machine under it (WARNING ONLY — the boundary is asserted over the AST and
> mutation-tested), and the watchdog transmits change instead of state after a
> measurement showed 12 h of `watchdog.log` was **3,808 lines carrying 16
> distinct messages**. See `claude/SENSING_ACROSS_LAYERS.md`. The ~03:10
> attended run closed **P11**: until v8.31 the node could not say which
> source it was running — `COVENANT_VERSION` read `"v8.9-merged"` and was
> referenced nowhere, the boot banner hard-coded `v7.0` on a v8.30 file, and
> `/health` carried no version at all. It also pulled twelve files off the PC
> that no run had logged. **Read `claude/RUNNING_VS_DEPLOYED.md` before
> reasoning about what is live**, and note the new standing check: the watchdog
> now compares each node's loaded-source hash against the file on disk every
> round, so "shipped but never restarted" is an ALERT rather than a silence.
> The 14:20
> attended run fixed the daily check (it had reported nothing since 08-20 on the
> strength of a superseded network measurement), added a second-venue price
> check, corrected DAILY_CHECK.md sections 2/3/6, rewrote the morning scheduled
> task to RUN `pc/daily.py` instead of re-deriving it, disabled the duplicate
> trend alert, and APPLIED `TRIGGER_PROMPT_PROPOSED.md` (DE2 narrowed:
> `update_trigger` works in an attended session). The 12:30
> attended run closed D3, D4, C1 and W1, and the "blocked on L's uploads"
> premise with them: the files were reachable over the device bridge all
> along in an L-STARTED session. D5/D6 are unblocked now too
> (`MY_STRATEGY.md` and `REAL_DATA_FINDINGS.md` are in the project).
> Still L's: A10, the A12 consolidation, A16 (Option A recommended), B4.
> Still hardware: C3/C4 (the phone).
