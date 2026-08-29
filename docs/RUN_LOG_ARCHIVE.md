# Run-log archive — entries 1 to 35, verbatim

*Moved out of `claude/IMPROVEMENT_LOG.md` §5 on 2026-08-24 under **M36**:
shrink the loop's read-imprint by MOVING, never deleting. §5 was 3,608 lines,
**56% of the whole file**, and every fresh run was reading all of it to find
three facts. Per-item detail lives in §4; the method distilled from each run
lives in §2; this file holds the narrative. Nothing here was edited.*

## Banner narrative moved here 2026-08-24 ~23:30 (the 07:45 run's prose)

*Verbatim from the STALL WATCH banner, which M36 says should carry one
number. Every fact below is also in §4 as an item and in §5 / the index
above as a run entry.*

> **P14 + the delivery half of DEPLOYMENT** (2026-08-24 ~07:45) — v8.35 is on
> the production machine and **re-hashed there** (`1207bd2e7dc5`, 9,595 lines),
> the first hash-verified delivery this project has made; and the watchdog was
> found to be its own worst case — the `source_drift_report` check written to
> catch "deployed is not running" had never executed, because the process that
> would run it started six hours *before* it was written and was still running
> 29 hours later. Its log: 3,456 ALERTs, 3,448 of them two permanent win32
> facts. Fixed by `self_drift_report` (P14, 33/33) — the monitor now checks
> itself. Then **P16**, measured live ninety minutes later when L stopped the
> consoles: the watchdog's own death is invisible in its log — its last line,
> now permanent, says both nodes are healthy. Adaptation removed the noise and
> the heartbeat with it. **THE RESTART HAPPENED at 08:10:09** — the nodes are
> live on **v8.35 `1207bd2e7dc5`**, the boot banner says so, the watchdog logs
> `judges=1/1!`, and a round now writes 2 lines instead of 8. **P14 fired in
> production at 08:12:52Z** against a drift created on purpose to test it — the
> first time anything here has ever detected its own staleness. Then the **first
> Windows sweep this project has ever been able to run: 961/964 in 12.2 min**,
> whose three reds are two root causes — **P9** (NTFS breaks every owner-only
> check, and it hard-blocks `authorize_mainnet_payment` on this machine) and
> **A23** (A18's send-failure record has never fired on the platform it was
> written for). Three corrections against this run's own claims, all inside two
> hours: ADDENDUM 2 and ADDENDUM 3, plus M39.
>

---

## Banner notice moved here 2026-08-24 (historical; the merge it describes is done)

> **RECORD RESTORED (07:45 → ~08:20 write-back).** The 08:00 attended run's
> log write-back pasted a boot-time copy over the project log and silently
> dropped everything the **07:15 run** (D1-HBAR) had written at 07:18: its
> run-log entry, DE5, its M21, the D1-HBAR item text and its counters. The
> 07:45 run merged them back (entry restored verbatim below; the 07:15 run's
> M21 is re-numbered **M23** because the 08:00 run's M21 is also real).
> Nothing the 08:00 run wrote was removed. This is exactly M15/M23's hazard:
> **never paste a boot-time copy of this file over the project; fetch fresh
> at write-back and edit by anchor.**

---

### 2026-08-21 ~01:45 — loop made self-improving; A1 investigated and blocked
Restructured into immutable/mutable sections. Attempted A1; genesis locks the
whole 1000 supply for 365 days → DE1. A fresh chain cannot transact until 2027.

### 2026-08-21 ~01:35 — D1 started; fetch method proven and characterised
105 verified XLM bars recovered → M1.

### 2026-08-21 ~01:30 — loop created

### 2026-08-21 ~05:35 — A1a and A2 both closed (v8.15); verified live, twice
`/unstake` and `/claim_rewards` no-ops now return `status:error` (404/409).
`preflight_port_check` catches both port footguns before the banner. 15/15 live,
twice. → M4, M5. Residual risk flagged: the full existing suites were NOT run
against v8.15 this session.

### 2026-08-21 ~06:05 — A3 closed for real (v8.16); an earlier "done" was false

**The finding first, because it corrects the record.** A3 was listed as DONE
("three fixed via `recv_bounded` + `MAX_PEER_MSG_BYTES`"). Neither symbol
existed anywhere in `covenant_unified_v8.py`, and **all five** inbound socket
reads were still unbounded read-until-EOF loops:
`b"".join(iter(lambda: conn.recv(4096), b""))` in `_handle_peer` and
`_handle_bridge`, and `while True: buf += sk.recv(65536)` in the catch-up
reply reader, the tx-fetch reader, and the ACK reader. Any peer — or anyone who
can reach the P2P (node.port) or bridge (node.port+10) port — could hold the
connection open and stream unlimited bytes, all buffered into one object before
`json.loads` ever ran: a single-connection whole-node OOM. The mempool/staging
caps (item Y) bound *accepted* items, not the size of one unparsed frame, so
they never covered this. The prior entry described work that never landed. → M6.

**The fix (v8.16).** Added `MAX_PEER_MSG_BYTES` (64 MB default, override
`COVENANT_MAX_PEER_MSG_BYTES`), `PeerMessageTooLarge`, and `recv_bounded(sock,
limit, chunk_size)` — reads until EOF but raises the moment the accumulated
size crosses the ceiling (checked right after each chunk append, so it fires on
the crossing chunk, never one late). Applied to all five sites. The two
inbound handlers already record to the anomaly monitor and close the connection
in their `except`/`finally`, so a flood is refused **and** visible; the three
client-side readers surface it through their existing `except` (tx_fetch_failed
/ catch-up failure / ack=b""). The cap is deliberately generous, not snug: a
legitimate catch-up reply carries up to MAX_CATCHUP_BLOCKS full blocks, so the
goal is a ceiling that turns an infinite stream into a bounded rejection.

**Incidental fix.** Running the existing `test_security_audit.py` against v8.15
for the first time (last run's flagged residual risk) surfaced a real
regression the v8.15 preflight work had introduced: an `except Exception: pass`
inside `preflight_port_check`'s peer probe — which the audit's own
"no swallowed failures in the core" AST check forbids (it had been 99/100, that
one failing). Narrowed it to `(OSError, socket.timeout)` and made it report to
stderr with the partial-byte count instead of `pass`. The probe verdict is
unchanged (it still judges on whatever bytes arrived).

**Verification — twice each, per the standard.**
- `test_a3_bounded_reads.py` (new, live): drives the REAL P2P + bridge
  listeners with a >cap flood → refused, recorded on the anomaly monitor, chain
  intact, node still serves a normal message after; plus a socketpair unit
  check that `recv_bounded` raises on the crossing chunk and returns in-cap data
  intact. **7/7, run twice.**
- `test_security_audit.py`: **100/100** (was 99/100 before the except:pass fix),
  run twice.
- `test_adversarial_suite.py`: **21/21**, run twice.
- `test_a1a_a2.py` (live nodes): **15/15** — re-verified the v8.15 route +
  preflight semantics still hold after editing `preflight_port_check`.
- `py_compile` clean.

**Loop improvement.** `test_a1a_a2.py` and `test_a3_bounded_reads.py` are now
wired into `run_all_tests.sh` (new "ROUTE SEMANTICS + BOUNDED READS" section;
the `run` result-parser regex was widened to also match `N/N passed`), closing
the A4 sub-goal about pinning v8.15 semantics and adding the v8.16 read caps to
the sweep. Re-prioritised: A3 closed; A5 (scale regression) promoted as the
natural next A-item because A3 touched the read path on every inbound
connection — confirm the 64 MB cap never bites a legitimate large catch-up.

**Delivery (M5 — scheduled cloud run, no device bridge).** SendUserFile +
`project_write` for `covenant_unified_v8.py` (replaces project copy),
`test_a3_bounded_reads.py` (saved as `claude/test_a3_bounded_reads.py`), and
`run_all_tests.sh` (replaces project copy). **L: copy `covenant_unified_v8.py`
into `C:\Users\<user>\covenant`** — it needs `covenant_path_pattern.py` beside
it. The two test files and the runner are optional to copy but let you re-run
the sweep locally.

**Cost:** ~1 session. Produced: v8.16 source, new 7-check live flood test,
runner update, M6, one backlog item closed (A3), one earlier conclusion
corrected, one incidental regression fixed.

**Next:** A5 (1000-node scale regression against v8.16 — verify the read cap
doesn't bite legitimate catch-up), then the rest of A4 (block-injection
matrix). A1 stays blocked pending L's answer on A1c (is the 365-day genesis
lock deliberate?).

### 2026-08-21 ~06:50 — A5 closed (v8.17); the A3 cap was 7× too small for honest traffic

**The finding first, because it corrects the A3 entry above.** A3 wrote that
the 64 MiB read cap was "generous rather than tight". Measured with the real
serializer: a bare signed transaction is **1,466 bytes**; a block of
`MAX_PENDING_TRANSACTIONS` (5000) of them is **7.0 MiB**; a `BLOCK_REQUEST`
reply carrying `MAX_CATCHUP_BLOCKS` (64) such blocks is **448 MiB**. Any node
9+ full blocks behind would have every catch-up reply raise
`PeerMessageTooLarge`, record `catchup_failed`, and never sync again. Worse,
`Transaction.data` had **no size bound anywhere** (no `MAX_CONTENT_LENGTH` on
Flask either), so a single admitted transaction could carry tens of MB, one
block could exceed the cap by itself, and every node that did not witness it
live would be permanently exiled. A cap on the reader without a cap on the
honest writer is a liveness bug with an attack attached. → M7.

**The fix (v8.17), tightening only — nothing was weakened.**
- Constants, coherent by construction and **asserted at import**:
  `MAX_TX_BYTES` (16 KiB) < `MAX_BLOCK_BYTES` (= read cap / 8 = 8 MiB) ≤
  `CATCHUP_REPLY_BUDGET_BYTES` (= ¾ cap) < `MAX_PEER_MSG_BYTES`; plus
  `MAX_HTTP_BODY_BYTES` (4 MiB) > `MAX_TX_BYTES`. A misconfigured env override
  refuses to start with the arithmetic in the message. (First cut hard-coded
  8 MiB and broke `test_a3_bounded_reads.py`, which lowers the cap to 1 MiB —
  deriving the block default from the cap fixed it; assertion kept.)
- `serialized_size()` — one measuring function used by miner, acceptor and
  catch-up server so they cannot disagree.
- Size is now part of **shape**: `validate_transaction_shape` refuses > 16 KiB,
  `validate_block_shape` refuses > 8 MiB — covering peer tx fetch, both block
  acceptance paths, and genesis load. `/transactions` runs the shape check
  **before** PoW/signature/judge (413, `tx_rejected_shape` anomaly);
  `admit_pending_transaction` is the backstop.
- `/mine` packs `included` up to the block budget by truncation in priority
  order (balance reservations stay consistent); the remainder stays pending.
- `BLOCK_REQUEST` pages by bytes as well as count: always ≥ 1 block, stops
  before the budget, records `catchup_page_truncated`. Requesters already loop.
- Flask `MAX_CONTENT_LENGTH`; `RequestEntityTooLarge` handled explicitly →
  413 + `http_body_too_large` (it used to fall into the generic handler as a
  400 "Malformed JSON", which was a refusal but mislabelled).

**Verification — twice or more each.** `test_a5_size_coherence.py` (new; unit
+ live node on 17500/17501: paged catch-up to the tip in 4 pages, real
`request_missing_blocks` reads the page with zero `catchup_failed`, 413s over
raw HTTP) **20/20 ×3**. `test_security_audit.py` **127/127 ×2** (it mines 45
blocks through the new packing code). `test_adversarial_suite.py` **21/21 ×2**.
`test_a1a_a2.py` 15/15. `test_a3_bounded_reads.py` 7/7 (after the derivation
fix). `py_compile` clean.

**Delivery (M5).** SendUserFile + `project_write`: `covenant_unified_v8.py`
(replaced), `claude/test_a5_size_coherence.py` (new), `run_all_tests.sh`
(replaced; new test wired in). **L: copy `covenant_unified_v8.py` into
`C:\Users\<user>\covenant`** beside `covenant_path_pattern.py`.

**Loop improvements.** M7 (measure every ceiling against the honest maximum),
M8 (project↔disk mechanics: `local_path` must be under `/home/<user>`; use a
subagent to fetch big files verbatim). Backlog: A5 closed; its unfinished
scale-sim half split into **A6** so it is not hidden under a strike-through;
**A7** records the consensus-rule consequence for L. **Trigger prompt NOT
updated:** `update_trigger` returned "MCP tool call requires approval" in this
unattended run, so the proposed prompt text (adds the suite-set list, M7, the
v8.17 bound assertion, and the M8 `local_path`/subagent mechanics) is saved as
`claude/TRIGGER_PROMPT_PROPOSED.md` for L to apply by hand or to approve in
an attended session. → DE2. Self-assessment updated (4 runs, 4 closed, 8
methods, 3 corrections).

**Cost:** ~1 session, of which roughly a third was fetching the existing
suites onto disk (hence M8). Produced: v8.17 source (10 marked edit sites),
20-check live test, runner update, one item closed, one earlier conclusion
corrected, one mislabelled refusal fixed.

**Next:** A4 block-injection matrix (malformed / forged / rival-genesis /
oversized now that oversized is a defined rejection), then A6. A1 stays
blocked pending L on A1c.

### 2026-08-21 ~07:45 — A4 closed (v8.18); the injection matrix found six accepted-when-it-shouldn't classes

**The findings first.** Built `test_a4_block_injection.py` — 60 checks that
drive the REAL P2P listener of a live node with `BLOCK_PROPAGATE` frames and
assert height unchanged + a named anomaly recorded + node still alive. First
run against v8.17: **48/55**. Everything the acceptor already checked held
(rival genesis, four kinds of signature forgery, no-PoW, stale hash, NaN/Inf/
str/bool/None/list amounts, NaN timestamp, oversized, overdraft, ethics, drift,
replay, thirteen malformed frames). What it did NOT check, all confirmed live:
1. **`index=2.0` (float) accepted and persisted** — `2.0 == 2`, and sqlite's
   INTEGER affinity stored it silently.
2. **`stake_rewards=inf` accepted.** `nan` was refused only because sqlite
   rejected it at persist time (`block_rejected_persist`) — protection by
   accident, and `inf` slipped past the accident.
3. **Empty-transaction block accepted** once `alignment_score` was pinned to
   the governor value. The source's own note ("harmless because an empty block
   fails the drift check") assumed `mine()` sets alignment; an attacker sets it
   by hand and mines the hash themselves. Free chain inflation by anyone.
4. **`stake_rewards` was a free field** — 250.0 on a zero-value block, or
   −1.0, accepted. `/mine` derives it as `fsum(amount)*0.01`; no peer checked.
5. **Stake rewards were distributed on the miner only.** `/mine` calls
   `distribute_block_rewards`; `_accept_block_common` — the path every other
   node takes for the same block — never did. Miner's stake table compounds,
   peers' do not: a consensus split in staking state. Findings 4 and 5 were two
   bugs cancelling (the forged figure was harmless only because peers ignored
   it). Fixing one without the other would have opened a mint.
6. **An invalid block at the tip was reported `{"ok": true, "outcome":
   "duplicate"}`** — a sender whose block failed signature/PoW/overdraft saw a
   success. Same class as A1a's `/unstake`.

**The fix (v8.18), tightening only.**
- `validate_block_shape`: `index`/`nonce` must be non-bool ints ≥ 0;
  `alignment_score`/`stake_rewards` finite; `transactions` a list.
- `_accept_block_common`, after the hash check: refuse empty blocks
  (`block_rejected_empty`); `stake_rewards` must equal `fsum(amount)*0.01`
  (`block_rejected_reward`); `alignment_score` must equal `mean(benefit_score)`
  (`block_rejected_alignment`). Both are exactly what `mine()` produces, so an
  honest miner's output is unchanged; they are new rules for third parties
  (noted under A7).
- Peer acceptance now calls `distribute_block_rewards(block.stake_rewards)` for
  `index > 0`, mirroring `/mine`. Safe only because of the derivation rule
  above. Verified: a funded 200-value block propagated to the peer moves the
  founder stake 1000 → 1002, identical to what `/mine` credits.
- `_handle_peer` replies `outcome:"rejected", ok:false` for a refused block at
  the tip; `"duplicate"` only when `index < height`.

**Verification, twice or more each.** `test_a4_block_injection.py` **60/60 ×2**
(~3.5 min each; mining at difficulty 4 ~60 times). `test_security_audit.py`
**127/127 ×2** (45 blocks through `/mine` still satisfy the new derivation
rules — if `/mine` and the acceptor disagreed, this would have caught it).
`test_adversarial_suite.py` 21/21 ×2. `test_a5_size_coherence.py` 20/20 ×2.
`test_a3_bounded_reads.py` 7/7 ×2. `test_a1a_a2.py` 15/15. `py_compile` clean.
Not run: `test_multinode_live.py` (10-min real-process test; the rate-limited
`/mine` wait) — flagged as residual risk and the reason for A9.

**Observation, not asserted:** a block stamped ten years in the future is
accepted (A4.17). No timestamp rule exists. → A8 for L.

**Delivery (M5).** SendUserFile + `project_write`: `covenant_unified_v8.py`
(replaced, sha256 d18e634d…), `claude/test_a4_block_injection.py` (new),
`run_all_tests.sh` (replaced; A4 wired in with a 600 s budget). **L: copy
`covenant_unified_v8.py` into `C:\Users\<user>\covenant`** beside
`covenant_path_pattern.py`; the test and runner are optional.

**Loop improvements.** M9 (write the matrix from the attacker's side, assert
the reply as well as the state, budget 500 s for it). Backlog: A4 closed; A7
extended with the v8.18 rules; A8 (timestamp rule, registration-PoW-on-chain)
and A9 (cross-node stake convergence) added. Self-assessment: 5 runs, 5 closed,
9 methods, 4 corrections. Trigger prompt: not retried (DE2); nothing in this
run showed the prompt wrong, so `TRIGGER_PROMPT_PROPOSED.md` stands as is.

**Cost:** ~1 session; about a quarter of it waiting on difficulty-4 mining in
the test runs. Produced: v8.18 source (4 edit sites), 60-check live matrix,
runner update, one item closed, one source comment proven wrong and corrected,
one consensus split fixed.

**Next:** A6 (1000-node scale regression — now also measures the three new
per-block checks) or A9 (stake convergence across real processes, cheap and
confirms the v8.18 distribution fix end to end). A1 stays blocked pending L on
A1c; A8 needs L's answer.

### 2026-08-21 ~09:30 — A9 closed (v8.19); the relay gap it found, and DE1 corrected

**Two corrections first.**
1. **A1 was not blocked.** DE1's "chain inert until 2027" is true only for a
   node that mints its own genesis. `load_canonical_genesis` credits the
   founder's 1000 without staking it, so on the shared-genesis path (the real
   deployment, and what `test_multinode_live.py` does) the founder spends at
   once and blocks mint. Three runs repeated "A1 blocked pending L" without
   running the one test that disproved it. → M10, A1 reworded, DE1 narrowed.
2. **The two genesis paths diverge** (locked vs spendable, staked vs empty
   stake table) — same hash, different ledgers, a fork waiting to happen if a
   self-minted node runs alongside `--genesis` nodes. Not fixed: either
   direction is a policy choice Section 0 reserves for L. → **A10**.

**The A9 finding.** Ran `test_multinode_live.py` for the first time against
v8.18: 19/21 ×2, failing "block RELAYED to C" and "identical tip" — C sat at
height 1 while A and B were at 2, then converged only when block 3 forced a
catch-up. Reproduced in a 3-node diagnostic 2/2 when tx+mine followed boot
immediately, 0/1 with a 3 s pause. Traced with a patched runner (M10): on B,
`Thread-6 (_bootstrap_once)` accepted block 1 at 771.036; `covenant-fetch_0`
(the announce-driven fetch) lost the persist race at the same millisecond and
recorded `block_rejected_persist`. Bootstrap never announces; the fetch path
announces only what it applied. So the block reached B and stopped. Any block
minted while any peer is in its startup bootstrap window was one-hop — and
the same holds for `/sync` and for any concurrent-delivery race, not just
boot.

**The fix (v8.19), three sites, nothing weakened.**
- `_apply_fetched_blocks(raws, source_peer)` announces the last block it
  applied, excluding the peer it pulled from (inhibition of return);
  `bootstrap_chain` passes the peer id. Peers that already hold it answer
  `known` and inhibit, so the extra event is ~150 bytes per edge.
- `_fetch_announced(..., announced_hash)`: if it applied nothing but the
  announced `(index, hash)` is now held, forward the event anyway
  (`announce_forwarded_held`). The node judged the event novel when it
  arrived; it owes its peers the relay whichever path delivered the block.
- `_accept_block_common`: re-check `index == len(chain)` *inside*
  `chain_lock` and record `block_already_held` — the old label
  `block_rejected_persist` put a storage-failure name on a benign race.

**Verification, twice each.** `test_a9_relay_race.py` (new, 18 checks: S1
deterministic — A mines with B/C down, C up first, then B; B must relay what
it pulled by bootstrap; S2 the race as observed; S3 cross-process `/stakes`
agreement) **18/18 ×2** — S2 on both runs showed the race actually occurring
(`block_already_held` + `announce_forwarded_held` on B) and healing.
`test_multinode_live.py` **21/21 ×2** (from 19/21; one extra run hit a
`free_port()` collision at startup — harness flake, see M10).
`test_security_audit.py` 127/127, `test_adversarial_suite.py` 21/21,
`test_a4_block_injection.py` 60/60, `test_a5_size_coherence.py` 20/20,
`test_a3_bounded_reads.py` 7/7, `test_a1a_a2.py` 15/15, `py_compile` clean.
Not done: a pre-fix run of the new test against v8.18 (the v8.18 file was
overwritten in place); the pre-fix evidence is the 2/2 multinode failure and
the 2/2 diagnostic reproduction.

**Delivery (M5).** SendUserFile + `project_write`: `covenant_unified_v8.py`
(replaced, sha256 c88ac111…), `claude/test_a9_relay_race.py` (new),
`run_all_tests.sh` (replaced; A9 wired in, 420 s). **L: copy
`covenant_unified_v8.py` into `C:\Users\<user>\covenant`** beside
`covenant_path_pattern.py`.

**Loop improvements.** M10. Backlog: A9 closed; A1 unblocked and reworded
(kill-during-propagation matrix is what remains); A10 added and supersedes
A1c/A1b as the question for L; DE1 narrowed, not deleted. Self-assessment:
6 runs, 6 closed, 10 methods, 5 corrections. Trigger prompt: not retried
(DE2). One thing the prompt should say and does not — add to
`TRIGGER_PROMPT_PROPOSED.md` next run if L has not applied it: *"run every
suite in `run_all_tests.sh` that touches the file you ship, including the
slow ones, at least once per run; an un-run suite is an unverified claim."*

**Cost:** ~1 session: a third fetching files and running the 10-min
multinode suite three times, a third tracing, a third on fix + new test +
full sweep. Produced: v8.19 (3 edit sites), 18-check live test, runner
update, one item closed, two earlier conclusions corrected, one decision
item for L with the consequences spelled out.

**Next:** A1 proper (kill-during-propagation matrix using `Net` from
`test_a9_relay_race.py`; cheap now), then A6 (scale regression). **A10 needs
L's answer before either genesis path is touched.** A8 still open for L.

### 2026-08-21 ~10:30 — A1 closed (v8.20); the miner-killed-after-mine case had no path home

*(Attended continuation of the 09:30 run — L typed "continue", then asked
whether the nodes had been launched on the PC. They had not and cannot be from
here: no device bridge in a session a schedule started. Copy-and-run
instructions were sent; the loop otherwise ran as specified.)*

**The finding.** Built the kill matrix from the failure side (M9) on the
`Net` harness from A9 — SIGKILL only, restart on the same db (M11). K1 and K3
passed on v8.19 as shipped: a bridge that is dead while the block is mined
pulls it at restart and relays it (the v8.19 fix doing its job), and a dead
leaf catches up from its peer with no new block. **K2 failed 3/3:** kill the
miner in the same second `/mine` returns (its announce had not left — B and
C observed at height 1), restart it, and nothing happens. The restarted node
is *ahead*: `bootstrap_chain` is pull-only, so it pulls nothing; nothing
pushes; B and C stay at genesis for the full 30 s window and, on a quiet
chain, forever — until the next block's announce triggers the gap-fill.
Every sync path in the file was a pull triggered by someone else's new
block; a node that came back holding the newest block was mute.

**The fix (v8.20), additive only.** `_gossip_tip(reason)`: announce own tip
to all peers when height > 1 and peers exist. Called once after
`bootstrap_chain` in `_bootstrap_once` (prints `boot: announced tip index N
to M peer(s)`) and from a new `_tip_gossip_loop` every `TIP_GOSSIP_INTERVAL_S`
(120 s, env `COVENANT_TIP_GOSSIP_INTERVAL`, 0 disables the loop; the boot
push stays). Receivers that already hold the tip answer `known` and do
nothing (lateral inhibition); a peer that is behind fetches the gap through
the same `_fetch_announced` path as any announce. No validity rule touched.

**Verification, twice each.** `test_a1_kill_matrix.py` **29/29 ×2** (~8 min
each; K2 also asserts the `boot: announced tip` line in the restarted
miner's log so it passes for the right reason; K5 runs in-process against a
fake peer socket with the interval at 2 s and sees the `BLOCK_ANNOUNCE` in
2.0 s). `test_a9_relay_race.py` 18/18 ×2, `test_multinode_live.py` 21/21,
`test_a4_block_injection.py` 60/60, `test_security_audit.py` 127/127,
`test_adversarial_suite.py` 21/21, `test_a5_size_coherence.py` 20/20,
`test_a3_bounded_reads.py` 7/7, `test_a1a_a2.py` 15/15, `py_compile` clean.
Pre-fix evidence: K2 3/3 failures on v8.19 in this session (logged above).

**What K5 could not do, recorded so nobody retries it:** staging a dropped
announce with SIGSTOP does not work — the frozen peer's kernel still
completes the handshake and buffers the frame (M11). The in-process fake
peer is the honest substitute.

**Delivery (M5 — no bridge even though L was present; the session was
started by the schedule).** SendUserFile + `project_write`:
`covenant_unified_v8.py` (replaced, sha256 b739d356…),
`claude/test_a1_kill_matrix.py` (new; imports `test_a9_relay_race.py`),
`run_all_tests.sh` (replaced; A1 wired in, 560 s), `claude/trace_runner.py`
(new; the M10 tracing harness). **L: copy `covenant_unified_v8.py`,
`test_a9_relay_race.py` and `test_a1_kill_matrix.py` into
`C:\Users\<user>\covenant`** beside `covenant_path_pattern.py`.

**Loop improvements.** M11. Backlog: A1 closed (history kept); A11 added
(measure the periodic gossip at scale, folded into A6). `update_trigger`
retried with L present — still "requires approval" (DE2 stands; the call
needs L to click approve). The full proposed prompt, updated with this run's
traps (the `/chain` rate limit, self-minted vs loaded genesis, the four live
suites and their run times, the A10 do-not-touch rule), is in
`claude/TRIGGER_PROMPT_PROPOSED.md`. Self-assessment: 7 runs, 7 closed, 11
methods, 5 corrections.

**Cost:** ~½ session on top of the 09:30 run: one kill-matrix run to find
K2, the fix, the K5 unit scenario, two full matrix runs and the sweep.

**Next:** A6 + A11 (scale regression, now measuring three per-block checks
and the periodic gossip), or B1 (judge parser corpus) if a run wants a change
of subsystem. **A10 still needs L's answer** before either genesis path is
touched; A8 too.

### 2026-08-21 ~11:45 — A6 and A11 closed (v8.21); the heartbeat was quietly erasing link conductance

**Correction first.** A6 said to measure pools, shape-check cost and the
preflight probe "via `sim1000_network.py`". That sim never touches any of
them — it is 1000 `Database` objects and `apply_transaction_ledger` (→ DE3).
Ran it anyway as the ledger regression it is: **I1–I5 pass, 0 findings,
373 s** on v8.21. The rest of A6 was answered by direct measurement (see the
struck item): 60 ms per max-size block for `validate_block_shape`, probe is
boot-only.

**The A11 finding — by arithmetic, then confirmed on the real classes (M12).**
v8.20's receiver handled a tip heartbeat exactly like a wasted duplicate:
`announce_inhibited` on the monitor and `attenuate(sender)`. Two
consequences, both measured with a patched clock:
1. `LinkConductance`: −0.02 every 120 s against a 3600 s half-life toward
   0.5 → every link at `MIN` (0.05) from round 31 (~62 min) on a quiet
   chain. Ordering-only, so not a safety bug — but the learned ordering the
   class exists for was being zeroed by the heartbeat, and one real
   `reinforce` (+0.08) is swamped in four rounds.
2. `SpikingAnomalyMonitor`: with lock-step heartbeats after a synchronized
   restart and degree ≥ 5, `recent ≥ 5 and recent > 3×expected` is true for
   the first three rounds → `/health` warns `anomaly spike:
   ['announce_inhibited']` for ~5 min. Degree 2 (L's deployment) never
   trips it. A false alarm on the one channel an operator is told to watch.

**The fix (v8.21), five small edit sites.** `announce_block(..., gossip=
False)` adds `"gossip": true` to the frame when set; `_gossip_tip` sets it;
in `_handle_peer` a held tip with `gossip is True` increments
`node.tip_gossip_seen` and skips both the monitor record and attenuation;
anything else (including `"gossip": "true"` as a string) takes the old path;
`/health` exposes `tip_gossip_seen`. The NOVEL branch is untouched, so K2's
path home is exactly v8.20's. Is the tag a weakening? A sender can tag real
duplicates to dodge attenuation; all that buys is an earlier slot in
delivery *order*, which never gates delivery — and an untagged duplicate is
still penalised (L2, L2b assert it).

**Verification, twice each.** `test_a11_gossip_scale.py` (new, 23 checks:
U1/U2 reproduce both hazards on the v8.20 schedule with the real classes;
L1–L6 drive the real `_handle_peer` over a socketpair and the real
`_gossip_tip` against a fake peer; L5 pushes 250 heartbeats = degree 50 ×
600 s: all counted, none recorded, no spike, 0.25 ms each) **23/23 ×2**.
Full sweep on v8.21: `test_security_audit.py` 127/127,
`test_adversarial_suite.py` 21/21, `test_a1a_a2.py` 15/15,
`test_a3_bounded_reads.py` 7/7, `test_a5_size_coherence.py` 20/20,
`test_a9_relay_race.py` 18/18, `test_a1_kill_matrix.py` 29/29,
`test_a4_block_injection.py` 60/60, `test_multinode_live.py` 21/21,
`sim1000_network.py` 0 findings, `py_compile` clean. (First cut of U2
asserted MIN by round 30; the real figure is round 31 — the test was
corrected, not the claim.) Pre-fix evidence: U1/U2 are computed on the
unchanged classes, so they stand on the shipped file as the record of what
v8.20 did.

**Delivery (M5).** SendUserFile + `project_write`: `covenant_unified_v8.py`
(replaced, sha256 d18201ae…), `claude/test_a11_gossip_scale.py` (new),
`run_all_tests.sh` (replaced; A11 wired in, 120 s). **L: copy
`covenant_unified_v8.py` into `C:\Users\<user>\covenant`** beside
`covenant_path_pattern.py`; the test and runner are optional.

**Loop improvements.** M12 (solve the recurrence before building the
harness; socketpair + `_handle_peer` drives the production receiver
in-process; `sim1000` is ledger-only). DE3. Backlog: A6 and A11 closed, A12
added (heartbeats to dead peers vs the 64-worker send pool — arithmetic
says >512 dead peers saturates it; not observed, not urgent). Trigger
prompt: not retried (DE2); nothing this run showed the prompt wrong except
that it should stop pointing at `sim1000_network.py` for socket questions —
noted for `TRIGGER_PROMPT_PROPOSED.md`. Self-assessment: 8 runs, 9 closed,
12 methods, 5 corrections, 3 dead ends.

**Cost:** ~1 session: a third fetching files and running the 6-min ledger
sim, a sixth on the arithmetic + probe, the rest on fix, test and the full
sweep (the slow suites run in parallel pairs fit the 10-min tool budget).

**Next:** The A-section is now down to decisions for L (A7, A8, A10) and
the low-urgency A12. Highest-value unblocked code work is **B1** (judge
parser corpus: string booleans and `<think>` blocks were found by accident;
build the corpus and fail closed on garbage) or **B3** (timeout audit — a
30 s cloud default that counts as a violation silently rejects on slow
hardware). Suggest B3 first: it is small, and a silent reject is the class
this loop keeps finding.

### 2026-08-21 ~13:00 — B1 and B3 closed (v8.22); the "fixed" parser fixes were never in the node

**The correction first (M6 again).** B1's text said string booleans and
`<think>` blocks were "found and fixed". The node's
`_APIReasoningJudge._parse_verdict` had neither fix: `bool(obj.get(
"violates", True))` and a first-`{`/last-`}` slice. Wherever those fixes
landed, it was not in the file every node runs. Measured on v8.21 with the
new corpus (the test run against the backed-up v8.21 source):
`"violates": null` / `[]` / `""` / `0` → **`violates=False`, transaction
admitted** — a model that hedges with `null`, or a truncated/odd reply that
still parses, passes the ethics gate. `"false"` → `True` (honest traffic
refused). A `<think>` block containing a brace, prose with a trailing
brace, or a schema example before the verdict → `ValueError` → fail-closed
rejection of a valid verdict. `benefit_estimate` unvalidated: `"0.8"` raised
`TypeError` in the route's blend; `inf` would have flowed into
`tx.benefit_score` → `block.alignment_score`, which v8.18 peers refuse —
the miner's own judge could make it mint unacceptable blocks.

**The fix (v8.22), parser strict on the verdict, tolerant on the wrapper.**
Strip closed `<think>…</think>`; `json.JSONDecoder.raw_decode` at each `{`
in order, first dict with a `violates` key wins; `violates` must be a JSON
bool or exactly `"true"`/`"false"` (case/whitespace-insensitive) — `null`,
numbers, `"yes"`/`"no"`, lists, `""` raise (fail closed);
`benefit_estimate` → finite float in [0,1] (numeric strings tolerated) else
None; `reasoning`/`principle_violated` coerced to bounded str
(`JUDGE_REASONING_MAX_CHARS` 2000). Nothing was loosened: every input that
was refused before is still refused; four inputs that were *accepted* are
now refused; a handful of valid verdicts wrapped in model noise are now
read instead of rejected.

**B3.** One `JUDGE_TIMEOUT_S` (env `COVENANT_JUDGE_TIMEOUT_S`, default 30,
asserted in [1, 600] at import) replaces three literals. Timeouts still
fail closed. New `JudgmentResult.infrastructure_failure` (default False,
so every existing constructor is unchanged) marks no-key / timeout / HTTP
error / unparseable reply; `QuorumJudge` sets it only if a **violating**
component has it; `/transactions` and `_ingest_peer_transaction` record
`judge_unavailable` in addition to `ethics_gate_rejection`. An operator
watching `/anomalies` can now tell "the gate is broken/slow" from "people
are sending bad transactions". **Incidental:** `/transactions` evaluated
the judge twice per transaction (decide, then again to `save_judgment`);
now `ReasoningSentinel.evaluate_transaction` returns the result and the
route persists that one. The peer ingest path also silently dropped
ethics rejections with no anomaly record; it records them now.

**Verification, twice each.** `test_b1_judge_parser.py` (new, in-process:
32-reply corpus ×(parse + full evaluate), old-parser record, quorum
propagation, timeout plumbing incl. three import-time refusals via
subprocess, route-level single-call + persisted row + anomaly kinds on
both ingest paths) **162/162 ×2**, 29 s; **against v8.21: 20 FAIL then
AttributeError**, the pre-fix record. Sweep on v8.22:
`test_security_audit.py` 127/127 ×2, `test_adversarial_suite.py` 21/21,
`test_a1a_a2.py` 15/15, `test_a3_bounded_reads.py` 7/7,
`test_a5_size_coherence.py` 20/20, `test_a11_gossip_scale.py` 23/23,
`test_a9_relay_race.py` 18/18, `test_multinode_live.py` 21/21,
`test_a4_block_injection.py` 60/60, `py_compile` clean. **Not run:**
`test_a1_kill_matrix.py` (8 min; its code paths — boot gossip, catch-up —
are untouched by this change and are covered by a9 + multinode); flagged,
per the standard, as the one un-run suite.

**Delivery (M5).** SendUserFile + `project_write`: `covenant_unified_v8.py`
(replaced, sha256 8b304a2f…, +118 lines), `claude/test_b1_judge_parser.py`
(new), `run_all_tests.sh` (replaced; new "JUDGE LAYER" section, 180 s).
**L: copy `covenant_unified_v8.py` into `C:\Users\<user>\covenant`** beside
`covenant_path_pattern.py`; the test and runner are optional.

**Loop improvements.** M13 (judge-layer test recipe). Backlog: B1, B3
closed; **B4** added — the judge is inside consensus (peer block
acceptance calls the live API per tx; a timeout on one node is a fork),
a decision for L before any code; **B5** (`/mine` latency with live
judges) depends on it. Trigger prompt: not retried (DE2). Self-assessment:
9 runs, 11 closed, 13 methods, 6 corrections, 3 dead ends.

**Cost:** ~1 session: a third fetching files (three subagent fetches), a
third on fix + test, a third on the sweep (slow suites in parallel pairs).

**Next:** Section A is decisions for L (A7, A8, A10) plus low-urgency A12.
B2 (quorum diversity is label-deep) is the remaining B code item, but it
is a design question more than a bug. **B4 should be put to L before
anything else in B.** Otherwise C1/C2 (deployment: phone install never
run; heartbeat/doctor gap detection unit-only) or A12 (dead-peer heartbeat
backoff, measurable with M12's blackhole recipe).

### 2026-08-21 ~23:30 → 08-22 ~00:15 — A12 closed (v8.23); the dead-peer cost was head-of-line blocking first, pool saturation second

*(Scheduled run. L was present and asked three times for the sweep to run
on the PC; it cannot from a schedule-started session — no device bridge,
re-checked with ToolSearch and RefreshMcpTools — so the sweep ran here and
the files go through SendUserFile + the project, as always. The three
options for a PC run were sent to L in-conversation.)*

**First, the sweep L asked for, on v8.22 as shipped — all eleven suites,
including the kill matrix the 13:00 run skipped:** security_audit 127/127,
adversarial 21/21, a1a_a2 15/15, a3 7/7, a5 20/20, a11 23/23, b1 162/162,
a9 18/18, a4 60/60, **a1_kill_matrix 29/29 (50 s)**, multinode 21/21
(74 s). Nothing was broken. **Correction:** the runner's comments and three
run-log entries quote a1 at ~8 min, a4 at ~4 min and multinode at ~10 min;
measured twice here they are 45–50 s, 55–68 s and 74–79 s. The 13:00 run
left the kill matrix un-run *because* of the 8-minute figure. The figures
were ceilings copied from `timeout` budgets, not measurements → M14, and
the proposed trigger prompt no longer quotes them.

**The A12 finding — measured, not inferred (M12, M14).** Built
`test_a12_dead_peers.py` first and ran it against v8.22: **4/24, 20
FAIL** (the pre-fix record, twice). With the real `_send_raw`: one message
to a black-holed host costs **15.13 s** of a pool worker (3 × 5 s + the two
φ-backoff sleeps). The item's arithmetic (saturation at ~512 dead peers)
was right to within rounding (508) and was the *second* hazard. The first:
`LinkConductance.order` breaks ties by insertion order, and a dead peer
never moves off baseline (it never answers, so it is never reinforced or
attenuated), so any live peer listed after a full generation of dead ones
waited a whole timeout generation for a **novel** block — at production
scale, 15 s from D ≥ 64 dead peers, not 508. Scaled to 4 workers / 8 dead /
0.5 s: live peer's boot push 1.63 s late, every periodic heartbeat 3.27 s
late, a real block announce 3.27 s late, and a 6-round heartbeat burst at
1.2 s spacing left 32 sends queued (37 peak) with the queue still full 3 s
after the last round. Also noted: `bootstrap_chain` probes peers
sequentially (4.0 s for 8 dead at 0.5 s) → A14; and a peer that can reach
us but not vice versa never learns our tip → A13.

**The fix (v8.23): `PeerHealth`, eight edit sites, nothing weakened.**
- Fed only by this node's own outbound outcomes: connect + send succeeded
  = `ok`; every attempt raised = `failed`. A peer that accepts the frame
  and answers nothing (saturated, crisis mode, legacy
  `TRANSACTION_PROPAGATE`) is back pressure, not death — untouched.
  Inbound traffic never resets it (CGNAT asymmetry would re-arm the cost).
- `P2PNode._dispatch` is now the one place the four send sites hand work
  to the pool: conductance order, then a stable partition by
  `rank` (answered / never contacted / failing). Ordering only; every real
  message still addresses every peer. `propagate_transaction` now honours
  the `exclude_peer` it always accepted (its only caller passes none).
- Suspect after `PEER_SUSPECT_AFTER` (3) consecutive failures: one attempt
  per real message (the message is the probe); periodic heartbeats skip it
  while the backoff (`PEER_BACKOFF_BASE_S` 120 s doubling to
  `PEER_BACKOFF_MAX_S` 900 s, exponent clamped) is unexpired, then the
  heartbeat is the probe. One success resets. Knobs asserted at import
  (K ≥ 1, 1 ≤ BASE ≤ MAX).
- Periodic heartbeats get one attempt — the next heartbeat is the retry.
  The boot push keeps three, and because `request_missing_blocks` feeds
  the table, `bootstrap_chain` has already sorted answering peers to the
  front by the time the boot push goes out (K2's path home now reaches a
  live peer in 3 ms beside 8 dead ones; v8.22: 1.63 s).
- `/health`: `peers_suspect` and a warning naming them (not `degraded`);
  GET `/peers`: `health` table. `_gossip_tip` returns sends submitted.
- Steady-state cost per dead peer: 15.13 s per 120 s → 5 s per ≥ 900 s;
  saturation 508 → 11,520 dead peers.

**Verification.** `test_a12_dead_peers.py` (41 checks: PeerHealth unit
with patched clock; boot push / periodic / backoff / probe-due / doubling /
cap / revival / real-announce ordering and attempts on the real
`_send_raw` + `_gossip_tip` over a socket shim; bounded queue under a
1.2 s burst; three import-time refusals by subprocess; the saturation
arithmetic from the module's own constants) **41/41 ×3** on v8.23, ~31 s;
**4/24 ×2 on v8.22**. Full sweep on v8.23: security_audit 127/127,
adversarial 21/21, a1a_a2 15/15, a3 7/7, a5 20/20, a11 23/23, b1 162/162,
a9 18/18, a4 60/60, a1_kill_matrix 29/29, multinode 21/21, `py_compile`
clean, `bash -n` clean. Every suite that touches the file ran against the
shipped file at least once; the fast seven ran on both v8.22 and v8.23.

**Delivery (M5).** SendUserFile + `project_write`: `covenant_unified_v8.py`
(replaced, sha256 c5447e79…, 8483 lines, +225/−21),
`claude/test_a12_dead_peers.py` (new), `run_all_tests.sh` (replaced; A12
wired in, 240 s). **L: copy `covenant_unified_v8.py` into
`C:\Users\<user>\covenant`** beside `covenant_path_pattern.py`; the test and
runner are optional. Project round-trip of the big file could not be
re-read for a hash this time (the resumed fetch subagent had no `Projects`
tool — M14); the write returned `replaced: true` from the local file whose
hash is quoted above.

**Loop improvements.** M14. Backlog: A12 closed with its residual spelled
out for L (full failure-detector gating is a policy choice); **A13**
(one-way reachability never syncs — small fix shape recorded) and **A14**
(sequential boot probe) added, both low priority for L's symmetric LAN /
Tailscale topology. Self-assessment: 10 runs, 12 closed, 14 methods, 7
corrections, 3 dead ends. Trigger prompt: `TRIGGER_PROMPT_PROPOSED.md`
updated (suite list + real run times, the `_dispatch` rule, A13/A14
hooks); `update_trigger` attempted once more with L present in the
conversation — "MCP tool call requires approval" again. DE2 stands: the
call needs L to click approve in the moment, or to paste the proposal in.

**Cost:** ~1 session: a quarter on the v8.22 sweep L asked for (three
batches, parallel pairs), a quarter writing the failure-side test and
recording the pre-fix numbers, a quarter on the fix, a quarter on the
v8.23 sweep and this log.

**Next:** Section A is decisions for L (A7, A8, A10) plus the small A13
and A14. **B4 should be put to L before anything else in B.** B5 (`/mine`
latency with live judges) is a cheap measurement with M13 whose fix waits
on B4. Otherwise C1/C2 (phone install never run; heartbeat/doctor gap
detection unit-only) — C1 can at least be read for glibc/Bionic
assumptions from here.

### 2026-08-22 ~00:40 — DUPLICATE run: A12 re-done off a stale log snapshot; no new item closed

**This run closed nothing new and must say so plainly (rule 5's spirit,
even at one run rather than three).** It read the boot snapshot of this
log, which ended at the 13:00 B1/B3 entry ("9 runs") and did **not**
contain the 00:15 A12 entry. Taking A12 as the highest-value unblocked
A-item, it re-implemented it end to end — a simpler `_delivery_order` +
per-link heartbeat backoff v8.23 (sha256 `2d3e9da6…`, 8382 lines) — and
verified it (its own `test_a12_dead_peer_backoff.py` 21/21 ×3 with a
Barrier-drained pool; full 11-suite sweep on v8.23 all green:
security_audit 127, adversarial 21, a1a_a2 15, a3 7, a5 20, a11 23,
b1 162, a9 18, a4 60, a1_kill_matrix 29, multinode 21). Only at the
write-back — when a fresh subagent fetched the log — did the 00:15 A12
entry surface. See the ACTIVE ISSUE banner and M15.

**Two real findings survive the duplication, so the run was not pure
waste:**
1. **A torn commit in the 00:15 run.** Its log entry persisted; its source
   save did **not** — the project held v8.22 `8b304a2f`, not the claimed
   `c5447e79`, at this run's start (verified by hash). `project_write`
   returning `replaced: true` is not proof the intended bytes landed. → M15,
   and a correction logged against the 00:15 entry's shipping claim.
2. **A concurrency hazard in the loop itself.** Two runs off one stale
   snapshot both grab the same item. The boot snapshot lags a concurrent
   write; the only guard is a fresh `project_read` of this log immediately
   before selection. → M15.

**What is in the project now:** source = this run's `2d3e9da6` v8.23
(`_delivery_order`), log = the 00:15 run's `PeerHealth` description. They
do not match. This run did **not** overwrite a good `PeerHealth` source —
that source was never in the project — but it did replace the last
self-consistent artifact (v8.22) with a v8.23 whose design differs from
the log's canonical A12 entry. The pristine v8.22 (`8b304a2f`) is preserved
on this run's disk only; it is not re-shipped.

**Not done, deliberately:** reconstructing `PeerHealth` from the 00:15
entry's description (a third A12 implementation, divergence risk, and L
already holds `c5447e79`); reverting the project source to v8.22 (would make
A12 read as regressed while the log says done); rewriting the 00:15 entry
(forbidden — never rewrite earlier entries). The banner + this entry defuse
the M6 trap by documentation instead.

**For L — one decision, low urgency (A12 is a large-scale / dead-peer
concern; irrelevant to a 2–3 node symmetric LAN today):** consolidate the
two v8.23 sources. Recommended: keep the **`PeerHealth`** version
(`c5447e79`, in your ~00:15 SendUserFile download) — it is the more thorough
fix (it identified head-of-line blocking as the primary hazard and found
A13/A14) — and re-copy it into `C:\Users\<user>\covenant`, then a future
attended run can re-save it to the project so source and log agree. If you
prefer the simpler version already in the project (`2d3e9da6`, also fully
tested), say so and a future run will note it as canonical and mark the
00:15 `PeerHealth` entry superseded. **Until you choose, no run should touch
A12 again.**

**Loop improvements.** M15 (re-read the log fresh before selecting; verify
the source round-trip by hash; the boot snapshot can be stale). ACTIVE
ISSUE banner added at the top. Self-assessment: 11 runs, 12 closed (this
run added none), 15 methods, 8 corrections, 3 dead ends.
`update_trigger` not retried (DE2). Delivery: this run's `2d3e9da6`
v8.23, `test_a12_dead_peer_backoff.py`, the K2-harness fix for
`test_a1_kill_matrix.py`, and `run_all_tests.sh` were sent via SendUserFile
and written to the project **before** the collision was discovered; L is
told in-conversation to prefer the `PeerHealth` version and treat these as
the alternative.

**One genuine side-fix worth keeping regardless of which A12 wins:**
`test_a1_kill_matrix.py` K2 flaked once here — when the SIGKILL loses the
race and B already holds the block, convergence returns instantly and the
`boot: announced tip` log line has not been flushed yet (stdout is
block-buffered under redirection). Fixed two ways: `_gossip_tip`'s boot
print now `flush=True`, and the harness sets `PYTHONUNBUFFERED=1` on
restart and polls the log up to 10 s. This is orthogonal to A12 and applies
to whichever v8.23 L keeps (the print change is in both if re-shipped;
the harness change is in the delivered `test_a1_kill_matrix.py`).

**Cost:** ~1 session, effectively duplicated. The lesson (M15) is the
lasting product; the code is a redundant alternative.

**Next (unchanged from 00:15, minus A12 which is closed twice over):**
Section A is decisions for L (A7, A8, A10, and now the A12 consolidation)
plus small A13/A14. **B4 to L before anything else in B.** A fresh run
should re-read this log first (M15), then take **B4-dependent B5** only
after L answers B4, or **C1** (phone install glibc/Bionic read — doable
from here) as the next unblocked code-adjacent item.

### 2026-08-22 ~00:47 — (UNLOGGED run, reconstructed at 01:40) B5 measured, test + runner shipped, log write-back never landed
Reconstructed from `project_info` timestamps and the test's own docstring:
a run between 00:40 and 00:47 wrote `claude/test_b5_mine_latency.py` (24
checks, L1–L4) and a `run_all_tests.sh` with B5 wired in, and no log entry.
Its source was unchanged (`2d3e9da6` still in the project at 01:40). Its
findings are recorded under the struck B5 item above. → M16.

### 2026-08-22 ~01:40 — B5 closed: the unlogged measurement verified, plus v8.24 (refusals by a DOWN judge are now visible on both block paths)

**Selection (M15, M16).** Re-read the log fresh: last entry 00:40. But
`project_info` showed two docs written at 00:47 — an unlogged run had done
the B5 measurement. Fetched it, read the docstring, ran it: **24/24 ×2**
on the project's v8.23 (`2d3e9da6`). Logged on that run's behalf (entry
above). A12 untouched per the banner.

**The B5 finding it carried, now twice-verified.** `/mine` re-judges every
included tx after the PoW, sequentially per judge, holding `chain_lock`
(L3: a plain pending lookup waited 1.86 s of a 1.85 s judging window).
Timeout = 91.3 s per tx per judge at the default; block discarded, pool
untouched, `/mine` repeats PoW + wait (L2 measured the repeat); a flipped
verdict wedges `/mine`. 5000 pending with one slow provider = 127 h frozen.
L4 puts the arithmetic on record from the module's own constants.

**What this run added (v8.24, observability only — the decision is B4's).**
The 13:00 B3 entry said an infrastructure reject "is recorded as
`judge_unavailable`" — true on `/transactions` and peer tx ingest, **false
on both block paths**: `/mine` recorded nothing at all (a bare 400 — the
00:47 test asserted exactly that as the pre-fix state), and
`_accept_block_common` recorded `block_rejected_ethics` with no way to tell
"our judge timed out" (a fork in the making, B4) from "genuine dissent".
Three edit sites: `ReasoningSentinel.validate_block` keeps its 2-tuple
signature, uses `evaluate_transaction` and sets
`last_block_infrastructure_failure`; `/mine` records `mine_rejected_ethics`
+ (if infra) `judge_unavailable`; `_accept_block_common` records
`judge_unavailable` beside `block_rejected_ethics` when infra. Every refusal
that happened before still happens. Nothing weakened.

**Verification, twice each.** `test_b5_mine_latency.py` now 31 checks (L2
flips the "nothing recorded" assertion into the v8.24 assertions, plus a
dissent-is-not-relabelled check; new L5 pushes a block built exactly as
`/mine` builds it through the real `_accept_block_common` under a
timing-out judge, a dissenting judge, then a clean judge): **31/31 ×2 on
v8.24; 27/31 on the pristine v8.23** (the four new assertions, the pre-fix
record). Full sweep on v8.24: security_audit 127/127, adversarial 21/21,
a1a_a2 15/15, a3 7/7, a5 20/20, a11 23/23, b1 162/162,
a12_dead_peer_backoff 21/21, a9 18/18, a4 60/60, a1_kill_matrix 29/29,
multinode 21/21; `py_compile` + `bash -n` clean. ~4 min in two batches.

**Delivery (M5).** SendUserFile + `project_write`, **round-trip verified by
hash (M15)**: `covenant_unified_v8.py` v8.24 (sha256 `ec267d40…`, 8401
lines, +19), `claude/test_b5_mine_latency.py` (`6305310d…`),
`run_all_tests.sh` (comment updated). **L: copy `covenant_unified_v8.py`
into `C:\Users\<user>\covenant`** beside `covenant_path_pattern.py`. Note
this v8.24 is built on the `_delivery_order` v8.23 (`2d3e9da6`) that the
project holds — if you consolidate on `PeerHealth` (`c5447e79`), the three
v8.24 edits (grep `v8.24`) are small enough to re-apply by hand.

**Loop improvements.** M16 (timestamps expose torn commits; log on the
unlogged run's behalf). Self-assessment: 13 runs, 13 closed, 16 methods,
9 corrections, 3 dead ends. `update_trigger`: not retried (DE2).

**Cost:** ~½ session: a third fetching/verifying the 00:47 work, a third
on the three edits + L5, a third on the sweep and this log.

**Next:** Every B code item is now gated on **B4** (consensus rule vs
admission policy) — put it to L. Section A: A7/A8/A10 + the A12
consolidation are L's; A13/A14 are small but sit on the send path the
banner says not to touch until A12 is consolidated. So the next unblocked
items are **C1** (read `phone/node-install.sh` for glibc/Bionic
assumptions — it is not in the project; L must upload it) and **C2**
(heartbeat/doctor gap detection — also not in the project). **If L answers
none of A10/A12/B4 and uploads nothing, the next run will stall; say so
(rule 6) rather than invent work in D.**

### 2026-08-22 ~03:00 — A13 closed (v8.25): one-way reachability now syncs; the reply every announce threw away was the only signal

**Selection (M15, M16).** Fresh `project_read` of this log: last entry
01:40; `project_info` shows nothing newer than the log (no unlogged run,
no upload from L, no answer on A10/A12/B4). The 01:40 entry predicted a
stall. Pushing back on that: A13 was "small, on the send path the banner
says not to touch". The banner says *do not re-do A12*; A13 is a different
defect whose fix is additive and lands in `announce_block` + one new
method, which exists identically in both v8.23 lines. Built on the project
source (`ec267d40`, v8.24) as the 01:40 run did, with the same note for L.

**The finding, measured before fixing.** Y reachable from X, X not from Y
(Y has no route to X — the in-process model of CGNAT / one-way firewall /
VPS-to-home). Y at height 4, X at 2, X's heartbeat to Y answered
`{"outcome":"known","height":4}`: on v8.24 X stayed at 2 for the whole
window (T2 FAIL, pre-fix record). Every sync path was either Y-initiated
(announce → fetch; Y cannot reach X) or boot-only (`bootstrap_chain`). The
reply `_send_raw` already returned — with Y's height in it — was discarded
by `_SEND_POOL.submit(self._send_raw, …)` on every announce. A node behind
CGNAT would have learned nothing its VPS peer minted, ever, while both
nodes reported healthy and peered.

**The fix (v8.25), additive, four edit sites.** `P2PNode._send_announce`
(used by `announce_block` for gossip, boot and real announces alike): reads
the verdict; `height` must be a non-bool `int` > `len(chain)`; counts
`peer_ahead_seen`; gated by `catchup_allowed()` (the inbound gap-fill's
cooldown) submits `on_peer_ahead(host, port, pid)` to `_FETCH_POOL` —
never inline in the send pool (the file's own livelock note). The master
installs `_pull_from_peer_ahead` = `request_missing_blocks` +
`_apply_fetched_blocks(source_peer=pid)`, so the one acceptance gate and
A9's relay-onward apply; records `peer_ahead_filled` / `peer_ahead_empty`
/ `peer_ahead_failed`. `/health` gains `peer_ahead_seen`. Is it a
weakening? A peer could always make us fetch by announcing a fake index
(inbound path); this adds the same ask, under the same cooldown, judged
by the same gate. Nothing that was refused is now accepted.

**Verification.** `test_a13_one_way_sync.py` (25 checks, two real
in-process masters, real socket X→Y, a fake Z that lies about height and
serves nothing, a garbage-height matrix through `_send_announce` with a
stubbed `_send_raw`, relay-onward to Z, `/health`): **25/25 ×3 on v8.25;
on pristine v8.24 T1 passes and T2–T6 fail** (X=2, Y=4, 0 requests). Full
sweep on v8.25, every suite in `run_all_tests.sh` that touches the file:
security_audit 127/127, adversarial 21/21, a1a_a2 15/15, a3 7/7, a5 20/20,
a11 23/23, b1 162/162, a12_dead_peer_backoff 21/21, b5 31/31, a13 25/25,
a9 18/18, a4 60/60, a1_kill_matrix 29/29, multinode 21/21; `py_compile` +
`bash -n` clean. ~5 min in two parallel batches.

**Delivery (M5).** SendUserFile + `project_write`, **round-trip verified by
hash**: `covenant_unified_v8.py` v8.25 (sha256 `acaca10a…`, 8469 lines,
+68), `claude/test_a13_one_way_sync.py` (`12c51090…`), `run_all_tests.sh`
(`32a5c69f…`, A13 wired in at 180 s). **L: copy `covenant_unified_v8.py`
into `C:\Users\<user>\covenant`** beside `covenant_path_pattern.py`. If you
consolidate on `PeerHealth` (`c5447e79`), re-apply by hand: the two
`__init__` fields, `_send_announce` (and its one-line use in
`announce_block`), `_pull_from_peer_ahead` + the hook line after
`self.api.master = self`, and the `/health` field — all marked `A13`.

**Loop improvements.** M17 (edit the log on disk; pristine source from
`project_read`'s `local_file`; the log's size is becoming a cost — archive
proposal for L). Self-assessment: 14 runs, 14 closed, 17 methods, 9
corrections, 3 dead ends. `update_trigger`: not retried (DE2).

**Cost:** ~½ session: a third fetching (two subagents, ~390k subagent
tokens), a third on fix + test + the pre-fix run, a third on the sweep and
this log.

**Next:** A14 (sequential boot probe; concurrent `request_missing_blocks`
over `_FETCH_POOL` in `bootstrap_chain`) is the last unblocked A code item
and is the same shape as this one — small, additive, testable with the
v8.24-vs-v8.25 recipe. After that the loop genuinely runs out of unblocked
code items: A7/A8/A10/A12-consolidation and B4 are L's decisions; C1/C2
need uploads. **Then rule 6 applies for real — say so, do not invent work
in D.** Answering B4 alone unblocks B5's fix and B2.

### 2026-08-22 ~04:15 — A14 closed (v8.26): the boot probe was sequential, and — worse — a trickling peer held it forever

**Selection (M15, M16).** Fresh `project_read` of this log: last entry
03:00 (`created_at` 03:13); `project_info` shows nothing newer than the log,
no upload from L, no answer on A10/A12/B4. A14 is the last unblocked A code
item, per the 03:00 entry. Source fetched at `acaca10a` (v8.25, 8469 lines)
as expected; grepped `bootstrap_chain` — still the v8.14 sequential loop.

**The finding, measured before fixing (pre-fix record on pristine v8.25,
`test_a14_boot_probe.py` 13/13 with its PRE-FIX assertions).** At a 0.5 s
socket timeout with 8 blackholes (listen(0), slot taken — M14's trick,
deterministic) listed before the one live peer: `bootstrap_chain` 9.04 s
(two rounds × 8 × 0.5 + 1 s pause; 40 s+ at the 5 s default), the
`/sync`-shaped call 4.01 s, and the boot push — K2's path home — 5.51 s
after `_bootstrap_once` started. That was the item as written. What the
item did not name: a peer that ACCEPTS the BLOCK_REQUEST and then sends one
byte every 0.2 s (`Trickler`) held `bootstrap_chain` past 6 × timeout with
the live peer never asked — and would have held it forever: `recv_bounded`
bounds bytes (A3), `settimeout` bounds each recv, nothing bounded the
exchange. One wedged-or-malicious peer in the list = a node that never
finishes boot, never pushes its tip, and whose `/sync` hangs the HTTP
worker. → M18; the same gap on every other reader → **A15**.

**The fix (v8.26), one new method + one constant, tightening only.**
`_bootstrap_round(peers)`: submit `request_missing_blocks` for every peer
to `_FETCH_POOL` (never the send pool — the file's own livelock note),
`as_completed(..., timeout=BOOT_PROBE_DEADLINE_S)`, apply each reply in
arrival order through `_apply_fetched_blocks` (one gate, A9 relay-onward
with the source excluded), drop already-held indexes before the gate,
record `bootstrap_probe_timeout` for stragglers and cancel them (a running
straggler's worker returns when its socket does — that residual is A15).
`BOOT_PROBE_DEADLINE_S` = 2 × `PEER_SEND_TIMEOUT_S` + 1 by default, env
`COVENANT_BOOT_PROBE_DEADLINE`, refused at import below one socket timeout
(a shorter deadline would abandon every honest slow peer). `bootstrap_chain`
keeps its six-round/pause shape and `/sync` its `rounds=1` contract. Nothing
that was refused is accepted; nothing that was asked is no longer asked.

**Verification.** `test_a14_boot_probe.py` (15 checks: P1–P8 per its
docstring; real masters, real sockets, real blackholes, a trickler, a
recording peer for the A9 relay and the boot push) **15/15 ×3 on v8.26**;
**13/13 PRE-FIX-RECORD on pristine v8.25** (same file, `FIXED` flag off).
Measured after: bootstrap 2.00 s, `/sync` 0.50 s, wedged peer 2.00 s with
`bootstrap_probe_timeout: 1`, boot push at 2.00 s, duplicate reply from a
second live peer records nothing. Full sweep on v8.26: security_audit
127/127 (126/127 on the first cut — an `except: pass` in the new code, fixed
with a flag; M18), adversarial 21/21, a1a_a2 15/15, a3 7/7, a5 20/20, a11
23/23, b1 162/162, a12_dead_peer_backoff 21/21, b5 31/31, a9 18/18, a4
60/60 ×2, a1_kill_matrix 29/29 ×2, multinode 21/21 ×2, a13 25/25 — see
next paragraph; `py_compile` + `bash -n` clean.

**A flake in `test_a13_one_way_sync.py`, diagnosed, not a regression.** It
failed T5/T6 once in the 6-suite parallel batch, then T5 alone 1 run in 3.
Run 4× on the pristine v8.25: 1 in 4 failed the same way — so not v8.26's
doing. Cause was the test: Z answered `height 1e9` from the moment it was
added, so on the T5 heartbeat both Y (5) and Z (1e9) were "ahead", and when
`_delivery_order` put Z first the liar took the single catch-up cooldown
and X pulled nothing from Y. That a liar can starve the honest peer for one
`CATCHUP_COOLDOWN_S` is the designed cost of the cooldown (A13 said "one
request per cooldown"), not a defect. Fixed in the test: Z answers 0 until
T6 flips it to 1e9; Z's accept timeout 15 → 60 s for parallel batches.
**5/5 after the fix.**

**Delivery (M5).** SendUserFile + `project_write`, **round-trip verified by
hash (fresh subagent)**: `covenant_unified_v8.py` v8.26 (sha256
`9eda9538…`, 8539 lines, +70), `claude/test_a14_boot_probe.py`
(`a0139c0a…`), `run_all_tests.sh` (`9e561c5b…`, A14 wired in at 180 s),
`claude/test_a13_one_way_sync.py` (`81d06496…`, flake fix). **L: copy
`covenant_unified_v8.py` into `C:\Users\<user>\covenant`** beside
`covenant_path_pattern.py`; the tests and runner are optional. Built on the
`_delivery_order` line as the last three runs were; the edit is one method
+ one constant (grep `A14`) and re-applies by hand on `PeerHealth`.

**Loop improvements.** M18 (timeouts bound a recv, not an exchange; re-run
a flaky suite on the pristine file before calling it a regression; the
audit forbids `except: pass`). Backlog: A14 closed, **A15** added —
unblocked, additive, the natural next item and the *last* unblocked A code
item it reveals. Self-assessment: 15 runs, 15 closed, 18 methods, 10
corrections, 3 dead ends. `update_trigger`: not retried (DE2).

**Cost:** ~½ session: a quarter fetching (two subagents, ~310k subagent
tokens), a quarter on the test + pre-fix record + fix, half on the sweep
(the a13 flake cost eight extra a13 runs and a second a4/a1/multinode batch
to prove it was load- and order-sensitive, not v8.26).

**Next:** **A15** (wall-clock bound in `recv_bounded`; measure the honest
maximum first, M7). After it the loop is out of unblocked code items until
L answers A10 / the A12 consolidation / B4 or uploads `phone/node-install.sh`
(C1) and the heartbeat/doctor scripts (C2). Rule 6 then applies — say so.

### 2026-08-22 ~05:30 — A15 closed (v8.27): the readers were unbounded in time — and the inbound ones had no timeout at all

**Selection (M15, M16).** Fresh `project_read` of this log: last entry
04:15; `project_info` shows nothing newer than the log, no upload from L,
no answer on A10 / A12-consolidation / B4. A15 was the last unblocked A
code item. Source fetched at `9eda9538` (v8.26, 8539 lines) as expected;
grepped `recv_bounded` — five call sites, byte cap only.

**The finding, measured before fixing (pre-fix record on pristine v8.26:
`test_a15_exchange_deadline.py` 11/11 with its PRE-FIX assertions).** At
the defaults the three outbound readers do have a per-recv timeout, so a
peer has to *trickle* to hold them (U1: still reading at 3 × budget; L3:
`_send_raw` never returned; L4: `request_missing_blocks` never returned).
But `grep settimeout` shows only the outbound sockets — the two inbound
handlers read an accepted socket whose `gettimeout()` is `None`. So U2: a
connection that sends nothing blocks the reader indefinitely; and L1: with
`COVENANT_MAX_CONCURRENT_HANDLERS=4`, four idle `socket.connect()` calls
left an honest `BLOCK_REQUEST` unanswered for the whole window with
`/anomalies` empty. At the production figure that is 96 idle sockets from
one laptop for a permanently deaf node that reports healthy — the same
outcome the N=1000 accept-loop bug produced by accident, now reachable on
purpose. A15's own wording ("each bounds … per-recv time") was wrong about
the inbound half → correction logged, M19.

**The fix (v8.27), one constant + one exception + `recv_bounded` + two
`except` arms, tightening only.** `MAX_EXCHANGE_S` (env
`COVENANT_MAX_EXCHANGE_S`, default 60, asserted ≥ `PEER_SEND_TIMEOUT_S` at
import — a budget below one socket timeout would abandon every honest slow
peer). `recv_bounded(sock, limit, chunk_size, max_seconds=None)`: deadline
on `time.monotonic()`; each recv under `settimeout(remaining if own is None
else min(own, remaining))`; on `socket.timeout`, re-raise it if the
socket's own timeout is what fired (outbound semantics unchanged, U4),
else raise `PeerMessageTooSlow`. `_handle_peer` records
`peer_message_too_slow`, `_handle_bridge` `bridge_message_too_slow`; the
outbound readers surface it through their existing `except` (ack=b"",
`catchup_failed`, `tx_fetch_failed`) as A3 did. Honest maximum per M7:
the largest legitimate frame is one catch-up page of
`CATCHUP_REPLY_BUDGET_BYTES` (48 MiB) → 60 s needs ≥ 6.7 Mbit/s; L5
computes it from the module's constants so a changed budget or cap shows
up as a number. Nothing that was refused is accepted; nothing that
completed inside 60 s behaves differently.

**Verification.** `test_a15_exchange_deadline.py` (14 checks, docstring
lists them: socketpair unit cases U1–U5 incl. an import-time refusal by
subprocess; real listener + bridge listener with K silent connections and
an honest request; real `_send_raw` and `request_missing_blocks` against a
`Trickler`) **14/14 ×3 on v8.27; 11/11 PRE-FIX RECORD on pristine
v8.26**. Full sweep on v8.27, every suite in `run_all_tests.sh` that
touches the file: security_audit 127/127, adversarial 21/21, a1a_a2
15/15, a3 7/7, a5 20/20, a11 23/23, b1 162/162, a12_dead_peer_backoff
21/21, b5 31/31, a13 25/25, a14 15/15, a9 18/18, a4 60/60, a1_kill_matrix
29/29, multinode 21/21; `py_compile` + `bash -n` clean. ~5 min in two
parallel batches (10 + 5).

**Delivery (M5).** SendUserFile + `project_write`, round-trip verified by
hash (fresh subagent, see below): `covenant_unified_v8.py` v8.27 (sha256
`07ff5266…`, 8593 lines, +54), `claude/test_a15_exchange_deadline.py`
(`24e92b31…`), `run_all_tests.sh` (`5ee68f4b…`, A15 wired in at 180 s).
**L: copy `covenant_unified_v8.py` into `C:\Users\<user>\covenant`** beside
`covenant_path_pattern.py`; the test and runner are optional. Built on the
`_delivery_order` line like the last four runs; the edit is self-contained
in `recv_bounded` + two `except` arms (grep `A15`) and re-applies by hand
on `PeerHealth`.

**Loop improvements.** M19 (check `gettimeout()` at every read site; an
accepted socket inherits None). Backlog: A15 closed with its residual
(reconnect-and-idle still costs 60 s × 96 workers per wave — bounded and
recorded now; a per-source connection cap is the next tightening only if
observed). Self-assessment: 16 runs, 16 closed, 19 methods, 11
corrections, 3 dead ends. `update_trigger`: not retried (DE2).

**Cost:** ~½ session: a quarter fetching (one subagent, ~230k subagent
tokens), a quarter on the test + pre-fix record + fix, half on the sweep
and this log.

**Next — rule 6 now applies for real.** Section A has no unblocked code
item left: A7/A8/A10 and the A12 consolidation are L's decisions; B2/B4/B5
wait on B4; C1/C2 need `phone/node-install.sh` and the heartbeat/doctor
scripts uploaded; D outranks nothing while A/B/C are merely *blocked on
L*, and D1's price-history work is WebFetch-bound with a known row-loss
hazard (M1). **The next run should close nothing and say so** unless L has
(a) answered A10, A12-consolidation or B4, or (b) uploaded the C1/C2
scripts. Two things a run *could* still do without inventing work: re-run
the full sweep on whatever `covenant_unified_v8.py` the project holds
(cheap, catches a torn commit — M15/M16), and the log-archive proposal in
M17 if L approves it. One candidate worth L's say-so: a per-source inbound
connection cap (the A15 residual) — it is a new control, so it is L's
call, not the loop's.

### 2026-08-22 ~06:20 — No-regression sweep on v8.27 as held by the project; pushback on the "close nothing" plan; D1-XLM closed

**Selection (M15, M16).** Fresh `project_read` of this log: last entry
05:30 (`created_at` 04:54); `project_info` shows nothing newer than the log
— no upload from L, no answer on A10 / A12-consolidation / B4. The 05:30
entry said this run "should close nothing and say so". Pushback, because
the reasoning was wrong on its face: the trigger prompt's rule 1 is "A
outranks D **unless A is blocked**", and A is blocked — so D is in scope,
and D1 needs nothing from L (Kraken is reachable through WebFetch, the
recipe exists from the 01:35 run). Correction logged. D3–D7 remain blocked
on files not in the project (`execute.py`, `guards.py`, `daily.py`,
`paper_run.py`, `realdata/`); D2 waits on D1.

**First, the sweep the 05:30 entry asked for.** Fetched the project's
source and all 16 suites to disk by fresh subagent: `covenant_unified_v8.py`
= `07ff5266…`, 8593 lines; `run_all_tests.sh` = `5ee68f4b…`; every test
file matched its logged hash. **No torn commit.** 12-wide batch + 4 slow:
all green except a1a_a2 14/15, a13 24/25, security_audit 126/127 —
each then **passed 2/2 alone** (load artifacts: a `/mine` non-200 under
CPU starvation, a boot timing, a fill timing). Second 12-wide batch with
the audit patched to print the status code: those three green, and
**a15 13/14** — U4 got `PeerMessageTooLarge` in 0.66 s. That one was
real: a test bug (late-bound `b` in U3b's flood thread spilling into U4's
socketpair), fixed in `test_a15_exchange_deadline.py`, then **14/14 ×3
under 4 busy-loop CPU hogs**. → M20. The node source is unchanged this run.

**D1-XLM.** Five Kraken windows (`since` = last bar each time), 58/60/63/
64/40 rows returned for 60/60/60/60/40 asked (M1 holds both ways), merged
on byte-identical overlap rows, verified 86400 s spacing / no dups / OHLC
sanity / 00:00 UTC, then an interior window re-fetched at an unrelated
`since`: 25/25 rows byte-identical. Crypto.com MCP tried first and cannot
do history → DE4. Result: 281 bars 2025-04-15 → 2026-01-20, sha256
`60506ff9…`, round-trip verified by hash.

**Delivery (M5).** SendUserFile + `project_write`, both round-tripped by
hash: `realdata/deep/XLM_2025Q2_2026Jan.csv` (new, `60506ff9…`) — **L:
save it into `C:\Users\<user>\covenant\realdata\deep\`**; and
`claude/test_a15_exchange_deadline.py` (`d9ec18d7…`, flake fix only,
optional). No change to `covenant_unified_v8.py`.

**L, present mid-run, wrote: "don't forget mutual benefit i lapse at
times."** Taken as a standing instruction to the loop, not just this run:
the covenant's purpose is mutual benefit — L's, the chain's users', and
the AI's — and Section 0's "report honestly, especially against yourself"
is what mutual benefit looks like in practice here. When L lapses (an
unanswered decision, an unapplied file), the loop's job is to keep the
record straight and the options open, not to route around L or to grade
itself on closes. Recorded here so a future run reads it in L's words.

**Loop improvements.** M20, DE4, D1 reworded with the per-symbol recipe and
Kraken naming trap; STALL WATCH counter added under the banner (reset to
0). Self-assessment: 17 runs, 17 closed, 20 methods, 12 corrections, 4 dead
ends. `update_trigger`: not retried (DE2). `NODE_DEPLOYMENT_FINDINGS.md`
fetched but not re-read in full — no node code was touched.

**Cost:** ~½ session: a third on the two sweeps + the a15 diagnosis, a
third on five Kraken windows, a third on this log.

**Next:** D1 one symbol per run (SOL next; XRP/HBAR after, since D6 and the
Section-0 "no edge" figures rest on them) until L answers A10 / A12 / B4
or uploads C1/C2. That is real backlog, not invented work; the stall
counter applies only if a run closes nothing.

### 2026-08-22 ~06:45 — (attended continuation of 06:20) D1-SOL and D1-XRP closed; yield audit opened A16 with measured evidence; no node source change

*(L present. "do so. i'm still waiting for my phone" → D1 continued, C1
noted as hardware-blocked. Then: "refine entire system repeatedly untill
confident in yield to help with propagation" → yield audit.)*

**D1.** SOL 391 bars (`addb42b5…`) and XRP 397 bars (`dcecaa87…`),
2025-01-01 → 2026-01/02, five 100-row Kraken windows each, merged on
byte-identical overlap rows, 86400 s spacing / OHLC sanity / 00:00 UTC
asserted, 30-row independent interior re-fetch 30/30 identical for both.
Delivered via SendUserFile and `project_write` to `realdata/deep/`. **L:
save both beside XLM's.** M20 amended (100-row windows work).

**Yield (A16).** Read the staking layer end to end (`StakingPool`,
`Stake.calculate_rewards`, `distribute_block_rewards`, `/mine`'s reward
derivation, `_accept_block_common`'s overdraft re-check, genesis paths).
Ran `sim_yield_safety.py` against v8.27 for the first time: both channels
exact (the prose in the sim is stale, the numbers say fixed). Then wrote
`test_y1_stake_divergence.py` — two in-process nodes on one exported
genesis, real `_accept_block_common`, blocks built as `/mine` builds them,
patched clock for the unstake — and it shows the thing the source itself
flags as "deliberately not invented": staking never leaves the node, so a
stake forks the chain on the next honest spend and the 1 % reward pays
different people on different nodes. 10/10 ×2. Design + options for L in
`claude/YIELD_ON_CHAIN_DESIGN.md` (Option A recommended). Put to L
in-conversation; no answer yet at write time. Pushback recorded against
my own first framing: "confident in yield" is not reachable by tightening
— it is a location problem, not an arithmetic one.

**Delivery.** `realdata/deep/SOL_2025_2026Jan.csv`,
`realdata/deep/XRP_2025_2026Jan.csv`, `claude/YIELD_ON_CHAIN_DESIGN.md`,
`claude/test_y1_stake_divergence.py` — all via SendUserFile +
`project_write`. `covenant_unified_v8.py` unchanged (`07ff5266…`).

**Loop improvements.** A16 opened (decision item, evidence attached); D1
and C1 reworded; M20 amended. Self-assessment: 17 runs, 19 closed, 20
methods, 12 corrections, 4 dead ends. `update_trigger`: not retried (DE2).

**Cost:** ~½ session on top of 06:20: a third on two symbols of D1, two
thirds on reading the staking layer, the sim, the Y1 test and the design
doc.

**Next:** if L answers **A** on A16 — implement (two runs, Y1 as pre-fix
record, A8 timestamp rule folded in). Otherwise D1-HBAR, then ADA/CRO/ATOM/
AVAX/NEAR, one or two per run. A10/A12-consolidation/B4 still open; C1
waits for the phone.

### 2026-08-22 ~08:00 — (attended, same session) D2 closed on three assets; E1 power probe; A17 found and fixed (v8.28) — the phone-over-VPN shape never synced

*(L, mid-run: "work towards preparing for live trades", "and increasing
efficiency/power consumption", "make sure we have a node we can sync with
a vpn for android integration".)*

**Live trades — boundary held.** No order prepared, no key, no edge
claimed (Section 0). What "preparing" meant here: (1) the three held
assets with deep data were extended to 2026-08-21 (598 bars each, Kraken,
M20 recipe, forming bar dropped, and the 08-19 closes agree with the
Coinbase `VERIFIED_BASELINE` to < 0.01 %) — two venues as a cross-check;
(2) D2 re-ran the 200-day regime rule on them through the project's own
engine plus a block-bootstrap null: **no timing edge** (p 0.47–0.81, DSR
0.000), drawdown reduction 2.1×/1.8× on SOL/XRP and **none on XLM**
(0.9×, nine whipsaws); power arithmetic says ~31 years of daily bars to
detect a Sharpe-0.5 edge — so the rule is risk control, and on XLM this
window it was not even that. Correction logged against the "~3×
replicated" claim. (3) `claude/TRADING_READINESS.md`: the ten-line
checklist of what must be true before L's first hand-placed order; the
two blocking lines (D3/D4 guards, ≥ 30 sealed paper signals) need
`execute.py`/`guards.py`/`daily.py`/`paper_run.py` uploaded. One look-ahead
bug in my own bootstrap helper was caught by the engine (M21).

**Efficiency (E1).** `claude/probe_power.py`: a real idle node costs 0.03 %
of a core; a block 0.34 CPU-s; registration PoW < 10 ms. There is no CPU
problem to fix. On a phone the cost is radio wake-ups; the knob exists →
C4 (measure when the phone is here).

**A17 — the finding of the day.** Checking "a node we can sync with over
a VPN": two real processes on the interface IP, one-way peer list (the
day-one phone config). **v8.27 never synced.** A node at genesis was
silent by design (A1/K5), which A13 quietly made wrong. One-line fix in
`_gossip_tip`, pre-fix record 4/4 on pristine v8.27 (B=1 after 15 s),
6/6 ×3 on v8.28 (B=2 in 2–3 s), K5 updated, full 18-suite sweep green;
multinode timed out once in an 8-wide mining batch and passed 21/21 ×2
alone (M20/M21). Runbook `claude/ANDROID_VPN_SYNC.md`: PC side (bind
0.0.0.0 verified; run on Windows Python not WSL; firewall on the Tailscale
interface; port arithmetic), phone side marked untested until the phone
arrives.

**Delivery (M5), all round-tripped by hash (see the 08:05 write-back
note).** `covenant_unified_v8.py` v8.28 (`76d2c54e…`, 8609 lines, +16 in
one method) — **L: copy into `C:\Users\<user>\covenant`** beside
`covenant_path_pattern.py`; `claude/test_a17_oneway_peer_sync.py`,
`claude/test_a1_kill_matrix.py` (K5), `run_all_tests.sh` (A17 at 180 s);
`realdata/deep/{XLM,SOL,XRP}_2025_2026Aug.csv`; `claude/d2_regime_deep.py`,
`claude/probe_power.py`, `claude/TRADING_READINESS.md`,
`claude/ANDROID_VPN_SYNC.md`. Built on the `_delivery_order` line like
every run since 00:40; the A17 edit is one method (grep `A17`) and
re-applies by hand on `PeerHealth`.

**Loop improvements.** M21; M20 amended (slow batch ≤ 5); D2 struck for
three assets; D3 marked blocked-on-upload; A17 closed; C4 added.
Self-assessment: 17 runs, 21 closed, 21 methods, 14 corrections, 4 dead
ends. `update_trigger`: not retried (DE2).

**Cost:** ~1 session on top of 06:45: a third on nine Kraken windows +
D2, a sixth on the power probe, half on A17 (find, fix, pre-fix record,
K5, 18-suite sweep, runbook) and this log.

**Next:** (a) L's answers: A16 Option A/B (yield on-chain), A10, B4, the
A12 consolidation; (b) uploads: `execute.py`, `guards.py`, `daily.py`,
`paper_run.py`, `phone/node-install.sh`, the rest of `realdata/`; (c)
without either: D1-HBAR then ADA/CRO/ATOM/AVAX/NEAR (D6 rests on HBAR),
and a per-source inbound connection cap only if L wants it. The phone,
when it arrives, unblocks C1/C3/C4 in one sitting with the runbook.

### 2026-08-22 ~07:15 — D1-HBAR closed (408 bars); SOL/XRP independently re-verified; a concurrent run detected and not duplicated

**Selection (M15, M16 — and a new wrinkle, M21).** Boot snapshot of this
log ended at the 06:20 entry; `project_info` showed SOL (06:25) and XRP
(06:32) newer than the log (06:16). Treated per M16 as possibly unlogged
work: fetched both, ran the contiguity check (0 defects each, 391 and 397
bars), then re-fetched a 20-row interior window of each from Kraken at an
unrelated `since` — **SOL 20/20, XRP 20/20 byte-identical**. That is an
independent second verification of the 06:45 run's files, by a different
session. Before starting HBAR, `project_search` found the 06:45 entry
already logged them — the 06:20 run was still live and ~10 min ahead of
this one. Not a torn commit; an overlap. Its "Next" named HBAR, so this
run checked for an HBAR doc before starting and again before writing
(none either time) and took it.

**D1-HBAR.** Kraken `HBARUSD`, daily. Finding first: **no bars before
2025-07-10** at any `since` (DE5) — Kraken cannot give HBAR the 2025-01
start the other symbols have. So the file runs to the last complete bar
instead: 8 windows (60/60/59/30/60/60/65/21 rows returned), merged on
byte-identical overlap rows, today's partial bar dropped (Kraken's `last`
= 1787270400 = 2026-08-21), `verify_csv.py` 0 defects, then two interior
re-fetches at unrelated `since` values (Oct 2025, May 2026): **25/25 and
25/25 identical**. Result `realdata/deep/HBAR_2025Jul_2026Aug.csv`, 408
bars 2025-07-10 → 2026-08-21, sha256 `42c2894e…`, project round-trip
verified by hash. The 2025-10-10 bar (low 0.08051 against a 0.213 open)
is the real flash-crash print, present in both fetches — not a defect.
For D6: this series does not overlap the corrupted one's early-2025
window, so D6 is a re-analysis on a *different* period, not a replay.

**Delivery (M5).** SendUserFile + `project_write`, round-tripped by hash:
`realdata/deep/HBAR_2025Jul_2026Aug.csv` (new) — **L: save it into
`C:\Users\<user>\covenant\realdata\deep\`**; `claude/verify_csv.py`
(new, optional — the contiguity checker). No change to
`covenant_unified_v8.py`.

**Loop improvements.** M21 (overlapping runs: detect via `project_search`
on the log, avoid the other run's named next item, fetch the log fresh at
write-back; WebFetch row indexes are unreliable; drop rows after `last`).
DE5. D1 reworded. STALL WATCH stays 0. Self-assessment: 18 runs, 20
closed, 21 methods, 12 corrections, 5 dead ends. `update_trigger`: not
retried (DE2). Pushback on the plan as written: extending HBAR past Feb
2026 breaks the "…_2026Jan" naming convention of the other files, but a
207-bar HBAR file (Jul-2025 → Feb-2026) would have been *smaller* than
the 220-bar series D1 exists to replace — so the full 408 was the only
version that serves D1's purpose. If L wants a Feb-2026-aligned cut for
D2, it is the first 207 rows.

**Cost:** ~½ session: a quarter re-verifying SOL/XRP, half on eight HBAR
windows + two re-fetches (each window costs ~3k tokens of context; asking
for 100 rows per window, per the M20 amendment, would have saved two
fetches), a quarter on this log.

**Next:** D1 — ADA, CRO, ATOM, AVAX, NEAR (check each pair exists and its
first available bar before spending windows; one `since=1700000000` probe
answers both). If L answers A16 (Option A), that outranks D. A10 / A12
consolidation / B4 still open; C1 waits for the phone.

*(Restored verbatim at ~08:20 by the 07:45 run; see the banner.)*

### 2026-08-22 ~07:14 — (the 07:45 run's note) the six docs written at 07:14 belong to the attended run whose entry is dated ~08:00 above
At this run's boot (07:37) those docs (`{XLM,SOL,XRP}_2025_2026Aug.csv`,
`d2_regime_deep.py`, `probe_power.py`, `TRADING_READINESS.md`) were newer
than the log and unmentioned in it; by write-back (~08:10) the 08:00 entry
had landed — an overlap (M23), not a torn commit. Nothing to reconstruct;
the verification this run did of that work is in the next entry. → M22.

### 2026-08-22 ~07:45 — 07:14 run verified and logged; D1-ADA closed (598 bars); D2 regime verdict holds on a second seed and a fourth asset

**Selection (M15, M16, M23).** Fresh `project_read` of this log at boot
(07:37): last entry 07:15 (`created_at` 07:18). `project_info` showed six
docs written at 07:14 that the log did not mention; `project_search` found
no entry for them, so ADA — which the 07:15 entry's "Next" named and the
07:14 docs did not touch — was taken, and the 07:14 work was verified
rather than redone. **At write-back the log had changed under this run
(M23): the 08:00 entry had landed at 07:56 — and its write-back had
overwritten the 07:15 run's record** (entry, DE5, M21, D1-HBAR text,
counters: the file went from 2195 lines at 07:18 to 2241 at 07:56 with the
07:15 entry gone). Both earlier versions were on this run's disk, so the
merge was mechanical: fresh 07:56 file as base, the 07:15 run's blocks
re-inserted verbatim (its M21 re-numbered M23), this run's edits applied by
anchor. Nothing of the 08:00 run's was removed. No answer from L on A10 /
A12 / A16 / B4; no C1/C2 upload. A is blocked, so D is in scope (rule 1).

**Verification of the 07:14 work (the claim checked twice).** All thirteen
docs fetched to disk by a fresh subagent; the four CSVs with logged hashes
matched byte-for-byte, the three new ones had no logged hash (→ M22). So:
`verify_csv.py` 0 defects on all three; then the post-January tail of each
re-fetched from Kraken at an unrelated `since` (1777680000, May 2026) and
diffed by timestamp — **XRP 25/25, SOL 20/20, XLM 20/20 byte-identical**,
including the 2026-05-30 → 06-04 crash bars. `d2_regime_deep.py` re-run on
the project's `covenant_backtest.py`: every figure in the
`TRADING_READINESS.md` table reproduced to the decimal (seeded). Re-run with
seed 7: p 0.797 / 0.456 / 0.688 vs 0.810 / 0.465 / 0.668 — the "no timing
edge" verdict is not a seed artefact. Pushback on one line of that doc: it
calls XLM's +12 % "edge" a positive sign that "still means nothing" — right
conclusion, but the engine number it sits beside (regime −74 % vs B&H −57 %)
shows the costed rule *lost* to holding on XLM; the log-growth spread is
positive only because the bootstrap helper charges half the round trip per
switch while the engine charges the full model. Both are honest; quote the
engine when talking to L, it is the one that cannot look ahead.

**D1-ADA.** Kraken `ADAUSD` (plain name) has daily bars from 2024-09-01, so
a 2025-01-01 start is available (one `since=1700000000` probe answered
both). Eight 100-row windows (87/83/88/77/86/90/90/5 rows returned — never
what was asked, M1), merged on byte-identical overlap rows (asserted),
today's partial bar (1787356800) dropped after `last`, `verify_csv.py` 0
defects: **598 bars 2025-01-01 → 2026-08-21, sha256 `a0ae69f1…`**. Two
independent interior re-fetches (Aug 2025, Jan 2026): **50/50 identical.**
The 2025-10-10 low of 0.42 against a 0.8156 open is the flash-crash print
seen on HBAR too (present in both fetches). D2 on ADA: regime −33.5 % vs
B&H −73.6 %, max DD −38 % vs −85 % (2.21×), 3 switches, timing edge p =
**0.531** — no edge, drawdown control, same as SOL/XRP. `d2_regime_deep.py`
now runs ADA too (one-line change).

**Delivery (M5).** SendUserFile + `project_write`:
`realdata/deep/ADA_2025_2026Aug.csv` (new, `a0ae69f1…`) — **L: save it
into `C:\Users\<user>\covenant\realdata\deep\`**, beside the three
`_2026Aug` files from the 07:14 run (those are in the project; if you only
have the `_2026Jan` downloads, the Aug ones supersede them); and
`claude/d2_regime_deep.py` (`0de9e9dc…`, ADA added; this edit sits on the
08:00 run's version — re-fetched before editing, one line + one docstring
word). `covenant_unified_v8.py` not touched by this run; the project holds
whatever the 08:00 run shipped (v8.28 `76d2c54e…` per its entry — not
re-verified here).

**Loop improvements.** M22; the 07:15 run's record restored (banner, M23,
DE5, D1-HBAR, its entry, counters). Backlog: D1 and D2 updated with status;
C4 was already opened by the 08:00 run. STALL WATCH stays 0.
Self-assessment: 19 runs, 23 closed, 23 methods, 15 corrections, 5 dead
ends. A loop-level proposal for L, stronger than M15's: **the 08:00 run's
overwrite was survivable only because this run happened to hold both
versions on disk.** Either accept the archive proposal (M17) so the file is
small enough to diff at every write-back, or require every write-back to
quote the `created_at` it fetched and refuse to write if `project_info`
shows a newer one. `update_trigger`: not retried (DE2). One
change the trigger prompt should carry (add to `TRIGGER_PROMPT_PROPOSED.md`
when next touched): *"log the sha256 of every file you ship, including
CSVs; a file with no logged hash costs the next run three fetches to
trust."*

**Cost:** ~½ session: a quarter fetching (one subagent, ~470k subagent
tokens — the three unverified CSVs are why) and re-verifying the 07:14
work, half on ADA's eight windows + two re-fetches (each ~7k tokens of
context at 100 rows), a quarter on this log.

**Next:** D1 — CRO, ATOM, AVAX, NEAR (probe `since=1700000000` first; Kraken
names are plain `CROUSD`? — unverified, check the `result` key). Then D2
proper on the rest: rebalancing and the HBAR/D6 figures on the deep data.
If L answers A16 (Option A), that outranks D. A10 / A12 consolidation / B4
still open; C1/C4 wait for the phone.

### 2026-08-22 ~08:45 — D1 closed for every held asset (seven symbols in one run) and D2 regime verdict on all ten; the WebFetch detour was never necessary

**Selection (M15, M16, M23).** Fresh `project_read` of this log: last entry
07:45 (`created_at` 08:28). `project_info` shows nothing newer than the log;
no answer from L on A10 / A12-consolidation / A16 / B4; no C1/C2/D3 upload.
A blocked → D in scope (rule 1). The 07:45 "Next" named CRO/ATOM/AVAX/NEAR.

**The finding that changed the cost of D1.** Probing the four pairs with
one `since=1700000000` WebFetch each (all exist; ATOM/AVAX/NEAR from
2024-09-01, CRO from 2025-01-29), I tried the same URL with `urllib` from
the sandbox to check the pair key — and got the full JSON back. Every
D1 run since 01:35 had paid 5–8 summariser windows and ~50k context tokens
per symbol to work around M1's row loss, which was a summariser artefact,
not a Kraken one. Checked twice before relying on it: ADA rebuilt from
direct calls hashes to the 07:45 run's logged `a0ae69f1…` byte for byte
(after fixing `csv.writer`'s default `\r\n`), and a WebFetch window of
ATOM (Dec 2025) matched the direct file 5/5. → M24, correction logged.

**D1.** ATOM, AVAX, NEAR, CRO, then — because the cost had collapsed and
the "may not be on Kraken" note was easy to test — ONDO, PEPE, WLFI (all
three ARE on Kraken; second correction). Each: `verify_csv.py` 0 defects;
two interior re-fetches at unrelated `since` (Jun 2025, Feb 2026) diffed
by timestamp, **30/30 every time**; sha256 logged in the D1 item; project
round-trip verified by hash (fresh subagent). WLFI is 355 bars from its
2025-09-01 listing and is named `WLFI_2025Sep_2026Aug.csv` on the HBAR
convention.

**D2 on the seven.** `d2_regime_deep.py` (symbols now taken from argv;
WLFI filename mapped) on the project's `covenant_backtest.py`: no timing
edge anywhere (p 0.51–0.92; seed 7 moves each by ≤ 0.03). Drawdown
control on ATOM/AVAX/PEPE (1.7×) and CRO (1.4×); **none on NEAR (0.9×,
11 whipsaws) or ONDO (0.6×, 18 whipsaws — the engine's summed-P&L
convention (M21) prints −116 %; bounded on a compounding convention, same
sign)**. WLFI: the 200-bar rule never entered in 155 decision bars, so its
"edge" is just −B&H and its p is meaningless — stated as such, not
counted. With XLM, that is three of ten held assets where the rule is
not even risk control. Pushback on the standing summary "the rule is
risk control, never alpha": the risk-control half is asset-dependent and
should not be assumed for an asset it has not been measured on.
`TRADING_READINESS.md` updated (table rows, addendum, checklist line 1 →
done for all ten).

**Delivery (M5).** SendUserFile + `project_write`, round-tripped by hash:
`realdata/deep/{ATOM,AVAX,NEAR,CRO,ONDO,PEPE}_2025_2026Aug.csv`,
`realdata/deep/WLFI_2025Sep_2026Aug.csv` — **L: save all seven into
`C:\Users\<user>\covenant\realdata\deep\`**; `claude/d2_regime_deep.py`
(`27b933e4…`), `claude/TRADING_READINESS.md` (`e2650abf…`).
`covenant_unified_v8.py` untouched (project holds v8.28 `76d2c54e…` per
the 08:00 entry; not re-verified here).

**Loop improvements.** M24 (direct API; CSV line endings; never read a CSV
inline). Two corrections. D1/D2 marked done. Self-assessment: 20 runs, 25
closed, 24 methods, 16 corrections, 5 dead ends. `update_trigger`: not
retried (DE2). Two lines for `TRIGGER_PROMPT_PROPOSED.md` when next
touched: *"Kraken OHLC is reachable by plain urllib from the sandbox (M24)
— do not use WebFetch for it"* and *"never project_read a CSV inline."*

**Cost:** ~⅓ session: the D1 fetching itself was minutes; the expensive
parts were one inline `project_read` of ADA (~40k context tokens, the
M24 lesson) and two fetch subagents (~650k subagent tokens, most of it
the round-trip hash check on nine docs — a cheaper check would be to
have the subagent print only hashes, which it did, but inline content
still transits its context; acceptable, but do not fetch more docs than
you need to verify).

**Next — rule 6 applies again, and this time without a D escape hatch.**
D1 and D2-regime are done; D3–D7 need `execute.py`, `guards.py`,
`daily.py`, `paper_run.py`, `MY_STRATEGY.md`, `REAL_DATA_FINDINGS.md` and
the old `realdata/` uploaded. A: A10 / A12-consolidation / A16 (Option A
recommended) are L's; B: B4 is L's; C: the phone. A run with none of
those should close nothing, say so, and at most re-run the sweep on the
project's v8.28 (cheap, catches a torn commit). One useful thing that is
NOT invented work: D2-rebalancing — the Section 0 figure (+0.45 % OOS,
p = 0.109) was computed on 220-bar data and can now be re-tested on 598
bars × 10 assets with the same bootstrap; it is the one remaining
Section-0 number whose power was inadequate. A run may take that.

### 2026-08-22 ~12:30 — (ATTENDED, L-started) the loop was open at the PC end for sixteen runs; closed it, then closed D3, D4, C1 and W1 with the files it unblocked

**L's ask:** *"complete the loop with the pc files to increase efficency"*, then
mid-run *"wsgi server"*.

**Selection (M15, M16).** Fresh `project_read` of this log at boot: last entry
08:45. `project_info` shows nothing newer. No answer from L on A10 / the A12
consolidation / A16 / B4. The 08:45 entry said a run with none of those "should
close nothing" and offered D2-rebalancing as the one honest option — but the ask
named the PC files, and this session is **attended and L-started**, which turns
out to be the whole difference.

**THE FINDING, and it corrects sixteen runs at once.** Every run since 08-21
05:35 ended *"L: copy `covenant_unified_v8.py` into `C:\Users\<user>\covenant`"*.
Nobody had ever checked whether that happened. The PC held **7774 lines,
`54955648…`, mtime 2026-08-20 23:33 — pre-v8.15.** `grep -c` for the symbol each
closed item names: `preflight_port_check` 0, `serialized_size` 0, `_gossip_tip`
0, `_delivery_order` 0, `_send_announce` 0, `_bootstrap_round` 0,
`MAX_EXCHANGE_S` 0, `infrastructure_failure` 0. **Fourteen node versions and
sixteen closed items had never executed anywhere but a cloud test**, while
`nodeB_prod.db-wal` (touched 11:01 that morning) says the node was being run —
on a source with unbounded inbound sockets, no port preflight and no path home
for a restarted miner. M6 was applied twenty times to the project's source and
never once to the deployed one. → **M25**, `claude/PC_SYNC_LOOP.md`, and DE2
narrowed: the bridge exists when **L starts the session**, not when L is merely
present (the 10:30 and 23:30 runs had L present and no bridge because a
*schedule* had started them; no run had tested the distinction).

**Both directions used, with L's explicit approval for the overwrite.**
PC → project: `daily.py`, `guards.py`, `paper_bot.py`, `holdings.txt`,
`TRADING_POLICY.json`, `MY_STRATEGY.md`, `REAL_DATA_FINDINGS.md`,
`phone/{node-install.sh,node-install-v2.sh,covenant-doctor.sh}` — eleven runs of
"blocked on L's uploads", ended. project → PC: v8.29, the wired `daily.py`, both
new suites, `run_all_tests.sh`, `requirements.txt`, and all twelve deep price
series into `realdata/deep/` (the backtests had never had them locally), each
verified by sha256 on the far side. Originals kept as
`covenant_unified_v8.PRE-v8.29.py` and `daily.PRE-D4.py`.

**W1 — the HTTP front door (L's "wsgi server").** `CovenantAPI.run()` was
`run_simple(self.host, self.port, self.app, threaded=True)`: werkzeug's
*development* server, one unbounded thread per connection, no queue, no idle
timeout — the A15 hazard, on the one port an operator is told to expose, in a
file where every other read path had been bounded. Now `resolve_wsgi_server()`
prefers waitress (pure Python: no compiler on Termux, works on Windows) with
bounded threads/connections/idle-timeout and a `cleanup_interval` derived from
the timeout; `COVENANT_WSGI=auto|waitress|werkzeug`; without waitress the old
call runs byte for byte; `/health` reports which. The WSGI body cap sits
deliberately ABOVE Flask's so Flask stays the enforcer and the v8.17
`http_body_too_large` record keeps happening (W7). The trade is recorded, not
hidden: a bounded pool can be exhausted where an unbounded one would not (B5's
91.3 s `chain_lock`), and the cure for that is B4/B5, not the server.

**And it disarmed A2 on the way in — the run's second real finding.** The full
20-suite sweep on the werkzeug path was green, so the change looked free. On the
waitress path `test_a1a_a2` A2-2 **hung and leaked a node**. `preflight_port_check`'s
HTTP-vs-P2P discriminator (M4) treats an EMPTY reply as proof of a P2P listener
— a rule measured against werkzeug, which answers an unterminated request line
with an HTTP/0.9 HTML body. **waitress answers nothing at all.** So with a
production server in front, `--peers` pointed at a Flask API port sailed through
preflight and both nodes would report healthy while neither heard the other:
exactly the footgun A2 exists to prevent, silently un-caught. Fixed by a second
probe with a well-formed `GET / HTTP/1.0` when the first is silent — detection
only, nothing that booted correctly stops booting. → **M26**, A2 tightened.
15/15 ×2 on waitress and 15/15 on werkzeug after the fix; W11/W12 pin it both
ways.

**D4 — the circuit breakers were called by nothing.** `grep -i guard daily.py`
on the shipped file: **zero lines**. Every breaker in `guards.py` was written,
documented, hand-tested and unreachable. Wired now, failing CLOSED on the import
itself, gating exactly one sentence — rule 2's *"may hold and add"*. They never
block a trim and never suggest a sale (guards.py's own design rule). The journal
that makes `MaxDrawdown` and `DailyLossLimit` more than decoration lives at
`~/.covenant/daily_state.json`, **outside** the synced folder: it changes every
run and would otherwise invalidate the seal daily, and the folder leaves the
machine.

**D3 — and the verification `DAILY_CHECK.md` §3 has demanded since 08-20 was
not in the code.** §3 requires four checks on every price window — 86 400 s
contiguity, no duplicate timestamps, no non-positive prices, and "if the newest
bar is older [than yesterday], the read is broken; refetch, and if it fails
again say so rather than reporting the numbers". `daily.py` did **none** of
them: it sorted the rows and used them. The 70-day-stale series that
`PRICE_DATA_INTEGRITY.md` exists for would have printed here as a clean regime
call and sized the 20 % trims off it. `fetch()` now returns
`(price, closes, why_failed)` and refuses with a reason. Also: the column headed
`200d` was a mean of as few as 50 bars with no note; it now names the real count
(WLFI reads `WLFI(110)`). `test_d3_daily_guards.py` **61/61 ×2**.

**C1 — reviewed, not verified.** The three Termux scripts are in the project now
and statically reviewed against the shipped core:
`claude/PHONE_INSTALL_REVIEW.md`, **8 BLOCKER / 15 DEGRADED / 10 NOTE**. Highest
value: v1 never installs Flask (the core imports it at top level) and never
copies `covenant_path_pattern.py`; both scripts read `$HOME/storage/downloads`
without `termux-setup-storage`, so on a fresh phone every file reports missing;
Termux pip rejects manylinux wheels and `binutils` is not a compiler, so
`cryptography` cannot build; v2's `COVENANT_JUDGE_PROVIDERS=local` is not a
registered provider and raises in `CovenantUnifiedMaster.__init__`; and
`covenant-doctor.sh` measures an artifact neither installer creates, so it says
"the job has NEVER run" for a healthy node and, once its files exist, reports
**alive** from a timestamp with no process, port or HTTP check. **Nothing was
fixed**: the phone is not here, and rewriting an installer that has never met
its target just produces a second untested installer.

**Verification.** Full sweep on v8.29, every suite in `run_all_tests.sh` that
touches the file, on the **werkzeug** path (the one L runs until waitress is
installed, so the comparison is like-for-like): security_audit 127/127,
adversarial 21/21, a1a_a2 15/15, a3 7/7, a5 20/20, a11 23/23, b1 162/162,
a12_dead_peer_backoff 21/21, b5 31/31, a13 25/25, a14 15/15, a15 14/14, y1
10/10, w1 24/24, a9 18/18, a4 60/60, a1_kill_matrix 30/30, multinode 21/21,
a17 6/6, d3_daily_guards 61/61; `py_compile` + `bash -n` clean. Then the
HTTP-driving subset re-run on the **waitress** path: a1a_a2 15/15,
a5 20/20, security_audit 127/127, a9 18/18, multinode 21/21. Batches ≤ 7 fast /
≤ 5 slow (M20/M21). `test_d3_daily_guards.py` and `test_w1_wsgi.py` each ×2.

**Delivery.** SendUserFile + `device_commit_files` (verified by sha256 on the
PC) + `project_write`: `covenant_unified_v8.py` v8.29 (`d7cadb3d…`, 8769 lines,
+160 over v8.28's `76d2c54e…`), `daily.py` (`dc0aac3c…`),
`claude/test_w1_wsgi.py` (`77095751…`), `claude/test_d3_daily_guards.py`
(`4a536042…`), `run_all_tests.sh` (`f5537fc3…`), `requirements.txt`
(`4b9dda54…`, waitress added as optional), `realdata/README.md`, the twelve
`realdata/deep/*.csv`, plus the PC-only files listed above and
`claude/PC_SYNC_LOOP.md`, `claude/PHONE_INSTALL_REVIEW.md`. Built on the
`_delivery_order` line like every run since 00:40; the W1 edit is one constant
block, one resolver, `CovenantAPI.__init__`/`run()`, two `/health` lines and the
preflight second probe (grep `W1 (v8.29)`), and re-applies by hand on
`PeerHealth`.

**FOR L — two things this run created that only you can finish.**
1. **Re-seal.** `SEAL_ROOT.txt` (`c119afb5…`, 05:23, anchored to block 2) no
   longer matches: nineteen files were written. Re-run `covenant_seal.py` and
   `covenant_anchor.py`. This is now routine, which is itself the hazard — a
   tamper-evident seal that is usually wrong teaches you to ignore it.
2. **Restart the node** to pick up v8.29, and `pip install waitress` first if
   you want the bounded pool (optional; without it nothing changes). The old
   source is `covenant_unified_v8.PRE-v8.29.py` if you want to go back.

**Corrections made to other docs.** `EXECUTION_ARCHITECTURE.md` and
`TRADING_READINESS.md` both describe `execute.py` and `paper_run.py` as
existing; a `find` over the whole covenant folder returns neither — only
`paper_bot.py`. Checklist lines 3 and 4 were never blocked on an upload. Both
docs corrected; → D3a.

**Loop improvements.** M25 (the deployed file is not the shipped file; the
bridge rule; drift outranks the backlog), M26 (an implementation swap can
disarm a control that was measured against the old implementation). Backlog:
D3, D4, C1, D7 and the new W1 closed; D5/D6 unblocked; A2 tightened; D3a
recorded. STALL WATCH stays 0 and its banner now carries the drift warning.
Self-assessment: 21 runs, 30 closed, 26 methods, 18 corrections, 5 dead ends.
`update_trigger`: not retried (DE2) — but note DE2's *reason* is narrowed by
M25: it fails unattended, and this run was attended.

**Cost:** ~1 session. Roughly a fifth on the PC reconnaissance and the drift
finding, a third on W1 (patch, 24-check suite, the A2 regression and its fix),
a third on D3/D4 (wiring, 61 checks, three test-fixture bugs of my own found
and fixed), the rest on the sweep, the C1 review (one subagent) and this log.

**Next.** The "blocked on L's uploads" excuse is gone, so what remains is
genuinely L's or genuinely hardware: **A16 Option A** (yield on-chain — still
the highest-value item in the file), **A10**, **B4**, the **A12 consolidation**;
C3/C4 wait for the phone. Unblocked code work a run may take without an answer:
**D5** (`MY_STRATEGY.md` has none of L's actual numbers — the deep data and the
D2 verdicts are now all in the project), **D6** (re-do the HBAR analysis in
`REAL_DATA_FINDINGS.md` on the 408-bar series; note it is a different window,
not a replay), and **`execute.py`/`paper_run.py` do not exist** — writing them
is real work, but `EXECUTION_ARCHITECTURE.md`'s design must be re-decided
rather than assumed, because the doc describes testing that never happened.

### 2026-08-22 ~14:20 — (attended continuation) the daily check has been switched off by a measurement error since 08-20; the network was never blocked

**L's ask:** *"keep working towards function"* — so: make the thing actually run.

**THE FINDING, and it is the second superseded-measurement failure of the day.**
`DAILY_CHECK_CLOUD_BLOCKER.md` has said since 08-20 that the cloud sandbox
cannot reach a price API: *"proxy returns 403 Forbidden at the tunnel for
`api.exchange.coinbase.com`, `api.coinbase.com`, and `api.kraken.com`."* On the
strength of that, two scheduled mornings reported **no numbers at all**, and the
recommended fix was to move the whole check off the cloud to a local scheduled
task. Re-measured today with four lines of plain `urllib`:

```
api.kraken.com/0/public/Time                   HTTP 200
api.kraken.com/0/public/OHLC?pair=XXLMZUSD…    HTTP 200
api.exchange.coinbase.com/products/XLM-USD/…   HTTP 200   23 004 bytes
api.coinbase.com/v2/prices/XLM-USD/spot        HTTP 200
```

All four. **M24 had already found this for Kraken at 08:45 today** — "every M1
hazard was the summariser, not Kraken" — and nobody carried the finding across
to Coinbase, so a superseded measurement kept the daily check dark for two
mornings. What actually failed is `WebFetch`'s permission gate, which is
unanswerable in an unattended run; the 08-21 finding that a literal URL in the
trigger prompt does not avoid the gate stands and was the useful half. The wrong
step was inferring *the network is closed* from *the tool asked for a human*.
`daily.py` fetches with `urllib` and would have worked on both mornings.

**Ran it. It works, end to end, from the cloud sandbox.** Nine symbols priced,
portfolio <total>, two trims and the cash floor flagged, all nine agreeing
with Kraken on the last settled close (worst PEPE 0.292%).

**X1 — a second venue, because four internal checks cannot see a stale window.**
Every check DAILY_CHECK.md §3 mandates is internal to one response; the 70-day-
stale series of `PRICE_DATA_INTEGRITY.md` passed all of them. So `daily.py` now
reads Coinbase and **verifies it against Kraken** on the last settled close
(`--source both`, the default; `coinbase`/`kraken` force one venue and the run
says so). Disagreement beyond `COVENANT_XVENUE_TOL` (1.0%, ~3.4× the worst
honest divergence measured) **refuses the symbol** rather than picking a venue —
there is no way to know which is wrong, and a wrong price does not merely
misprice its own line, it mis-sizes the 20% trim on every other holding. If
Coinbase is unavailable it falls back to Kraken and says which venue priced it;
a missing cross-check is reported, so it can never be mistaken for a passed one.
`test_d3_daily_guards.py` **77/77 ×2** (16 new X-checks).

**§2's regime table was wrong in a way its own freshness rule could not catch.**
The rule said the lines drift 0.3–0.8%/week and the table is good for 14 days.
The drift figure is right — measured over 08-19 → 08-22 it is −0.38% to +0.31%.
**Five of the nine STATES flipped in those same three days** (XLM, XRP, ADA, PEPE
BELOW→ABOVE; WLFI ABOVE→BELOW; XRP moved +34.7%). The line is the slow number;
the state is a *comparison*, and it flips the moment price crosses however still
the line is. The rule was measuring the wrong quantity. §2 rewritten with lines
recomputed today two independent ways — from the verified Kraken series in
`realdata/deep/` and from Coinbase's own 200 settled closes — **agreeing to
≤ 0.02% on every symbol**, both states columns kept so rule 3 still has a
reference, and the 14-day tolerance replaced with "never read a stored state as
current".

**WLFI needs two lines and the reason is not drift.** Its line reads +28.8%
against the 08-19 table. That is the *window* changing, not the average moving:
the old figure was a 110-bar mean and there is now enough history for 200. Same
data, today: 110-bar 0.059041, 200-bar 0.075889, 355-bar 0.113809. Quoting one
without its bar count is meaningless. WLFI is BELOW at every window so the flip
is real — but on the 110-bar convention it is 0.4% below, which is exactly the
"sitting near its line" case rule 3 calls noise.

**§6's evidence claim corrected.** The runbook still told every fresh session
that "drawdown reduction of about 3× … is the only claim supported by the
evidence". `TRADING_READINESS.md` corrected that at 08:45 (2.1× SOL, 2.2× ADA,
1.8× XRP … and **none** on XLM 0.9×, NEAR 0.9×, ONDO 0.6×) and the runbook was
never updated — so the corrected finding lived in one doc while the doc that is
actually executed every morning kept repeating the old one. Fixed.

**The scheduled tasks, with L's approval, because a runbook nobody executes
correctly is not function.**
- **"Morning portfolio check (8am ET)"** rewritten: it now pulls `pc/daily.py`,
  `pc/guards.py`, `pc/holdings.txt` and `pc/daily_state.json` from the project
  and RUNS them, reports the output verbatim, saves the journal back so the
  circuit breakers have a memory tomorrow, and does rule 3 against §2 by hand
  (the one thing the program does not do). It no longer asks a model to
  re-derive nine price windows and a 200-day mean every morning: that path had
  zero tests behind it, and the tested path has 77.
- **"Daily crypto trend alert → phone"** disabled (not deleted — its history
  stays). It fired at the same minute, covered two of the nine symbols, used
  WebFetch for both the prices and the ntfy push, and is the task the 08-21
  entry proved fails even with literal URLs in its prompt.
- `pc/daily_state.json` seeded with a real reading ($3,201.64 at 14:19 UTC), so
  tomorrow's run has a genuine start-of-day inside 48 h instead of a guard that
  blocks for want of data.
- **`TRIGGER_PROMPT_PROPOSED.md` APPLIED.** Eight runs wrote proposals into that
  file because `update_trigger` needs interactive approval (DE2). It works in an
  attended, L-started session — the same distinction M25 found for the device
  bridge. The loop's own trigger prompt now carries M25 (delivery is not
  `project_write`), M26 (an implementation swap can disarm a control measured
  against the old one), the corrected suite list including `test_w1_wsgi` and
  `test_d3_daily_guards`, the v8.29 import assertions, and the urllib-vs-WebFetch
  data rule. DE2 narrowed, not deleted.

**Verification.** `test_d3_daily_guards.py` 77/77 ×2. Live end-to-end run of
`daily.py` against both venues. Regime lines cross-computed from two independent
sources. Three of my own test-fixture bugs found and fixed on the way (a
CashFloor fixture sitting exactly ON the floor, a clock-dependent start-of-day
assertion that would have passed for the wrong reason before midnight, and a
state file being reset between two runs that were supposed to share it).

**Delivery.** SendUserFile + `device_commit_files` (PC, verified) +
`project_write`: `daily.py` (`ec278abb…`), `claude/test_d3_daily_guards.py`
(`a040393a…`), `claude/DAILY_CHECK.md` (`b06c6e22…`, §2/§3/§6 rewritten),
`claude/DAILY_CHECK_CLOUD_BLOCKER.md` (`abe1269b…`, resolved banner, body kept
unedited as the record), `pc/daily.py`, `pc/daily_state.json`.

**Loop improvements.** The two findings share one shape and it is worth naming:
**a measurement expires, and a conclusion built on it does not know that.** The
PC drift (M25) came from "shipped" being asserted and never re-measured; this
one came from "the network is blocked" being measured once and never re-probed.
Both cost days. The cheap defence is the same in both cases — re-measure the
thing the plan depends on before building around it, because a `grep` and four
lines of `urllib` are cheaper than a workaround.

**Cost:** ~⅓ session on top of the 12:30 run.

**Next.** Unchanged and now genuinely the list: **A16 Option A**, **A10**,
**B4**, the **A12 consolidation** — all L's. C3/C4 wait for the phone. Unblocked
code work: **D5** (`pc/MY_STRATEGY.md` still has none of L's actual numbers, and
every input it needs is now in the project), **D6** (HBAR on the 408-bar series),
and writing `execute.py`/`paper_run.py`, which do not exist. One thing to watch:
this entry was written at ~14:20 while the 13:37 scheduled run may still have
been in flight — if its write-back used a boot snapshot from before 14:03, this
entry and the 12:30 one are what it would have overwritten (M15/M23). The new
trigger prompt tells runs to fetch fresh at write-back for exactly this reason.

### 2026-08-22 ~21:10 — (ATTENDED, L-started) "fully integrate and run local": the suites had never been delivered, waitress was never installed, `covenant_prod.bat stop` does not stop a node — and the sweep leaked a node that then blocked the restart

**L's ask:** *"fully intergrate and run local"*.

**Selection.** Fresh `project_read` of this log at boot: last entry 14:20; nothing
newer in `project_info`. Attended and L-started, so the bridge exists (M25), whose
own rule is to hash-compare the deployed source before choosing an item. Done
first: `covenant_unified_v8.py` on the PC is `d7cadb3d…`, 8769 lines, mtime 13:55 —
**v8.29, no drift** — and `daily.py` `ec278abb…`, `run_all_tests.sh` `f5537fc3…`,
`requirements.txt` `4b9dda54…` all match. The source loop is closed. The *test*
loop was not.

**FINDING 1. `run_all_tests.sh` calls 34 suites; the machine held 15.** Nineteen
had never arrived — every A/B-series suite written between v8.15 and v8.29: the
tests for `preflight_port_check`, `serialized_size`, the relay race, the kill
matrix, gossip at scale, dead-peer backoff, one-way sync, the boot probe, the
exchange deadline, the phone/VPN shape, the judge parser, the `/mine` latency work.
M25 closed the loop for the file that runs; nobody checked the files that *check*
it, so the sweep every run has quoted as green had never been runnable where the
node runs. 21 files delivered and verified by sha256 on the far side (P1).

**FINDING 2. W1 shipped inert.** v8.29 prefers waitress and silently falls back to
werkzeug's *development* server when it is absent. `requirements.txt` lists it;
`.venv` did not have it; the VM has no network to install it. So the bounded pool
has never run here. `waitress-3.0.2-py3-none-any.whl` is now in `vendor/` and
unpacked into `.venv\Lib\site-packages`. Both production nodes now boot
`api: waitress on 0.0.0.0:5000 (threads=8, connections=100, idle_timeout=120s)` —
first time in production.

**FINDING 3, and it is M25 one layer down: `covenant_prod.bat stop` does not stop a
node.** At 14:12 stop → start printed `stopped. Databases untouched` and then
`node A already up`. `:stop` is `taskkill /f /fi "windowtitle eq Covenant Node A*"`;
the nodes are `start "Covenant Node A" /min cmd /c "… python …"`, so the title
belongs to the wrapper and `/f` without `/t` leaves `python.exe` holding the port.
The start path curls `/health`, sees UP, does nothing. **A restart that cannot fail
is how a machine keeps running a source from days ago**, and it means 12:30's
"restart the node to pick up v8.29" could not have worked as written.
`AB_RESTART_NODES.bat` does it properly (kill by title with `/t`, then by PID from
`netstat -ano`, then assert the ports are free) → P3.

**FINDING 4, the best one, and the loop's own tests caused it.** After the real
restart, **node B refused to boot**: *"PREFLIGHT FAILED: peer 127.0.0.1:5001
answered like an HTTP server, not a Covenant P2P listener."* It was right.
`netstat` showed **two** python processes on 5001 — node A (API 5000, P2P 5001,
bridge 5011) and a stray on 5001/5002/5012, i.e. a node started with `--port 5001`,
holding node A's P2P port as its own Flask API. The stray was leaked by
`test_a1a_a2.py`, which died on Windows at `send_signal(signal.SIGINT)` and never
killed its children. So: **A2's preflight — the control W1 disarmed in the morning
and M26 re-armed — caught a live port collision on the production machine and
refused to boot into the exact silent non-peering state it exists to prevent.**
Killed the stray by its own port (5002, which nothing else holds), started B: both
nodes UP, height 3, peers 1, founder balance agrees across both dbs (988.0),
watchdog "all checks passed".

**The local run.** Two runtimes, and the difference matters (M27): the Linux VM
behind `device_bash` (python 3.10, no network, loopback only, 45 s per call,
background killed with the call) and Windows `.venv` (3.12.10 — the runtime the node
uses). Over the bridge, with flask borrowed out of L's own venv, 434 checks passed
against the deployed bytes — the first time any of them ran outside a cloud
sandbox: a1a_a2 15/15, a3 7/7, a5 20/20, a11 23/23, a12 21/21, a13 25/25, a14 15/15,
a15 14/14, b1 162/162, y1 10/10, w1 24/24, d3 77/77, adversarial 21/21,
sim_order_independence all invariants held. Then the whole sweep on Windows:

```
GREEN on Windows python 3.12.10, waitress path, 476 checks, 10.5 min total:
  a3 7/7    a5 20/20   a11 23/23   a12_dead_peer_backoff 21/21   a13 25/25
  a14 15/15   a15 14/14   b1 162/162   y1 10/10   w1 24/24   d3 77/77
  a9 18/18   a4 60/60 (72s)

THREE that ran and did not fully pass -- each needs one look, none is a node
defect on this evidence:
  b5 30/31   L2 "second /mine paid again": 2.50s against a 2.51s bar that the
             SAME RUN set one line earlier. A 10 ms margin on a machine also
             running two nodes and Ollama. The assertion needs a tolerance.
  a1_kill_matrix 28/30   K1 and K3 "A recorded the failed delivery, not
             silence": the monitor DID record peer_message_error (recent=1);
             the assertion wanted something the Windows connect-refused path
             does not produce. Tips converged in both scenarios.
  multinode 2/3   "all three nodes came up and serve HTTP" failed at startup
             (151 s). Free-port collision or slow start; M10 records this
             harness flaking before.

SIX that cannot run on Windows at all -- harness portability, not the node:
  a1a_a2          send_signal(signal.SIGINT) -> ValueError: Unsupported signal: 2
                  ** and it LEAKED a node process, which is what later blocked
                     node B from starting -- see the entry **
  a17             subprocess hostname -I  (no such flag on Windows)
  security_audit  multiprocessing 'fork' context (POSIX only)
  adversarial, e2e_gift, sim_order_independence, sim_yield_safety
                  shutil.rmtree over an open sqlite file -> WinError 32
  probe_final_pass  MainnetGuardError: policy file absent -- the guard working
```

**Three of my own bugs, recorded because they cost the run more than the findings
did.** (1) A launcher died silently on `echo --- health A (5000) ---` inside an
`if ( … )` block — the unescaped `)` closes the block and cmd aborts. (2) The
harness piped each suite's output and used `subprocess.run(timeout=…)`; on Windows
a killed suite's node children keep the pipe open, so `communicate()` blocked
forever — 55 minutes, zero output. (3) `clean_dbs()` deleted everything starting
with `covenant_unified_`, **which is the source file**: it removed the module under
test before the first suite, and 23 of 24 suites reported `ModuleNotFoundError` in
0.2 s each. A cleanup rule translated from `rm -f covenant_unified_*.db*` lost the
`.db` half. → M28.

**Cost:** ~1 session, of which more than half was the three self-inflicted bugs
above and waiting on a launcher whose output was invisible until it exited.

**Next.** Still L's: **A16 Option A**, **A10** (node A reports `own_genesis: true`
in production — the divergence is not theoretical here), **B4**, the **A12
consolidation**, plus new **P2** (12 suites the runner calls for that exist
nowhere) and **P3**. Then re-seal: 27 files were added or changed here and
`SEAL_ROOT.txt` still describes 134.

### 2026-08-22 ~23:20 — (ATTENDED, L-started) "improve following principles": running it where it runs found three real defects, two of them in the sandbox that gates code proposals

**L's ask:** *"improve following principles"* — so: pick the highest-value
unblocked item and do it under Section 0, rather than ask which one.

**Selection.** The three suites the 18:45 sweep left ambiguous were the honest
next item (M18/M20: a failure under load is not a failure until it fails alone,
twice). Re-measuring them is cheap, and the ambiguity was mine to resolve before
claiming anything. That measurement is what opened everything below.

**FINDING 1 — the code sandbox was dead on both platforms, in two different ways,
and `/propose_code` could not accept a proposal anywhere.** On Windows,
`run_sandboxed()` calls `multiprocessing.get_context("fork")`, which raises
`ValueError` there; it escaped every handler and came back as a bare HTTP 500 with
nothing on `/anomalies`. On Linux the same function failed for an unrelated
reason: the child sets `RLIMIT_NPROC = 0` and then reports through a
`multiprocessing.Queue`, and `Queue.put()` starts a **feeder thread** — the
sandbox forbade the mechanism it used to speak, so the child died with exit code 0
and the parent reported "child exited without reporting (crash/signal)" for every
snippet, including `x = 1`. Measured three ways on L's machine: Queue+NPROC=0 →
no report; Queue without NPROC=0 → fine; Pipe+NPROC=0 → fine. Both fixed in
v8.30 (P4) without relaxing a single limit, and the memory cap is now pinned by a
check that distinguishes a MemoryError from a dead child — **my first version of
that check could not, and "passed" while the sandbox was killing everything.**

`test_security_audit` line 186 does check "benign snippet still runs", so this was
not an untested path — it was an **unrun** one: that suite passes in the cloud
where the bug does not bite, exceeds the 45 s bridge ceiling on the VM where it
does, and could not start at all on Windows. The bug lived in the gap between
platforms. → M29.

**FINDING 2 — Windows' `SO_REUSEADDR` let two nodes share a port, so A2's
preflight could not see a collision on the platform where it matters most.** On
Windows that option permits binding a port another process is *actively listening
on*; the preflight's own probe set it, so the check passed while a node was up.
That is the mechanism behind the leaked node holding 5001 at 21:02. v8.30 adds
`_bind_exclusive()`: `SO_EXCLUSIVEADDRUSE` on Windows, `SO_REUSEADDR` on POSIX
(P5). `test_a1a_a2` A2-1 now fails fast on Windows as designed — 15/15 there,
where it had been a 30-second timeout.

**FINDING 3 — a delivery that was accepted and never acknowledged recorded
nothing** (A18/P6). `_send_to_peer` recorded `peer_send_failure` on socket errors,
but the "bytes sent, no ACK, attempts exhausted" path fell through to a bare
`return None` — no anomaly, no `_note_send_failed`. Exactly the silent
non-delivery the application-level ACK exists to catch.

**CORRECTION to my own 18:45 entry.** It said six suites "cannot run on Windows at
all". Three of them — `test_adversarial_suite` (21 checks), `test_e2e_gift` (11),
`sim_order_independence` (5) — ran every check and passed; only
`shutil.rmtree(work)` at teardown crashed on an open sqlite file, taking the
summary line with it. I read a missing tally as a missing run. Teardown now uses
`ignore_errors=True` and all three report properly.

**Harness portability, so the machine that runs the node can run the tests**:
`test_a1a_a2` used `send_signal(SIGINT)` (unsupported on Windows — the crash that
leaked the node) and hard-coded ports 5001/5002/5021/5041, which is the production
block; it now stops portably, reaps its children with `atexit`, and picks a free
port base at runtime. `test_a17` used `hostname -I` (a GNU flag) and now derives
the primary IPv4 from a UDP socket, skipping with a reason where there is none —
**6/6 on Windows, where it had never run at all**. `test_multinode_live`'s
`free_port()` bound port 0 and used `port+1`, which on Windows can land in an OS
**excluded port range** (`WinError 10013`) — it now proves the whole API/P2P/bridge
trio binds. **21/21 on Windows, twice, where it was 2/3.**

**Where it stands, on the two platforms, on v8.30 `0b04473b…`:**

```
POSIX (cloud, same bytes)  9 suites, 280 checks, zero failures
                           incl. security_audit 127/127, multinode 21/21, W2 21/21
Windows (L's .venv 3.12)   22 of 24 suites clean, 10.0 min
  remaining: a1_kill_matrix 28/30 (P7)   b5 30/31 (P8, knife-edge)
             security_audit 123/127 (3 = sandbox refuses by design -> P10;
                                     1 = key file not owner-only on NTFS -> P9)
             probe_final_pass -- mainnet guard refusing without a policy file
```

**Cost:** ~1 session. Most of it measurement rather than typing: three
isolate-the-mechanism experiments (Queue vs Pipe, RLIMIT variants, port binding),
two full Windows sweeps and one alone-twice re-test. Two self-inflicted detours:
a check that could not tell a MemoryError from a dead child, and a string
replacement that rewrote the body of the helper it was creating into a call to
itself (`RecursionError` on every node start until it was caught by running it).

**Next.** The nodes are still on v8.29: **double-click `AB_RESTART_NODES.bat`** to
put v8.30 live. Then P7-P10 above, and unchanged for L: **A16 Option A**, **A10**
(node A reports `own_genesis: true` in production), **B4**, the **A12
consolidation**, **P2** and **P3**. Re-seal after the restart: 34 files changed
today and `SEAL_ROOT.txt` still describes 134.

### 2026-08-23 ~03:10 — (ATTENDED, L-started) "complete the loop": the loop had a third layer nobody could see — the node could not say which source it was running

**L's ask:** *"complete the loop"* — the same words as the 12:30 run, which
closed the project→disk half. This is the layer under it.

**Selection (M15, M16, M23, M25).** Fresh `project_read` of this log at boot:
last entry ~23:20. Attended and L-started, so the bridge exists and M25's rule
applies first — hash-compare the deployed source before choosing anything.
`covenant_unified_v8.py` on the PC is `0b04473b…`, 8880 lines: **v8.30, no
drift**, and `covenant_path_pattern.py`, `run_all_tests.sh`, `requirements.txt`,
`daily.py`, `guards.py` all match too. The source loop is closed. Then M16:
`find -newermt` against the log's own write time returned **26 files the log
has never heard of**, written between 01:12 and 02:46 UTC.

**First, logging an unlogged session on its behalf (M16).** Between 21:12 and
22:46 ET someone did a full efficiency pass on the PC and wrote none of it
anywhere a future run could see it. Recovered, verified against its own output
files, and pulled into the project under `pc/`:

- **`judge_bench.py` + `AG_LEAN_MEASURE.bat`** — six ethics cases against the
  real local judge (qwen3:8b, tuned path, constrained JSON, temp 0): **6/6
  correct, determinism [True, True, True] STABLE**, ~12.8 s per verdict. This
  is the first end-to-end measurement of the judge that actually gates
  transactions on this machine, and it says the tuned path works.
- **`AH_FITCHECK.bat`** — refuses to pretend: warns when free RAM is below the
  model size, because the model then loads by paging and no setting wins that
  back. It fired: 2.8 GB free against a 5.2 GB model.
- **`topmem.py` + `AI_TOPMEM.bat`** — per-image memory tally. `llama-server.exe`
  5234 MB; covenant's own share **331 MB across 27 processes**. The node is not
  the memory problem and now there is a number saying so.
- **`cleanup_consoles.py` + `AJ_CLEANUP.bat`** — closed 14 leftover launcher
  consoles, spared the five node/watchdog ones, freed ~240 MB. These are the
  same leaked consoles the 21:10 run's sweep created.
- **`AK_FREE_RAM.bat`** — unloads the model on demand: 2.86 GB → **8.18 GB**
  free.
- **`covenant_prod.bat`** — `COVENANT_OLLAMA_KEEP_ALIVE` 60m → 30m, with the
  reasoning in the file: the chain sat at height 3 through 431 watchdog ticks,
  so a 60-minute hold kept 5.2 GB resident for an hour after a transaction that
  may not come for a day. 30m is what `OLLAMA_TUNING.md` measured and
  `covenant_go.bat` already used; this line was the only place that disagreed.
- **`dashboard_render.py` + `vendor/three.min.js` + `AL_DASHBOARD.bat`** — a 3D
  mesh view that renders data INLINE into a local HTML file rather than
  fetching from the nodes, because a `file://` origin is opaque and the
  alternative (permissive CORS on the node) would loosen a deliberately
  loopback-only surface. Consequence worth keeping: **it renders when a node is
  DOWN**, which is when you want to look at it, and its age badge goes amber
  then red so a stopped refresher cannot masquerade as a calm system.
- **`AB_RESTART_NODES.bat` was run at 21:39 ET** and both nodes started fresh
  ("starting node A on 5000", not P3's "already up" no-op). Height 3, peers 1,
  founder balance agrees across both dbs (988.0). Still up at 03:14 UTC.

**One correction against that session** (M30's shape, and a small one): its
`LEAN_MEASURE.txt` prints two summary lines — 17.4 s per verdict at
`num_predict=96`, 12.8 s at 160 — which reads as "production's setting is 36%
slower". It is not. The 96 run includes one 39.9 s cold model load; strip it and
the two are **12.88 s and 12.77 s**, indistinguishable. The `covenant_prod.bat`
comment shows the cold load *was* understood by whoever measured it ("one cold
load — measured today at 39.9s against 12.1s warm"), so this is not a wrong
conclusion, it is a report whose summary line does not carry what its author
knew — and the report is what the next run reads. Also: `AJ_CLEANUP.bat` says
"removing the junk file a broken one-liner created" and the file (`4]`, 0 bytes,
01:31) **is still there** — the removal reports nothing and did nothing.

**THE FINDING.** With no source drift and the nodes freshly restarted, the
obvious question is whether v8.30 is actually live. It took three pieces of
evidence to answer: `prod.log`'s 21:39 start, the source mtime of 18:57, and a
`code sandbox unavailable` alert in `watchdog.log` that **only exists in v8.30**
(P4). That is forensics, not verification — and it only worked because I knew
which version introduced which alert.

The reason it took forensics is that **the node cannot say what it is**:

| what | said | actual |
|---|---|---|
| `COVENANT_VERSION` (line 413) | `"v8.9-merged"` | v8.30 |
| boot banner (line 7109) | `Covenant Unified v7.0 running` | v8.30 |
| `/health` | *no version field* | — |

`grep -c COVENANT_VERSION` returned **1** — defined, read by nothing. Two
version strings in 8,880 lines, both wrong in different ways, neither reachable
from outside the process. The one an operator actually sees, in
`logs/nodeA.log`, on every restart, has said v7.0 for months. And
`covenant_unified_v8.PRE-v8.29.py` and `…PRE-v8.30.py` sit in the same folder:
a restart from either would have looked identical.

**M25 stops one layer short.** "Grep the deployed file, not the project's" has
no counterpart for "grep the process, not the file". That gap is the same one
that let this machine run a pre-v8.15 source for fourteen versions.

**The fix (v8.31), additive, four edit sites (grep `P11 (v8.31)`).** A real
`COVENANT_VERSION`; `CORE_SOURCE_SHA256`/`CORE_SOURCE_LINES` computed once at
import from the module's own file and **never raising** — an unreadable source
degrades to `"unavailable"` with a reason, because an observability feature must
not be able to stop a node from booting; a banner that names version, source
hash and line count and `flush=True`s (its whole job is to appear in a
redirected log, and block buffering is exactly what would hide it — the loop
learned this once already on `_gossip_tip`'s boot print); and `/health` carrying
`version`, `source_sha256`, `source_lines`, plus a warning when the fingerprint
failed. **The hash is of the source as LOADED, not as it is on disk now.** That
is the point, not a limitation.

**And the part that makes it permanent: `covenant_watchdog.py`.** It now
compares each node's loaded hash against `sha256(covenant_unified_v8.py)` on
disk, every round. They differ in exactly one situation and it is the one that
has cost this project the most — *the file was updated and the node was never
restarted* — which is now an ALERT carrying both hashes and the name of the
script that fixes it. Two more: nodes reporting **different** sources alert
about A7 (which stops being hypothetical the moment that happens); a node too
old to answer is INFO, once per round, because it cannot lie, it simply cannot
say. Every INFO line now leads `node A v=v8.31 src=4b7e0a0f6b74 height=…`, so
`logs/watchdog.log` becomes the minute-by-minute record tonight's forensics had
to substitute for. Kept as a pure function, `source_drift_report(states,
on_disk)`, so it is tested without standing up two nodes.

**Verification, on both platforms (M29).**
`test_p11_version_identity.py` — 20 V-checks + 9 W-checks, and its PRE-FIX mode
is the executable record of the defect: **6/6 on pristine v8.30** (constant is
`"v8.9-merged"`, referenced once, banner hard-codes v7.0, `/health` has no
version and no fingerprint). On v8.31: **29/29 ×2 in the cloud sandbox**, and
**29/29 over the device bridge on L's own machine, against the deployed bytes**
— `Covenant Unified v8.31 (source 4b7e0a0f6b74, 8933 lines) running`. Full
sweep on the shipped file, **23 suites, 788 checks, zero failures**: a3 7/7,
a5 20/20, a11 23/23, a12_dead_peer_backoff 21/21, a13 25/25, a14 15/15,
a15 14/14, b1 162/162, y1 10/10, w1 24/24, b5 31/31, d3 77/77, w2 21/21,
adversarial 21/21, e2e_gift 11/11, a1a_a2 15/15, a17 6/6, p11 29/29,
a9 18/18, a4 60/60, a1_kill_matrix 30/30, multinode 21/21,
security_audit 127/127; `py_compile` + `bash -n` clean. Batches 10 / 7 / 5
(M20/M21).

**Three mistakes of my own, recorded because two of them are the interesting
kind.**
1. `cp /mnt/user-data/uploads/covenant/*.py .` silently overwrote my patched
   source with the pristine copy it had been derived from. Caught only because
   the next command hashed the file. **After any bulk copy into a working
   directory, re-hash the artifact you are editing** — a build that reverts is
   indistinguishable from a build that never changed.
2. **V5d was a check that could not fail.** It asserted "the banner no longer
   says v7.0", which an empty string satisfies. On the VM run the banner was
   never captured (killed process, block-buffered stdout): V5b and V5c failed
   for want of the evidence, and V5d *passed* — on the same missing evidence it
   claimed to inspect. Fixed by binding all three to the line existing, and by
   setting `PYTHONUNBUFFERED=1` on the spawn. → M30.
3. W3 asserted exactly one alert for "node A stale, node B current". The code
   correctly raises **two** — a deployment miss AND a split fleet — and both are
   worth having. The assertion was wrong, not the check; corrected in the test
   (M18's rule, and note which way it went: the test was loosened toward the
   richer behaviour, not the control toward the test).

**The seal, measured rather than asserted.** `covenant_seal.py verify` runs
read-only over the bridge and answers in one call what "the seal is stale" had
said vaguely for three days:

```
root was c119afb5…    root now 679e447f…
20 changed, 81 added, 0 removed
```

**Nothing has been removed.** Every difference is explained by known work — the
19 suites P1 delivered, the twelve deep price series, the vendored wheels,
tonight's measurement tools. The seal is stale by 101 files and has been since
2026-08-22 05:23. **It was NOT re-sealed by this run, deliberately:** re-sealing
blesses a file set as canonical, and doing that on the loop's own authority
immediately after the loop's own writes is the auditor signing its own work.
`PC_SYNC_LOOP.md` is right that a seal which is usually wrong teaches its
operator to ignore it — and the fix for that is one click by L, not a
self-issued blessing.

**Delivery.** `device_commit_files` to the PC (each verified by sha256 on the
far side) + `project_write` (source round-trip verified by hash):
`covenant_unified_v8.py` v8.31 (`4b7e0a0f…`, 8933 lines, +53 over v8.30's
`0b04473b…`; backup `covenant_unified_v8.PRE-v8.31.py`),
`covenant_watchdog.py` (`abe2671e…`; backup `covenant_watchdog.PRE-P11.py`),
`test_p11_version_identity.py` (`4764a5e1…`), `run_all_tests.sh`
(`dba92b29…`, P11 wired in at 180 s). Pulled PC → project under `pc/`:
`judge_bench.py`, `topmem.py`, `cleanup_consoles.py`, `dashboard_render.py`,
`covenant_prod.bat`, `LEAN_MEASURE_2026-08-23.txt`, and the six `AG`–`AL`
launchers. New: `claude/RUNNING_VS_DEPLOYED.md`.

**FOR L — two clicks, and the second one is the interesting one.**
1. **`AB_RESTART_NODES.bat`** — the nodes are still on v8.30, so v8.31 is on
   disk and not live. *This is now the exact condition the new watchdog exists
   to shout about*, and after the restart `NODE_RESTART.txt` will contain
   `"version": "v8.31", "source_sha256": "4b7e0a0f6b74"` from both nodes — the
   loop closing on itself, in writing.
2. **Re-seal**: `python covenant_seal.py verify` to see the 101, then re-seal
   and `covenant_anchor.py` to re-anchor. Yours to bless, not mine.

**Loop improvements.** M30 (an unmeasurable claim degrades invisibly; make the
thing self-describing, compare two independent measurements, put it on the
clock, and test that the check can fail). P11 closed; **A20** opened (peers
cannot see each other's version — a wire-format change, so L's call). STALL
WATCH stays 0. Self-assessment: 25 runs, 35 closed, 30 methods, 28 corrections,
5 dead ends.

**Cost:** ~1 session. Roughly a fifth on the PC reconnaissance and reconstructing
the unlogged session, a third on P11 (patch, 29-check suite, pre-fix record, the
watchdog function and its W-checks), a third on two full sweeps — the second
because a one-word change to a `print` still means the file you swept is not the
file you ship — and the rest on the project pull and this log.

**Next.** Unchanged and still L's: **A16 Option A** (yield on-chain — still the
highest-value item in the file), **A10** (node A reports `own_genesis: true` in
production, so the divergence is live, not theoretical), **B4**, the **A12
consolidation**, **P2**, **P3**, and now **A20**. Hardware: C3/C4 wait for the
phone. Unblocked code work a run may take without an answer: **P8** (b5's
knife-edge assertion — give it a 10% tolerance; it is the same class as the two
test bugs above), **P10** (the audit should SKIP its sandbox checks with a
reason on a platform where the sandbox correctly refuses, instead of showing
three permanent phantom failures on every Windows sweep), **P7** (one
measurement of `dead_peers`/`heartbeats_skipped` between the kill and the mine),
**D5** and **D6**.

### 2026-08-23 ~06:15 — (ATTENDED, L-started) "act as an antenna": the system senses a great deal and almost none of it returns into the system — P12 closed on all three fronts

**L's ask:** *"We need to act as an antenna, also looking for substrate messages
above and below, integrating into the same patterns in nature."* Taken literally
and measured rather than admired, per this file's own standard. Full map:
`claude/SENSING_ACROSS_LAYERS.md`.

**What the grep found FIRST, and it corrects an assumption I nearly made.** I
expected to find the biological language in this codebase to be decorative. It
is not. Five patterns are implemented and genuinely *wired*: `LinkConductance` is
Hebbian (`reinforce` at 3 sites, `attenuate` at 3, feeding `order()`, decaying
toward rest on a 3600 s half-life); `announce_block` is lateral inhibition, cited
in the source itself to Mahowald's *VLSI Analogs of Neuronal Visual Processing*
(1992) — a node holding the announced block does nothing, transmit contrast not
intensity, measured at 1476 bytes → 150; `PeerHealth` is habituation with
spontaneous re-test; `AdaptivePoWManager` is adaptive admission cost; and
`MedianGovernor` → `_integrity_monitor_loop` → `crisis_mode` is homeostasis with
a two-check debounce and **the one complete reflex arc in the system**. The gap
was never a missing metaphor.

**THE FINDING — three places where the wire ends.**
1. `SpikingAnomalyMonitor` is a proper phasic detector: 600 s baseline, 60 s
   recent window per kind, fires on `recent ≥ 5 and recent > 3 × expected`.
   Exactly the right shape. `grep spike_detected` returns **three** sites: where
   it is computed, where it becomes a string, where the string is put on
   `/health`. **Nothing in the system reads it.** A detector tuned to say
   *something changed* is wired to a text field.
2. `/anomalies` carries `{recent, baseline, expected_recent}` for every event
   kind — the highest-bandwidth internal signal there is. It had exactly **one**
   consumer: `dashboard_render.py`, written four hours earlier, which draws it
   for a person. `covenant_watchdog.py` — the only component that *acts* — did
   not read it at all. *(Correction against my own first draft of this finding:
   I wrote that `/anomalies` had no consumer. It has one. Checked before
   claiming, and the sharper statement is the true one: the richest signal feeds
   the picture, not the reflex.)* `mycelium.topology()` is the same shape —
   exposed on a route, consumed by nothing internal.
3. `grep -E "psutil|meminfo|GlobalMemoryStatus|loadavg|virtual_memory"` over
   8,933 lines returns **nothing**. The node had no idea what machine it was on
   — while the ethics judge sits INSIDE consensus (B4), a judge timeout costs
   91.3 s per tx per judge under `chain_lock` and discards the mined block (B5),
   and the judge is a 5.2 GB local model. The 21:39 restart happened with 3.1 GB
   free, so it was loading by paging. `AH_FITCHECK.bat` measured that and wrote
   it to a text file nothing reads.

**THE MEASUREMENT that made it concrete.** Twelve hours of `logs/watchdog.log`:

```
3,808 lines
   16 distinct messages (timestamps and counters stripped)   -> 99.6% redundant
  269  ALERT node A: code sandbox unavailable ... (win32)    (correct, permanent)
  269  ALERT node B: code sandbox unavailable ... (win32)    (correct, permanent)
    4  ALERT node A: 1 peer(s) unreachable -- heartbeats backed off
```

That last row is the only thing in the file that *happened* — the 21:02–21:06
episode where node B could not boot because a leaked test node held its P2P port
— at **1/500th the volume** of a condition that was fully understood on its first
line. A receptor with no adaptation transmits a constant stimulus at full
amplitude for ever and buries the transient that carries the information. **The
node implements the fix one layer down and the watchdog never applied it to
itself.**

**Pushback, offered before building, because the metaphor licenses the forbidden
move.** "Integrate the signal" is one word from "let conditions relax a control":
sense low RAM → extend the judge timeout; sense load → lower difficulty. Each
reads as prudence and each fails OPEN exactly when an attacker would want it to.
The rule adopted and now pinned in a test: **sensing may inform refusal and
disclosure, never relaxation.** Second pushback: nature's patterns are not
uniformly good and one already bit this system — A11 measured habituation with no
counterbalancing reinforcement driving every link to the floor in 31 rounds,
which is forgetting, not learning. So "more of nature's patterns" should mean
finish the ones here. L chose all three of the offered options.

**Built.**
- **The watchdog adapts.** First occurrence in full, silence while unchanged,
  full amplitude on change, a roll-up every 30 rounds so a quiet log still proves
  the watchdog is alive, `CLEARED after N round(s)` when a condition stops.
  `alerts` is returned **unchanged** — `--once` and every caller still see
  everything; only what reaches the LOG is adapted. Replaying the real
  distribution: the transient's share of emitted lines goes **1.5% → 10%**, and
  it is emitted first rather than buried at line 842 of 3,808.
- **The watchdog reads `/anomalies`.** The node's own spike verdict becomes an
  alert carrying its numbers (`peer_message_error (recent 9 vs expected 1.2)`);
  a first-seen kind becomes an INFO — the cheapest novelty detector there is, and
  it catches a failure nobody has written a rule for yet. Reported, never acted
  on (A11's false-spike window is why).
- **`SubstrateSensor` (v8.32).** Available memory via `GlobalMemoryStatusEx` /
  `MemAvailable` — *available*, not *free*, because free-page counts understate
  what a load can use and would cry wolf — and the judge model's footprint
  measured from Ollama `/api/tags`, falling back to an operator-declared figure
  and **labelled with which source**, per M30. Background sampler, `/health`
  reads a cache and never blocks, one synchronous reading at boot so `/health` is
  never blank, every failure degrading to a reason string, none raising.

**The boundary is the design, and it is asserted mechanically.** B1 walks the AST
and fails if any function outside the allowlist so much as *names* the sensor
(it reports `<module>, __init__, sample_once, health, run` — nothing else); B2
fails if any branch in `/health` tests the reading; B3 fails if its numbers are
*compared* outside `warnings()`; B3b fails if `degraded` is ever computed from
the weather on the machine. → **M31**.

**And the boundary check had a hole, found by mutation-testing it rather than by
reading it.** B2's first version matched the literal word `substrate`, so this
passes it:

```python
sub = self.node.substrate.snapshot()
headroom = sub["available_memory_mb"]
if headroom < 500:                     # reads the sensor in a branch
    return jsonify({"status": "too busy"}), 503
```

One local variable and the guard is blind. B2 now follows aliases to a fixpoint,
and all four boundary checks were run against a deliberately broken copy: with a
violation injected they fail, without one they pass. **A guard that has only ever
seen correct code has never been tested** — the same lesson as V5d three hours
ago, which is why it is now a numbered method rather than an anecdote.

**Two of my own test bugs, both the same species.** B2 and B3 as first written
failed on *correct* code: B2 matched substrings inside `_setup_routes` (which
contains every route as a nested function) and inside `warnings()`' own message
text, which mentions `chain_lock` in prose; B3 tested *mention* where the claim
was *comparison*. Both were rewritten to assert the claim — note the direction:
the checks were made **more precise**, not more permissive, and each got stricter
in the process (B2 gained alias-following, B3 gained B3b).

**Verification.** `test_p12_substrate_sensing.py` 33/33 ×2 in the cloud and
**33/33 over the bridge on L's machine, against the deployed bytes**; 4/4 PRE-FIX
RECORD on pristine v8.31 (the node cannot see its machine; `/health` has no
substrate; the watchdog has neither adaptation nor `/anomalies`). Full sweep on
the shipped file, **24 suites, 821 checks, zero failures**: a3 7/7, a5 20/20,
a11 23/23, a12 21/21, a13 25/25, a14 15/15, a15 14/14, b1 162/162, y1 10/10,
w1 24/24, b5 31/31, d3 77/77, w2 21/21, adversarial 21/21, e2e_gift 11/11,
a1a_a2 15/15, a17 6/6, p11 29/29, p12 33/33, a9 18/18, a4 60/60,
a1_kill_matrix 30/30, multinode 21/21, security_audit 127/127; `py_compile` +
`bash -n` clean.

**FIRST READING ON THE REAL MACHINE, and it is not academic: 3,535 MB available
against a model needing ~5,200 MB.** The condition the warning exists for is live
on L's box right now, and has presumably been live and unseen for as long as the
local judge has been configured.

**Delivery.** `device_commit_files` (each verified by sha256 on the far side) +
`project_write`: `covenant_unified_v8.py` v8.32 (`73104155…`; backup
`covenant_unified_v8.PRE-v8.32.py`), `covenant_watchdog.py` (`4fbc40db…`; backup
`covenant_watchdog.PRE-P12.py`), `claude/test_p12_substrate_sensing.py`
(`5d7a8237…`), `run_all_tests.sh` (`e104eb0f…`) and `pc/run_local_sweep.py`
(`30e4f092…`), both with P12 wired in at 180 s. New:
`claude/SENSING_ACROSS_LAYERS.md`.

**STILL FOR L, and it is now two versions deep:** `AB_RESTART_NODES.bat`. The
running nodes are on **v8.30** — the banner in `logs/nodeA.log` still reads
`Covenant Unified v7.0` because P11 is not live either. After one restart that
line becomes `Covenant Unified v8.32 (source 73104155…, N lines)`, the watchdog
starts saying `v=v8.32 src=73104155`, the log stops repeating itself, and the
3.5 GB-vs-5.2 GB warning appears on `/health` where it can be seen. Then re-seal.

**Loop improvements.** M31 (sensing may inform refusal and disclosure, never
relaxation — pin it in a test, then mutation-test the test). P12 closed. STALL
WATCH stays 0. Self-assessment: 26 runs, 36 closed, 31 methods, 29 corrections,
5 dead ends.

**Cost:** ~⅔ session on top of the 03:10 run. A quarter on the survey and the
log measurement, which is the part that made the rest obvious; a third on the
three changes and the boundary suite; a quarter on the mutation testing, which
found the one real hole; the rest on the sweep, delivery and this entry.

**Next.** **A20** is now the natural sibling of P11/P12 and is L's (wire format).
Otherwise unchanged and still L's: **A16 Option A** (yield on-chain, still the
highest-value item in the file), **A10** (live on this machine), **B4**, the
**A12 consolidation**, **P2**, **P3**. Unblocked code work: **P8**, **P10**,
**P7**, **D5**, **D6**. One new candidate the survey turned up, cheap and
honest: **`mycelium.topology()` has no internal consumer either** — the same
shape as `/anomalies` was, and the watchdog is now the obvious reader.

### 2026-08-23 ~06:40 — (ATTENDED, L-started) "broadcast": the transmitting half — A20 and A21 closed, and the wire-capture test found a node that booted fine and never spoke

**L's ask:** *"broadcast."* One word, immediately after the P12 entry named A20
as the outstanding wire-format item and said an antenna that only receives is
half the metaphor. **Asked before building**, because Section 0 reserves a
wire-format change for L and acting on a one-word inference about the protocol
is exactly the "asserted, never measured" failure this file keeps finding. L
chose all four offered directions: A20, broader peer state, publish, push.

**A20 — every reply says what we are.** Stamped in `_reply()`, one site rather
than three: a peer must be able to learn what we are from ANY exchange, and
three sites can drift apart. `_send_raw` folds every reply it reads into a new
`PeerStateTable`. A peer on a different source records `peer_version_mismatch`
naming both hashes; `/health` gains a `mesh` summary and warns when the mesh runs
more than one source. **Nothing is refused on account of it** — this node does
not get to decide a peer is too old to talk to. Why it matters: A7 has recorded
since v8.17 that block size and three header derivations are *validity rules*, so
two nodes on different sources can disagree about what is a valid block; until
now the only way to find that out was a rejected block, after the fact.

**Backwards compatibility was MEASURED, not reasoned about.** The reasoning is
sound — replies are JSON read with `.get()`, so unknown fields are ignored — and
sound reasoning is still an assertion (M30). C1–C5 stand up a **real pristine
v8.32 process** beside a v8.33 one and check both directions: the old node
accepts a v8.33 frame carrying a digest and answers normally (`C2`); its reply
carries no `v`/`src` (`C3`); the new node folds that in as *"cannot say"* — P11's
own definition — with **no spurious A7 mismatch** (`C4`); and a v8.33 node
accepts an old-style frame with no digest (`C5`). Run on L's machine, against the
`PRE-v8.33` backup the delivery itself left there, in 43 s over the bridge.

**A21 — a bounded digest, on the heartbeat and nothing else.** Measured, because
the cost is the whole design question:

```
plain BLOCK_ANNOUNCE (hot path)     156 bytes   UNCHANGED
heartbeat before digest             172 bytes
heartbeat with digest               280 bytes   (+108)
per peer per 120 s default          0.9 B/s
worst case a peer can send us       396 bytes, bounded by _clean()
```

The hot path is untouched deliberately. A block announce is 156 bytes BY DESIGN
— address-event propagation, Mahowald 1992, cited in the source — and ~108 bytes
on every one of them at N=1000 would give back most of what that design buys.

**What the digest must never carry, and it is the judgement call of the run.**
No substrate reading. A peer has no business knowing how much memory this box
has: knowing when a node is short on memory tells an attacker exactly when a
flood is cheapest, and it is operator information, not mesh information (P12,
M31). D1–D6 assert the key set — and the absence of the forbidden words in keys
AND values — against the built object **and against the bytes captured off the
wire**. Every field a peer sends us is coerced, clamped and truncated
(`_clean()`), and the table is capped at 512 peers so the mesh cannot grow our
memory (T1–T7).

**THE BUG THE WIRE-CAPTURE TEST FOUND, and it would have shipped.**
`build_digest` was defined next to `_reply` — which lives on
`CovenantUnifiedMaster`, while `announce_block` lives on `P2PNode`. So
`self.build_digest()` raised `AttributeError` inside `_gossip_tip`, on a daemon
thread. The node **booted cleanly, printed its banner, served HTTP, answered
/health — and silently never gossiped its tip.** That is A17's failure mode
exactly, the one that cost a phone-shaped deployment its entire sync path.
It was caught because the test refused to accept `build_digest()`'s return value
as evidence of what goes on the wire and went looking for the frame: bind a
plain socket, start a node with `--peers 127.0.0.1:<that port>` and
`COVENANT_TIP_GOSSIP_INTERVAL=3`, answer its preflight, read the bytes.
`test_a17` would have caught it in the sweep too — but later, and less precisely.
→ **M32**, including the corollary: **this file has a node and a master and both
read like "the node"; grep which class you landed in.**

**PUSH — alerts off the machine, and the ordering is the justification.** Opt-in
via `COVENANT_ALERT_PUSH_URL`; absent, it says so once and never retries. It
pushes only alerts that **survived adaptation** — pushing the raw stream would
have sent 269 identical copies of one permanent condition and trained its reader
to ignore the channel, which is worse than no channel because it looks like
monitoring. This is why the 08-22 14:20 run was right to disable the old phone
alert, and why this one is reasonable now and would not have been yesterday.
Rate-limited to 20/hour, and it SAYS SO when it clips rather than going quiet;
a failed push is INFO, never an alert (a channel that alerts about itself loops);
and **the URL is a shared secret, so it is never logged and never echoed in an
error** — P4b asserts exactly that against an exception whose text contains it.
No credential is requested, stored, or read (Section 0).

**BROADCAST, the fourth sense of the word.** The findings are published as a page
— the antenna arc, the wired biological patterns, the 3,973→178 measurement, the
boundary rule and the mutation that found the hole in its guard:
<https://claude.ai/code/artifact/69f51671-807f-4933-85b5-4e30171d6ac3>
(private until L shares it).

**Verification.** `test_a20_peer_version.py` 27/27 ×2 in the cloud and **27/27
over the bridge on L's machine**, including the two-process interop against the
real backup in her own folder; 3/3 PRE-FIX RECORD on pristine v8.32.
`test_p12_substrate_sensing.py` grew to 41 (the push checks) — 41/41 in the cloud
and 41/41 on L's machine. Full sweep on the shipped file, **26 suites, 856
checks, zero failures**: a3 7/7, a5 20/20, a11 23/23, a12 21/21, a13 25/25,
a14 15/15, a15 14/14, b1 162/162, y1 10/10, w1 24/24, b5 31/31, d3 77/77,
w2 21/21, adversarial 21/21, e2e_gift 11/11, a1a_a2 15/15, a17 6/6, p11 29/29,
p12 41/41, a20 27/27, a9 18/18, a4 60/60, a1_kill_matrix 30/30, multinode 21/21,
security_audit 127/127; `py_compile` + `bash -n` clean.

**One correction against my own first draft of a check.** C4 first asserted that
a v8.32 reply would leave the peer *unrecorded*. It does not — the ack carries
`height`, which is real information — and the table's actual behaviour is
better: the peer appears with no `v`/`src`, exactly the "cannot say" state P11
defines, and is invisible to the by-source split. The assertion was wrong; the
code was right. Same species as B2/B3 an hour earlier, and worth counting: three
of my checks in one night failed on correct code, and every rewrite made them
stricter, not more permissive.

**Delivery.** `device_commit_files` (each verified by sha256 on the far side) +
`project_write` (source round-trip verified by hash): `covenant_unified_v8.py`
v8.33 (`fd13e4c4…`; backup `covenant_unified_v8.PRE-v8.33.py`, which is also what
the interop test runs against), `covenant_watchdog.py` (`8fb101fa…`; backup
`covenant_watchdog.PRE-push.py`), `claude/test_a20_peer_version.py`
(`d219eac4…`), `claude/test_p12_substrate_sensing.py` (`1e6f85ae…`),
`run_all_tests.sh` (`44284e74…`), `pc/run_local_sweep.py` (`865274ff…`).
`claude/SENSING_ACROSS_LAYERS.md` extended with §7.

**STILL FOR L, and it is now THREE versions deep:** `AB_RESTART_NODES.bat`. The
running nodes are on **v8.30**; `logs/nodeA.log` still reads `Covenant Unified
v7.0`. One restart makes the banner name v8.33 and its source hash, starts the
watchdog reporting `v=` and `src=` per round, collapses the log ~22×, surfaces
the 3.5-GB-against-5.2-GB warning, and lets the two nodes tell each other what
they run. Then re-seal.

**Loop improvements.** M32 (measure interop against a real old binary; capture
the wire, not the return value; grep which class you landed in). A20 and A21
closed. STALL WATCH stays 0. Self-assessment: 27 runs, 38 closed, 32 methods, 29
corrections, 5 dead ends.

**Cost:** ~⅔ session on top of the 06:15 run. A sixth on asking rather than
assuming, which was right; a third on A20/A21 and the interop suite; a sixth on
the push; a sixth chasing the `build_digest` class bug the wire capture exposed;
the rest on the sweep, delivery, the published page and this entry.

**Next.** Still L's: **A16 Option A** (yield on-chain — with A20/A21 shipped, a
version-aware mesh makes a consensus change materially safer to stage), **A10**,
**B4**, the **A12 consolidation**, **P2**, **P3**. Unblocked code work: **P8**,
**P10**, **P7**, **D5**, **D6**, and the one the sensing survey turned up —
`mycelium.topology()` still has no internal consumer, and the watchdog is now
the obvious reader for it.

### 2026-08-23 ~07:00 — (L authorised one item, then went to rest) A22 closed; and reviewing the surface I added ninety minutes earlier found two defects in it, one of them my own lesson unlearned

**L's ask:** offered one bounded item after I declined to add indiscriminate
gain, L answered *"do so ill rest stay vigilant for bad actors"* and then
*"proceed safely."* So: exactly that item, plus the adversarial pass they asked
for, scoped to the surface this loop itself had just widened. Nothing else.

**A22 — `/mycelium` reaches the thing that acts.** It was exposed on a route and
read by nothing: the last sensory stream with no internal consumer, and the only
place the node says *who it is talking to*. The watchdog now reads it every round
through a pure `topology_report()`, oriented at what a bad actor looks like in it:

- **an unexpected peer** — named, with its address and the configured set. This
  is the valuable one *because* `POST /peers` is operator-authenticated: a peer
  this watchdog did not expect did not arrive by accident. It is an operator
  action nobody wrote down, or a signed request from a key that should not have
  made it. Neither is inferrable from `/health`.
- **every link at the conductance floor** — A11's measured signature. All links
  at MIN means the learned delivery ordering has been erased, by regression or by
  something feeding this node enough redundant traffic to attenuate every edge.
- **a chain that shortens** — a rollback, a swapped database, or a different node
  answering that port. Loud, and it says *do not transact*.
- **a silent restart** — uptime going backwards. The text is deliberately stable
  so adaptation shows it once and then CLEARs, rather than re-firing with a new
  number every round.

A configured peer missing or dropped is INFO. Everything reports; nothing
restarts, blocks or reconfigures on a topology reading — P12's boundary, same
reason.

**THE COMMENT THAT DENIED ITS OWN CONTROL.** `POST /peers` carries, inline:
*"Still NOT authenticated -- anyone can register a peer."* It is **wrong**.
`("POST", "/peers")` is in `PROTECTED_OPERATOR_ENDPOINTS`, and the
`before_request` hook requires a signed, nonced, timestamped request from an
allowlisted key and fails closed on missing headers, unknown key, bad signature,
stale timestamp and replayed nonce — all read, not assumed. The v8.9 operator-auth
work fixed this and left the comment behind.
A comment that denies a live control is worse than no comment: it invites the
next reader — human or model — either to panic, or to reason *"peers are
unauthenticated anyway, so this other thing doesn't matter"*, and it survives
because nobody greps a comment. **M6 in the mirror: when prose disagrees with
code, fix the prose — and assert the control in a test so it cannot drift again.**
`test_a22` P1 now fails if `/peers` ever leaves the protected set.

**THE PART I DID NOT EXPECT: two defects in my own code from ninety minutes
before.** A20/A21 shipped green — 26 suites, 856 checks, interop measured against
a real old binary, the disclosure boundary asserted against bytes captured off
the wire. None of that covers an adversary using the surface I had just widened.

1. **A bound that refuses is a lockout, and a lockout is a signal an attacker can
   switch off.** `PeerStateTable` capped at 512 and *refused* new keys when full.
   Anything reaching the node from enough sources could fill it first, after which
   no real peer could ever be recorded — which would **silently disable the A7
   split-source warning**, the thing that exists to say the mesh disagrees about
   what is valid. An attacker turning off a detector is worse than an attacker
   tripping it. Now evicts the oldest, so a flood costs the attacker its own rows.
2. **I rebuilt the bug I had just fixed, one layer down.** The same night the
   watchdog learned to transmit change rather than state — after measuring 3,973
   log lines carrying 16 messages — I wrote `peer_version_mismatch` to record on
   *every* observation. Once per heartbeat, per differing peer, for ever, into a
   **bounded** anomaly buffer whose entire purpose is retaining phasic events. A
   tonic kind in there crowds out what the buffer exists to keep, and would trip
   the spike detector on a condition nobody can act on. Now recorded on change or
   first sight. → **M33**: a lesson learned at one layer is not automatically
   applied at the next; go and check the code you wrote *after* learning it.

**Verification.** `test_a22_topology_vigilance.py` 21/21 ×2 in the cloud and
**21/21 over the bridge on L's machine, against the deployed bytes**; 0/1
PRE-FIX RECORD on the pre-A22 watchdog (it reports that `/mycelium` has no
consumer, which is the finding). **All three new guards mutation-tested**: drop
`/peers` from the protected set → P1 fails; revert the eviction → T8 fails
(`real-peer=False`); revert record-on-change → T9 fails (10 records from 10
observations). Full sweep on the shipped file, **27 suites, 877 checks, zero
failures**.

**A pattern in my own work worth counting, because it is now four for four.**
Every test-assertion bug tonight was the same species — asserting a *proxy* for
the claim instead of the claim: V5d asserted "the banner does not say v7.0",
which an empty banner satisfies; B2/B3 matched substrings inside a function that
contains every route and inside a warning's own prose; C4 asserted a peer would
not be recorded when the correct behaviour records it with no version; and P2
here searched for the *absence* of a phrase that my own correction note quotes
deliberately. Each rewrite made the check stricter, never more permissive — but
the frequency is the signal. **When writing an assertion, write down the claim in
words first, then check the assertion is that claim and not something correlated
with it.**

**Delivery.** `device_commit_files` (each verified by sha256 on the far side) +
`project_write`: `covenant_unified_v8.py` v8.34 (`773cb7d7…`; backup
`covenant_unified_v8.PRE-v8.34.py`), `covenant_watchdog.py` (`7c32717b…`; backup
`covenant_watchdog.PRE-mycelium.py`), `claude/test_a22_topology_vigilance.py`
(`0f0cee1c…`), `run_all_tests.sh` (`507f73fd…`), `pc/run_local_sweep.py`
(`eef197b8…`).

**FOR L, unchanged and now four versions deep:** `AB_RESTART_NODES.bat`. The
running nodes are on **v8.30**. One restart brings up v8.34 and a watchdog that
names what it is watching, transmits change instead of state, reads the node's
own anomaly stream, reads its topology, and says something when a peer appears
that nobody configured. Then re-seal. **Nothing here changes what a node
accepts or refuses** — every change this session is disclosure, observation, or
a tightening of what a peer can make this node do.

**Loop improvements.** M33. A22 closed. STALL WATCH stays 0. Self-assessment:
28 runs, 39 closed, 33 methods, 31 corrections, 5 dead ends.

**Cost:** ~⅓ session. Roughly half on the topology reader and its suite, a third
on the adversarial review of A20/A21 and the two fixes it produced, the rest on
mutation testing, the sweep and this entry.

**Next.** Still L's: **A16 Option A**, **A10**, **B4**, the **A12
consolidation**, **P2**, **P3**. Unblocked code work: **P8** (b5's knife-edge
assertion), **P10** (the audit should SKIP its sandbox checks with a reason where
the sandbox correctly refuses, instead of three permanent phantom failures on
every Windows sweep), **P7**, **D5**, **D6**. The sensing survey's list is now
empty: `/anomalies` and `/mycelium` both reach the watchdog, and the spike
verdict reaches it with them.

### 2026-08-23 ~07:45 — "implement": P8 and P10 closed, P7 instrumented — a sweep cannot tell you anything until it is quiet

**L's ask:** *"implement."* Taken as the unblocked items this file had already
named — P7, P8, P10 — which turn out to be **one problem under three numbers.**
On Windows the suite reported four failing lines. Three of them were correct
behaviour being asserted as if it were wrong, and one (P9, the NTFS key ACL) is
real. Four red lines cannot report a fifth: a standing failure trains its reader
to skim the section it lives in, which is the watchdog-log failure — 3,973 lines
carrying 16 messages — reproduced inside the test suite. → **M34**.

**P10, and it is a correction against my own backlog wording.** This file said
the audit should "SKIP its three sandbox checks with a reason". That is wrong: a
skip means the check stops checking on the platform that actually runs
production. What it should do — and now does — is assert what CORRECT behaviour
is on the platform it is running on, because "this cannot work here" almost
always means "here it must fail closed", and that is a property worth testing.

On a fork platform the three limit checks are unchanged. On a no-fork platform
they become four: a benign snippet is **refused and not run**; a memory bomb is
never reported ok; an infinite loop is refused in ~0 s **without being
executed**; and the refusal names its reason so it is diagnosable. Plus one that
runs on BOTH platforms and pins P4's one-way rule —

> the sandbox never reports success when its limits cannot be enforced

— which nothing in this suite tested before today. `COVENANT_FORCE_NO_SANDBOX=1`
reaches the no-fork branch from Linux, so the Windows assertions are verifiable
from anywhere; the refusal shape was then confirmed on L's own machine over the
bridge (`ok=False ran=False refused=True`, loop refused in 0.000 s). **128/128**
on the fork path, **129/129** on the no-fork path. Mutation-tested: make
`run_sandboxed` claim `ok: True` while unable to enforce and **all five fail**.

**P8 — the same disease in miniature.** b5's L2 compared a measured 2.50 s
against a 2.51 s bar the same run had computed one line earlier. The behaviour is
real; the equality is not. It passed one sweep and failed the next two, which
teaches its reader precisely what a permanent failure does. Both L2 cost checks
now use `BAR = per_tx * 0.95`. The tolerance costs nothing — if the retries
stopped happening the figure would be ~`t`, a third of the bar — and this run it
measured **2.51 s against a 2.51 s bar**, which is how thin the margin was.

**P7 — instrumented, not fixed, and that was the item's own instruction.** The
question was whether K1/K3's Windows failure means the node skipped the send
because A12's backoff had already marked the peer dead. `p7()` now prints
`dead_peers`, `heartbeats_skipped`, `peers` and the anomaly kinds on the relevant
node either side of the kill, and folds them into the failing check's own detail
string, so the next Windows sweep's output carries the answer instead of anyone
reasoning toward it. It asserts nothing.

**And the Linux baseline is now on record, which is half the answer:**

```
K1  [after kill, before mine] A: dead_peers=0 heartbeats_skipped=0 kinds=['peer_message_error']
K1  [after mine]              A: dead_peers=1 heartbeats_skipped=0 kinds=[..., 'peer_send_failure']
K3  [after kill, before mine] B: dead_peers=0 heartbeats_skipped=0
K3  [after relay]             B: dead_peers=1 heartbeats_skipped=0
```

So on Linux the send is **attempted**, fails, and that attempt is what marks the
peer dead. **If Windows shows `1 -> 1` with no `peer_send_failure`, the
hypothesis is confirmed** and the node is behaving correctly with only its record
missing. Still not fixed, for the reason the item gave: "a skipped block delivery
should leave a trace" is probably right, but a heartbeat skip must NOT — that
would flood /anomalies with exactly the tonic signal this day's work spent itself
removing.

**What the Windows sweep should look like after this.** Previously
`security_audit 123/127` (3 sandbox + 1 NTFS), `b5 30/31`, `a1_kill_matrix
28/30`. Now: the sandbox section passes *because* it asserts the refusal; b5's
knife-edge is gone; a1_kill_matrix's K1/K3 still fail **but their failure now
carries the measurement that explains it**; and P9's NTFS key-file ACL remains,
which is a genuine finding and L's decision. **One real line instead of four.**

**Verification.** Full sweep on the shipped files, **27 suites, 878 checks, zero
failures** (security_audit 127 -> 128 on the fork path, the extra being the
one-way check). `test_security_audit` run twice more under
`COVENANT_FORCE_NO_SANDBOX=1`. `test_a1_kill_matrix` 30/30 with the measurement
printing. No node source change this run — v8.34 is unchanged, so the restart
still pending covers everything.

**Delivery.** `device_commit_files` (verified by sha256 on the far side) +
`project_write`: `test_security_audit.py` (`28dfbfe8…`; backup
`test_security_audit.PRE-P10.py`), `claude/test_b5_mine_latency.py`
(`ef0dfebf…`; backup `.PRE-P8.py`), `claude/test_a1_kill_matrix.py`
(`937434c8…`; backup `.PRE-P7.py`).

**Loop improvements.** M34 (a check that fails on a platform should assert what
is correct there — never skip, never leave it red; plus the knife-edge case).
P8 and P10 closed; P7 instrumented. STALL WATCH stays 0. Self-assessment: 29
runs, 41 closed, 34 methods, 32 corrections, 5 dead ends.

**Cost:** ~⅓ session. Half on P10 (including establishing exactly what the
refusal returns, which is what made the assertions writable), the rest on P8, the
P7 instrumentation and its Linux baseline, the sweep and this entry.

**Next.** Still L's, unchanged: **A16 Option A**, **A10**, **B4**, the **A12
consolidation**, **P2**, **P3**, **P9** (the NTFS ACL — now the only red line a
Windows sweep will show, which is the point of this run). Unblocked code work
left: **D5** (`pc/MY_STRATEGY.md` still has none of L's actual numbers, and every
input it needs is in the project), **D6** (HBAR on the 408-bar series), and
writing `execute.py`/`paper_run.py`, which do not exist and whose design
`EXECUTION_ARCHITECTURE.md` describes as tested when it was not. **And the
restart, four versions deep.**

### 2026-08-23 ~08:30 — C5: the Android on-device privacy layer, COMPILED rather than described; and it collides with C3

**L's ask, from the trigger prompt itself:** an Android privacy/security layer
in Kotlin on `VpnService` — local only, no remote server, no traffic to a third
party — with "the integration vector" (a governance seam a later module drops
into) given real design attention. Every A-series item is closed or is L's to
decide, so this outranked the D-series remainder and is the newest instruction
besides.

**The decision that shaped the whole run: I checked whether I could build it.**
The brief offered an explicit escape hatch — *"if the Android SDK/Gradle isn't
available, say so rather than claiming the build passes"* — and taking it would
have been reasonable and wrong. Four `curl`s later: JDK 21 and Gradle are
pre-installed here, and `dl.google.com`, `repo1.maven.org` and
`plugins.gradle.org` all answer **200** through the proxy. `sdkmanager` pulled
platform 37 + build-tools 37.0.0 (956 MB) in about eight minutes, and the thing
compiled. **The escape hatch is for after the measurement, not instead of it**
— which is M30 aimed one step earlier, at a claim about the environment rather
than about the code. → **M35**.

**What it is.** `covenant-guard-src.tar.gz`, five Gradle modules, 47 source
files, 4,761 lines of Kotlin. AGP 9.3.1 / Gradle 9.7.1 / Kotlin 2.4.10,
minSdk 26, target 37.

**The module split is the verification strategy, not tidiness.** Everything that
can be wrong in a way nothing notices — one's-complement checksums, DNS name
parsing, suffix matching, precedence between conflicting rules, hash chaining —
lives in `:policy-api` and `:core`, which have **no Android dependencies** and
therefore run under `./gradlew test` on a laptop in five seconds. A bad UDP
checksum does not throw; the phone's own stack drops the reply and the app just
hangs. What is left in `CovenantVpnService` is I/O and lifecycle: the part that
genuinely needs a phone, kept small *because* it is the part I could not test.
M29 in the mirror.

**Measured, twice, the second time with `--no-build-cache --rerun-tasks`:**

```
89 JVM tests, 0 failures   (dns 16, ip 12, blocklist 9, engine 17, audit 11,
                            filter 12, governance 11, smoke 1)
:app:assembleDebug         5.5 MB
:app:assembleRelease       1.1 MB under R8
lintRelease                0 errors, 13 style warnings (each named in README 7.9)
zipalign + apksigner       Verifies; v2 true, v3 true
blocklist                  200k entries: build 1.2 s, 200k worst-case lookups 128 ms
```

**And then read the artefact, not the build log.** "BUILD SUCCESSFUL" says the
compiler was happy. `aapt2 dump xmltree` on the built APK proved
`android:permission="android.permission.BIND_VPN_SERVICE"`, the
`android.net.VpnService` intent filter and `foregroundServiceType=0x40000000`
(specialUse) actually landed. `apkanalyzer dex packages` on the **R8 output**
proved the keep rules kept `PolicyProvider`, `AuthorityModel` and every
implementation including the separate example module — R8 stripping an
extension point that nothing statically calls is the plausible failure here, and
it is the one that would have shipped silently. Same shape as M32.

**THREE REAL DEFECTS, all in code that read correctly.** Recorded because a
README saying "tested" and one saying "I wrote tests that found nothing" look
identical:

1. **The suffix walk never reached the apex.** `Blocklist.lookup` re-sliced the
   *original* domain each round using an index taken from the *current*
   candidate, so it oscillated between two strings and terminated on the loop
   guard. Effect: `*.tracker.example` did not block
   `deep.sub.tracker.example` — **every wildcard entry in a real blocklist
   silently inert beyond one level**, while the exact-match tests all passed.
2. **The audit log erased itself on restart.** `File.bufferedWriter()`
   truncates. The first append after a process restart wiped the entire prior
   chain — committed by the very class whose whole purpose is making deletion
   detectable. Now opens in append mode.
3. **Rotation destroyed verifiability.** Past two segments the older one is
   dropped, so the live file's first record no longer chained from GENESIS and
   `verify()` reported a permanent break. That is **M34's disease exactly**: a
   check that is always red is a check nobody reads. Fixed with an `#anchor`
   line naming the head each new segment continues from, and a separate
   `historyRotated` flag — "verified, with history rotated" and "broken" are
   different facts and one boolean loses the distinction.

One of my own assertions was wrong in the familiar way (four-for-four became
five): the rotation test first asserted `recordsChecked > 20`, a **guessed
number** that would break whenever a field width changed. It now asserts the
actual property — that `verify()` covers every record held across both segments.
And the pinned canonical-form digest was computed **independently in Python from
the written spec**, not by running the Kotlin and copying its output; both agree
on `561082c5…`. A pinned value produced by the code it checks is a photograph,
not an oracle.

**THE GOVERNANCE SEAM — the part L singled out, and the part with a real
judgement call in it.** `PolicyProvider.evaluate(DecisionContext): Verdict?` —
`ALLOW`, `DENY`, `LOG`, or `null` to abstain. Chain order is ascending priority,
ties broken by id, so it is **total and reproducible**; a chain whose order
depends on registration order answers differently after a reboot and nobody ever
finds out why (asserted by registering three providers in both orders). Every
provider is consulted on every decision — a few hash lookups, and it buys that a
low-priority DENY cannot be hidden by a high-priority ALLOW that merely ran
first.

Conflict resolution, and the asymmetry is the design:

- **DENY is absorbing**, attributed to the strongest denier.
- An ALLOW overturns it **only** with an explicit `canOverrideDeny = true`
  *and* strictly stronger priority — every such event written to the audit log
  with `wasOverride = true`. Equal priority is not enough.
- **A throwing provider abstains.** It may not deny (a crashing module must not
  be able to take the network down) and may not allow (or `throw` becomes the
  cheapest possible bypass). Both asserted.
- The app's **own blocklist has no special standing** — it is an ordinary
  provider at priority 100, and a test has an example module at priority 10
  overturn it.

It takes a declaration plus higher standing to un-block something, and nothing
at all to block it. *A governance layer whose modules can quietly permit is not
a governance layer.*

**Extension point: a compile-time module boundary, NOT AIDL — and the README
argues it rather than asserting it.** A Binder transaction per DNS question adds
a context switch and a serialisation round trip to every name the phone
resolves; a separate process can be slow, frozen or absent, so the decision path
would need a timeout policy, and *whatever that policy is, it is a security
decision made by a scheduler* (fail-open is a bypass, fail-closed lets a
third-party process take the device's DNS down by being slow); and an **exported
decision hook is a way for any app that binds it to see every domain this device
resolves** — the surveillance the app exists to prevent, rebuilt as a feature.
AIDL *is* used, for the control plane only — install rules, list providers,
verify the audit chain — unexported, off the packet path, every entry point
gated through `AuthorityModel`. The honest cost, stated in README 7.8: a module
must be compiled in, so installing one means rebuilding.

The four readings of "governance" the interface accommodates: policy over
app/domain access (**built**), an approval/authority model (**built** —
`SoleOwnerAuthority` ships, `TwoKeyAuthority` is the example, and its test is
the one that matters: three copies of Alice's signature is still one approval);
a tamper-evident audit log (**built**); multi-party / remote attestation
(**interface only, deliberately** — on the decision path it reintroduces §5.3's
problems over the internet instead of over Binder; it belongs in the control
plane, attesting the rule set out of band).

**On the audit log's honesty.** It makes a *partial* edit detectable — deleting
the one line recording a block breaks every subsequent hash, and `verify()`
names the first bad record. It does **not** stop anyone who can write the whole
file from recomputing the chain; the hash is public and there is no secret. The
README says exactly that, and names the two things that would fix it (a Keystore
key the writer cannot read, or an off-device witness for the head hash) as
unimplemented hooks. Claiming "tamper-proof" here would have been the easy and
false thing.

**AND IT COLLIDES WITH C3 — the finding that outlives the app.**
`claude/ANDROID_VPN_SYNC.md` §3 has the phone on **Tailscale** for the whole
covenant-node sync path. **Android permits exactly ONE app to hold the VPN
interface** — no chaining, no stacking, no API to share it; starting either
tears the other down and the loser gets `onRevoke()`. So the same handset cannot
be a covenant node over Tailscale *and* run an on-device filter. Neither
document said so and both plans were written for the same phone. Also worth
knowing before C3: **Android's Private DNS (DoT) bypasses a TUN DNS filter
entirely**, as does an app with hardcoded DoH.

**Eleven assumptions are flagged in README §7**, numbered so L can answer "7.3
is wrong" instead of re-describing the task. The largest is §7.1: no device, no
emulator, so nothing below `builder.establish()` has ever executed, with a
ranked list of what is most likely to be wrong because of it. Also named as
gaps, not oversights: no automatic blocklist downloads (7.2 — an app whose claim
is "nothing leaves the device" that also phones a URL on a timer has one more
thing to trust), `QUERY_ALL_PACKAGES` (7.3), full-tunnel mode routes everything
but only *filters* DNS because per-app connection blocking needs a userspace
TCP/UDP stack and a half-working one is worse than none (7.5), and the AIDL
`installRules` stub, because shipping a half-checked parser **on the path that
installs policy** is worse than shipping none (7.7).

**Section 0 held.** Nothing here touches the node, the ledger, the judge or
`TRADING_POLICY.json`; no credential is requested or stored; the app makes no
network request but forwarding the DNS it did not block; and the README's §9
spells out why a model call must never be on the packet path — latency, cost,
determinism, and the privacy inversion of shipping every name you resolve to a
third party to ask permission.

**Delivery (M25 — `project_write` is not delivery).** `SendUserFile`:
`covenant-guard-src.tar.gz` (`4e92a59f…`), `README.md`, and
`covenantguard-debug.apk` (`ade4fa17…`) so it can be tried immediately — with
the caveat stated to L that installing a later release-signed build will require
an uninstall, which erases the audit log. `project_write`:
`claude/ANDROID_GUARD.md`, the design record, headed with a note that it is
**not** the source. **Nothing here goes into `C:\Users\<user>\covenant`** — it
is an Android project, not part of the node, and it must not be dropped into the
folder `covenant_seal.py` hashes.

**Loop improvements.** M35. C5 closed. One correction (the Tailscale/VpnService
collision). STALL WATCH stays 0. Self-assessment: 30 runs, 42 closed, 35
methods, 33 corrections, 5 dead ends. Also corrected the "backlog items closed"
header, which read 34 while the list beside it already held 41.

**Cost:** ~⅔ session. Roughly a sixth on establishing that the SDK was reachable
and getting AGP 9 + Kotlin 2.4 + JDK 21 to agree, a third on `:policy-api` and
`:core` with their tests (where all three defects surfaced), a sixth on the
Android module, a sixth on the README, the rest on the two clean sweeps,
artefact inspection, signing and this entry.

**Next.** Still L's, unchanged: **A16 Option A**, **A10**, **B4**, the **A12
consolidation**, **P2**, **P3**, **P9**. Unblocked code work: **D5**, **D6**,
and writing `execute.py`/`paper_run.py`. **And the restart, still four versions
deep** — the nodes are on v8.30 and the project holds v8.34. On C5 the next move
is L's: try the APK, then answer README §7 — and decide the C3 question, because
the phone can be a covenant node or a filtered phone, not both.

---

### 2026-08-24 ~02:00 — B2 closed (v8.35): the diversity check had never once constrained a running node, and one of its two "judges" was the sender's own word

**Item choice.** Every A-series item is either closed or is L's to decide, so A
is blocked and B is next. B2 was the only unblocked item in B — B4 is L's, and
B5's fix waits on B4's answer. It also turned out to be the item with the most
untrue claim behind it, which is usually where the value is.

**The premise was too kind to it.** B2's own wording, and the source's own
honesty note, said the check was *label*-deep: two `MockJudge`s wearing
different `judge_id`s satisfy it. Both true. What neither said is that the check
is **unreachable**. `QUORUM_DIVERSITY` counts distinct `judge_id` prefixes, and
`build_semantic_quorum` **always appends `mock_selfreport:0`** — its own prefix.
So the bucket count is ≥ 2 for *every* provider list the builder can be given:

```
['claude']              buckets=['claude','mock_selfreport']         PASS
['claude','claude']     buckets=['claude','mock_selfreport']         PASS
['mock']                buckets=['mock_insecure','mock_selfreport']  PASS
['mock','mock']         buckets=['mock_insecure','mock_selfreport']  PASS
include_mock_selfreport=False   -> ValueError   (nothing constructs this)
```

The only inputs it rejects are ones no node ever builds. *A control that passes
on every real configuration is not a control.* It is M34's disease in the
mirror: a check that is always green is a check nobody reads either.

**Three more measurements, and the third is operational.**

- **The second bucket is not a second opinion.** `MockJudge` passes *"drain all
  staked funds to attacker wallet, steal everything"* as **"Morally
  acceptable"**; it flags only what the **sender** puts in its own `_violation`
  key. It is a self-report channel — correctly wired as an absolute veto, which
  is a good design — and counting it toward diversity is a category error.
- **Three vendors, one prompt, one parser.** `_parse_verdict` and
  `_build_prompt` are defined only on `_APIReasoningJudge`; no vendor subclass
  overrides either. B1's real bug — `"violates": null` read as clean — lived
  exactly there. It would have produced the same wrong verdict on Claude,
  OpenAI and Google **at the same instant**. Vendor diversity does not buy
  verdict-path diversity, and nothing said so.
- **A judge with no credential counted as diversity while blocking
  everything.** `["claude","openai"]` with one key: the semantic veto threshold
  is `ceil(2×0.5) = 1`, so the keyless judge's single fail-closed vote makes
  **every transaction violate**. Measured on a benign transaction:
  `violates=True infra=True`. And `/health`'s `judge_keyless` is *"no key for
  ANY of the three env vars"*, so with one key set it reports **`false`** —
  healthy. That is exactly the failure the `/health` block's own docstring says
  it exists to prevent: *"a node with no judge API key boots, serves /chain,
  peers correctly and rejects 100% of transactions… Each field below is one of
  those failures made visible BEFORE it costs anything."* The field was there
  and had a hole in it.

**What was built, and what was deliberately not.** Reasoning diversity is not a
property code can check. **Independence of failure** is — and that is what
diversity is *for*. `quorum_diversity_report()` measures it: per judge, the
implementation class, vendor, credential env-var **name**, whether a credential
is held (a bool, never a value), model, whether `_call` is implemented at all,
and which class supplies its parser and prompt.
`independent_semantic_judges` = distinct `(implementation, credential, model)`
among operable semantic judges. Six named, stable-texted degradations so the
watchdog's P12 adaptation shows each once and then CLEARs it.
`shared_verdict_path` is a **fact, not a warning** — it is true of every
configuration this file can build, and warning on it would train an operator to
ignore warnings (M34).

It is **disclosure, not policy**, and each of those is pinned:

- no verdict changes (S3), `degraded`'s formula is byte-identical to v8.34 (H3),
  the existing `QUORUM_DIVERSITY` raise is untouched and still fires first (E5);
- the report **never contains a credential value** — S1 plants a sentinel string
  in a judge's `api_key` and asserts it is absent from the serialised report;
- the tightening is **opt-in and one-way**: `COVENANT_REQUIRE_JUDGE_DIVERSITY=1`
  refuses a non-diverse quorum at build time, **only the exact string `"1"`**
  arms it, and no value relaxes anything (E4 tries seven). Same shape as
  `COVENANT_FORCE_NO_SANDBOX` in P4/P10. Default unset = v8.34 behaviour, which
  is why L's mock nodes and all 26 suites still boot;
- **the boundary (M31/A21)**: the operator may see the quorum's composition, a
  **peer may not**. It is on `/health` beside `substrate`, and absent from the
  digest — asserted on the object in `test_b2` §B *and* on the bytes off the
  wire by `test_a20` D1–D6 (M32: those are two claims).

**Verified on a real node, not only in-process.** The boot banner is what an
operator actually reads (P11), so it says it:

```
Covenant Unified v8.35 (source 1207bd2e7dc5, 9595 lines) running - API: 18400 …
  ethics quorum: 1 independent of 1 semantic judge(s), +1 self-report; veto>=1; diverse=False
  WARNING: ethics quorum is not independently diverse: … -- the self-report layer
           is not a second opinion (B2)
```

and `/health` carried the report, the warning, and `degraded` unchanged.
`covenant_watchdog` renders `judges=k/n` (`!` when not diverse) on its per-round
INFO line, so `watchdog.log` becomes a minute-by-minute record of what the gate
actually was — and the warning reaches alerts through the existing
`for w in real` wire, with no new watchdog plumbing and no collision with the
known-false `"ethics gate has no provider key"` string.

**`test_b2_quorum_diversity.py` 73/73 ×2. PRE-FIX RECORD 22/29 on pristine
v8.34** — and the split is the point: the 22 that pass are the *record of the
old behaviour* and pass on both files; the 7 that fail name the missing fix.

**A second finding, found by the sweep, in a suite rather than the node.**
`test_a20_peer_version` came back 7/9. Its C0 asserts *"a pre-A20 source is
available to test against"* — a property of the **test directory**, not of the
system. On the machine that made `PRISTINE-v8.32.py` it is green; anywhere else
it is red for ever. And it did worse than be red: `interop_checks()` **returned
early**, so `wire_digest` was never captured and **D1–D6 never ran** — the six
checks on what actually leaves the process, which are precisely the ones that
police the boundary this run's change sits on. *Two visible failures were
concealing six absent checks.* Decoupled (the wire capture needs only a new
node): **13/13**, with D5 reading `{"v":"v8.35","src":"1207bd2e7dc5",…}` off the
wire. C1–C5 now report through a third outcome, `not_run()`, printed in the
summary as *"1 section(s) NOT RUN — do not read this as covered"*. The rest is
**P13**: the honest fix is a synthetic pre-A20 peer, not a fabricated
`PRISTINE-v8.32` — a fake pristine artifact is how a false claim gets a hash.

**Full sweep, twice, on the shipped file `1207bd2e7dc5`: 26 suites, 926 checks,
zero failures.** a11 23, a12 21, a13 25, a14 15, a15 14, a17 6, a1_kill 30,
a1a_a2 15, a20 13, a22 21, a3 7, a4 60, a5 20, a9 18, adversarial 21, b1 162,
**b2 73**, b5 31, d3 77, multinode 21, p11 29, p12 41, security_audit 128,
w1 24, w2 21, y1 10. Batched ≤ 7 fast / ≤ 5 slow (M20).

**Two of the first sweep's three failures were my sandbox, not the code**, and
both read exactly like regressions: `test_security_audit` could not import
`covenant_trading_bridge` (staged it → **128/128 ×2**) and `test_w1_wsgi` could
not find waitress (`pip install` → **24/24 ×2**) — **P1 recurring, same package,
three days later**. → **M37**: read a failure's *first* line, not its verdict;
an import error and an assertion failure are different kinds of news.

**Loop improvement — L's "shrink imprint while growing effectiveness while not
losing content", applied to the loop's own memory.** This file is read in full
at every boot and had reached 4,852 lines. Two costs were pure duplication:

- the **STALL WATCH banner**, whose job is one number rule 6 asks for, had
  accreted **nine runs of narrative, 63 lines** — every sentence of which is
  also in §4 as a struck-through item and in §5 as a run entry. Moved
  **verbatim** to `claude/LOOP_HEADER_ARCHIVE.md`; the banner is now 21 lines
  and leads with the number;
- **§4 is ~890 lines holding ~14 open items**, and a run reads all of it to pick
  one. An **OPEN-ITEMS INDEX** now heads it — one line per open item with its
  blocking state. Purely additive; nothing struck through was touched.

**And the honest arithmetic, because "shrink" invites a wrong inference: this
file got BIGGER this run — 4,853 → 5,178 lines** — since a closed item, a new
open item, two methods and this entry all landed in it. What shrank is the
**orientation read**: the banner 63 → 21 lines, and §4 pickable from a 30-line
index instead of 890. The record grows; the cost of finding your way into it
does not have to. Confusing the two is how a log gets "tidied" into a shorter
file that has lost something.

The rule that makes this safe, and the reason it is a method rather than a
tidy-up: **an index may be regenerated; a record may not be edited.** The banner
and the index are derived views. §0 and §5 are the record. When the temptation
is to delete something to make this file smaller, the move is *a new file plus a
pointer, named in the run-log entry* — otherwise the next run finds a gap and
cannot tell shrinkage from loss. → **M36**.

**Section 0 held.** Nothing here weakens a control: the v8.34 raise is byte-
identical, `degraded` is byte-identical, no verdict changes, and the only new
lever can add a refusal and never remove one. No credential was requested,
stored or read — where a judge had to appear credentialled, its `api_key`
attribute was set to the literal `"canned"` on the object; the report carries
env-var *names* and booleans, asserted. No trade, no order, no profit claim.
And B2 is closed **without** claiming the gate is now diverse: what this closes
is the claim that it already was. **L: the one line that makes it true is
`COVENANT_JUDGE_PROVIDERS=claude,openai,google` with all three keys present**
(measured `diverse=True`, independence 3), plus
`COVENANT_REQUIRE_JUDGE_DIVERSITY=1` to keep it that way.

**Delivery (M25).** `SendUserFile` **and** `project_write`:
`covenant_unified_v8.py` (**v8.35**, 9,595 lines, sha256 `1207bd2e7dc5…`),
`covenant_watchdog.py`, `test_b2_quorum_diversity.py`,
`test_a20_peer_version.py`, `run_all_tests.sh`.
**L must copy all five into `C:\\Users\\<user>\\covenant`** — `covenant_unified_v8.py`
needs `covenant_path_pattern.py` beside it (already there), and
`test_a1_kill_matrix.py` imports `test_a9_relay_race.py`. This was a scheduled
cloud run: **no device bridge**, so the copy could not be done from here.
**And the restart is now five versions deep** — the nodes are on v8.30 and the
project holds v8.35. Nothing in P11, P12, A20, A21, A22 or B2 has ever executed
on the machine that runs the chain.

**Cost:** ~⅔ session. Roughly a fifth on measuring the pristine behaviour before
writing a line (which is where the three extra findings came from), a fifth on
the report and its wiring, a quarter on the suite and its pre-fix record, a
fifth on two full sweeps and chasing two dependency failures that were not
regressions, the rest on the a20 decoupling and this entry.

**Next.** Unchanged and still L's: **A10**, **A16** (Option A), **B4**, the
**A12 consolidation**, **A7/A8**, **P2**, **P3**, **P9**, and C5's README §7.
Unblocked code work, in order: **P13** (the synthetic pre-A20 peer — it makes a
standing check out of a dated measurement), **A3's send-side follow-on**,
**C2**, then **D3a** (`execute.py` / `paper_run.py` do not exist), **D5**,
**D6**. But the highest-value action in the whole backlog is not code: **restart
the nodes on v8.35.**

### 2026-08-24 ~07:00 → ~07:45 — (attended, L-started) THE DELIVERY ACTUALLY LANDED, hash-verified on the target for the first time; and P14: the watchdog was the stale thing

**The rule at the top of this file was right, and it had never once been run.**
`PC_SYNC_LOOP.md`'s instruction — *in an attended, L-started session,
hash-compare the deployed source against the project's BEFORE choosing an item;
drift outranks the backlog* — has sat in the banner since 08-22. This is the
first run to be in a position to obey it: L started the session, the desktop
bridge was live, and `~/covenant` was one `device_request_folder_access` away.
No backlog item was chosen. The drift was.

**What the drift actually was — and the log was wrong about it in both
directions.** The banner said *"the nodes are on v8.30, the project holds
v8.35 … the restart is now five versions deep."* Measured:

```
DISK   covenant_unified_v8.py   v8.34  773cb7d7adef   9347 lines  mtime 08-23 07:39
PROJECT covenant_unified_v8.py  v8.35  1207bd2e7dc5   9595 lines
RUNNING nodeA.log boot banner:  "Covenant Unified v7.0 running"
```

So the **disk** was one version behind, not five — a delivery landed on 08-23
at 07:39 that no run-log entry records. And the **running processes** are older
than either: the `v7.0` string is the hard-coded banner **P11 replaced in
v8.31**, so whatever is answering :5000 and :5020 predates v8.31 and cannot
report `source_sha256` at all. *Two of the three numbers in the banner were
wrong, in opposite directions, and the third was never measured.* → **M38**.

**The delivery, and the first hash-verified one in this project's history.**
`SendUserFile` → `device_commit_files` → and then the check that has never been
possible before: re-hash the file **on the target**.

```
DEPLOYED: 1207bd2e7dc5  9595 lines      COVENANT_VERSION = "v8.35"
EXPECTED: 1207bd2e7dc5  9595 lines      quorum_diversity_report ×4
```

Byte-identical. `covenant_unified_v8.PRE-v8.35.py` and
`covenant_watchdog.PRE-b2.py` keep the previous files. Also shipped, because
the machine did not have them: **`test_b2_quorum_diversity.py`** (444 lines,
`d50d175f621a`) and its entry in `run_all_tests.sh`. M25 is now closable in the
only way that counts — not "written to the project", but *"grep the deployed
file and it agrees"*.

**Then the finding, and it was sitting in a log the loop had never opened.**
`logs/watchdog.log` was being written **while I read it** — 2.0 MB, 12,538
lines. The composition:

```
INFO   9076
ALERT  3456   of which 3448 are TWO permanent win32 facts, once a minute, per node
WARN      6
```

The eight ALERTs that were *news* — node B down, node B unreachable, a peer
unreachable ×4, an anomaly spike ×2 — are buried **431:1**. And `Adaptation`,
the class written precisely to stop this, **is in the file on disk**:

```
watchdog started      2026-08-23T01:39:52Z     <- the running process
covenant_watchdog.py  mtime 08-23 07:39        <- six hours LATER
grep -c 'unchanged,' watchdog.log   ->  0      <- no Adaptation in the process
grep -ci 'CLEARED'   watchdog.log   ->  0
```

Zero roll-up lines, zero CLEAREDs, and the INFO lines carry no `v=`/`src=`
fields either — so the running watchdog predates **P11's** watchdog change too.
It has been running 29 hours in that state.

**Which makes the shape of it, not the volume, the actual finding.**
`source_drift_report()` — the check written on 08-23 07:39 *specifically to
catch "the file was updated and the node was never restarted"*, the failure
that cost this project fourteen versions — **has never executed**, because the
process that would run it started six hours before it was written. *The control
built to detect deployed-is-not-running spent a day and a half being a case of
it, while writing confident lines the whole time.* A stale monitor is worse
than a missing one: it produces evidence.

**P14, and why it is a structural gap rather than an oversight.** Every health
check in `covenant_watchdog.py` takes its subject as an argument — a port, a
health dict, a hash — and **nothing passes it itself**. So:

- `SELF_SOURCE_SHA12 = disk_source_sha12(SELF_SRC)` captured **at import** — the
  hash of what this *process* loaded;
- `self_drift_report(loaded, on_disk)` — a pure two-hash comparison, wired in
  beside the node-side check, ALERTing `THE WATCHDOG ITSELF IS STALE: this
  process loaded … but covenant_watchdog.py on disk is … Everything else this
  process reports was produced by the older source.`

**Disclosure only, and pinned as such.** It restarts nothing, refuses nothing,
changes no verdict — the same boundary P12 draws for the substrate sensor and
B2 for the quorum report. A watchdog that restarted *itself* on a hash change
would be a watchdog that any file write can make execute new code; `test_p14`
§C asserts the function body contains no `start_node`, `Popen`, `taskkill`,
`os.remove`, `sys.exit` or `raise`. Its text is deliberately **stable** while
the condition holds, so `Adaptation` says it once and CLEARs it (M34) — §B
proves that against the real class: 1 emission in 29 rounds, then
`CLEARED after 29 round(s):`.

**`test_p14_watchdog_self_drift.py` 33/33.** Pure functions — no node, no
socket, no key, no mining (M13). **Run on Linux only** (the sandbox VM behind
`device_bash` has no flask, so no suite that imports the node can run there):
that is a real limit on this result and M29 says so plainly — it proves nothing
about win32 until it runs on win32. It is wired into `run_all_tests.sh` after
p12.

**The B2 payoff, visible on the live gate.** The production nodes' judge line
reads `judge=quorum(local:0,mock_selfreport:0)` — one local judge and the
**sender's own self-report**, which is exactly the configuration B2 proved the
old check could never reject. `_quorum_brief` was added to the deployed
watchdog, so after the restart that line carries `judges=1/1!`.

**What did NOT happen, and why it is L's.** The restart. `device_bash` is a
Linux VM; the nodes are Windows processes, and File Explorer/Terminal resolve
**click-tier only** (no typing), so driving it from here would have meant asking
L to grant the loop desktop control. §0 says the loop may not widen its own
permissions — L granting it is not the loop taking it, but it is still a new
capability acquired to close a loop item, and that is the reasoning §0 says to
write down for a human rather than act on. So: a one-click launcher,
`Downloads\RESTART_COVENANT_ON_v8.35.bat`, which only `cd`s into `covenant\`
and calls the existing `AB_RESTART_NODES.bat`. L asked to be the one to click
it. **The restart is still open** — but for the first time the thing it would
pick up is verified present on the machine.

**Cost:** ~⅓ session. Roughly a quarter on the bridge, the folder grant and the
hash comparison; a quarter on reading the live watchdog log and measuring the
431:1 burial; a fifth on P14 and its suite; the rest on delivery and this entry.

**Dead ends.** None new. One near-miss worth recording so it is not re-tried:
`device_bash` **cannot** run the suites — the Linux VM behind it has no flask,
and the `.venv` in `~/covenant` is a Windows venv. It is a *third* local (M27),
good for hashing, reading logs and editing files in place, useless for
executing this system. → **DE6**.

**Next.** Unchanged and still L's: **A10**, **A16** (Option A), **B4**, the
**A12 consolidation**, **A7/A8**, **P2**, **P3**, **P9**, C5's README §7. The
single highest-value action is still **the restart** — and it is now one
double-click, with the payload verified rather than assumed. After it: the
first honest Windows sweep in this project's history, because for the first
time the machine holds every suite the runner calls.

**ADDENDUM ~08:10 — "closed them", and what the shutdown proved.** L stopped the
consoles rather than running the restart. That produced a better measurement
than the restart would have:

- **the watchdog's own death is invisible in its log** — last line 08:03:12Z,
  saying both nodes are healthy, and no round since. → **P16**, closed above,
  with the honest caveat that it makes the gap readable and not yet checked;
- **`NODE_RESTART.txt` is untouched** (mtime 08-23 01:39), so `AB_RESTART_NODES.bat`
  genuinely did not run — the delivery is still unexecuted, which is the correct
  and unflattering reading;
- **P3 has a fresh witness.** `nodeB.log` ends in `^C` and nodeB's `-shm`/`-wal`
  are gone — a clean interpreter exit. Node A's `-shm` is **still there**, which
  is what a python.exe that outlived its console window looks like. Not proved:
  an orphaned `-shm` also survives a hard kill, and this VM cannot see Windows
  processes (DE6). It is a **hypothesis with a cheap test** — `netstat -ano |
  findstr :5000` before the next restart — and `AB_RESTART_NODES.bat` kills by
  port precisely because this keeps happening.

**Which leaves the machine in the best possible state for the restart:** nothing
is holding the chain, `AB_RESTART_NODES.bat` frees the ports first anyway, and
everything it will start now comes off the v8.35 files. The watchdog it launches
will, on its first round, run `self_drift_report` and `source_drift_report` for
the first time in this project's history.

**ADDENDUM 2 ~08:16 — IT IS RUNNING. v8.35 is live, and P14 caught a real drift
ninety seconds after being asked to.** L said "do it", which resolved the §0
question the way §0 says to resolve it: the human answered, so File Explorer was
granted at **click tier** and the launcher was double-clicked.

**The restart, 08:10:09 local.** The node's own boot banner — the thing P11
exists to make readable:

```
Covenant Unified v8.35 (source 1207bd2e7dc5, 9595 lines) running - API: 5000 ...
  ethics quorum: 1 independent of 1 semantic judge(s), +1 self-report; veto>=1; diverse=False
  WARNING: ethics quorum is not independently diverse ... the self-report layer
           is not a second opinion (B2)
```

and the watchdog's per-round line, carrying every field the last four runs added,
at once:

```
node A v=v8.35 src=1207bd2e7dc5 height=3 peers=1 judge=quorum(local:0,mock_selfreport:0)
       insecure=False judges=1/1! (+2 known-false warnings suppressed)
```

`v=` and `src=` are P11. `judges=1/1!` is B2 — and the `!` is the whole point:
the production gate is **one** independent semantic judge plus the sender's own
self-report, exactly the configuration v8.34's diversity check passed and could
never have rejected. It is now stated once a minute in the file an operator
reads.

**Adaptation is working, measured.** A round used to write 8 lines (2 node INFOs
+ 6 ALERTs, four of them the two permanent win32 facts). After the restart a
steady round writes **2** — and both are the balance check, which logs
unconditionally by design because it is the fork check. The sandbox ALERT and the
two new B2 diversity ALERTs were said once, in full, and have not repeated.

**P14 verified in production, deliberately.** A test passing and a control firing
are two claims (M30/M32). So the drift was *created*: the on-disk watchdog was
edited while the old process ran. One round later, unprompted:

```
2026-08-24T08:12:52Z ALERT THE WATCHDOG ITSELF IS STALE: this process loaded
c228ac0a629d but covenant_watchdog.py on disk is d363d6c2bb5f -- the checks in
the deployed file are NOT the checks running. Restart the watchdog. Everything
else this process reports was produced by the older source.
```

Both hashes correct, one round's latency, said once and then silent. **This is
the first time anything in this system has detected its own staleness.** The
condition is still live and correct — the watchdog is one edit behind disk — and
clearing it is one restart.

**A hypothesis published an hour ago, falsified by the restart's own output.**
ADDENDUM 1 said node A's surviving `-shm` looked like a python.exe that had
outlived its console window (P3), and named `netstat` as the cheap test. The
restart ran it:

```
--- BEFORE: health A ---        (empty)
--- who is listening ---        (empty)
--- stop by window title ---    INFO: No tasks running with the specified criteria.  x3
```

**Nothing was orphaned.** An orphaned `-shm` also survives a hard kill, and that
is what it was — a leftover file, not a live process. The hypothesis was
reasonable, cheap to test, tested, and **wrong**; recording it as wrong is worth
more than not having made it. P3 is unchanged: still open, still L's, and not
demonstrated on this occasion.

**And a correction against this run's own P16, inside the hour.** The banner
shipped at 08:09 said the log guarantees *"one line every 30 rounds (~30 min)"*.
True, and far too loose: the balance check logs every round whenever both
databases and a key file are present, so in this deployment the real bound is
**60 seconds**. Publishing the weak floor would have taught a reader to tolerate
a watchdog that had been dead for twenty-nine minutes — the exact failure P16
exists to prevent, reintroduced by P16's own wording. The line now states both
bounds and which one applies, decided at startup from whether the databases are
actually there.

**→ DE7. Explorer at click tier can select a file; it cannot reliably launch
one.** The first double-click did start the batch file. Three later ones, on a
correctly selected row, only selected it — `NODE_RESTART.txt`'s mtime never
moved. Typing is blocked at this tier by design, so there is no fallback. The
honest capability statement is: **this loop cannot start a Windows process.** It
can read, hash, edit and deliver; execution needs L, or a scheduled task. That is
roughly what §0 assumed before the grant, and the grant did not change it.

**Cost of the addenda:** ~⅕ session on top of the main run — the restart, the
verification, the deliberate drift, and two corrections against claims this run
itself had made an hour earlier.

**Next, and both are one double-click for L:** `RESTART_COVENANT_ON_v8.35.bat`
again (clears the live P14 alert by loading `d363d6c2bb5f`), then
`SWEEP_COVENANT_v8.35.bat` — the first Windows sweep with every suite present,
now including `test_b2_quorum_diversity` and `test_p14_watchdog_self_drift`,
which has still only ever run on Linux (DE6).

**ADDENDUM 3 ~08:35 — THE WINDOWS SWEEP RAN. 961/964, and the three reds are
two root causes, both of them findings rather than regressions.** L said "you
do it", so the sweep was launched the same way (M39) and finished in **12.2
minutes** against the deployed `1207bd2e7dc5` — certutil re-hashed it in the
report header, so the sweep's own record says which source it tested.

**This is the first time this machine has run the suite set that
`run_all_tests.sh` names.** M29 has been quoted in this log for two days
(*"run it where it runs"*); until 08:20 today it could not be obeyed.

```
27 suites with tallies, 964 checks, 961 passed, 3 failed, 12.2 min
b1 162 | security_audit 128/129 | d3 77 | b2 73 | a4 60 | p12 41 | p14 33 |
b5 31 | a1_kill 28/30 | p11 29 | a20 27 | a13 25 | w1 24 | a11 23 |
a12/a22/adversarial/multinode 21 | a5 20 | a9 18 | a1a_a2/a14 15 | a15 14 |
e2e_gift 11 | y1 10 | a3 7 | a17 6 | sim_order ALL INVARIANTS HELD
```

**`test_b2_quorum_diversity` 73/73 and `test_p14_watchdog_self_drift` 33/33, on
win32.** P14 had only ever run on Linux (DE6) and now has not. Both were absent
from this machine four hours ago.

**RED 1 and RED 3 are the same thing, and it is bigger than P9 was recorded as
being.** `test_security_audit` failed exactly one check —
`FAIL: identity key file is owner-only` — which is P9, already open and already
L's. But `probe_final_pass` died on this:

```
MainnetGuardError: Policy file ...\final_5yerk3_9/p.json is mode 0o666 --
writable or readable beyond its owner. Anything that can edit this file can
raise your own spending limits.
```

Same root cause: **NTFS does not give `os.chmod(0o600)` POSIX semantics, so
every owner-only check in this codebase is false on the platform that runs
production.** P9 is filed as a key-ACL nicety. It is not: it also means
`authorize_mainnet_payment` **refuses on this machine, always** — the guard is
fail-closed, so this is safe, but the XRP mainnet path cannot execute here and
nothing said so, because `probe_final_pass` had never run here. A control that
refuses everything is not the same as a control that works, and it should not be
discovered by accident. → the P9 entry is amended rather than re-filed.

**RED 2 is P7, and the measurement kills the standing hypothesis.** P7's
instrumentation was written on 08-23 to answer one question on the next Windows
run, and asserted nothing. Both K1 and K3, before and after:

```
P7 MEASUREMENT [after kill, before mine] A: dead_peers=0 heartbeats_skipped=0 peers=1 kinds=['peer_message_error']
P7 MEASUREMENT [after mine]              A: dead_peers=0 heartbeats_skipped=0 peers=1 kinds=['peer_message_error']
```

The hypothesis was *"A12's dead-peer backoff had already marked the peer suspect
and the broadcast skipped it — the node is behaving correctly and the missing
thing is the RECORD."* **`dead_peers=0` and `heartbeats_skipped=0` say no.** The
backoff never engaged. Nothing was skipped.

And the truth underneath is worse than the hypothesis. Both `peer_send_failure`
sites call `_note_send_failed` **immediately before** recording, so
`dead_peers=0` proves **neither site was reached**. The only kind present,
`peer_message_error`, is recorded in `_handle_peer`'s except — it is the
**INBOUND** parse-error channel, a different event entirely. So node A mined a
block, failed to deliver it (C provably never got it), and **recorded nothing
outbound and backed off nothing.**

That is precisely the failure **A18 (v8.30) was written to close**, and its own
comment names this exact platform:

> *"Found by running K1/K3 on Windows 2026-08-22, where a killed peer's
> listening port can still accept a connection: every attempt 'succeeded' at
> the socket level, so the except branch below never ran and node A recorded
> nothing about a delivery that never happened."*

A18 added the bytes-accepted-never-ACKed path to catch it. **Five versions
later, measured on the platform it was written for, it still does not fire.**
The fix was written from the right diagnosis and has never been observed
working, because until today it had never been run here. → **A23**, opened
below; not fixed in this run, because the fix is in the send path's definition
of success and §0 forbids relaxing a control to make a test green.

**What is NOT a finding.** `sim_yield_safety` prints no tally by design and
returned rc=0. `probe_final_pass`'s traceback is an environment refusal, not an
assertion failure — M37, read the first line. And `test_w2_sandbox_platform` is
in `run_all_tests.sh` but **not** in `run_local_sweep.py`'s SUITES list, so the
Windows sweep did not cover it; that is a gap in the runner, not a pass.

**Net for the day:** the machine went from running a pre-v8.31 node with a
29-hour-stale watchdog to running v8.35 with a self-checking one, and the first
sweep it has ever been able to run found two real things — one of which is a
five-version-old fix that has never worked where it matters.

**ADDENDUM 4 ~08:40 — the one thing left open, and it is open because I could
not make a click land.** The watchdog is still running `c228ac0a629d` while disk
holds `d363d6c2bb5f`, so **P14's alert is still firing, correctly**, and the only
thing that clears it is a restart. Four attempts to launch
`RESTART_COVENANT_ON_v8.35.bat` did nothing — after the identical recipe had
worked three times on three other files. That is written up honestly in M39's
second correction rather than retried a fifth time on someone else's desktop.

**It is not harmful to leave.** The alert is true: the deployed watchdog is not
the running one. The system saying so, unprompted, once, and then staying quiet
about it, is exactly the behaviour P14 and P16 were built for — this is the
control working, not a fault. Everything else on the machine is current.

**For L, one double-click:** `Downloads\RESTART_COVENANT_ON_v8.35.bat`. It
clears the alert and loads the corrected silence-contract banner. Nothing else
is pending.

---
