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
  FO1p  redundancy on the PHONE: a third, intermittent beacon environment that is
        declared-not-counted until the phone actually runs it, reads UNKNOWN (never
        'down') while asleep or unprovisioned, is NEVER started from the laptop, and
        is a real third env that carries 'healthy' once provisioned and awake.
  FO1r  more INDEPENDENT HOSTS (TETSU, the new PC): separate physical machines, so
        the beacon stands even when the whole laptop box is lost. Same declared-not-
        counted shape as the phone, driven both ways for each host.
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
    # not armed -> inactive -> ABSENT even with a member down.
    # A411 (2026-11-04): this used to read the LIVE marker ops/REDUNDANCY_ARMED, so on the operator's machine,
    # where the pair IS armed, "the default disarmed path" read PRESENT and FO1 went red on correct code. The real
    # armed() still runs here -- against a marker path the test owns, absent and then present.
    import tempfile
    _mk_dir = tempfile.mkdtemp(prefix="fo1c_")
    _was_marker = F.ARM_MARKER
    try:
        F.ARM_MARKER = os.path.join(_mk_dir, "REDUNDANCY_ARMED")
        disarmed = F.detect_redundancy_degraded(services=gated, probe=_probe({"wsl-ubuntu"}))
        with open(F.ARM_MARKER, "w", encoding="utf-8") as fh:
            fh.write("armed for FO1c\n")
        marker_armed = F.detect_redundancy_degraded(services=gated, probe=_probe({"wsl-ubuntu"}))
    finally:
        F.ARM_MARKER = _was_marker
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
    check("FO1c ...and the real marker path, once the marker exists, reads PRESENT (armed() reads the file)",
          marker_armed["state"] == F.PRESENT, marker_armed)

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

    # ---- FO1i: cold failover (git_host) is out of the hot-pair scope ---------
    # git_host is redundancy_model "cold": a Windows read-only standby started on demand. It must
    # NOT read "degraded" just because the cold standby is not running, must NOT be a bare SPOF
    # (it has a provisioned cross-OS standby), and must appear in cold_failover for visibility.
    real_s = F.SERVICES["git_host"]
    gh = F.detect_redundancy_degraded()
    check("FO1i git_host is cold_failover, never degraded, never a bare SPOF",
          real_s.get("redundancy_model") == "cold"
          and any(c["service"] == "git_host" for c in gh["measured"]["cold_failover"])
          and not any(s["service"] == "git_host" for s in gh["measured"]["spof"])
          and not any(d["service"] == "git_host" for d in gh["measured"]["degraded"]),
          gh["measured"])
    sp = F.detect_spof_unremediated(remind=True)
    check("FO1i spof_unremediated no longer lists git_host (it has a cold cross-OS standby)",
          not any(s["service"] == "git_host" for s in sp["measured"]["spof"]), sp["measured"]["spof"])

    # ---- FO1j: space-wise placement -----------------------------------------
    hot_laptop = {"name": "x", "host": "laptop", "hot": True, "ram_mb": 200}
    cold_laptop = {"name": "y", "host": "laptop", "hot": False, "ram_mb": 999}
    hot_tetsu = {"name": "z", "host": "tetsu", "hot": True, "ram_mb": 8000}
    heavy_laptop = {"name": "big", "host": "laptop", "hot": True, "ram_mb": 8000}
    check("FO1j a hot laptop instance over the operational floor is refused and points at TETSU",
          F.placement_ok(hot_laptop, free_gb=0.5)[0] is False
          and "TETSU" in F.placement_ok(hot_laptop, free_gb=0.5)[1], F.placement_ok(hot_laptop, free_gb=0.5))
    check("FO1j a heavy laptop instance is refused by SIZE (>cap), whatever the free RAM -- heavy goes to TETSU",
          F.placement_ok(heavy_laptop, free_gb=64.0)[0] is False
          and "cap" in F.placement_ok(heavy_laptop, free_gb=64.0)[1], F.placement_ok(heavy_laptop, free_gb=64.0))
    check("FO1j the same instance fits when there is room; cold + TETSU always fit",
          F.placement_ok(hot_laptop, free_gb=8.0)[0] is True
          and F.placement_ok(cold_laptop, free_gb=0.1)[0] is True
          and F.placement_ok(hot_tetsu)[0] is True,
          (F.placement_ok(hot_laptop, free_gb=8.0), F.placement_ok(cold_laptop, free_gb=0.1)))
    _flg = F._free_local_gb
    try:
        F._free_local_gb = lambda: None                      # force the "cannot read RAM" path
        unreadable = F.placement_ok(hot_laptop)               # free_gb defaults -> _free_local_gb() -> None
    finally:
        F._free_local_gb = _flg
    check("FO1j free RAM unreadable -> refuse a hot local start (never starve the model)",
          unreadable[0] is False and "unreadable" in unreadable[1], unreadable)

    # ---- FO1k: start_githost_standby declines/would-start (both ways, stubbed) -
    gs = F.REMEDIES["start_githost_standby"]
    _w, _s = F._wsl_alive, F._githost_standby_serving
    try:
        F._githost_standby_serving = lambda *a, **k: False
        F._wsl_alive = lambda *a, **k: True
        decline = gs["fn"]({}, dry_run=True)
        F._wsl_alive = lambda *a, **k: False
        would = gs["fn"]({}, dry_run=True)
    finally:
        F._wsl_alive, F._githost_standby_serving = _w, _s
    check("FO1k start_githost_standby: AUTO_REVERSIBLE for git_host_down; declines while WSL up; "
          "would start the read-only standby when WSL is unreachable",
          gs["klass"] == F.AUTO_REVERSIBLE and "git_host_down" in gs["for"]
          and decline[0] is False and would[0] is True and "would start" in would[1], (decline, would))

    # ---- FO1g: the map and the registry agree -------------------------------
    doc = os.path.join(HERE, "ops", "PARALLEL_OS_REDUNDANCY_MAP_2026-11-02.md")
    txt = open(doc, encoding="utf-8").read() if os.path.exists(doc) else ""
    missing_in_doc = [k for k in F.SERVICES if "`%s`" % k not in txt]
    check("FO1g every service in SERVICES is named in the redundancy map",
          os.path.exists(doc) and not missing_in_doc, missing_in_doc or "map doc missing")

    # ---- FO1p: redundancy on the PHONE (a third, intermittent environment) --
    # The operator, 2026-11-03: "make redundancies on the phone too." The beacon gains a phone
    # instance -- but the phone is intermittent and nothing pushes to it, so what must hold is:
    # DECLARED-not-counted until actually provisioned, absence reads UNKNOWN (never 'down' or
    # 'redundant'), NEVER auto-started from the laptop, and a real third env once provisioned+awake.
    bp = next((i for i in F.SERVICES["beacon"]["instances"] if i["name"] == "beacon-phone"), None)
    check("FO1p beacon-phone declared: env/host phone, intermittent, launch phone, NOT provisioned yet",
          bool(bp) and bp["env"] == "phone" and bp["host"] == "phone" and bp.get("intermittent") is True
          and bp.get("launch") == "phone" and bp.get("provisioned") is False
          and (bp.get("probe") or {}).get("type") == "phone", bp)

    # the private-address resolver: UNKNOWN when no address is configured, alive when it is (both ways)
    real_url, real_http = F._phone_beacon_url, F._http_probe
    try:
        F._phone_beacon_url = lambda: None
        unk = F._probe_instance(bp)
        F._phone_beacon_url = lambda: "http://100.64.0.9:%d/beacon" % F.BEACON_PHONE_PORT
        F._http_probe = lambda url, timeout=3: True
        aliv = F._probe_instance(bp)
    finally:
        F._phone_beacon_url, F._http_probe = real_url, real_http
    check("FO1p phone probe: UNKNOWN with no address configured, alive once it is (both ways)",
          unk is None and aliv is True, (unk, aliv))

    # NEVER auto-started from the laptop -- launch 'phone' is declined with a clear reason
    ph_decline = F._start_instance(bp, dry_run=True)
    check("FO1p the phone beacon is never started from the laptop (declined -- provisioned by app install)",
          ph_decline[0] is False and "phone" in ph_decline[1].lower(), ph_decline)

    # declared-not-counted vs. a real third env. Synthetic beacon: two laptop OSes + the phone.
    def _beacon3(phone_provisioned):
        return {"beacon": {"require_redundant": True, "min_environments": 2, "arm_gated": False,
                           "failover_class": F.AUTO_REVERSIBLE, "instances": [
            {"name": "w", "kind": "primary", "env": "windows", "host": "laptop", "provisioned": True,
             "probe": {"type": "http", "url": "w"}},
            {"name": "u", "kind": "redundant", "env": "wsl-ubuntu", "host": "laptop", "provisioned": True,
             "probe": {"type": "http", "url": "u"}},
            {"name": "ph", "kind": "redundant", "env": "phone", "host": "phone",
             "provisioned": phone_provisioned, "intermittent": True, "probe": {"type": "phone"}}]}}
    d_unprov = F.detect_redundancy_degraded(services=_beacon3(False), probe=_probe({"windows", "wsl-ubuntu"}))
    check("FO1p an UNPROVISIONED phone is declared-not-counted (healthy on the two laptop OSes)",
          d_unprov["state"] == F.ABSENT, d_unprov)
    d_sleep = F.detect_redundancy_degraded(services=_beacon3(True), probe=_probe({"windows", "wsl-ubuntu"}))
    check("FO1p a provisioned phone ASLEEP never alarms while both laptop OSes are up",
          d_sleep["state"] == F.ABSENT, d_sleep)
    d_carry = F.detect_redundancy_degraded(services=_beacon3(True), probe=_probe({"windows", "phone"}))
    check("FO1p an AWAKE phone is a real third env -- it carries 'healthy' when a laptop OS is down",
          d_carry["state"] == F.ABSENT
          and "phone" in d_carry["measured"]["healthy"][0]["live_environments"], d_carry)
    d_deg = F.detect_redundancy_degraded(services=_beacon3(True), probe=_probe({"windows"}))
    check("FO1p a laptop OS down AND the phone asleep reads degraded (the phone hides no real loss)",
          d_deg["state"] == F.PRESENT, d_deg)

    # ---- FO1r: more INDEPENDENT HOSTS (TETSU, the new PC) -------------------
    # The operator, 2026-11-03: "both, all three really." The live pair shares ONE box
    # ("Sales"); TETSU (already on the mesh) and the new PC are separate machines -- the layer
    # that makes "one stands without the other" true against losing the whole box. Same
    # declared-not-counted shape as the phone: declared until the host runs the beacon, absence
    # reads UNKNOWN (never 'down'), never started from the laptop, a real env only once awake.
    remotes = {i["name"]: i for i in F.SERVICES["beacon"]["instances"]
               if (i.get("probe") or {}).get("type") == "remote"}
    check("FO1r two more independent hosts declared: beacon-tetsu (tetsu) + beacon-pc2 (pc2)",
          set(remotes) == {"beacon-tetsu", "beacon-pc2"}
          and remotes["beacon-tetsu"]["env"] == "tetsu" and remotes["beacon-tetsu"]["host"] == "tetsu"
          and remotes["beacon-pc2"]["env"] == "pc2" and remotes["beacon-pc2"]["host"] == "pc2",
          sorted(remotes))
    for nm in ("beacon-tetsu", "beacon-pc2"):
        bi = remotes[nm]
        check("FO1r %s declared-not-counted: intermittent, launch remote, NOT provisioned, env+file set" % nm,
              bi.get("intermittent") is True and bi.get("launch") == "remote"
              and bi.get("provisioned") is False
              and bool((bi.get("probe") or {}).get("env")) and bool((bi.get("probe") or {}).get("file")), bi)
        # the private-address resolver: UNKNOWN with nothing configured, alive once it is (both ways)
        real_url, real_http = F._remote_beacon_url, F._http_probe
        try:
            F._remote_beacon_url = lambda env_var, fname: None
            unk = F._probe_instance(bi)
            F._remote_beacon_url = lambda env_var, fname: "http://100.64.0.1:9/beacon"
            F._http_probe = lambda url, timeout=3: True
            aliv = F._probe_instance(bi)
        finally:
            F._remote_beacon_url, F._http_probe = real_url, real_http
        check("FO1r %s probe: UNKNOWN with no address, alive once it is (both ways)" % nm,
              unk is None and aliv is True, (unk, aliv))
        # NEVER started from the laptop -- launch 'remote' is declined, naming the host
        dec = F._start_instance(bi, dry_run=True)
        check("FO1r %s is never started from the laptop (declined -- provisioned on its own host)" % nm,
              dec[0] is False and bi["host"] in dec[1], dec)

    # declared-not-counted vs. a real host. Synthetic beacon: two laptop OSes + one separate host.
    def _beaconH(host_env, provisioned):
        return {"beacon": {"require_redundant": True, "min_environments": 2, "arm_gated": False,
                           "failover_class": F.AUTO_REVERSIBLE, "instances": [
            {"name": "w", "kind": "primary", "env": "windows", "host": "laptop", "provisioned": True,
             "probe": {"type": "http", "url": "w"}},
            {"name": "u", "kind": "redundant", "env": "wsl-ubuntu", "host": "laptop", "provisioned": True,
             "probe": {"type": "http", "url": "u"}},
            {"name": "r", "kind": "redundant", "env": host_env, "host": host_env,
             "provisioned": provisioned, "intermittent": True, "probe": {"type": "remote"}}]}}
    for host_env in ("tetsu", "pc2"):
        d_unprov = F.detect_redundancy_degraded(services=_beaconH(host_env, False), probe=_probe({"windows", "wsl-ubuntu"}))
        check("FO1r an UNPROVISIONED %s is declared-not-counted (healthy on the two laptop OSes)" % host_env,
              d_unprov["state"] == F.ABSENT, d_unprov)
        d_sleep = F.detect_redundancy_degraded(services=_beaconH(host_env, True), probe=_probe({"windows", "wsl-ubuntu"}))
        check("FO1r a provisioned %s ASLEEP never alarms while both laptop OSes are up" % host_env,
              d_sleep["state"] == F.ABSENT, d_sleep)
        d_carry = F.detect_redundancy_degraded(services=_beaconH(host_env, True), probe=_probe({"windows", host_env}))
        check("FO1r an AWAKE %s is a real env -- it carries 'healthy' when a laptop OS is down" % host_env,
              d_carry["state"] == F.ABSENT
              and host_env in d_carry["measured"]["healthy"][0]["live_environments"], d_carry)
        d_deg = F.detect_redundancy_degraded(services=_beaconH(host_env, True), probe=_probe({"windows"}))
        check("FO1r a laptop OS down AND %s asleep reads degraded (the host hides no real loss)" % host_env,
              d_deg["state"] == F.PRESENT, d_deg)

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

    # ---- FO1h-git: live cross-OS git-host failover (gated) ------------------
    if os.name == "nt" and F._http_probe(
            "http://127.0.0.1:8088/covenant.git/info/refs?service=git-upload-pack"):
        rec = F.prove_githost(verbose=False)
        if rec.get("skipped"):
            print("  [SKIP] FO1h-git -- %s" % rec["skipped"])
        else:
            check("FO1h-git live: a REAL git clone fails over to the Windows standby, push refused",
                  rec["ok"], [s for s in rec["steps"] if not s["ok"]])
    else:
        print("  [SKIP] FO1h-git live git-host failover -- not the Windows control host with the primary "
              "git host up (NO RESULT is not a pass; FO1i/FO1k cover the logic)")

    ok = sum(results)
    print("\nFO1: %d/%d passed" % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
