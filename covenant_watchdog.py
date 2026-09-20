#!/usr/bin/env python3
"""
covenant_watchdog.py -- keep two Covenant nodes up, and notice the failure
that nothing else notices.

WHAT THIS IS FOR
  Two console windows started by hand is a demo. Production means: it comes
  back after a crash, it comes back after a reboot, it writes to a log
  somebody can read tomorrow, and it tells you when it is wrong.

THE CHECK THAT MATTERS
  Every other health signal on this node compares TIP HASHES.
  SANDBOX_VERIFICATION section 3 demonstrated two nodes reporting
  `converged on one tip: True` while disagreeing 0 vs 1000 on a spendable
  balance. Tip equality is not state equality.

  So this watchdog reads the founder and node-B balances out of BOTH
  databases and compares them. If two nodes ever disagree about who owns
  what, that is a fork, and it is loud here even when /health is calm.
  That is the silent-failure class HANDOFF.md section 9.3 calls the worst
  one in this codebase.

THE WARNINGS IT IGNORES, AND WHY
  /health reports `degraded: true` permanently on a correct keyless setup,
  because one of the four inputs to `degraded` is a false positive:

    keyless      (line 6142) tests for ANTHROPIC/OPENAI/GOOGLE_API_KEY in the
                 environment. It never checks whether a judge is reachable or
                 working, so a functioning local judge always trips it.

  A monitor that pages on that would page forever and be muted within a day,
  taking `insecure` and `crisis_mode` -- the ones that are real -- with it. So
  it is recorded at INFO and never alerts. If you fix the health reporting
  upstream, delete FALSE_POSITIVE_WARNINGS below.

  own_genesis USED TO BE ON THAT LIST and no longer is (2026-09-14, A114). It
  tested WHO MINTED the genesis rather than whether this node's genesis is the
  canonical one, so the founder -- node A, whose key signed the genesis every
  other node adopted -- declared itself unable to converge, forever, while
  running a chain identical to its peers block for block. That is fixed
  upstream, so the mute is gone and this warning alerts again.

WHAT IT ALERTS ON
  node unreachable          restarts it after 3 consecutive failures
  judge_insecure true       the keyword mock is live; the gate is not judging
  crisis_mode true          the node says so itself
  height gap > 1            peers are not keeping up
  BALANCE DISAGREEMENT      fork; never auto-restarted, always alerted

RUN
  python covenant_watchdog.py                 (foreground, ctrl-C to stop)
  python covenant_watchdog.py --once          (single pass, exit code 0/1)
  python covenant_watchdog.py --interval 30

  Exit code 1 from --once means at least one ALERT. Wire that into whatever
  you already use.
"""
import argparse
import hashlib
import http.client            # HTTPException: not an OSError, not a URLError (A115b)
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import covenant_quiet                                    # no console window on Windows
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
LOGDIR = os.path.join(HERE, "logs")
LOGFILE = os.path.join(LOGDIR, "watchdog.log")
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_KEEP = 5

# TOPOLOGY IS A LINE: A <-> B <-> C. C is deliberately NOT a peer of A.
# A22 compares each node's ACTUAL peers against the "peers" string below, so
# this is the expectation, not a comment -- an unexpected peer is an alert, and
# POST /peers is operator-authenticated, so one did not arrive by accident.
# THE PHONE IS PEERED TO NODE A OVER THE TAILNET (2026-09-14, the operator's
# "can't you use tailscale"). It heartbeats to node A's API and node A had
# already recorded it inbound as 100.86.158.1 with an UNKNOWN port, which is an
# address it could never dial -- so the acquaintance ran one way and the phone
# sat at chain height 12 through fourteen check-ins while these three went to
# 23. The tailnet address is the stable one (lawrences-s25); the phone's LAN
# address is not. Port 5001 is its P2P port (API 5000 + 1, the same convention
# as the loopback entries below), and it is the only one reachable: the phone
# binds its API to loopback, so 5000 refuses and 5001 accepts.
#
# CHECKED BEFORE ADDING IT, because the phone runs an OLDER core (27a9bf2b01ad,
# the build of 2026-09-13) than these three (2f5e4e914bb5):
#   * The phone is on the CANONICAL genesis 00009b31c6c6, not one of its own.
#   * The whole diff between those two cores is four HTTP routes, the signed
#     update manifest and the own_genesis health field. Nothing in it touches
#     block validation, proof-of-work, transaction verification, the P2P wire
#     protocol, the peer handshake or fork choice. The delta is inert with
#     respect to consensus.
#   * There is no chain-REPLACEMENT path in this codebase to abuse: the chain
#     only ever grows by append, and every append goes through
#     _accept_block_common. A peer at height 12 cannot roll these nodes back.
# What node A does with it is announce its tip at boot, which is what tells the
# phone it is behind so it can pull the gap itself.
NODES = [
    {"id": "A", "port": 5000, "db": "nodeA_prod.db", "key": "nodeA_prod.db.key",
     "peers": "127.0.0.1:5021,100.86.158.1:5001"},
    {"id": "B", "port": 5020, "db": "nodeB_prod.db", "key": "nodeB_prod.db.key",
     "peers": "127.0.0.1:5001,127.0.0.1:5061"},
    {"id": "C", "port": 5060, "db": "nodeC_prod.db", "key": "nodeC_prod.db.key",
     "peers": "127.0.0.1:5021"},
]

# Documented false positives on a correct keyless single-founder setup.
# Recorded, never alerted. See the module docstring for the line numbers.
FALSE_POSITIVE_WARNINGS = (
    # Matched as a SUBSTRING, so keep these short and stable. The full text
    # used to be "ethics gate has no provider key and is failing CLOSED --
    # this node will reject every transaction"; on 2026-09-06 that sentence was
    # corrected (it was false under the deferring seat) to "no provider key:
    # the ethics seat is the deferring chain...". The longer pattern stopped
    # matching, and the watchdog began ALERTing on all three nodes every pass
    # -- a rewording turned a documented non-event into permanent noise, which
    # is how an operator learns to ignore alerts. Match the stable fragment.
    "provider key",
    # "node minted its OWN genesis" WAS HERE UNTIL 2026-09-14 (A114/A40).
    # The instruction above says to delete these once the health reporting is
    # fixed upstream, and it now is: own_genesis asks whether this node's
    # genesis is the canonical one rather than who signed it, so the founder
    # no longer trips it and every node that still does is genuinely on a
    # chain its peers cannot reach. Leaving the mute in place would have
    # turned a fixed false positive into a swallowed true one -- the same
    # trade the "provider key" comment above describes, run backwards.
    # A platform fact on Windows, not an incident: without a usable 'fork'
    # start method the sandbox cannot enforce its limits, so /propose_code
    # REFUSES every proposal rather than running one unbounded. It fails
    # closed, it cannot change, and it was alerting on every node every pass.
    "code sandbox unavailable",
)

FAIL_BEFORE_RESTART = 3
_fail_counts = {n["id"]: 0 for n in NODES}

# --------------------------------------------------------------------------
# P11 (2026-08-23). The check that closes the delivery loop.
#
# Until v8.31 nothing could answer "is the node running the file I shipped?"
# The source on disk was verifiable; the RUNNING PROCESS was not. That gap is
# how this machine ran a pre-v8.15 source for fourteen node versions while the
# log recorded every one of them as delivered (M25), and why "is v8.30 live?"
# had to be answered by forensics on 2026-08-23.
#
# A v8.31+ node reports the sha256 of the source it LOADED. Compared every
# minute against the sha256 of the source on DISK, the two differ in exactly
# one situation, and it is the one that has cost this project the most: the
# file was updated and the node was never restarted. That is now an ALERT
# carrying both hashes, instead of a silence discovered two days later.
#
# Kept as a pure function so it can be tested without standing up two nodes:
# it takes what /health said and what the disk says, and returns text.
# --------------------------------------------------------------------------
CORE_SRC = os.path.join(HERE, "covenant_unified_v8.py")

# --------------------------------------------------------------------------
# P12 (2026-08-23). TRANSMIT CHANGE, NOT STATE.
#
# Measured over twelve hours of this log: 3,808 lines carrying 16 distinct
# messages -- 99.6% redundancy. 269 identical "code sandbox unavailable" ALERTs,
# correct and permanent and understood on the first one. And FOUR lines, 0.1% of
# the file, reading "1 peer(s) unreachable -- heartbeats backed off": the
# 21:02-21:06 episode where node B could not boot because a leaked test node
# held its P2P port. The only thing in the file that HAPPENED, at 1/500th the
# volume of a thing that merely IS.
#
# A receptor that does not adapt transmits a constant stimulus at full amplitude
# for ever, and buries the transient that carries the information. The node
# implements the fix one layer down -- SpikingAnomalyMonitor holds a baseline
# and fires on deviation -- and the watchdog never applied it to itself.
#
# So: first occurrence in full, silence while unchanged, full amplitude again on
# any change, a periodic roll-up so a quiet log still proves the watchdog is
# alive, and an explicit CLEARED line when a condition stops. Nothing is
# suppressed that has not already been said verbatim.
# --------------------------------------------------------------------------
ROLL_UP_EVERY = 30          # rounds; at 60 s that is a heartbeat every 30 min


class Adaptation:
    """Renders a repeating observation only when it is news."""

    def __init__(self, roll_up_every=ROLL_UP_EVERY):
        self.roll_up_every = max(1, int(roll_up_every))
        self._state = {}                      # key -> {"text": str, "count": int}

    def observe(self, key, text):
        """Return the line to emit, or None to stay silent."""
        prev = self._state.get(key)
        if prev is None:
            self._state[key] = {"text": text, "count": 1}
            return text
        if prev["text"] != text:
            self._state[key] = {"text": text, "count": 1}
            return text
        prev["count"] += 1
        if prev["count"] % self.roll_up_every == 0:
            return f"{text}   [unchanged, {prev['count']} rounds]"
        return None

    def sweep(self, live_keys):
        """CLEARED lines for conditions that stopped being observed."""
        out = []
        for k in [k for k in self._state if k not in live_keys]:
            st = self._state.pop(k)
            out.append(f"CLEARED after {st['count']} round(s): {st['text']}")
        return out


_adapt_alert = Adaptation()
_adapt_info = Adaptation()

# --------------------------------------------------------------------------
# BROADCAST (2026-08-23). Push alerts off this machine -- but only the ones
# that survived adaptation, and that ordering is the whole point.
#
# The previous "Daily crypto trend alert -> phone" task was disabled on 08-22
# because it could not run unattended. This is a different thing and it is only
# reasonable BECAUSE adaptation came first: the real twelve-hour log replayed
# through Adaptation is 3,973 lines -> 178. Pushing the unadapted stream would
# send 269 identical copies of one permanent condition and train its reader to
# ignore the channel -- which is worse than no channel, because it looks like
# monitoring.
#
# Rules, all deliberate:
#   * OPT-IN. No URL in the environment -> disabled, said once, never retried.
#   * NO CREDENTIALS anywhere. The URL is read from the environment, never
#     written to the log, never echoed in an error. Section 0.
#   * NEVER BLOCKS a round: short timeout, failures are INFO, and a failing
#     push is never itself an alert (a channel that alerts about itself loops).
#   * RATE LIMITED, and it says so when it clips rather than going quiet.
# --------------------------------------------------------------------------
PUSH_URL = os.environ.get("COVENANT_ALERT_PUSH_URL", "").strip()
PUSH_TIMEOUT_S = float(os.environ.get("COVENANT_ALERT_PUSH_TIMEOUT", "4"))
PUSH_MAX_PER_HOUR = int(os.environ.get("COVENANT_ALERT_PUSH_MAX_PER_HOUR", "20"))
_push_times = []
_push_state = {"announced": False, "clipped": False}


def push_alert(text, now=None, url=None, opener=None):
    """(action, detail). Pure enough to test: clock and transport injectable.

    action is one of: disabled, sent, failed, rate-limited.
    """
    url = PUSH_URL if url is None else url
    if not url:
        return "disabled", "no COVENANT_ALERT_PUSH_URL set"
    now = time.time() if now is None else now
    cutoff = now - 3600
    while _push_times and _push_times[0] < cutoff:
        _push_times.pop(0)
    if len(_push_times) >= PUSH_MAX_PER_HOUR:
        return "rate-limited", f"{PUSH_MAX_PER_HOUR}/hour reached"
    _push_times.append(now)
    body = text.encode("utf-8")[:900]
    try:
        if opener is None:
            req = urllib.request.Request(url, data=body, method="POST")
            req.add_header("Title", "covenant")
            req.add_header("Content-Type", "text/plain; charset=utf-8")
            with urllib.request.urlopen(req, timeout=PUSH_TIMEOUT_S) as r:
                code = getattr(r, "status", 200)
        else:
            code = opener(url, body)
        return "sent", f"HTTP {code}"
    except Exception as e:
        # The URL is a shared secret. Report the failure TYPE, never the target.
        return "failed", type(e).__name__


def anomalies(port, timeout=8):
    """The node's own interoception. Until now only dashboard_render.py read it.

    /anomalies carries {recent, baseline, expected_recent} per event kind and
    the node's own spike verdict -- the richest signal in the system, and the
    component that ACTS was not reading it.
    """
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/anomalies", timeout=timeout) as r:
            return json.loads(r.read().decode()), None
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as e:
        return None, f"{type(e).__name__}: {e}"


def anomaly_report(node_id, rep, seen_kinds):
    """(alerts, infos) from one node's /anomalies. Pure, so it is testable.

    Two signals, and only two, because the node has already done the work:
      * its own spike verdict -- deviation from ITS baseline, not ours;
      * a kind appearing for the first time since this watchdog started, which
        is the cheapest possible novelty detector and catches a failure mode
        nobody wrote a rule for yet.
    A11 measured a FALSE spike for the first ~3 rounds after a synchronized
    restart at degree >= 5; these nodes are degree 1, but that is why the spike
    is reported and not acted on.
    """
    alerts, infos = [], []
    if not isinstance(rep, dict):
        return alerts, infos
    kinds = rep.get("per_kind") or {}
    if rep.get("spike_detected"):
        named = [sp.get("kind") for sp in rep.get("spikes") or []]
        detail = []
        for k in named:
            st = kinds.get(k) or {}
            detail.append(f"{k} (recent {st.get('recent')} vs expected "
                          f"{st.get('expected_recent')})")
        alerts.append(f"node {node_id}: anomaly SPIKE -- " + ", ".join(detail))
    fresh = sorted(k for k in kinds if k not in seen_kinds)
    if fresh:
        infos.append(f"node {node_id} recorded a new anomaly kind: "
                     + ", ".join(f"{k}={(kinds.get(k) or {}).get('recent')}"
                                 for k in fresh))
    seen_kinds.update(kinds)
    return alerts, infos


_seen_kinds = {"A": set(), "B": set()}


# --------------------------------------------------------------------------
# TOPOLOGY (2026-08-23). The last sensory stream with no internal consumer.
#
# /mycelium reports the node's real peer table plus each link's conductance. It
# was exposed on a route and read by NOTHING -- the same shape /anomalies had
# twelve hours earlier. This is where an attacker becomes visible, because it is
# the only place the node says WHO IT IS TALKING TO.
#
# POST /peers is operator-authenticated (it is in PROTECTED_OPERATOR_ENDPOINTS
# and the before_request hook fails closed on missing headers, unknown key, bad
# signature, stale timestamp and replayed nonce). So a peer this watchdog did not
# expect did not arrive by accident: it is either an operator action nobody wrote
# down, or a signed request from a key that should not have made it. Both are
# worth waking up for; neither is inferrable from /health.
#
# Everything here REPORTS. Nothing restarts, blocks or reconfigures a node on
# the strength of a topology reading -- the same boundary P12 draws for the
# substrate sensor, for the same reason.
# --------------------------------------------------------------------------
CONDUCTANCE_MIN = 0.05          # LinkConductance.MIN in the node source
_topo_prev = {}                 # node_id -> last reading


def mycelium(port, timeout=8):
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/mycelium", timeout=timeout) as r:
            return json.loads(r.read().decode()), None
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as e:
        return None, f"{type(e).__name__}: {e}"


def topology_report(node_id, topo, prev, expected):
    """(alerts, infos, state) for one node's /mycelium. Pure, so it is testable.

    expected -- set of "host:port" strings this node is configured to peer with.
    prev     -- the state dict this function returned last round, or {}.
    """
    alerts, infos = [], []
    if not isinstance(topo, dict):
        return alerts, infos, prev or {}

    links = topo.get("links")
    links = links if isinstance(links, list) else []
    seen, floored = set(), 0
    for ln in links:
        if not isinstance(ln, dict):
            continue
        host, port = ln.get("host"), ln.get("port")
        pid = str(ln.get("peer_id"))[:60]
        if host is None or port is None:
            continue
        addr = f"{host}:{port}"
        seen.add(addr)
        if addr not in expected:
            # POST /peers is operator-authenticated -- this did not arrive by
            # accident. Named in full so the operator can act on it.
            alerts.append(f"node {node_id}: UNEXPECTED PEER {pid} at {addr} -- "
                          f"not in this node's configured peer set "
                          f"{sorted(expected) or '(none)'}; POST /peers requires "
                          f"an operator signature, so this was authorised by "
                          f"someone or something")
        c = ln.get("conductance")
        if isinstance(c, (int, float)) and not isinstance(c, bool) \
                and c <= CONDUCTANCE_MIN + 1e-9:
            floored += 1

    missing = sorted(a for a in expected if a not in seen)
    if missing:
        infos.append(f"node {node_id} is not holding configured peer(s) "
                     f"{missing} in its table")

    if links and floored == len(links):
        # A11's measured signature: every link at the floor means the learned
        # ordering has been erased -- by a regression, or by something feeding
        # this node enough redundant traffic to attenuate every edge.
        alerts.append(f"node {node_id}: EVERY link is at the conductance floor "
                      f"({floored}/{len(links)} at {CONDUCTANCE_MIN}) -- the "
                      f"learned delivery ordering has been erased (see A11)")

    height = topo.get("chain_height")
    uptime = topo.get("uptime_seconds")
    state = {"height": height, "uptime": uptime,
             "addrs": sorted(seen)}

    if prev:
        ph, pu = prev.get("height"), prev.get("uptime")
        if isinstance(height, int) and isinstance(ph, int) and height < ph:
            # A chain does not get shorter. A shorter one means a rollback, a
            # different database, or a different node answering this port.
            alerts.append(f"node {node_id}: CHAIN HEIGHT WENT BACKWARDS "
                          f"{ph} -> {height} -- a chain does not shorten; this "
                          f"is a rollback, a swapped database, or a different "
                          f"node on this port. Do not transact.")
        if isinstance(uptime, (int, float)) and isinstance(pu, (int, float)) \
                and uptime < pu:
            # Deliberately a stable string: it must appear once and then CLEAR,
            # not re-fire every round with a new number.
            alerts.append(f"node {node_id}: restarted since the last check "
                          f"(uptime went backwards)")
        pa = prev.get("addrs") or []
        gone = [a for a in pa if a not in seen and a in expected]
        if gone:
            infos.append(f"node {node_id} dropped configured peer(s) {gone} "
                         f"from its table")
    return alerts, infos, state


def _quorum_brief(h):
    """B2: 'independent/semantic' from /health's quorum block, or 'n/a' on a
    node too old to carry one. Never raises -- a log line must not be able to
    stop the watchdog round that produces it."""
    try:
        q = h.get("quorum")
        if not isinstance(q, dict) or not q.get("is_quorum"):
            return "n/a"
        return (f"{q.get('independent_semantic_judges')}/{q.get('semantic_judges')}"
                f"{'' if q.get('diverse') else '!'}")
    except Exception:
        return "n/a"


def disk_source_sha12(path=None):
    """First 12 hex of sha256(covenant_unified_v8.py on disk), or None."""
    try:
        with open(path or CORE_SRC, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()[:12]
    except OSError:
        return None


# THE MODULES THE NODE FILE NAMES (2026-09-19, A153). disk_source_sha12 above
# hashes covenant_unified_v8.py alone, and that is what every consumer of
# "source" means -- the phone ships a subset of this tree, so a wider hash
# there would fake a mesh split. But the node imports PC-only modules at
# start (covenant_daily_plan, covenant_app_update, covenant_highway ...) and
# runs the bytes it imported until restarted: on 2026-09-19 all three nodes
# ran a 240-character cap that no file on disk contained for three hours
# while rolling_restart --status said "on the disk source". This is a SECOND
# fingerprint, additive, over the modules the node file and the launcher name
# by discovery -- an `import covenant_x` or `import_module("covenant_x")`
# in their text -- hashed as (name, bytes) for each that exists on disk. It
# is one level deep on purpose: what those modules import in turn is not
# read, and the docstring says so rather than pretending.
_IMPORT_PAT = None


def runtime_import_set(root=None):
    """Sorted module names the node file and launcher name, by discovery."""
    global _IMPORT_PAT
    import re
    if _IMPORT_PAT is None:
        _IMPORT_PAT = re.compile(r'(?:^|\s)(?:import|from)\s+(covenant_[a-z0-9_]+)|import_module\("(covenant_[a-z0-9_]+)"\)', re.M)
    root = root or HERE
    names = set()
    for fn in ("covenant_unified_v8.py", "run_node.py"):
        try:
            with open(os.path.join(root, fn), "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        for a, b in _IMPORT_PAT.findall(text):
            n = a or b
            if n and n != "covenant_unified_v8":
                names.add(n)
    return sorted(names)


def disk_imports_sha12(root=None):
    """First 12 hex of sha256 over (name, bytes) of each named module on disk, or None."""
    root = root or HERE
    h = hashlib.sha256()
    seen = 0
    for n in runtime_import_set(root):
        p = os.path.join(root, n + ".py")
        try:
            with open(p, "rb") as fh:
                raw = fh.read()
        except OSError:
            continue
        h.update(n.encode("utf-8") + b"\0" + raw + b"\0")
        seen += 1
    return h.hexdigest()[:12] if seen else None


def source_verdict(h, want, wimp):
    """One line for a live node's health against the disk: source, then imports."""
    src = str(h.get("source_sha256", ""))[:12]
    if src != want:
        return "STALE -- restart would pick up %s" % want
    if wimp is None:
        return "on the disk source"
    imp = str(h.get("imports_sha12") or "")[:12]
    if imp == wimp:
        return "on the disk source, imports current"
    return "on the disk source but IMPORTS STALE (%s on disk) -- a module it imports changed; restart (A153)" % wimp


def source_drift_report(states, on_disk):
    """(alerts, infos) for the deployed-vs-running comparison.

    states  -- {node_id: health dict or None}
    on_disk -- sha12 of covenant_unified_v8.py, or None if unreadable

    A node older than v8.31 reports no source at all. That is not an alert --
    it cannot lie, it simply cannot answer -- but it IS the reason the check
    is impossible, so it is said out loud once per round.
    """
    alerts, infos = [], []
    reported = {i: (s or {}).get("source_sha256")
                for i, s in states.items() if s}
    known = {i: v for i, v in reported.items() if v}

    for i in sorted(i for i, v in reported.items() if not v):
        infos.append(f"node {i} predates v8.31 and cannot report which source "
                     f"it is running -- upgrade to make the deployed-vs-running "
                     f"check possible")

    if known and on_disk:
        stale = {i: v for i, v in known.items() if v != on_disk}
        if stale:
            alerts.append(
                "node(s) running a source that is NOT the one on disk: "
                + ", ".join(f"{i} runs {v}" for i, v in sorted(stale.items()))
                + f" but covenant_unified_v8.py is {on_disk} -- restart to pick "
                  "up the deployed file (AB_RESTART_NODES.bat)")
    if known and on_disk is None:
        alerts.append("cannot read covenant_unified_v8.py to compare against "
                      "the running nodes -- deployed-vs-running is unverified")
    if len(set(known.values())) > 1:
        alerts.append(
            "nodes are running DIFFERENT sources: "
            + ", ".join(f"{i}={v}" for i, v in sorted(known.items()))
            + " -- they may disagree on validity rules (see A7)")
    return alerts, infos



# --------------------------------------------------------------------------
# P14 (2026-08-24). THE MONITOR NEVER CHECKED ITSELF.
#
# source_drift_report() above compares the source the NODES loaded against the
# file on disk, and it exists because this machine once ran a node from days ago
# while every restart reported success (M25). It was written on 2026-08-23 at
# 07:39. The watchdog process that would have run it started at 01:39 that
# morning -- six hours EARLIER -- and was still running at 07:02 on 08-24,
# twenty-nine hours later, with neither this check nor Adaptation in it.
#
# So the control built to detect "deployed is not running" spent a day and a
# half being a case of it. Measured in the log it was writing the whole time:
# 3,456 ALERT lines, of which 3,448 are two permanent win32 facts repeated once
# a minute per node, and 8 are things that actually happened -- a 431:1 burial
# of the signal by the noise Adaptation was written to remove.
#
# The gap is structural, not accidental: EVERY health check in this file takes
# its subject as an argument, and nothing passes it itself. A monitor that can
# go stale silently is worth less than its log suggests, because a stale monitor
# still writes confident lines.
#
# SELF_SOURCE_SHA12 is captured at import -- it is what this PROCESS loaded.
# Compared against the file on disk each round, the two differ in exactly one
# situation: someone shipped a new watchdog and nobody restarted it.
#
# Disclosure only. It changes no verdict, restarts nothing, and refuses nothing
# -- the same boundary P12 draws for the substrate sensor and B2 for the quorum
# report. A monitor that restarted itself on a hash change would be a monitor
# that a file write can make execute new code.
# --------------------------------------------------------------------------
SELF_SRC = os.path.abspath(__file__)
SELF_SOURCE_SHA12 = disk_source_sha12(SELF_SRC)   # what THIS process loaded


def self_drift_report(loaded, on_disk):
    """(alerts, infos) for the watchdog's own deployed-vs-running comparison.

    Pure, so it is testable without restarting anything: it takes two hashes
    and returns text. Deliberately a STABLE string while the condition holds,
    so Adaptation says it once and then CLEARs it (M34: an alert that re-fires
    every round with a new number trains its reader to skip it).
    """
    alerts, infos = [], []
    if loaded is None or on_disk is None:
        infos.append("cannot hash covenant_watchdog.py -- the watchdog's own "
                     "deployed-vs-running check is unverified this round")
        return alerts, infos
    if loaded != on_disk:
        alerts.append(
            f"THE WATCHDOG ITSELF IS STALE: this process loaded {loaded} but "
            f"covenant_watchdog.py on disk is {on_disk} -- the checks in the "
            f"deployed file are NOT the checks running. Restart the watchdog "
            f"(AB_RESTART_NODES.bat). Everything else this process reports was "
            f"produced by the older source.")
    return alerts, infos


def _quorum_policy():
    """ops/quorum_policy.json (2026-09-03): the operator's standing decision.
    Read only to DESCRIBE the gate truthfully -- with a deferring seat, a silent
    a silent local seat does not make the gate fail closed, and an alert that says it does
    is a false alert. Nothing here restarts, relaxes or reconfigures."""
    path = os.environ.get("COVENANT_QUORUM_POLICY_PATH") or os.path.join(HERE, "ops", "quorum_policy.json")
    try:
        with open(path, encoding="utf-8") as fh:
            p = json.load(fh)
        return p if isinstance(p, dict) else {}
    except (OSError, ValueError):
        return {}


def _seat_defers(pol=None):
    pol = _quorum_policy() if pol is None else pol
    return "deferring" in str(pol.get("providers", ""))


# --------------------------------------------------------------------------
# SELF-EVALUATION (2026-08-29). "Constant self-evaluating by all systems
# involved" -- the operator's words, and the missing consumer of everything
# this file already senses. Every stream above ends in the LOG, which is a
# record for a reader who already knows something is wrong. This section
# turns the same readings into a periodic VERDICT: one dated block, one line
# per layer, PASS/WARN/FAIL each, appended to a ledger a person or a later
# session reads FIRST.
#
# It operates on METADATA AND MYCELIUM the pass already holds -- the /health
# fields, the topology states, the judge identity baseline, the P14 drift
# answer. No new probe: a self-evaluation that probes is measuring its own
# probe, and one that re-asks the node is measuring the network twice.
#
# REPORT-ONLY, the same boundary P12 draws for the substrate sensor and the
# topology reader: nothing here restarts, blocks or reconfigures anything on
# the strength of its own verdict. A monitor that acts on its self-opinion
# is a loop; a monitor that publishes it is a record.
#
# For Misha, and all that were lost to injustice.
# --------------------------------------------------------------------------
SELF_EVAL_EVERY = int(os.environ.get("COVENANT_SELF_EVAL_ROUNDS", "60"))
SELF_EVAL_PATH = os.environ.get(
    "COVENANT_SELF_EVAL_PATH", os.path.join(HERE, "ops", "SELF_EVAL.md"))
SELF_EVAL_MAX_BYTES = 512 * 1024
_self_eval = {"round": 0, "persist": False}
# The counter used to live only in memory, and that was wrong (found
# 2026-09-16). covenant_highway.py's schedule_watchdog_restart kills and
# respawns this process BY DESIGN -- five times in its own ledger -- and its
# docstring justifies that with "it writes its state as it goes rather than at
# the end". True of every other reading here. False of exactly this one, which
# produces output only on reaching round SELF_EVAL_EVERY, i.e. at the end of an
# hour. On 2026-09-16 four guard revivals (attempts #8-#11, each "no live
# watchdog PID") truncated the count before it ever got there, so
# ops/SELF_EVAL.md held nothing between 14:55Z and 18:53Z while every round
# logged normally and the guard read the log as fresh. The ledger was not
# broken; the counter could not survive the restart the system schedules.
#
# NOT resumed by --once. A one-shot run that inherited a count of 59 would
# write a verdict block from a single pass's readings and number it as if an
# hour of them stood behind it.
SELF_EVAL_STATE = os.path.join(HERE, "logs", "self_eval_state.json")


def _self_eval_resume():
    """Daemon start only: restore the round counter across a restart.

    Returns the resumed round, or 0 when there is nothing to resume or the
    file is unreadable. Never raises: a lost counter costs one late block,
    and a counter that can crash the pass costs the monitoring itself."""
    try:
        with open(SELF_EVAL_STATE, "r", encoding="utf-8") as fh:
            n = int(json.load(fh).get("round", 0))
    except (OSError, ValueError, TypeError, AttributeError):
        return 0
    if n < 0:
        return 0
    _self_eval["round"] = n
    return n


def _self_eval_persist():
    """Write the counter where the next process will find it.

    Atomic via os.replace: this process is killed with Stop-Process -Force, so
    a plain write could be interrupted mid-file and leave a truncated JSON that
    resets the count to zero -- reintroducing the bug in a form that only shows
    up under the exact condition this exists to survive."""
    if not _self_eval["persist"]:
        return
    try:
        os.makedirs(os.path.dirname(SELF_EVAL_STATE), exist_ok=True)
        tmp = SELF_EVAL_STATE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"round": _self_eval["round"],
                       "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                      fh)
        os.replace(tmp, SELF_EVAL_STATE)
    except OSError:
        pass


SELF_EVAL_HEADER = (
    "# covenant self-evaluation ledger\n"
    "# For Misha, and all that were lost to injustice.\n"
    "# One block per evaluation: PASS/WARN/FAIL per layer, worst wins.\n"
    "# Written by covenant_watchdog.py (report-only) and by the scheduled\n"
    "# covenant-self-eval task. Append-only; rotates to .prev at 512KB.\n\n")

_RANK = {"PASS": 0, "WARN": 1, "FAIL": 2}

# ---------------------------------------------------------------------------
# OFFLINE READINGS (2026-09-19, at the operator's instruction: "this should be
# greenlit or a local pc function constantly").
#
# WHY THIS EXISTS. Until today the hourly block carried five layers -- nodes,
# mycelium, judge, self, alerts -- all of them readings of the RUNNING chain.
# The scheduled Claude session carried four more: the trader, the deploy pins,
# git drift and disk. On 2026-09-19 both of the day's failures were in those
# four (a trader cycle that could not seal at 09:00, and a deploy verifier
# pinning a build deleted nine days ago), and the hourly block said WARN
# through all of it, because it was structurally unable to look. A ledger that
# can only see the layers that were green is not an evaluation of the system.
#
# WHAT IT STRUCTURALLY CANNOT SEE. These are local file and git reads only.
# No network: git drift is measured against the last fetch this PC did, and
# the row says how old that is rather than pretending it is live. It does not
# run the trader, read a key, or touch funds. It compares the core against
# MANIFEST.sha256, which is the record that has been telling the truth, and
# NOT against verify_deploy.py's in-source pins, which have been stale since
# 2026-09-12 -- so this row can miss a substitution that also rewrote the
# manifest, and it says so in its own detail line.
#
# It is separate from self_evaluation(), which stays pure (everything arrives
# as arguments), and every reading fails to None rather than raising: the
# evaluation must not be able to kill the evaluator.
# ---------------------------------------------------------------------------
TRADER_LOG = os.path.join(HERE, "trader_log.txt")
CORE_FILE = os.path.join(HERE, "covenant_unified_v8.py")
MANIFEST_FILE = os.path.join(HERE, "MANIFEST.sha256")


def _read_text(path, tail_bytes=0):
    try:
        with open(path, "rb") as fh:
            if tail_bytes:
                try:
                    fh.seek(max(0, os.path.getsize(path) - tail_bytes))
                except OSError:
                    pass
            return fh.read().decode("utf-8", "replace")
    except OSError:
        return None


def _git(*args, timeout=20):
    try:
        p = covenant_quiet.run(("git",) + args, cwd=HERE, timeout=timeout,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace").strip()


def _trader_reading(now=None):
    """(verdict, detail) for the trader, or None when there is no log.

    Freshness is trader_freshness.verdict() -- the existing measurement, not a
    second one that could disagree with it. On top of that: a cycle that RAN
    and then failed its seal produced no audit record, which the freshness
    code does not and should not know about, so it is asked separately."""
    text = _read_text(TRADER_LOG, tail_bytes=200_000)
    if text is None:
        return None
    try:
        import trader_freshness
    except Exception:
        return "WARN", ("trader_log.txt is here but trader_freshness.py did "
                        "not import -- freshness UNMEASURED this pass")
    t = time.localtime(now if now is not None else time.time())
    try:
        code, line = trader_freshness.verdict(
            text, (t.tm_year, t.tm_mon, t.tm_mday), (t.tm_hour, t.tm_min))
    except Exception as e:                                   # never fatal
        return "WARN", f"trader_freshness.verdict raised {type(e).__name__}"
    try:
        age_h = (time.time() - os.path.getmtime(TRADER_LOG)) / 3600.0
    except OSError:
        age_h = float("nan")
    # The last cycle only: everything after the second-to-last COMPLETE line.
    parts = text.split("---- CYCLE COMPLETE")
    last = ("---- CYCLE COMPLETE" + parts[-2] + "---- CYCLE COMPLETE"
            + parts[-1]) if len(parts) >= 2 else text
    seal_lines = [l.strip() for l in last.splitlines() if " SEAL " in l]
    seal_failed = bool(seal_lines) and "FAILED" in seal_lines[-1].upper()
    exit_bad = [l.strip() for l in last.splitlines()
                if l.strip().startswith("exit ")
                and not l.strip().startswith("exit 0")]
    detail = f"log {age_h:.1f}h old; freshness exit {code}: {line[:150]}"
    if seal_failed or exit_bad:
        why = (seal_lines[-1][:120] if seal_failed else exit_bad[-1][:120])
        return "FAIL", (detail + f" -- BUT the last cycle did not finish "
                                 f"clean: {why}")
    if code == 1:
        return "FAIL", detail
    if code == 2:
        return "WARN", detail
    return "PASS", detail


def _repo_reading():
    """(verdict, detail) comparing the core on disk to MANIFEST.sha256."""
    blob = _read_text(MANIFEST_FILE)
    if blob is None or not os.path.exists(CORE_FILE):
        return None
    try:
        with open(CORE_FILE, "rb") as fh:
            disk = hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None
    want = None
    for row in blob.splitlines():
        bits = row.split(None, 1)
        if len(bits) == 2 and bits[1].strip().replace("\\", "/").endswith(
                "covenant_unified_v8.py"):
            want = bits[0].strip()
            break
    if want is None:
        return "WARN", ("MANIFEST.sha256 carries no row for "
                        "covenant_unified_v8.py -- the core is unpinned")
    if want != disk:
        return "FAIL", (f"core on disk {disk[:12]} but MANIFEST.sha256 pins "
                        f"{want[:12]} -- an old copy, a partial copy or a "
                        f"hand edit. Re-pin in the SAME change as the file")
    return "PASS", (f"core {disk[:12]} matches MANIFEST.sha256. This compares "
                    f"the manifest only; a substitution that also rewrote the "
                    f"manifest would read clean here")


def _git_reading():
    """(verdict, detail) for drift against the LAST FETCH -- no network."""
    head = _git("rev-parse", "--short", "HEAD")
    if head is None:
        return None
    counts = _git("rev-list", "--left-right", "--count", "origin/main...HEAD")
    dirty = _git("status", "--short")
    n_dirty = len([l for l in (dirty or "").splitlines() if l.strip()])
    port = [l for l in (dirty or "").splitlines()
            if "holdings" in l.lower() or "portfolio" in l.lower()]
    fetch_age = ""
    fh_path = os.path.join(HERE, ".git", "FETCH_HEAD")
    try:
        fetch_age = " last fetch %.1fh ago;" % (
            (time.time() - os.path.getmtime(fh_path)) / 3600.0)
    except OSError:
        fetch_age = " no FETCH_HEAD (origin never fetched here);"
    if counts is None:
        return "WARN", (f"HEAD {head};{fetch_age} origin/main not resolvable "
                        f"-- drift UNMEASURED")
    behind, ahead = (counts.split() + ["?", "?"])[:2]
    detail = (f"HEAD {head}, {ahead} ahead / {behind} behind origin/main as "
              f"of the last fetch;{fetch_age} {n_dirty} file(s) not committed")
    if port:
        return "FAIL", (detail + " -- INCLUDING what looks like a portfolio "
                        f"file: {port[0].strip()[:80]}. Never git add -A here")
    if behind not in ("0", "?") or ahead not in ("0", "?"):
        return "WARN", detail
    return "PASS", detail


def _disk_reading():
    try:
        du = shutil.disk_usage(HERE)
    except OSError:
        return None
    free_g = du.free / (1024.0 ** 3)
    logs = 0
    for root, _dirs, files in os.walk(os.path.join(HERE, "logs")):
        for f in files:
            try:
                logs += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    detail = (f"{free_g:.0f}G free of {du.total / (1024.0 ** 3):.0f}G "
              f"({du.used * 100 // du.total}% used); logs/ "
              f"{logs / (1024.0 ** 2):.0f}M")
    if free_g < 5:
        return "FAIL", detail + " -- under 5G free"
    if free_g < 20:
        return "WARN", detail + " -- under 20G free"
    return "PASS", detail


def offline_readings(now=None):
    """{layer: (verdict, detail)} for everything this PC can check without the
    chain. Any reading that cannot be taken is ABSENT from the dict rather
    than guessed, so self_evaluation() omits the row instead of asserting."""
    out = {}
    for name, fn in (("trader", lambda: _trader_reading(now)),
                     ("repo", _repo_reading),
                     ("git", _git_reading),
                     ("disk", _disk_reading)):
        try:
            r = fn()
        except Exception as e:                               # never fatal
            r = ("WARN", f"{name} reading raised {type(e).__name__}: {e}"[:160])
        if r:
            out[name] = r
    return out


def self_evaluation(states, topo, judge, self_drift, alerts, now_iso,
                    round_no=0, rate_limited=(), offline=None):
    """(block, overall) -- every layer, judged from what this pass sensed.

    Pure, the same shape as topology_report and judge_identity_report:
    everything it needs arrives as arguments and it only returns text.
      states     -- node_id -> /health dict or None       (metadata)
      topo       -- node_id -> topology state dict         (mycelium)
      judge      -- the judge-identity baseline state      (metadata)
      self_drift -- P14's alert list for THIS file          (metadata)
      alerts     -- every alert this pass raised
      offline    -- {layer: (verdict, detail)} from offline_readings(), or
                    None. A layer that is absent is OMITTED, never guessed:
                    the block must not be able to report PASS on something
                    nobody measured.
    """
    layers = []

    def layer(name, verdict, detail):
        layers.append((name, verdict, detail))

    up = {k: s for k, s in states.items() if s}
    if not up and rate_limited and len(rate_limited) >= len(states):
        # A115b: every node answered 429. The ledger must not record a healthy
        # chain as down -- this file's own history is that a permanent false
        # reading is how a true one stops being believed.
        layer("nodes", "UNKNOWN", "every node was rate-limiting /health (429) this pass: %s. "
                                  "Alive and refusing to be asked again; nothing was measured."
                                  % ", ".join(sorted(rate_limited)))
    elif not up:
        layer("nodes", "FAIL", "no node reachable -- the chain is not running")
    else:
        down = sorted(set(states) - set(up))
        srcs = {str(s.get("source_sha256"))[:12] for s in up.values()}
        hs = [s.get("chain_height") for s in up.values()
              if isinstance(s.get("chain_height"), int)]
        spread = (max(hs) - min(hs)) if hs else 0
        d = (f"{len(up)}/{len(states)} up, height {max(hs) if hs else '?'} "
             f"(spread {spread}), source {'/'.join(sorted(srcs))}")
        if down:
            layer("nodes", "FAIL", f"{down} unreachable; " + d)
        elif len(srcs) > 1 or spread > 1:
            layer("nodes", "WARN", d)
        else:
            layer("nodes", "PASS", d)

    reporting = {k: v for k, v in topo.items()
                 if isinstance(v, dict) and v.get("addrs") is not None}
    if not reporting:
        layer("mycelium", "WARN", "no topology state held -- /mycelium has "
                                  "not answered yet this process")
    else:
        held = ", ".join(f"{k}={len(v.get('addrs') or [])}"
                         for k, v in sorted(reporting.items()))
        v = "PASS" if len(reporting) == len(states) else "WARN"
        layer("mycelium", v, f"{len(reporting)}/{len(states)} reporting; "
                             f"links held: {held}")

    if isinstance(judge, dict) and judge.get("digest"):
        layer("judge", "PASS", f"baseline digest {str(judge['digest'])[:19]}, "
                               f"{len(judge.get('served') or {})} model(s)")
    elif _seat_defers():
        layer("judge", "WARN", "no local judge baseline; the seat defers per "
                               "ops/quorum_policy.json (GitHub runner, then the "
                               "distilled fallback; silence is not dissent)")
    else:
        layer("judge", "FAIL", "no judge identity baseline -- unreachable or "
                               "expected model never seen (gate fails closed)")

    if self_drift:
        layer("self", "FAIL", str(self_drift[0])[:120])
    else:
        layer("self", "PASS", "running watchdog matches its file on disk (P14)")

    if alerts:
        v = "FAIL" if any("FORK" in a or "down" in a or "NO node" in a
                          for a in alerts) else "WARN"
        layer("alerts", v, f"{len(alerts)} live -- first: {alerts[0][:110]}")
    else:
        layer("alerts", "PASS", "none this pass")

    # The offline layers, in a fixed order so the ledger is greppable. Only
    # what was actually read appears.
    for name in ("trader", "repo", "git", "disk"):
        r = (offline or {}).get(name)
        if r:
            layer(name, r[0], r[1])

    overall = max((v for _, v, _ in layers), key=lambda v: _RANK[v])
    block = [f"## {now_iso}  overall {overall}  (round {round_no})"]
    block += [f"{n:9s} {v:4s}  {d}" for n, v, d in layers]
    return "\n".join(block) + "\n\n", overall


def _self_eval_write(block):
    """Append one block to the ledger. A failed write is logged and never
    raised: the evaluation must not be able to kill the evaluator."""
    try:
        os.makedirs(os.path.dirname(SELF_EVAL_PATH), exist_ok=True)
        fresh = not os.path.exists(SELF_EVAL_PATH)
        if not fresh and os.path.getsize(SELF_EVAL_PATH) > SELF_EVAL_MAX_BYTES:
            os.replace(SELF_EVAL_PATH, SELF_EVAL_PATH + ".prev")
            fresh = True
        with open(SELF_EVAL_PATH, "a", encoding="utf-8", newline="\n") as fh:
            if fresh:
                fh.write(SELF_EVAL_HEADER)
            fh.write(block)
        return True
    except OSError as e:
        log("INFO", f"self-eval ledger write failed ({type(e).__name__}: {e})"
                    f" -- this round's verdict is in the log only")
        return False


# ---------------------------------------------------------------- logging --
def _rotate():
    try:
        if os.path.exists(LOGFILE) and os.path.getsize(LOGFILE) > LOG_MAX_BYTES:
            for i in range(LOG_KEEP - 1, 0, -1):
                a, b = f"{LOGFILE}.{i}", f"{LOGFILE}.{i + 1}"
                if os.path.exists(a):
                    os.replace(a, b)
            os.replace(LOGFILE, f"{LOGFILE}.1")
    except OSError:
        pass


def log(level, msg):
    os.makedirs(LOGDIR, exist_ok=True)
    _rotate()
    line = (f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} "
            f"{level:<5} {msg}")
    print(line, flush=True)
    try:
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


# ------------------------------------------------------------------ probes --
def health(port, timeout=8):
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/health", timeout=timeout) as r:
            return json.loads(r.read().decode()), None
    except urllib.error.HTTPError as e:
        # A 429 means the node is UP and refusing to be asked again (2026-09-14).
        # /health is an unlisted read endpoint carrying RATE_LIMIT_DEFAULT -- 20
        # requests per 60 s from one source -- and 127.0.0.1 is ONE source no
        # matter which tool is asking. urllib raises HTTPError for it, HTTPError
        # is a SUBCLASS of URLError, and the clause below caught URLError: a
        # rate-limited node was indistinguishable from a refused connection.
        # Three in a row restarts it, and when every node trips together the
        # threshold drops from three to one, so the answer to "I asked too
        # often" was to restart the whole mesh. Measured today: B and C returned
        # 429 in 1.5 ms, were logged unreachable, and this watchdog tried to
        # start second copies of both. The only thing standing between that and
        # an outage was run_node's port preflight refusing them.
        if e.code == 429:
            return None, "429 rate-limited (the node is UP and refusing to be asked again)"
        return None, f"HTTPError {e.code}"
    except http.client.HTTPException as e:
        # A truncated body, a bad status line, a connection closed mid-response.
        # http.client.HTTPException is NOT an OSError and NOT a URLError, so
        # until 2026-09-14 it escaped this function entirely and aborted the
        # whole pass -- every node after the bad one went unchecked, and the
        # loop that restarts a dead node never ran. Exactly the shape of the
        # 429 bug one layer along: an unclassified failure is worse than a
        # misclassified one, because it takes the monitor down with it.
        return None, f"{type(e).__name__}: {e}"
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as e:
        return None, f"{type(e).__name__}: {e}"


def balance(db, of_key, timeout=45):
    """Read a balance straight out of a database file. SQLite WAL allows a
    reader while the node holds it open."""
    try:
        p = covenant_quiet.run(
            [sys.executable, "covenant_client.py", "balance",
             "--db", db, "--of-key", of_key],
            cwd=HERE, capture_output=True, text=True, timeout=timeout)
        for tok in p.stdout.split():
            try:
                return float(tok)
            except ValueError:
                continue
        return None
    except (subprocess.SubprocessError, OSError):
        return None


def start_node(node):
    """Relaunch a dead node. Does NOT delete or recreate its database --
    production resumes a chain, it does not rebuild one.

    PAUSABLE (2026-09-16). With ops/pause/watchdog-restarts present this
    refuses to launch and says why, so a node can be taken down for an update
    without the watchdog putting it back up mid-edit. The watchdog goes on
    watching and alerting either way -- the pause stops the ACTION, never the
    observation, because a monitor silenced for an update is how an outage
    becomes an incident nobody saw.
    """
    try:
        import covenant_pause as _p
        is_paused, why = _p.paused("watchdog-restarts")
    except Exception:                                            # noqa: BLE001
        is_paused, why = False, ""
    if is_paused:
        log("WARN", "node %s is down and restarts are PAUSED (%s) -- not starting it"
            % (node.get("id", "?"), why))
        return False
    env = dict(os.environ)
    env["COVENANT_DB_PATH"] = node["db"]
    env.setdefault("COVENANT_LOCAL_JUDGE_TIMEOUT", "600")
    env.setdefault("COVENANT_JUDGE_TIMEOUT", "600")
    # v8.40: match run_node.py's pair -- a node the watchdog
    # revives must judge with the same quorum a node the operator starts
    # does, or a restart silently changes the gate (P17's hazard sideways).
    # 2026-09-12: "deferring,semantic", the launcher's new no-policy default
    # (run_node.py, A93). Kept identical so the two never drift.
    env["COVENANT_JUDGE_PROVIDERS"] = "deferring,semantic"
    # 2026-09-03: the operator's standing quorum decision, ops/quorum_policy.json,
    # read here so a node this watchdog revives is wired like one the operator
    # starts (the runner applies the same file again; this only keeps the env
    # honest for anyone reading it). Disclosure of a decision, not a decision.
    # ONE IMPLEMENTATION (2026-09-07). This used to read the policy file itself
    # and apply the two keys it happened to know about. That is fine until the
    # policy grows a third: COVENANT_RELAX_VALUELESS_FOR (the trading
    # exception) was added to covenant_judge_defer.apply_policy and this copy
    # did not know it existed, so a node the WATCHDOG revived would have had
    # the GitHub runner switched off WITHOUT the exception that makes that
    # survivable -- every trader seal failing closed, and only on the revival
    # path, which is the path nobody watches. That is precisely the hazard the
    # comment above names. So this asks the same function the operator's
    # runner asks, and a fourth key will reach both without another edit.
    try:
        import covenant_judge_defer as _defer
        _defer.apply_policy(env)
    except Exception:                                             # noqa: BLE001
        # The watchdog must revive a node even if that import is broken. Fall
        # back to the two keys, and leave the exception OFF -- the strict
        # posture, which refuses rather than trades.
        try:
            with open(os.path.join(HERE, "ops", "quorum_policy.json"), encoding="utf-8") as _fh:
                _pol = json.load(_fh)
            if _pol.get("providers"):
                env["COVENANT_JUDGE_PROVIDERS"] = str(_pol["providers"])
            if _pol.get("silence_is_not_dissent") is True:
                env["COVENANT_SILENCE_IS_NOT_DISSENT"] = "1"
        except (OSError, ValueError, AttributeError):
            pass
    env.pop("COVENANT_INSECURE_MOCK_JUDGE", None)
    os.makedirs(LOGDIR, exist_ok=True)
    out = open(os.path.join(LOGDIR, f"node{node['id']}.log"), "a",
               encoding="utf-8", errors="replace")
    cmd = [sys.executable, "run_node.py",
           "--port", str(node["port"]), "--node-id", node["id"],
           "--genesis", "genesis.json", "--peers", node["peers"]]
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    if os.name == "nt":
        flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen(cmd, cwd=HERE, env=env, stdout=out, stderr=out,
                     creationflags=flags)
    log("WARN", f"node {node['id']} restarted -> logs/node{node['id']}.log")


# ------------------------------------------------------------------- pass --
def _student_state():
    """What the self-evaluation's judge layer measures since 2026-09-12: the
    distilled student that actually judges (fallback_model.json), by digest.
    Until today this was a model server's identity baseline (P15), removed
    with the server; a missing student file is the fail-closed case now."""
    p = os.path.join(HERE, "fallback_model.json")
    try:
        with open(p, "rb") as fh:
            d = hashlib.sha256(fh.read()).hexdigest()
        return {"digest": "student@" + d[:12], "served": {"fallback_model.json": os.path.getsize(p)}}
    except OSError:
        return {}


def one_pass(strict=False):
    """strict=True is the single-shot / monitoring mode.

    The 3-strike counter exists so a node that blips during a slow verdict is
    not restarted out from under itself. But a SINGLE pass can never reach
    three consecutive failures -- so in --once mode that counter would make a
    node that is flat on its back report "all checks passed" and exit 0. The
    one thing you most want a monitor to catch would be the one thing it
    structurally cannot. In strict mode, unreachable is an alert on the first
    miss, and nothing is restarted: a monitoring probe should report, not
    change what it is measuring."""
    alerts = []
    states = {}

    # PROBE THE WHOLE MESH BEFORE ACTING ON ANY OF IT. The 3-strike rule is
    # there so a node that blips during a slow verdict is not restarted out
    # from under itself -- and that is a statement about ONE node. When every
    # node is unreachable in the same pass, nothing is mid-verdict: the mesh
    # is gone, and waiting two more passes is waiting for nothing. Measured
    # 2026-09-06: a full pass takes minutes because of everything else it
    # checks, so three consecutive misses is ten minutes or more of a dead
    # mesh, and in a seven-minute outage that day the watchdog never reached
    # the third strike at all. A total outage restarts on the first miss.
    probes = [(n,) + health(n["port"]) for n in NODES]
    # "Whole mesh down" drops the restart threshold from three strikes to one,
    # so it must mean UNREACHABLE, never merely rate-limited (2026-09-14). A
    # burst of polling trips all three limiters at once -- they are separate
    # limiters but they all see the same 127.0.0.1 and the same burst -- and
    # under the old test that read as the whole mesh being down, which would
    # have restarted every node on the first pass. A node that answers 429 is
    # answering.
    all_down = all(h is None and not str(e).startswith("429") for _, h, e in probes)
    # WHO IS MERELY RATE-LIMITED (2026-09-14, A115b). `states` below maps a node
    # to its /health dict or None, and a 429 lands in it as None -- so every
    # later test of the form "is anything alive" counts a node that answered in
    # under two milliseconds as absent. The restart path was taught the
    # difference; these were not, and an adversarial review measured a fully
    # healthy mesh still raising "NO node is reachable -- the chain is not
    # running" while every node was answering 429. That sentence is the loudest
    # thing this file can say, and saying it about a healthy chain is how an
    # operator learns to disbelieve it.
    rate_limited = {n["id"] for n, h, e in probes if h is None and str(e).startswith("429")}

    # TENDING, on a pass where something is actually up. Moved here from
    # covenant_watchdog_guard.py on 2026-09-07: the guard's stated property is
    # that it heals ONLY the watchdog and touches no node, database or key,
    # and test_c3_guard.py asserts that against its source. Mining the pending
    # pool needs the node key, so putting it in the guard broke the property
    # the moment it was written. This is the layer that already touches nodes.
    if not strict and not all_down:
        ss = tend_seal_service()
        if ss != "up":
            log("INFO", "seal service: %s" % ss)
        mp = tend_pending()
        if mp != "nothing pending":
            log("INFO", "pool: %s" % mp)

    for n, h, err in probes:
        states[n["id"]] = h
        if h is None and str(err).startswith("429"):
            # NOT A FAILURE. The node answered -- it answered "stop asking".
            # Counting this would let a busy minute of polling restart a healthy
            # node, and restarting is the only thing here that costs anything.
            # The counter is NOT reset either: a real outage that began during a
            # rate-limited window should not have its tally wiped by one 429.
            log("INFO", f"node {n['id']} :{n['port']} is rate-limiting /health "
                        "(429) -- alive, asked too often; not counted as down")
            continue
        if h is None:
            if strict:
                alerts.append(f"node {n['id']} :{n['port']} unreachable ({err})")
                continue
            _fail_counts[n["id"]] += 1
            threshold = 1 if all_down else FAIL_BEFORE_RESTART
            log("WARN", f"node {n['id']} :{n['port']} unreachable "
                        f"({_fail_counts[n['id']]}/{threshold}"
                        + (", whole mesh down -- not a blip" if all_down else "")
                        + f") {err}")
            if _fail_counts[n["id"]] >= threshold:
                alerts.append(f"node {n['id']} down")
                start_node(n)
                _fail_counts[n["id"]] = 0
            continue
        _fail_counts[n["id"]] = 0

        real = [w for w in h.get("warnings", [])
                if not any(fp in w for fp in FALSE_POSITIVE_WARNINGS)]
        muted = len(h.get("warnings", [])) - len(real)

        # P11: name what is RUNNING, every minute, in the log an operator
        # reads afterwards. A node older than v8.31 cannot say, and printing
        # that is more use than leaving the field blank.
        line = (f"node {n['id']} v={h.get('version') or 'pre-v8.31'} "
                f"src={h.get('source_sha256') or 'cannot-say'} "
                f"height={h.get('chain_height')} "
                f"peers={h.get('peers')} judge={h.get('judge')} "
                f"insecure={h.get('judge_insecure')} "
                # B2 (v8.35): what the gate ACTUALLY is, minute by minute,
                # in the file an operator reads afterwards -- same reason
                # P11 put the version here. "2 judges" can mean one opinion
                # and the sender's own word for it; this says which. A node
                # older than v8.35 has no `quorum` block and prints n/a
                # rather than a guess.
                f"judges={_quorum_brief(h)} "
                f"(+{muted} known-false warnings suppressed)")
        rendered = _adapt_info.observe(f"node:{n['id']}", line)   # P12
        if rendered:
            log("INFO", rendered)

        # Topology: who this node is actually talking to.
        topo, terr = mycelium(n["port"])
        if topo is None:
            log("INFO", f"node {n['id']} /mycelium unavailable ({terr}) -- "
                        f"skipped, not an alert")
        else:
            expected = {p.strip() for p in str(n.get("peers", "")).split(",")
                        if p.strip()}
            t_alerts, t_infos, t_state = topology_report(
                n["id"], topo, _topo_prev.get(n["id"], {}), expected)
            _topo_prev[n["id"]] = t_state
            alerts.extend(t_alerts)
            for msg in t_infos:
                log("INFO", msg)

        # P12: the node's own interoception, read by the thing that acts.
        rep, aerr = anomalies(n["port"])
        if rep is None:
            log("INFO", f"node {n['id']} /anomalies unavailable ({aerr}) -- "
                        f"skipped, not an alert")
        else:
            a_alerts, a_infos = anomaly_report(
                n["id"], rep, _seen_kinds.setdefault(n["id"], set()))
            alerts.extend(a_alerts)
            for msg in a_infos:
                log("INFO", msg)

        if h.get("judge_insecure"):
            alerts.append(f"node {n['id']}: INSECURE mock judge active -- the "
                          f"gate is keyword matching, not judging")
        if h.get("crisis_mode"):
            alerts.append(f"node {n['id']}: crisis_mode")
        for w in real:
            alerts.append(f"node {n['id']}: {w}")

    live = [s for s in states.values() if s]
    if not live and rate_limited and len(rate_limited) == len(NODES):
        # Every node answered, and every one of them answered "stop asking".
        # That is a statement about the caller, not the chain.
        log("INFO", "every node is rate-limiting /health (429): %s -- alive, asked "
                    "too often. Not reporting the chain down." % ", ".join(sorted(rate_limited)))
    elif not live and rate_limited:
        alerts.append("no node returned a health document; %s were rate-limiting (429, alive) "
                      "and the rest were unreachable"
                      % ", ".join(sorted(rate_limited)))
    elif not live:
        alerts.append("NO node is reachable -- the chain is not running")
    if len(live) == len(NODES):
        hs = [s.get("chain_height", 0) for s in live]
        if max(hs) - min(hs) > 1:
            alerts.append(f"height gap {hs} -- peers not keeping up")

    # THE PHONE'S HEARTBEAT (2026-09-12): what a phone last said about itself,
    # and an alert when one that was reporting goes quiet.
    try:
        import covenant_daily_plan as _dp
        c_alerts, c_infos = _dp.checkin_report()
        # THE BUILD THE PHONE IS HOLDING (2026-09-16). The heartbeat has always
        # carried it and nothing read it, which is how the phone sat two days on
        # a build that predates the in-app updater -- a gap that cannot close
        # itself, because that build has no way to ask for its successor. Said
        # here, once, with the URL to open; it clears when the phone reports the
        # sha it was handed.
        b_alerts, b_infos = _dp.build_report()
        c_alerts, c_infos = list(c_alerts) + b_alerts, list(c_infos) + b_infos
        # THE HIGHWAY'S PASS (2026-09-16). Sense, and repair what is reversible:
        # a held copy out of sync, a build not fetched, a log eating the disk.
        # Its own restart is EXCLUDED here for the obvious reason -- a remedy
        # that kills its caller mid-round is not a repair -- so P14's alert
        # above stays the way a stale watchdog gets reported. Anything the
        # engine may not run comes back as an alert carrying the covenant's own
        # reading and the cost beside the gain, not as a silent skip.
        try:
            import covenant_highway as _hw
            h_alerts, h_infos = _hw.run_once(dry_run=False, exclude=("restart_watchdog",))
            c_alerts, c_infos = c_alerts + h_alerts, c_infos + h_infos
        except Exception as e:                                   # noqa: BLE001
            c_infos.append("highway pass unavailable: %s: %s" % (type(e).__name__, str(e)[:120]))
        # EVERY STANDING PAUSE, SAID ON EVERY ROUND (2026-09-16). A pause is a
        # decision and never an alert -- but a pause nobody is reminded of is
        # how a system runs half-off for a week and the operator finds out
        # from a consequence. The line carries its age for that reason.
        try:
            import covenant_pause as _pz
            p_alerts, p_infos = _pz.report()
            c_alerts, c_infos = c_alerts + p_alerts, c_infos + p_infos
        except Exception as e:                                   # noqa: BLE001
            c_infos.append("pause states unreadable: %s" % type(e).__name__)
    except Exception as e:                                       # noqa: BLE001
        c_alerts, c_infos = [], ["phone check-ins unreadable: %s" % type(e).__name__]
    # THE PC'S SAY TO THE PHONE BRAIN (2026-09-13, phase 3): one status line.
    try:
        import covenant_actuator_guide as _ag
        c_infos.append(_ag.status())
    except Exception as e:                                       # noqa: BLE001
        c_infos.append("phone brain guide unreadable: %s" % type(e).__name__)
    alerts.extend(c_alerts)
    for msg in c_infos:
        log("INFO", msg)

    drift_alerts, drift_infos = source_drift_report(states, disk_source_sha12())
    s_alerts, s_infos = self_drift_report(
        SELF_SOURCE_SHA12, disk_source_sha12(SELF_SRC))   # P14
    drift_alerts = list(drift_alerts) + s_alerts
    drift_infos = list(drift_infos) + s_infos
    alerts.extend(drift_alerts)
    for line in drift_infos:
        log("INFO", line)

    # The check nothing else does: same identity, both databases, must agree.
    if all(os.path.exists(os.path.join(HERE, n["db"])) for n in NODES) and \
            os.path.exists(os.path.join(HERE, "nodeA_prod.db.key")):
        _identities = [("founder", "nodeA_prod.db.key")] + [
            (f"node{n['id']}", n["key"]) for n in NODES if n["id"] != "A"]
        for who, keyfile in _identities:
            if not os.path.exists(os.path.join(HERE, keyfile)):
                continue
            # Every database, not a hardcoded pair. With three nodes a
            # pairwise A-vs-B check would leave C's ledger cross-checked by
            # nothing -- a silent coverage gap of exactly the kind this
            # function exists to catch.
            reads = {n["id"]: balance(n["db"], keyfile) for n in NODES}
            got = {k: v for k, v in reads.items() if v is not None}
            missing = sorted(k for k in reads if k not in got)
            if len(got) < 2:
                log("INFO", f"balance read for {who} unavailable on "
                            f"{missing or 'all'} -- fewer than two databases "
                            f"readable, skipped, not an alert")
                continue
            if missing:
                log("INFO", f"balance for {who} not readable on {missing}; "
                            f"comparing {sorted(got)}")
            lo, hi = min(got.values()), max(got.values())
            if hi - lo > 1e-9:
                detail = ", ".join(f"node{k}_prod.db says {v}"
                                   for k, v in sorted(got.items()))
                alerts.append(
                    f"FORK: {who} balance disagrees across databases -- "
                    f"{detail}. Tip equality is not state equality; do not "
                    f"transact.")
            else:
                log("INFO", f"{who} balance agrees across "
                            f"{len(got)} dbs ({'/'.join(sorted(got))}): {lo}")

    # P12: full amplitude the first time and on any change, a roll-up every
    # ROLL_UP_EVERY rounds, and a CLEARED line when a condition goes away.
    # `alerts` is returned unchanged -- --once and every caller still sees them
    # all; only what reaches the LOG is adapted.
    live = set()
    for a in alerts:
        key = f"alert:{a[:80]}"
        live.add(key)
        rendered = _adapt_alert.observe(key, a)
        if rendered:
            log("ALERT", rendered)
            action, detail = push_alert(rendered)
            if action == "disabled" and not _push_state["announced"]:
                _push_state["announced"] = True
                log("INFO", "alert push is off (set COVENANT_ALERT_PUSH_URL "
                            "to send surviving alerts to a phone)")
            elif action == "failed":
                log("INFO", f"alert push failed ({detail}) -- logged only")
            elif action == "rate-limited" and not _push_state["clipped"]:
                _push_state["clipped"] = True
                log("INFO", f"alert push rate limit hit ({detail}) -- further "
                            f"alerts this hour are logged, not pushed")
    for cleared in _adapt_alert.sweep(live):
        log("INFO", cleared)
    if not alerts:
        rendered = _adapt_info.observe("summary", "all checks passed")
        if rendered:
            log("INFO", rendered)
    else:
        _adapt_info._state.pop("summary", None)

    # SELF-EVALUATION: every SELF_EVAL_EVERY rounds, one verdict block from
    # this pass's own readings -- see the section above one_pass for the
    # boundary. Logged unconditionally (it is at most hourly, and a verdict
    # that Adaptation could mute would defeat the ledger's purpose).
    _self_eval["round"] += 1
    _self_eval_persist()          # before the write, so a kill between the two
                                  # costs a block, never a repeated one
    if SELF_EVAL_EVERY > 0 and _self_eval["round"] % SELF_EVAL_EVERY == 0:
        block, overall = self_evaluation(
            states, dict(_topo_prev), _student_state(),
            list(s_alerts), list(alerts),
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            round_no=_self_eval["round"], rate_limited=rate_limited,
            offline=offline_readings())
        if _self_eval_write(block):
            log("INFO", f"self-evaluation: {overall} "
                        f"(round {_self_eval['round']}) -> {SELF_EVAL_PATH}")
    return alerts


def _port_listening(port, host="127.0.0.1"):
    import socket
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def tend_seal_service(spawn=None):
    """Start the Sentinel-Witness seal service if nothing listens on 8433.
    The Startup-folder copy needed administrator hands; this guard runs every
    two minutes under the scheduler regardless, so it is the layer that makes
    the service survive a reboot. Returns 'up', 'started' or 'failed: ...'."""
    if _port_listening(8433):
        return "up"
    try:
        if spawn is None:
            pyw = os.path.join(HERE, ".venv", "Scripts", "pythonw.exe")
            if not os.path.exists(pyw):
                pyw = sys.executable
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
            subprocess.Popen([pyw, os.path.join(HERE, "ops", "hidden_task.py"),
                              "sentinel_witness/seal_service.py"], cwd=HERE, creationflags=flags)
        else:
            spawn()
        return "started"
    except Exception as e:                                   # noqa: BLE001
        return "failed: %s: %s" % (type(e).__name__, e)


def tend_pending(port=5000, http=None, signer=None):
    """Mine whatever is pending on node A. The trader mines its own seals; the
    seal service's and any other sender's waited for the next trader cycle,
    and a node restart discards them (A53). Operator-signed with the node key,
    exactly as covenant_trader.seal_decision and covenant_client.cmd_mine do.
    Returns a one-line result; never raises."""
    try:
        import json as _json
        import urllib.request
        if http is None:
            with urllib.request.urlopen("http://127.0.0.1:%d/health" % port, timeout=8) as r:
                h = _json.loads(r.read().decode())
        else:
            h = http("GET", port, "/health", None)[1]
        pending = int(h.get("pending_transactions", 0))
        if pending <= 0:
            return "nothing pending"
        if signer is None:
            import covenant_client as cc
            import covenant_unified_v8 as cov
            import covenant_trader as T
            cfg = T.load_config()
            keypath = os.path.join(HERE, cfg.get("node_key", "covenant_A.db.key"))
            sk, pem = cc.load_key(keypath), cc.pub_of_key(keypath)
            hdrs = cov.sign_operator_request(sk, pem, "POST", "/mine", b"{}")
            st, resp = cc.http("POST", port, "/mine", {}, headers=hdrs, timeout=310)
        else:
            st, resp = signer(pending)
        return "mined %d pending -> HTTP %s %s" % (pending, st, _json.dumps(resp)[:80])
    except Exception as e:                                   # noqa: BLE001
        return "mine failed: %s: %s" % (type(e).__name__, str(e)[:80])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=60)
    a = ap.parse_args()
    if a.once:
        sys.exit(1 if one_pass(strict=True) else 0)
    # P16 (2026-08-24). SAY HOW LONG SILENCE IS ALLOWED TO BE.
    #
    # Adaptation (P12) is right, and it has a cost nobody wrote down: the
    # 3,448 redundant ALERTs it removes were noise, but they were also a
    # HEARTBEAT. A flooding watchdog is provably alive; a quiet one is not,
    # and the difference between "quiet because healthy" and "quiet because
    # dead" is invisible in the file.
    #
    # It is not hypothetical. At 2026-08-24T08:03:12Z the previous watchdog
    # process stopped, and the LAST LINE IT EVER WROTE says both nodes are
    # healthy. A monitor that dies silently reports health for ever.
    #
    # The roll-up already guarantees a line every ROLL_UP_EVERY rounds. What
    # was missing is that a reader had no way to know that, so no reader could
    # judge a gap. Now the first line states the contract, and every line
    # carries a UTC timestamp -- so "the last line is N seconds old against a
    # stated floor" is a fact anyone can check, including a script
    # (test_c2_watchdog_live.py's gap_check() is that script, run live).
    #
    # CORRECTED 2026-08-29 (M42's family): this comment used to claim "every
    # line carries the round number". No line ever did -- only the roll-up's
    # "[unchanged, N rounds]" and CLEARED's "after N round(s)" carry counts --
    # and the suite's G3 check now pins that. The claim was not only stale, it
    # was structurally impossible as written: a per-line round number changes
    # every line's TEXT, and Adaptation keys on text, so it would have
    # re-emitted every adapted condition every round and undone P12 -- unless
    # kept out of the observe() key. Gap detection is timestamp-based, on
    # purpose.
    # C3 (2026-08-29): name this process so the guard that heals THIS layer
    # (covenant_watchdog_guard.py, run by the OS scheduler) can tell a dead
    # watchdog from a wedged one. A stale pid file is harmless -- the guard
    # verifies the PID is a live python before believing it; what would not
    # be harmless is a guard with no pid to check spawning a second watchdog
    # beside a slow one, doubling every restart the first might still make.
    try:
        with open(os.path.join(LOGDIR, "watchdog.pid"), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write(str(os.getpid()) + "\n")
    except OSError as e:
        log("INFO", f"could not write watchdog.pid ({e}) -- the guard will "
                    f"treat a long gap as unverifiable and report, not act")
    log("INFO", f"watchdog started, every {a.interval}s, log {LOGFILE}")
    # CORRECTED within the hour, against my own first wording. That said the
    # guarantee was "one line every 30 rounds (~30 min)", which is TRUE and far
    # too loose: the balance check at the end of one_pass logs unconditionally
    # whenever both databases and a key file are present, so in THIS deployment
    # the log is never quiet for more than one round. Stating the weak floor
    # would have taught a reader to tolerate a watchdog that had been dead for
    # 29 minutes. Both numbers, and which one applies, or the line is useless.
    _dbs = all(os.path.exists(os.path.join(HERE, n["db"])) for n in NODES) and \
        os.path.exists(os.path.join(HERE, "nodeA_prod.db.key"))
    log("INFO", f"watchdog source {SELF_SOURCE_SHA12} -- SILENCE CONTRACT: "
                f"guaranteed floor is one line every {ROLL_UP_EVERY} rounds "
                f"(~{ROLL_UP_EVERY * a.interval // 60} min) from the roll-up; "
                + (f"and both databases are present, so the balance check logs "
                   f"EVERY round -- expect a line at least every {a.interval}s."
                   if _dbs else
                   f"the databases are NOT both present, so the roll-up is the "
                   f"only floor -- expect a line at least every "
                   f"{ROLL_UP_EVERY * a.interval // 60} min.")
                + " A LONGER GAP THAN THAT MEANS THIS PROCESS IS DEAD, not "
                  "that all is well.")
    # Daemon only, and only here: --once exits at the branch above without
    # ever reaching this, so a one-shot run neither resumes nor persists.
    _self_eval["persist"] = True
    _resumed = _self_eval_resume()
    if _resumed:
        _next = ((_resumed // SELF_EVAL_EVERY) + 1) * SELF_EVAL_EVERY \
            if SELF_EVAL_EVERY > 0 else 0
        log("INFO", f"self-evaluation: resumed at round {_resumed}, next block "
                    f"at round {_next} -- the count now survives the restarts "
                    f"covenant_highway.py schedules and the guard performs")
    while True:
        try:
            one_pass()
        except Exception as e:                              # noqa: BLE001
            log("ERROR", f"watchdog pass failed: {type(e).__name__}: {e}")
        time.sleep(a.interval)


if __name__ == "__main__":
    main()
