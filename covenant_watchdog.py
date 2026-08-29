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
  because two of the four inputs to `degraded` are false positives:

    keyless      (line 6142) tests for ANTHROPIC/OPENAI/GOOGLE_API_KEY in the
                 environment. It never checks whether a judge is reachable or
                 working, so a functioning local judge always trips it.
    own_genesis  (line 6144) tests WHO MINTED the genesis, not whether this
                 node minted it. Adopting a genesis your own founder key
                 created sets the flag -- and the node then converges fine.

  A monitor that pages on those two would page forever and be muted within a
  day, taking `insecure` and `crisis_mode` -- the two that are real -- with
  it. So they are recorded at INFO and never alert. If you fix the health
  reporting upstream, delete FALSE_POSITIVE_WARNINGS below.

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
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
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
NODES = [
    {"id": "A", "port": 5000, "db": "nodeA_prod.db", "key": "nodeA_prod.db.key",
     "peers": "127.0.0.1:5021"},
    {"id": "B", "port": 5020, "db": "nodeB_prod.db", "key": "nodeB_prod.db.key",
     "peers": "127.0.0.1:5001,127.0.0.1:5061"},
    {"id": "C", "port": 5060, "db": "nodeC_prod.db", "key": "nodeC_prod.db.key",
     "peers": "127.0.0.1:5021"},
]

# Documented false positives on a correct keyless single-founder setup.
# Recorded, never alerted. See the module docstring for the line numbers.
FALSE_POSITIVE_WARNINGS = (
    "ethics gate has no provider key",
    "node minted its OWN genesis",
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


# --------------------------------------------------------------------------
# P15 (2026-08-28). THE FOURTH LONG-LIVED PROCESS IS THE JUDGE ITSELF.
#
# P11 named the nodes' identity, P14 named the watchdog's own. That left
# exactly one long-lived process unwatched, and it is the one INSIDE
# consensus: ollama. This file mentioned ollama twice, both in start_node --
# it LAUNCHES against the judge and never PROBES it. Nothing anywhere read
# /api/tags or /api/ps, so nothing could say which model answers the ethics
# gate, whether the served tag still resolves to the same digest, or whether
# the endpoint is up at all. Re-pull or re-tag the model and the gate's
# verdicts change with no surface in this system saying anything changed.
#
# Two probes, both GET, both read-only:
#   /api/tags  -> which models this endpoint serves, each with its digest.
#                 The digest is the identity: same tag, new digest means the
#                 gate's behaviour may have changed.
#   /api/ps    -> which model is loaded right now. Recorded in state for a
#                 reader; deliberately NOT in the log line, because ollama
#                 loads and unloads on demand and a line that flips with that
#                 weather would churn Adaptation (P12: change, not state --
#                 and on-demand loading IS the state working).
#
# What it says, and when:
#   first sight        INFO, identity in full (model@digest, served count)
#   digest change      ALERT once, both digests named, then baseline moves --
#                      an alert that re-fires for ever trains its reader (M34)
#   tag missing        ALERT: the gate's calls will fail, and it fails closed
#   unreachable        ALERT: fail-closed means every transaction refused.
#                      The node's own /health CANNOT say this -- its "no
#                      provider key" warning tests env vars, not the judge
#                      (that is FALSE_POSITIVE_WARNINGS above, and why this
#                      probe asks the judge itself).
#
# Disclosure only. It restarts nothing, blocks nothing, reconfigures nothing
# -- the same boundary P12, P14 and B2 draw, for the same reason (M31/M47:
# sensing may inform disclosure, never behaviour).
# --------------------------------------------------------------------------
JUDGE_URL = os.environ.get("COVENANT_LOCAL_JUDGE_URL",
                           "http://127.0.0.1:11434/v1/chat/completions")
JUDGE_MODEL = os.environ.get("COVENANT_LOCAL_JUDGE_MODEL", "qwen3:8b")


def _judge_root(url=None):
    """scheme://host:port of the judge endpoint -- the ollama API root."""
    from urllib.parse import urlsplit
    p = urlsplit(url or JUDGE_URL)
    return f"{p.scheme}://{p.netloc}"


def judge_identity(root=None, timeout=8, opener=None):
    """Probe the judge endpoint. GET only -- a monitor must not be able to
    make the thing it watches do work (no POST, no /api/generate, ever).

    Returns {"reachable", "error", "served" {name: digest12}, "loaded" [names]}.
    Never raises: transport injectable via opener(url)->parsed-json for tests.
    """
    root = (root or _judge_root()).rstrip("/")

    def _get(path):
        if opener is not None:
            return opener(root + path)
        with urllib.request.urlopen(root + path, timeout=timeout) as r:
            return json.loads(r.read().decode())

    ident = {"reachable": False, "error": None, "served": {}, "loaded": []}
    try:
        tags = _get("/api/tags")
    except Exception as e:                                  # noqa: BLE001
        ident["error"] = type(e).__name__
        return ident
    ident["reachable"] = True
    models = tags.get("models") if isinstance(tags, dict) else None
    for m in models if isinstance(models, list) else []:
        if isinstance(m, dict) and m.get("name"):
            ident["served"][str(m["name"])] = str(m.get("digest") or "")[:12]
    try:
        ps = _get("/api/ps")
        pm = ps.get("models") if isinstance(ps, dict) else None
        if isinstance(pm, list):
            ident["loaded"] = sorted(str(m.get("name")) for m in pm
                                     if isinstance(m, dict) and m.get("name"))
    except Exception:                                       # noqa: BLE001
        pass    # /api/ps failing is not /api/tags failing; identity stands
    return ident


def judge_identity_report(ident, prev, expected_model=None, root=None):
    """(alerts, infos, state) for the judge-identity reading. Pure, so it is
    testable: everything it needs arrives as arguments, and it only returns
    text -- it can restart, block and reconfigure nothing.

    prev is the state dict this function returned last round, or {}. An
    OUTAGE keeps the baseline (an unreachable judge is not a changed one);
    a digest change moves the baseline after being said once, so the alert
    appears, then CLEARs, and the log carries the transition (M34).
    """
    expected_model = expected_model or JUDGE_MODEL
    root = root or _judge_root()
    alerts, infos = [], []
    prev = prev if isinstance(prev, dict) else {}

    if not isinstance(ident, dict) or not ident.get("reachable"):
        err = ident.get("error") if isinstance(ident, dict) else None
        alerts.append(
            f"JUDGE UNREACHABLE: the ethics gate's endpoint {root} did not "
            f"answer ({err}) -- the gate fails closed, so every transaction "
            f"will be refused while this holds. The nodes' own /health cannot "
            f"say this: their 'no provider key' warning tests env vars, not "
            f"the judge.")
        return alerts, infos, prev

    served = ident.get("served") if isinstance(ident.get("served"), dict) \
        else {}
    digest = served.get(expected_model) or None
    if digest is None:
        alerts.append(
            f"JUDGE MODEL MISSING: '{expected_model}' is not among the "
            f"model(s) served at {root} ({sorted(served) or 'none'}) -- the "
            f"ethics gate's calls will fail, and the gate fails closed.")

    pd = prev.get("digest")
    if pd and digest and digest != pd:
        alerts.append(
            f"JUDGE MODEL CHANGED: {expected_model} was digest {pd} and is "
            f"now {digest} -- the gate's verdicts may differ and NOTHING in "
            f"the chain records this. If this re-pull or re-tag was not "
            f"yours, treat the change as hostile until explained.")

    infos.append(f"judge: {expected_model}@{digest or 'NOT-SERVED'} -- "
                 f"{len(served)} model(s) served at {root}")

    # A vanished tag keeps the old digest as baseline, so a reappearance
    # under a NEW digest still reads as a change, not a first sight.
    return alerts, infos, {"digest": digest or pd,
                           "served": dict(sorted(served.items())),
                           "loaded": list(ident.get("loaded") or [])}


_judge_prev = {}


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
_self_eval = {"round": 0}

SELF_EVAL_HEADER = (
    "# covenant self-evaluation ledger\n"
    "# For Misha, and all that were lost to injustice.\n"
    "# One block per evaluation: PASS/WARN/FAIL per layer, worst wins.\n"
    "# Written by covenant_watchdog.py (report-only) and by the scheduled\n"
    "# covenant-self-eval task. Append-only; rotates to .prev at 512KB.\n\n")

_RANK = {"PASS": 0, "WARN": 1, "FAIL": 2}


def self_evaluation(states, topo, judge, self_drift, alerts, now_iso,
                    round_no=0):
    """(block, overall) -- every layer, judged from what this pass sensed.

    Pure, the same shape as topology_report and judge_identity_report:
    everything it needs arrives as arguments and it only returns text.
      states     -- node_id -> /health dict or None       (metadata)
      topo       -- node_id -> topology state dict         (mycelium)
      judge      -- the judge-identity baseline state      (metadata)
      self_drift -- P14's alert list for THIS file          (metadata)
      alerts     -- every alert this pass raised
    """
    layers = []

    def layer(name, verdict, detail):
        layers.append((name, verdict, detail))

    up = {k: s for k, s in states.items() if s}
    if not up:
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
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as e:
        return None, f"{type(e).__name__}: {e}"


def balance(db, of_key, timeout=45):
    """Read a balance straight out of a database file. SQLite WAL allows a
    reader while the node holds it open."""
    try:
        p = subprocess.run(
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
    production resumes a chain, it does not rebuild one."""
    env = dict(os.environ)
    env["COVENANT_DB_PATH"] = node["db"]
    env.setdefault("COVENANT_LOCAL_JUDGE_URL",
                   "http://127.0.0.1:11434/v1/chat/completions")
    env.setdefault("COVENANT_LOCAL_JUDGE_MODEL", "qwen3:8b")
    env.setdefault("COVENANT_LOCAL_JUDGE_TIMEOUT", "600")
    env.setdefault("COVENANT_JUDGE_TIMEOUT", "600")
    env["COVENANT_JUDGE_PROVIDERS"] = "local"
    env.pop("COVENANT_INSECURE_MOCK_JUDGE", None)
    os.makedirs(LOGDIR, exist_ok=True)
    out = open(os.path.join(LOGDIR, f"node{node['id']}.log"), "a",
               encoding="utf-8", errors="replace")
    cmd = [sys.executable, "run_with_ollama_judge.py",
           "--port", str(node["port"]), "--node-id", node["id"],
           "--genesis", "genesis.json", "--peers", node["peers"]]
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    if os.name == "nt":
        flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen(cmd, cwd=HERE, env=env, stdout=out, stderr=out,
                     creationflags=flags)
    log("WARN", f"node {node['id']} restarted -> logs/node{node['id']}.log")


# ------------------------------------------------------------------- pass --
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

    for n in NODES:
        h, err = health(n["port"])
        states[n["id"]] = h
        if h is None:
            if strict:
                alerts.append(f"node {n['id']} :{n['port']} unreachable ({err})")
                continue
            _fail_counts[n["id"]] += 1
            log("WARN", f"node {n['id']} :{n['port']} unreachable "
                        f"({_fail_counts[n['id']]}/{FAIL_BEFORE_RESTART}) {err}")
            if _fail_counts[n["id"]] >= FAIL_BEFORE_RESTART:
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
    if not live:
        alerts.append("NO node is reachable -- the chain is not running")
    if len(live) == len(NODES):
        hs = [s.get("chain_height", 0) for s in live]
        if max(hs) - min(hs) > 1:
            alerts.append(f"height gap {hs} -- peers not keeping up")

    drift_alerts, drift_infos = source_drift_report(states, disk_source_sha12())
    s_alerts, s_infos = self_drift_report(
        SELF_SOURCE_SHA12, disk_source_sha12(SELF_SRC))   # P14
    drift_alerts = list(drift_alerts) + s_alerts
    drift_infos = list(drift_infos) + s_infos
    alerts.extend(drift_alerts)
    for line in drift_infos:
        log("INFO", line)

    # P15: the fourth long-lived process -- the judge itself. One probe per
    # pass (all three nodes share one ollama), disclosure only.
    j_alerts, j_infos, _judge_prev["state"] = judge_identity_report(
        judge_identity(), _judge_prev.get("state", {}))
    alerts.extend(j_alerts)
    for line in j_infos:
        rendered = _adapt_info.observe("judge:identity", line)
        if rendered:
            log("INFO", rendered)

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
    if SELF_EVAL_EVERY > 0 and _self_eval["round"] % SELF_EVAL_EVERY == 0:
        block, overall = self_evaluation(
            states, dict(_topo_prev), _judge_prev.get("state", {}),
            list(s_alerts), list(alerts),
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            round_no=_self_eval["round"])
        if _self_eval_write(block):
            log("INFO", f"self-evaluation: {overall} "
                        f"(round {_self_eval['round']}) -> {SELF_EVAL_PATH}")
    return alerts


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
    while True:
        try:
            one_pass()
        except Exception as e:                              # noqa: BLE001
            log("ERROR", f"watchdog pass failed: {type(e).__name__}: {e}")
        time.sleep(a.interval)


if __name__ == "__main__":
    main()
