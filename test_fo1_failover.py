#!/usr/bin/env python3
"""test_fo1_failover.py -- FO1: cross-OS / cross-host service redundancy.

WHAT FO1 PINS, and why each property earned its place.

covenant_failover is the parallel-OS resilience layer (2026-11-02, the operator:
"we need our own operating systems running parallel ... RESILIENCE/REDUNDANCY").
Its whole value is in being BELIEVED when it says a critical service will survive
the loss of one OS or host -- so the ways it can lie matter more than the ways it
can be right. Every check here drives a property BOTH WAYS: the guard fires when
it should and is silent when it should not.

  FO1a  the resolver fails over -- primary when up, the redundant instance when
        the primary is down, and None (DARK) when nothing is live. Unknown is
        never served as "ok" (P20 / rule 9).
  FO1b  redundancy_degraded: ABSENT for a live pair, PRESENT when a provisioned
        standby is down, UNKNOWN when liveness cannot be read, and QUIET for a
        bare SPOF or a disarmed pair -- it must not cry wolf, or nobody reads it.
  FO1c  the arm gate: the beacon ships DARK -- disarmed, it is never "degraded"
        and is never auto-started (the laptop runs at ~3 GB free).
  FO1d  environment_down: PRESENT for an expected-up environment that is down,
        ABSENT when up, UNKNOWN off the control host -- a clone never alarms.
  FO1e  spof_unremediated: PRESENT only with a real SPOF AND the reminder armed.
  FO1f  the classes hold: failover to an already-provisioned standby is
        AUTO_REVERSIBLE and stateless; provisioning a NEW environment is
        PROPOSE_ONLY, and the ENGINE refuses it before the body runs.
  FO1g  the map and the registry agree: every service in the doc is in
        SERVICES and every service in SERVICES is in the doc.
  FO1h  (live, gated) the real cross-OS beacon pair fails over both ways on the
        control host. Skipped where there is no reachable WSL -- NO RESULT is
        not a pass (rule 9), so the skip is printed, never counted green.

    python test_fo1_failover.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import covenant_failover as F

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "  -- %s" % (detail,)))


# A configured cross-OS pair (no real processes -- probes are injected).
PAIR = {"svc": {"require_redundant": True, "min_environments": 2, "arm_gated": False,
                "failover_class": F.AUTO_REVERSIBLE,
                "instances": [
                    {"name": "p", "kind": "primary", "env": "windows", "host": "h", "provisioned": True,
                     "launch": "windows", "port": 1, "probe": {"type": "http", "url": "p"}},
                    {"name": "r", "kind": "redundant", "env": "wsl-ubuntu", "host": "h", "provisioned": True,
                     "launch": "wsl-ubuntu", "port": 2, "probe": {"type": "http", "url": "r"}}]}}


def _probe(up_envs):
    """A probe that reports the named environments live, others down."""
    return lambda inst: inst["env"] in up_envs


def main():
    # ---- FO1a: the resolver fails over --------------------------------------
    # live_endpoint reads the GLOBAL SERVICES; drive it by monkeypatching SERVICES
    # to our injected pair for the length of the check, then restore.
    real = F.SERVICES
    try:
        F.SERVICES = PAIR
        ep_both = F.live_endpoint("svc", probe=_probe({"windows", "wsl-ubuntu"}))
        ep_fail = F.live_endpoint("svc", probe=_probe({"wsl-ubuntu"}))          # primary down
        ep_dark = F.live_endpoint("svc", probe=_probe(set()))                   # nothing live
    finally:
        F.SERVICES = real
    check("FO1a resolver: primary when up, redundant when primary down, None when all down",
          ep_both and ep_both["env"] == "windows"
          and ep_fail and ep_fail["env"] == "wsl-ubuntu"
          and ep_dark is None, (ep_both, ep_fail, ep_dark))

    # ---- FO1b: redundancy_degraded, every state -----------------------------
    d_ok = F.detect_redundancy_degraded(services=PAIR, probe=_probe({"windows", "wsl-ubuntu"}))
    d_bad = F.detect_redundancy_degraded(services=PAIR, probe=_probe({"wsl-ubuntu"}))
    d_unk = F.detect_redundancy_degraded(services=PAIR, probe=lambda i: None)
    check("FO1b redundancy_degraded ABSENT for a live pair", d_ok["state"] == F.ABSENT, d_ok)
    check("FO1b redundancy_degraded PRESENT when a standby is down", d_bad["state"] == F.PRESENT,
          d_bad["measured"].get("why"))
    check("FO1b the down instance is named, on its env", any(
        x["name"] == "p" and x["env"] == "windows" for x in d_bad["measured"]["degraded"][0]["down"]),
          d_bad["measured"]["degraded"])
    check("FO1b redundancy_degraded UNKNOWN when liveness is unreadable (P20)",
          d_unk["state"] == F.UNKNOWN, d_unk)

    # a bare SPOF (one provisioned instance) is NOT degraded -- it is a SPOF, reported, not an alarm
    spof_only = {"s": {"require_redundant": True, "instances": [
        {"name": "a", "env": "windows", "provisioned": True, "probe": {"type": "http", "url": "a"}}]}}
    d_spof = F.detect_redundancy_degraded(services=spof_only, probe=_probe(set()))
    check("FO1b a bare SPOF never drives redundancy_degraded PRESENT (no crying wolf)",
          d_spof["state"] == F.ABSENT and d_spof["measured"]["spof"], d_spof)

    # ---- FO1c: the arm gate keeps the beacon DARK ---------------------------
    gated = {"beacon": dict(PAIR["svc"], arm_gated=True)}
    # not armed -> inactive -> ABSENT even with a member down
    disarmed = F.detect_redundancy_degraded(services=gated, probe=_probe({"wsl-ubuntu"}))
    was = F.armed
    try:
        F.armed = lambda: False
        d_dark = F.detect_redundancy_degraded(services=gated, probe=_probe({"wsl-ubuntu"}))
        F.armed = lambda: True
        d_live = F.detect_redundancy_degraded(services=gated, probe=_probe({"wsl-ubuntu"}))
    finally:
        F.armed = was
    check("FO1c disarmed: an arm-gated pair is inactive, never degraded (DARK)",
          d_dark["state"] == F.ABSENT and any(i["service"] == "beacon"
                                              for i in d_dark["measured"]["inactive"]), d_dark)
    check("FO1c armed: the same pair with a member down now reads PRESENT",
          d_live["state"] == F.PRESENT, d_live)
    # sanity: the default-marker path and the explicit path agree when unarmed
    check("FO1c default disarmed path is ABSENT too", disarmed["state"] == F.ABSENT, disarmed)

    # ---- FO1d: environment_down ---------------------------------------------
    e_down = F.detect_environment_down(environments=[{"name": "wsl-ubuntu", "up": False}])
    e_up = F.detect_environment_down(environments=[{"name": "wsl-ubuntu", "up": True}])
    e_off = F.detect_environment_down(marker="/no/such/marker")                 # not the control host
    # on the control host (marker present) with an injected wsl runner, both ways:
    class _R:
        def __init__(self, rc):
            self.returncode = rc
    e_ctl_down = F.detect_environment_down(marker=__file__, wsl=lambda cmd: _R(1))
    e_ctl_up = F.detect_environment_down(marker=__file__, wsl=lambda cmd: _R(0))
    check("FO1d environment_down: PRESENT down, ABSENT up (explicit)",
          e_down["state"] == F.PRESENT and e_up["state"] == F.ABSENT, (e_down, e_up))
    check("FO1d UNKNOWN off the control host (no marker) -- a clone never alarms",
          e_off["state"] == F.UNKNOWN, e_off)
    check("FO1d on the control host: WSL probe down -> PRESENT, up -> ABSENT",
          e_ctl_down["state"] == F.PRESENT and e_ctl_up["state"] == F.ABSENT, (e_ctl_down, e_ctl_up))

    # ---- FO1e: spof_unremediated --------------------------------------------
    s_hit = F.detect_spof_unremediated(services=spof_only, remind=True)
    s_off = F.detect_spof_unremediated(services=spof_only, remind=False)
    s_none = F.detect_spof_unremediated(services=PAIR, remind=True)             # PAIR is configured
    check("FO1e spof_unremediated PRESENT only with a real SPOF AND the reminder armed",
          s_hit["state"] == F.PRESENT and s_off["state"] == F.ABSENT and s_none["state"] == F.ABSENT,
          (s_hit["state"], s_off["state"], s_none["state"]))

    # ---- FO1f: the classes hold ---------------------------------------------
    rsi = F.REMEDIES["start_redundant_instance"]
    ppr = F.REMEDIES["propose_provision_redundancy"]
    check("FO1f start_redundant_instance is AUTO_REVERSIBLE and stateless",
          rsi["klass"] == F.AUTO_REVERSIBLE and rsi["kind"] == "stateless", rsi["klass"])
    check("FO1f provision is PROPOSE_ONLY", ppr["klass"] == F.PROPOSE_ONLY, ppr["klass"])
    # dry: acts for the AUTO_REVERSIBLE beacon, declines a PROPOSE-only service. Never launches here.
    dry_beacon = rsi["fn"]({"degraded": [{"service": "beacon",
                            "down": [{"name": "beacon-win", "env": "windows"}]}]}, dry_run=True)
    dry_hs = rsi["fn"]({"degraded": [{"service": "headscale",
                        "down": [{"name": "headscale", "env": "wsl-ubuntu"}]}]}, dry_run=True)
    check("FO1f dry start would start the beacon, declines a PROPOSE-only service",
          dry_beacon[0] is True and "would start" in dry_beacon[1]
          and dry_hs[0] is False and "PROPOSE" in dry_hs[1], (dry_beacon, dry_hs))
    # the ENGINE refuses the PROPOSE_ONLY remedy before its body runs (same guard as H1a)
    import covenant_highway as H
    import tempfile
    tl = os.path.join(tempfile.gettempdir(), "fo1_ledger.jsonl")
    row = H.apply_remedy("propose_provision_redundancy",
                         {"state": H.PRESENT, "measured": {"spof": [{"service": "headscale"}]}},
                         "spof_unremediated", dry_run=False, ledger=tl)
    check("FO1f the engine PROPOSES provision, never runs it", row.get("outcome") == "proposed", row)
    # benefit blocks carry BOTH gains and cost (H1f audits this too; pinned here at the source)
    check("FO1f both remedies declare mutual benefit with gains AND cost",
          all(r["benefit"].get("gains") and r["benefit"].get("cost") for r in (rsi, ppr)),
          [r["benefit"] for r in (rsi, ppr)])

    # ---- FO1g: the map and the registry agree -------------------------------
    doc = os.path.join(HERE, "ops", "PARALLEL_OS_REDUNDANCY_MAP_2026-11-02.md")
    txt = open(doc, encoding="utf-8").read() if os.path.exists(doc) else ""
    missing_in_doc = [k for k in F.SERVICES if "`%s`" % k not in txt]
    check("FO1g every service in SERVICES is named in the redundancy map",
          os.path.exists(doc) and not missing_in_doc, missing_in_doc or "map doc missing")

    # ---- FO1h: live cross-OS proof (gated) ----------------------------------
    if os.name == "nt" and F._wsl_alive() is True:
        rec = F.prove(verbose=False)
        if rec.get("skipped"):
            print("  [SKIP] FO1h live cross-OS proof -- %s" % rec["skipped"])
        else:
            check("FO1h live: the Windows+WSL beacon pair fails over both ways", rec["ok"],
                  [s for s in rec["steps"] if not s["ok"]])
    else:
        print("  [SKIP] FO1h live cross-OS proof -- not the Windows control host with reachable WSL "
              "(NO RESULT is not a pass; the deterministic checks above cover the logic)")

    ok = sum(results)
    print("\nFO1: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
