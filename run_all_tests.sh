#!/usr/bin/env bash
# Full verification sweep. Run before any launch or after any change.
cd "$(dirname "$0")"
export COVENANT_JUDGE_PROVIDERS="${COVENANT_JUDGE_PROVIDERS:-mock}"
export COVENANT_INSECURE_MOCK_JUDGE="${COVENANT_INSECURE_MOCK_JUDGE:-1}"

# RUN AGAINST THE PROJECT'S OWN INTERPRETER (added 2026-08-27).
#
# This sweep called `python3` directly. On Windows that resolves to the
# WindowsApps shim, not to .venv, and the two interpreters do not carry the
# same packages. Measured on L's PC that day:
#
#   interpreter                         flask cryptography waitress requests xrpl
#   WindowsApps python3 (3.12)           yes     yes        yes      yes     NO
#   .venv/Scripts/python.exe             yes     yes        yes      yes     yes
#
# So probe_final_pass.py died with MainnetGuardError and test_xrp_signer.py
# with XRPSignerError, both saying "xrpl-py not importable", and both were
# scored red. Nothing was wrong with either suite or with the code they
# test: the sweep was simply run against an interpreter that requirements.txt
# was never installed into.
#
# That is the §8 failure -- a sweep is green for the environment it ran in,
# and this one did not name its environment. It does now, on the first line
# of output, because a red suite that is really a missing package is the kind
# of red that trains a reader to skim.
if   [ -x .venv/Scripts/python.exe ]; then PY=".venv/Scripts/python.exe"
elif [ -x .venv/bin/python ];        then PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then PY="python3"
else                                      PY="python"
fi
echo "interpreter: $PY -> $("$PY" -c 'import sys; print(sys.executable)' 2>/dev/null)"
# A PRE-EXISTING KEY IS A NODE IDENTITY, NEVER A TEST ARTEFACT (added 2026-08-27).
#
# The cleanup here, and the identical line at the end of `run`, used to be
#     rm -f covenant_unified_*.db* *.db.key
# The second glob is unanchored. The suites create short-named databases
# (a.db, m.db, exporter.db ...) whose keys it was meant to reap -- but it
# matches EVERY *.db.key in the directory, and on an operator's machine that
# set includes covenant_A.db.key and the six node keys nodeA/B/C_{prod,run}.
# Those decrypt the persisted ledger. Deleting one does not fail a test, it
# strands an encrypted database with no key.
#
# It fired twice over: once here, and once at the tail of `run`, so a full
# sweep executed it 47 times. The documented instruction is to run this
# script before any launch and after any change.
#
# Fix: snapshot the keys present BEFORE the sweep and never delete those.
# Only keys that appear DURING the run are reaped. This fails safe -- a key
# this script did not create is a key this script does not remove -- and it
# needs no list of node names to maintain.
PRESERVE_KEYS="$(ls -1 -- *.db.key 2>/dev/null | sort)"

clean_test_dbs () {
  rm -f -- covenant_unified_*.db* 2>/dev/null
  for k in *.db.key; do
    [ -e "$k" ] || continue
    printf '%s\n' "$PRESERVE_KEYS" | grep -qxF -- "$k" && continue
    rm -f -- "$k" 2>/dev/null
  done
}

clean_test_dbs; rm -rf __pycache__ 2>/dev/null
TOTAL=0; FAILED=0; UNSCORED=0
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
  out=$(timeout "${2:-120}" "$PY" "$1" 2>/dev/null); rc=$?
  line=$(echo "$out" | grep -iE '[0-9]+ passed|ALL PASS|[0-9]+/[0-9]+ checks|[0-9]+/[0-9]+ passed|RESULTS:' | tail -1)

  # A FAILURE COUNTED AS A PASS (fixed 2026-08-27).
  #
  # The scrape here was:
  #     p=$(... grep -oE '[0-9]+ passed' ...)
  #     f=$(... grep -oE '[0-9]+ failed' ...)
  # Two defects, and they compounded in the same direction -- upward.
  #
  # 1. On "28/30 passed, 2 FAILED" the pattern `[0-9]+ passed` matches the
  #    substring "30 passed". 30 is the TOTAL, not the passes. The two
  #    failures were added to the pass count.
  # 2. Both inner greps are case-SENSITIVE, while the line-selecting grep
  #    above is -i. Suites that print "2 FAILED" in caps therefore scored
  #    f=0. The failures vanished.
  #
  # Measured on the 2026-08-27 win32 sweep: reported "1152 checks, 2 failed";
  # actually 1147 passed and 7 failed across 1154 checks. Five real failures
  # were reported as five passes -- a 10-check swing in the wrong direction,
  # in the number the README quotes.
  #
  # 3. A suite that RAN but printed nothing parseable scored 0 and 0, so it
  #    could not fail. That is ABSENT IS NOT ZERO one layer down: the file is
  #    on disk, it executed, and it still contributed nothing. Those are now
  #    counted separately as UNSCORED and are never silently zero.
  n=""; f=""
  ab=$(echo "$line" | grep -oiE '[0-9]+ */ *[0-9]+ +(checks )?passed' | head -1)
  if [ -n "$ab" ]; then
    n=$(echo "$ab" | cut -d/ -f1 | tr -dc '0-9')
    tot=$(echo "$ab" | cut -d/ -f2 | tr -dc '0-9')
    f=$((tot - n))
  else
    n=$(echo "$line" | grep -oiE '[0-9]+ +passed' | grep -oE '[0-9]+' | head -1)
  fi
  # An explicit "K failed"/"K FAILED" always wins over a derived count.
  fx=$(echo "$line" | grep -oiE '[0-9]+ +failed' | grep -oE '[0-9]+' | head -1)
  [ -n "$fx" ] && f="$fx"
  n=${n:-0}; f=${f:-0}

  if [ -z "$line" ]; then
    UNSCORED=$((UNSCORED+1))
    printf "  %-30s %s\n" "$1" "NO RESULT (exit $rc) -- ran, printed no tally. NOT counted as a pass."
  else
    TOTAL=$((TOTAL+n)); FAILED=$((FAILED+f))
    printf "  %-30s %s\n" "$1" "$line"
  fi
  clean_test_dbs
}
echo "=== INTEGRITY ==="
"$PY" verify_bundle.py 2>&1 | tail -1
# THE RULES THEMSELVES (added 2026-08-30). Nothing ran constitution.py --
# not this file, not CI, not verify_deploy.py, not covenant_one.py. Three
# independent verifiers existed and all three only ran when a human typed the
# command. A non-zero exit here is a FAILURE, because a protected rule that no
# longer hashes to the published anchor is an amendment nobody announced.
"$PY" constitution.py verify 2>&1 | tail -3
if [ "${PIPESTATUS[0]}" != "0" ]; then
  FAILED=$((FAILED+1))
  printf "  %-30s %s
" "constitution.py" "PROTECTED RULES DO NOT MATCH THE ANCHOR -- counted as a failure."
fi
# ELEVEN PHANTOM SUITES REMOVED (2026-08-27, on L's instruction).
#
# The lines below used to invoke eleven suites that do not exist. Checked
# individually on that date: none is in the working tree, none is in any
# commit in this repository, and none is among the 302 entries of
# MANIFEST.sha256. They are v8.11/v8.12-era names carried over from
# MANIFEST.json, and this bundle never contained them.
#
#   verify_patches.py 60              verify_auth.py 120
#   verify_tx_aer.py 120              test_path_pattern.py 60
#   test_succession_seal.py 90        test_ethics_judge.py 60
#   test_golden_ratio.py 60           test_judge_individuality.py 60
#   test_multi_provider_quorum.py 60  test_v86_bridge.py 90
#   test_v86_loss_tracking.py 60
#
# Four section headers went with them because every suite beneath each was a
# phantom: CRYPTOGRAPHY, ETHICS GATE, TRADING BRIDGE, PROPAGATION. Those
# names described coverage that is not here. What remains of each concern is
# covered elsewhere in this file -- the judge layer by test_b1_judge_parser
# and test_b2_quorum_diversity, propagation by test_a9_relay_race and
# test_a11_gossip_scale, the trading bridge by test_backtest_guardrails.
#
# THIS IS A DELETION OF CLAIMED COVERAGE, NOT A RESTORATION OF IT. Nothing
# that ran before this change stops running. Eleven names that never ran stop
# being counted, and the sweep can reach a total that means something. If any
# of the eleven is ever written, add it back with its section.
echo "=== SECURITY & REGRESSION ==="
run test_security_audit.py 180
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
#   test_p15_judge_identity (P15, 2026-08-28) the watchdog probes ollama ITSELF:
#                       /api/tags digest is the identity, ALERT on digest change /
#                       missing expected tag / unreachable (fail-closed consequence
#                       named). Canned responses, GET-only pinned by AST -- no
#                       ollama, no socket needed. Shipped 08-28 with watchdog
#                       8b878ee771f3 but wired into NO runner until 2026-08-29:
#                       29/29 x2 here while absent from both sweep lists.
run test_p15_judge_identity.py 120
#   test_c2_watchdog_live (C2, 2026-08-29) every watchdog check above is a
#                       PURE function handed its subject as an argument; the
#                       loop that FEEDS them -- health(), the 3-strike counter,
#                       start_node's Popen, Adaptation on a real log, the P16
#                       silence contract -- had never run against a live chain.
#                       This boots the watchdog's OWN hardcoded topology
#                       (A:5000/B:5020/C:5040) on real v8.39 nodes, SIGKILLs C,
#                       and measures detect -> restart -> recover -> CLEAR,
#                       plus a live judge digest change and gap-based death
#                       detection of the watchdog itself. NOTE it binds the
#                       PRODUCTION ports, so on the PC it can only run with the
#                       chain STOPPED (same class as test_covenant_app) -- in
#                       this sandbox sweep there is no chain to collide with.
#                       ~3.5 min; 27/27 x2 on Linux 2026-08-29.
run test_c2_watchdog_live.py 480
#   test_p20_watchdog_self_eval (P20, 2026-08-29) the watchdog's periodic
#                       self-evaluation: every sensory stream it reads becomes
#                       one dated PASS/WARN/FAIL block per layer in
#                       ops/SELF_EVAL.md, worst wins. Pure function + a temp-dir
#                       writer test; AST-pins REPORT-ONLY (no probe, no restart,
#                       no I/O from the evaluator itself). 23/23 on delivery.
#                       No node, no socket, no key.
run test_p20_watchdog_self_eval.py 120
#   test_c3_guard (C3, 2026-08-29) the guard that heals the WATCHDOG:
#                       every branch of its pure decide(), including the
#                       three refusals that matter more than the action
#                       (a wedged pid is not a dead one; inside the
#                       cooldown it holds; a watchdog that does not
#                       compile is never revived). AST-pins decide() as
#                       unable to spawn, kill or log. 21/21, no process
#                       started, no node touched.
run test_c3_guard.py 120
#   test_m2_merkle_seal (M2, 2026-08-29) followable branches, sealed
#                       base: the flat seal root proves the SET and
#                       discloses every filename to do it; the merkle
#                       layer proves ONE file with ~log2(n) siblings and
#                       nothing about the rest. Pins domain separation,
#                       odd nodes carried not duplicated, four ways of
#                       faking a proof, and that the seal never hashes
#                       its own output -- which it was doing. 21/21,
#                       pure hashing, nothing sealed or encrypted.
run test_m2_merkle_seal.py 120
#   test_t1_triangulate (T1, 2026-08-29) PC, GitHub and cloud each hold
#                       a root; agreement is a fact anyone can check and
#                       divergence NAMES the outlier without overwriting
#                       it. Everything trustworthy here is a refusal: a
#                       silent witness is not a disagreeing one, too few
#                       answers is UNPROVEN and UNPROVEN IS NOT SUCCESS,
#                       and the limits ride inside the verdict so it
#                       cannot be quoted without its caveat. Pure -- no
#                       network, no git, no cloud. 20/20.
run test_t1_triangulate.py 120
#   test_e1_secret_egress (E1, 2026-08-29) an adversarial audit found an
#                       UNAUTHENTICATED REMOTE CREDENTIAL DISCLOSURE: the
#                       Google judge passed its key in the URL, requests'
#                       raise_for_status() puts the whole URL in the
#                       exception, the fail-closed handler surfaces that
#                       verbatim, the quorum preserves it verbatim, and
#                       the 400 body goes to whoever POSTed -- on an
#                       endpoint that is deliberately not operator-only.
#                       Five reasonable links; the defect lived only at
#                       the JOIN, which is what this suite tests. L2 is
#                       the end-to-end regression. 15/15, no key, no net.
run test_e1_secret_egress.py 120
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
echo "=== ANOMALY BUFFER FAIRNESS (A24) ==="
# Up to v8.37 the anomaly buffer evicted OLDEST-OVERALL, so 5,200 garbage
# frames from one socket filled 5,000/5,000 slots with one peer-triggered
# kind, evicted a real peer_send_failure, and left a GENUINE spike of a
# third kind undetectable -- /health and the watchdog then reported exactly
# what the attacker chose. v8.38 fair-shares capacity between kinds.
# A24b (v8.39, section S10): the v8.38 fix left the attacker one thing --
# `buffer_pressure` was bool(self._evicted) and _evicted is monotonic, so
# ONE flood turned on a /health warning that never turned off again
# (measured on v8.38: at +15 min zero evicted records were still inside
# the baseline window and /health still warned; at +30 days, still). The
# flag is now bounded by the same window report() reports on. PRE-FIX
# RECORD 64/70 on v8.38 6ddedcdc7c6b, 70/70 on v8.39.
run test_a24_anomaly_eviction.py 300
echo "=== VERSION IDENTITY ACROSS THE TREE (P18) ==="
# Two runs branched from v8.37 on 2026-08-26 and both stamped their output
# v8.38: 6ddedcdc7c6b (the A24 fix, shipped) and 27264e46218d (the semantic
# judge, parked in pending-v8.38\). Neither knew about the other. P11 made
# the node self-describing and left the NAMING unguarded, so for eighteen
# hours a node reporting "v8.38" identified nothing. No other copy of the
# core under this folder may claim the live version with different bytes,
# and a PRE-vX.Y backup may not declare X.Y. Pure AST + hashing, never
# imports a candidate; ~2 s and platform-independent.
run test_p18_version_collision.py 120
echo "=== SWEEP GATE INTEGRITY (P19) ==="
# run_local_sweep.py's --candidate overlay copied the candidate's *.py OVER
# the staged tree -- suites included. A candidate folder carrying its own
# test_a23_ack_health.py would replace the gate's check with its own claim
# and the results file would report that claim as the sweep's verdict.
# Gate files (test_*/sim_*/probe_*/verify_*, the runners) now never come
# from the folder under test; blocked files are reported with both hashes;
# --allow-suite-overlay overrides loudly; and every suite that runs is
# hashed AS STAGED into the results file (M40 -- "which test_a23 ran?"
# cost a morning of AST forensics on 08-29). Needs run_local_sweep.py
# beside it or in pc/. PRE-FIX RECORD 10/23 on the pristine 00:55Z runner
# 2405768bee5e, 23/23 on the guarded one. ~10 s, no node, no socket.
run test_p19_overlay_guard.py 120
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
#   The semantic-judge layer (v8.40, landed 2026-08-29). Five gates that
#                       rode in with the layer itself:
#   test_j1_judge_paths      maps every path a verdict can take to a judge;
#                       X2 (registry overwrite on the record) and X4 (report
#                       the model that will be SENT, not the constructor
#                       override) are the fixes it pins. 34/34 on v8.40.
#   test_sem4_degraded_model the judge may not report full competence on a
#                       model that cannot measure it -- inert passes named,
#                       'unfitted' derived from the guards, install() warns
#                       once on stderr, format /2 minus its keys REFUSED,
#                       verdicts proven unchanged against the pristine
#                       pre-fix source (docs/semantic/). 28/28.
#   test_competence          the v2 model pair loads and the competence
#                       machinery works both directions. 56/56.
#   test_semantic_judge      the judge itself: verdict lattice, holds,
#                       who_can_clear, the ILLEGIBLE floor. 26/26.
#   test_sem5_register_coverage  the register rule as designed, and S5:
#                       whatever the model misses it must DECLARE
#                       (missing_seeds carries six formal verbs). 6/6.
run test_j1_judge_paths.py 120
run test_sem4_degraded_model.py 120
run test_competence.py 120
run test_semantic_judge.py 120
run test_sem5_register_coverage.py 120
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
"$PY" sim_yield_safety.py > /dev/null 2>&1 && echo "  sim_yield_safety.py            ran clean (see output for curves)" || echo "  sim_yield_safety.py            ERROR"
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
echo "=== THIS RUNNER'S OWN CLEANUP (K1) ==="
# Added 2026-08-27 with the key-preservation fix at the top of this file.
# It is registered HERE, in the same change that introduced it, because an
# unregistered suite is the orphan problem this script already documents
# twice. It runs in temporary directories only and touches nothing beside it.
run test_k1_runner_key_preservation.py 60
run test_k3_p9_owner_only_guard.py 60
# K2 pins this runner's own arithmetic: a failure must never be counted
# as a pass. Registered with the fix, not after it.
run test_k2_tally_arithmetic.py 60
# D1 (2026-08-30) pins the other half of "can this run at all": a DECLARED
# dependency that is not installed must name itself, and name the suites it
# takes down with it. On the run that produced this line, xrpl-py was absent
# and it surfaced as four failures in three sections -- one of them a SECURITY
# suite reading 14/16, which is exactly what a regression looks like and was
# not one. Four symptoms named, the single cause named nowhere.
run test_d1_preflight_deps.py 60
# R2 (2026-08-30) pins redundancy.py -- one question at every scale, how many
# independent carriers and what survives the first loss. Chiefly it pins the
# SUBSTRING bug that tool shipped with: twelve files under ai_memory_system/
# (public software) flagged for containing "ai_memory" (the private record).
run test_r2_redundancy.py 60
# S1 (2026-08-30) pins scale.py: a level's verdict is a witness one level up,
# so governance composes to any depth and any shape with no new machinery. The
# invariant that makes it safe is that divergence never disappears as you
# climb -- a diverged level goes SILENT upward rather than passing its majority
# root along, because the obvious implementation launders disagreement into
# consensus one level at a time.
run test_s1_scale.py 60
# N1 (2026-08-30) pins a conformance root that compares the COMPUTATION
# rather than the artefact, so a fork in another language can prove it
# agrees without running these exact bytes. From the 2025 Mahowald Prize
# shortlist (Pedersen, Neuromorphic Intermediate Representation).
run test_n1_conformance.py 60
# C4 (2026-08-30) pins three unauthenticated paths that grew without a bound:
# succession register (5,000 guardians, 48.8s, lock held throughout), the
# rate limiter's own key map (200,000 keys, 40.76 MB), and peer-supplied
# nonces (1 MB accepted, expired rows never deleted).
run test_c4_bounded_resources.py 60
# E2 (2026-08-30) pins that the faster /chain serialiser emits BYTE-IDENTICAL
# output to asdict, and that the new range is optional and half-open.
run test_e2_chain_serialisation.py 60
# Y2 (2026-08-30) pins supply conservation: 5000 blocks mint EXACTLY their
# intent. Before v8.12 that scenario over-issued by 270 billion per cent.
run test_y2_supply_conservation.py 60
# F1 (2026-08-30) pins that silence is not dissent: an UNREACHABLE judge
# was counted alongside genuine dissent, so one stopped Ollama refused every
# transaction AND every peer block. Off by default -- F1 pins both modes.
run test_f1_fallback_silence.py 60
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
echo "TOTAL: $((TOTAL + FAILED)) checks -- $TOTAL passed, $FAILED failed, $UNSCORED suite(s) UNSCORED"
if [ "$UNSCORED" -ne 0 ]; then
  echo "UNSCORED means the suite ran and printed no tally this runner could read."
  echo "It is not a pass. Read its output before treating this sweep as green."
fi
rm -rf __pycache__ 2>/dev/null
[ "$FAILED" -eq 0 ] && [ "$UNSCORED" -eq 0 ] || exit 1
