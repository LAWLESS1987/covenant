#!/usr/bin/env bash
# Full verification sweep. Run before any launch or after any change.
cd "$(dirname "$0")"
export COVENANT_JUDGE_PROVIDERS="${COVENANT_JUDGE_PROVIDERS:-mock}"
export COVENANT_INSECURE_MOCK_JUDGE="${COVENANT_INSECURE_MOCK_JUDGE:-1}"
rm -f covenant_unified_*.db* *.db.key 2>/dev/null; rm -rf __pycache__ 2>/dev/null
TOTAL=0; FAILED=0
# ABSENT IS NOT ZERO (added 2026-08-27).
#
# `run` swallowed stderr and scraped a tally out of stdout. A suite that is
# not on disk therefore produced no tally, contributed `0 passed, 0 failed`,
# printed NO RESULT, and left FAILED untouched -- so eleven named suites could
# be missing and this sweep would still end green. Measured on L's PC that day:
# verify_patches, verify_auth, verify_tx_aer, test_path_pattern,
# test_succession_seal, test_ethics_judge, test_golden_ratio,
# test_judge_individuality, test_multi_provider_quorum, test_v86_bridge and
# test_v86_loss_tracking are all invoked below and none of the eleven exists
# there. The README's "33 suites, 1,043 checks" is counted from this runner.
#
# This is the orphan problem from the other direction. run_local_sweep.py had
# four suites on disk that no runner called; this one calls eleven suites that
# are not on disk. Both read as coverage and neither is. A missing suite is now
# a FAILURE, loudly, because the alternative is a green run that means nothing.
run () {
  if [ ! -f "$1" ]; then
    FAILED=$((FAILED+1))
    printf "  %-30s %s\n" "$1" "ABSENT -- not on disk, so it did NOT run. Counted as a failure, never as a pass."
    return
  fi
  out=$(timeout "${2:-120}" python3 "$1" 2>/dev/null)
  line=$(echo "$out" | grep -iE '[0-9]+ passed|ALL PASS|[0-9]+/[0-9]+ checks|[0-9]+/[0-9]+ passed|RESULTS:' | tail -1)
  p=$(echo "$line" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+')
  f=$(echo "$line" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+')
  c=$(echo "$line" | grep -oE '^[0-9]+/[0-9]+' | cut -d/ -f1)
  n=${p:-${c:-0}}; f=${f:-0}
  TOTAL=$((TOTAL+n)); FAILED=$((FAILED+f))
  printf "  %-30s %s\n" "$1" "${line:-NO RESULT}"
  rm -f covenant_unified_*.db* *.db.key 2>/dev/null
}
echo "=== INTEGRITY ==="
python3 verify_bundle.py 2>&1 | tail -1
echo "=== SECURITY & REGRESSION ==="
run verify_patches.py 60
run verify_auth.py 120
run test_security_audit.py 180
echo "=== CRYPTOGRAPHY ==="
run test_path_pattern.py 60
run test_succession_seal.py 90
echo "=== ETHICS GATE ==="
run test_ethics_judge.py 60
run test_golden_ratio.py 60
run test_judge_individuality.py 60
run test_multi_provider_quorum.py 60
echo "=== TRADING BRIDGE ==="
run test_v86_bridge.py 90
run test_v86_loss_tracking.py 60
echo "=== PROPAGATION ==="
run verify_tx_aer.py 120
# NEW v8.11 -- the audit suites. Every check in test_adversarial_suite.py
# corresponds to an exploit that WORKED against an earlier revision, so a
# failure here means a closed hole has reopened, not that a test is fussy.
echo "=== ADVERSARIAL (findings AB-AJ) ==="
run test_adversarial_suite.py 300
run test_e2e_gift.py 180
# NEW v8.16 -- route semantics + bounded reads. These pin behaviour that a
# refactor could silently revert:
#   test_a1a_a2         (v8.15) /unstake + /claim_rewards no-ops stay status:error;
#                       preflight_port_check catches both port footguns.
#   test_a3_bounded_reads (v8.16) every inbound P2P/bridge read is capped at
#                       MAX_PEER_MSG_BYTES -- a flood is refused, recorded, and
#                       the node survives. test_a1a_a2 launches REAL processes.
echo "=== ROUTE SEMANTICS + BOUNDED READS (v8.15 / v8.16) ==="
run test_a1a_a2.py 240
run test_a3_bounded_reads.py 120
#   test_a5_size_coherence (v8.17) MAX_TX < MAX_BLOCK <= catch-up page < read cap,
#                       enforced at every ingress; BLOCK_REQUEST pages by bytes;
#                       HTTP body capped. Measured: 64 full blocks = 448 MiB vs
#                       a 64 MiB read cap -- the A3 cap alone could exile a
#                       late-joining node for good.
run test_a5_size_coherence.py 180
#   test_a4_block_injection (v8.18) the block-injection matrix against a LIVE
#                       P2P listener: rival genesis, forged/tampered signatures,
#                       no PoW, stale hash, NaN/Inf/str/bool fields, oversized,
#                       overdraft, ethics, drift, malformed frames, float index,
#                       empty blocks, forged stake_rewards/alignment_score, and
#                       peer-side stake-reward distribution (was miner-only).
run test_a4_block_injection.py 600
#   test_a9_relay_race (v8.19) three real processes in a line A-B-C: a block
#                       that enters B by startup bootstrap (or any path that
#                       wins the delivery race) must still be relayed to C.
#                       Pre-fix, test_multinode_live failed its two relay
#                       checks 2/2; this pins the deterministic form plus the
#                       race as observed, and cross-process /stakes agreement.
run test_a9_relay_race.py 420
#   test_a1_kill_matrix (v8.20) SIGKILL matrix on a live A-B-C line: bridge
#                       dead during the mine, miner killed the second /mine
#                       returns, leaf dead mid-flight, db survives every kill,
#                       plus in-process periodic tip gossip. Pre-fix the
#                       restarted miner was AHEAD and silent: peers stayed at
#                       genesis until the next block (K2 failed 3/3).
run test_a1_kill_matrix.py 560
#   test_a11_gossip_scale (v8.21) the tip heartbeat must be free on a held tip:
#                       pre-fix it attenuated every link to MIN within ~1 h of
#                       a quiet chain and raised a false anomaly spike for ~5
#                       min after a synchronized restart with >=5 peers.
#                       Real _handle_peer over a socketpair; untagged
#                       duplicates must still be attenuated and recorded.
run test_a11_gossip_scale.py 120
#   test_a12_dead_peer_backoff (v8.23) heartbeats to DEAD peers must not hold
#                       the send pool: one costs 3 x PEER_SEND_TIMEOUT + sleeps
#                       (~15 s) per worker per tick, so >~508 dead peers grew
#                       the queue without bound and a novel announce waited
#                       behind it (measured: 3.1 s late with pool=4, 8 dead;
#                       1 ms after). Boot push / novel / tx announces are never
#                       gated; an inbound frame clears the backoff.
run test_a12_dead_peer_backoff.py 240
#   test_a13_one_way_sync (v8.25) a peer that can reach us but that we cannot
#                       reach never synced: its announces to us fail, and our
#                       heartbeats to it came back "known" with ITS (higher)
#                       height, which announce_block discarded. Measured on
#                       v8.24: X sat at height 2 beside a reachable peer at 4
#                       indefinitely. Now _send_announce reads the reply and
#                       pulls the gap on _FETCH_POOL, gated by the catch-up
#                       cooldown; garbage/lying heights cost one request.
run test_a13_one_way_sync.py 180
#   test_a14_boot_probe (v8.26) boot catch-up asked peers one at a time: each
#                       dropped peer cost a full socket timeout before the next
#                       was asked (8 dead peers = 9 s at a 0.5 s timeout, 40 s+
#                       at the default) and the boot push waited behind it; a
#                       peer that trickled bytes held the boot FOREVER (the A3
#                       cap bounds bytes, not time). Now one round probes every
#                       peer at once on _FETCH_POOL under BOOT_PROBE_DEADLINE_S
#                       and applies replies in arrival order. ~25 s.
run test_a14_boot_probe.py 180
#   test_a15_exchange_deadline (v8.27) every read bounded bytes (A3) but not
#                       TIME, and ACCEPTED sockets had no timeout at all: one
#                       idle TCP connection pinned one receive worker for ever,
#                       unrecorded -- MAX_CONCURRENT_HANDLERS of them (96, one
#                       host) made the node deaf to every peer (measured with
#                       4: honest BLOCK_REQUEST never answered). Now
#                       recv_bounded takes a wall-clock budget (MAX_EXCHANGE_S,
#                       60 s, >= socket timeout) and raises PeerMessageTooSlow,
#                       recorded as peer/bridge_message_too_slow. ~25 s.
run test_a15_exchange_deadline.py 180
#   test_a17_oneway_peer_sync (v8.28) two REAL processes peered ONE WAY over
#                       the host's interface IP (B lists A, A does not list B
#                       -- phone-to-PC / VPN shape): a block mined on A must
#                       reach B with no second block, restart or /sync.
#                       Pre-fix B stayed at genesis for ever (_gossip_tip was
#                       silent at height 1, so A13's probe never fired).
run test_a17_oneway_peer_sync.py 180
#   test_p11_version_identity (v8.31) P11: the node must be able to SAY which
#                       source it is running. Pre-fix COVENANT_VERSION read
#                       "v8.9-merged" and was referenced nowhere, the boot
#                       banner hard-coded "v7.0" on a v8.30 file, and /health
#                       carried no version at all -- so after M25's "grep the
#                       DEPLOYED file", nothing could tell you whether the
#                       PROCESS on :5000 was running those bytes. Now the
#                       banner and /health carry the version and the sha256 of
#                       the source as LOADED, and the watchdog compares that
#                       against the file on DISK every round and alerts on
#                       drift. ~35 s.
run test_p11_version_identity.py 180
#   test_p12_substrate_sensing (v8.32) P12: the node had no idea what machine it
#                       was on -- grep for psutil/meminfo/GlobalMemoryStatus over
#                       8,933 lines returned nothing -- while the ethics judge
#                       sits INSIDE consensus and is a multi-GB model (the nodes
#                       restarted 08-23 with 3.1 GB free against 5.2 GB, so it
#                       paged). Now sampled in the background and reported on
#                       /health as a WARNING. B1-B3b assert the boundary over the
#                       AST -- sensing may inform refusal and disclosure, never
#                       relaxation -- and B2 follows aliases, because matching on
#                       the word "substrate" alone is evaded by one local
#                       variable (mutation-tested). W1-W10 cover the watchdog's
#                       adaptation: 12 h of watchdog.log was 3,808 lines carrying
#                       16 distinct messages. ~40 s.
run test_p12_substrate_sensing.py 180
#   test_p14_watchdog_self_drift (P14, 2026-08-24) source_drift_report checks
#                       the NODES against the file on disk. Nothing checked the
#                       WATCHDOG. It was written 08-23 07:39; the process that
#                       would run it started 08-23 01:39 and was still running
#                       29 hours later with neither it nor Adaptation -- so the
#                       control built to catch deployed-is-not-running spent a
#                       day and a half BEING a case of it, while writing 3,448
#                       redundant ALERT lines out of 3,456. Pure functions, no
#                       node, no socket, no key: 33/33.
run test_p14_watchdog_self_drift.py 120
#   test_a20_peer_version (v8.33) A20/A21: every peer reply carries this node's
#                       version and source hash, and the 120 s tip-gossip
#                       heartbeat carries a bounded state digest -- so two nodes
#                       on different sources find out by being TOLD instead of
#                       by a rejected block (A7). Backwards compatibility is
#                       MEASURED, not asserted: C1-C5 run a real pristine v8.32
#                       process and check both directions. D1-D6 pin what the
#                       digest may carry -- no substrate reading, no judge
#                       identity, no paths -- against the object AND against the
#                       bytes captured off the wire, and that the digest rides
#                       the heartbeat only (+108 bytes/peer/120 s; the ~156-byte
#                       block announce is untouched). ~90 s, starts 3 nodes.
run test_a20_peer_version.py 300
#   test_a22_topology_vigilance (2026-08-23) /mycelium was exposed on a route and
#                       read by NOTHING -- the last sensory stream with no
#                       internal consumer, and the only place the node says who
#                       it is TALKING TO. The watchdog now reads it and alerts on
#                       an unexpected peer (POST /peers is operator-authenticated,
#                       so one did not arrive by accident), on every link at the
#                       conductance floor (A11's signature), on a chain that
#                       shortens, and on a silent restart. Also pins two defects
#                       found in this loop's OWN A20/A21 code: the peer table
#                       locked newcomers out when full (an attacker could thereby
#                       suppress the A7 warning) and recorded the version
#                       mismatch on every heartbeat instead of on change. ~35 s.
run test_a22_topology_vigilance.py 180
#   test_a23_ack_health (A23, v8.36) DELIVERY IS CONFIRMED BY A REPLY, NEVER BY
#                       sendall(). _note_send_ok fired the instant sendall
#                       returned -- the exact claim A18 exists to deny -- and it
#                       CLEARS the link's consecutive-failure count, so every
#                       send to a peer that accepts bytes and never answers (the
#                       shape a killed Windows node presents) both recorded a
#                       failure and erased the previous one. Measured: five
#                       total failures left k=1 and the backoff pinned at ONE
#                       interval, while five sends to a REFUSED peer reached k=5
#                       and 16x. A12's 508 -> 11,520 headroom is bought by the
#                       escalation, so for this class of dead peer it bought
#                       nothing. Also: a NON-JSON reply returned None in silence
#                       -- now peer_ack_unparseable. PRE-FIX RECORD 16/24 on
#                       pristine v8.35, 24/24 on v8.36. ~15 s.
run test_a23_ack_health.py 180
#   test_a3s_send_bounds (A3 send-side, v8.37) THIS NODE NEVER TRANSMITS A
#                       FRAME IT KNOWS THE RECEIVER MUST REFUSE, AND NEVER
#                       BLAMES A PEER FOR ONE. Three measurements on v8.36:
#                       (1) a TX_ANNOUNCE's tx_id is chosen by the SENDER and
#                       echoed verbatim into the TX_REQUEST we build -- a
#                       204,893-byte announcement produced a 204,872-byte
#                       request, ~3,200x the honest 64-char sha256 id, on a
#                       fetch-pool worker gap-fill needs; (2) an over-cap frame
#                       was transmitted 3x (897 KB) to a peer that must refuse
#                       it, and A23's new rule then read the missing reply as
#                       non-delivery and escalated the backoff AGAINST THAT
#                       PEER (k=1) -- A23's own new edge, found by auditing the
#                       surface it widened; (3) A5's relation bounds the
#                       PAYLOAD, and the receiver's cap applies to the FRAME
#                       (envelope measured at 129/181/62 bytes). PRE-FIX RECORD
#                       23/49 on pristine v8.36, 49/49 on v8.37. ~35 s.
run test_a3s_send_bounds.py 240
echo "=== JUDGE LAYER (in-process, no API keys) ==="
#   test_b1_judge_parser (v8.22) B1+B3: 32-reply parser corpus -- pre-fix the
#                       judge parser ACCEPTED {"violates": null/[]/""} as clean
#                       (bool() of a falsy non-bool) and REJECTED "false"; a
#                       <think> block with a brace broke the first/last-brace
#                       slice. Also: one judge call per /transactions (was two),
#                       COVENANT_JUDGE_TIMEOUT_S plumbed to all providers, and
#                       a fail-closed infrastructure reject is recorded as
#                       judge_unavailable so it is distinguishable from dissent.
run test_b1_judge_parser.py 180
#   test_b2_quorum_diversity (B2, v8.35) the v8.34 QUORUM_DIVERSITY check
#                       counted judge LABELS, and build_semantic_quorum always
#                       appends its own mock_selfreport bucket -- so it passed
#                       for EVERY configuration a node can be given, including
#                       one provider and the same provider twice. It never once
#                       constrained a running node, and one of the two buckets
#                       it counted was the SENDER's self-report.
#                       quorum_diversity_report() measures INDEPENDENCE OF
#                       FAILURE instead (implementation, credential, model) and
#                       discloses it on /health -- to the operator, never to a
#                       peer. Section X is the PRE-FIX RECORD: 22/29 on pristine
#                       v8.34, 73/73 on v8.35.
run test_b2_quorum_diversity.py 180
#   test_b5_mine_latency (B5, measurement; the FIX waits on L's B4 answer.
#                       v8.24 adds observability only: a /mine refusal is now
#                       recorded as mine_rejected_ethics, and an infrastructure
#                       refusal (timeout / no key / bad reply) on BOTH /mine and
#                       peer block acceptance also records judge_unavailable;
#                       a real dissent never is. 31 checks, 27/31 on v8.23.)
#                       /mine re-judges every included tx AFTER
#                       the PoW, sequentially, per judge, while holding
#                       chain_lock: 5000 tx x 2 judges x 2 s = 5.6 h with the
#                       node frozen; one timing-out provider = 91 s per tx and
#                       the mined block is thrown away with the txs left
#                       pending, so the next /mine repeats it all. A verdict
#                       that flips clean->violating at mine time wedges /mine.
run test_b5_mine_latency.py 300
echo "=== HTTP FRONT DOOR (W1, v8.29) ==="
# The last unbounded resource in the file. A3/A5/A14/A15 bounded every peer
# read path; the HTTP port was served by werkzeug's development server --
# one thread per connection, no ceiling, no idle timeout -- on the one port
# an operator is told to expose. W10 is the pre-fix record of that (the dev
# server never reaps an idle connection); W11 is the finding that came with
# the switch: waitress answers NOTHING to a malformed request line, which the
# A2 preflight probe used to read as "this is a P2P listener" -- silently
# disarming the peer-port footgun check the moment the server changed.
run test_w1_wsgi.py 300
echo "=== DAILY CHECK + CIRCUIT BREAKERS (D3/D4) ==="
# guards.py existed and was called by NOTHING (grep -i guard daily.py returned
# zero lines). D4 wires it into daily.py; these 61 checks pin both the breakers
# and DAILY_CHECK.md section 3's price-window verification, which daily.py had
# never implemented. No network, no key, nothing here trades.
run test_d3_daily_guards.py 180
echo "=== MULTI-NODE P2P (real processes, real sockets) ==="
# Launches real OS processes on localhost. Slow by design: /mine is rate-limited
# to 1/60s and the test waits that window out rather than fighting the control.
run test_multinode_live.py 600
echo "=== LEDGER CONVERGENCE ==="
run sim_order_independence.py 600
# NEW v8.12 -- reports yield curves rather than asserting a rate. Informational:
# read it before changing YIELD_RATE, do not treat a clean run as approval of
# any particular rate. The block-reward correctness checks it used to expose are
# now assertions inside test_security_audit.py (items AK/AL).
echo "=== YIELD SAFETY (informational) ==="
python3 sim_yield_safety.py > /dev/null 2>&1 && echo "  sim_yield_safety.py            ran clean (see output for curves)" || echo "  sim_yield_safety.py            ERROR"
echo "=== THE DEPLOYMENT ITSELF, AND THE RADIO BEARER ==="
# Added 2026-08-27. All three shipped in MANIFEST.sha256 and were called by
# NEITHER runner -- found by diffing the test files on disk against the two
# suite lists. r1_lora is the LoRa frame codec (R1); backtest_guardrails pins
# that paper trades pay the backtest's costs; 3node_config asserts that
# covenant_prod.bat, AB_RESTART_NODES.bat, covenant_watchdog.py, launch_check.py
# and dashboard_render.py all agree about the three nodes -- a config suite, so
# it reads the .bat files and needs them beside it.
#
# test_covenant_app.py (54 checks) is the fourth orphan and is deliberately NOT
# here: it binds the real production ports and can only run with the chain
# stopped. See the note in run_local_sweep.py.
run test_r1_lora_frame.py 120
run test_backtest_guardrails.py 180
run test_3node_config.py 120
echo "=== XRP SIGNER + MAINNET GUARDS (offline) ==="
# probe_final_pass.py is an ADVERSARIAL PROBE, not a pass/fail suite: it prints
# FINDINGS: n. Any n > 0 means a closed hole has reopened.
run probe_final_pass.py 120
run test_xrp_signer.py 120
run test_xrp_mainnet.py 180
echo ""
echo "NOT COVERED BY THIS SWEEP -- both need a live network and neither is"
echo "exercised above; do not read a green run as covering them:"
echo "  test_xrp_live.py   XRP autofill/submission against a funded testnet account"
echo "                     -- mainnet stays BLOCKED until this has run once"
echo "  (multi-node P2P over real sockets is now COVERED, above)"
echo ""
echo "TOTAL: $TOTAL checks, $FAILED failed"
rm -rf __pycache__ 2>/dev/null
[ "$FAILED" -eq 0 ] || exit 1
