#!/usr/bin/env python3
"""covenant_failover.py -- cross-OS / cross-host service redundancy for the highway.

OPERATOR, 2026-11-02: "we need our own operating systems running parallel --
Windows, Python, Linux, the whole 9," primary goal RESILIENCE / REDUNDANCY. This
is the OS-layer sibling of the parallel headscale network and takeover
resistance: NO SINGLE OS, HOST, OR DISTRO SHOULD BE A SINGLE POINT OF FAILURE for
a critical fleet service.

WHAT THIS ADDS, AND WHAT IT LEANS ON. covenant_highway.py already senses that a
service is DOWN ON THIS HOST and restarts our own daemon (headscale, git host).
That does nothing when the host, the OS, or the one WSL distro dies entirely.
This module adds the layer above: does a critical service have a LIVE REDUNDANT
INSTANCE on a DIFFERENT OS or host, and is an OS environment the fleet depends on
actually up? Two new senses, one auto-safe repair, one proposal.

  redundancy_degraded   a service that HAS a provisioned redundant instance has
                        lost one -- fewer distinct live environments than it
                        needs. AUTO_REVERSIBLE remedy: start the standby that
                        already exists (same class as restart_headscale).
  environment_down      an OS environment the fleet depends on (the control
                        host's WSL, TETSU) is not answering. ALARM-ONLY: booting
                        or re-provisioning an OS is PROPOSE-only and RAM-heavy,
                        so a person decides (like the takeover guards).
  spof_unremediated     a known single-point-of-failure has no redundancy at all
                        (headscale, git host, the unison feed are laptop-WSL
                        only). PROPOSE_ONLY remedy points at the PROPOSE_LIST.
                        OFF by default (the map already documents the SPOFs; a
                        constant alarm helps no one) -- armed by a marker.

THE FREE-WILL LINE (unchanged, highway's two classes).
  * Failover to an ALREADY-provisioned redundant instance -- starting/routing to
    a standby that EXISTS -- is reversible => AUTO_REVERSIBLE.
  * Provisioning a NEW environment / OS / distro / VM / container installs
    software or changes system state => PROPOSE_ONLY, forever.
  * Keys, private/, holdings, *.key NEVER cross OS environments. The one service
    this module actually provisions (the beacon) serves only non-secret
    liveness/identity.

RAM. The laptop runs at ~3 GB free with a ram_guard holding room for the model
(covenant_model). The only instance this module starts is the stdlib beacon
(a few MB), and it ships DARK: nothing auto-starts until the operator writes
ops/REDUNDANCY_ARMED. Heavy redundancy (a headscale standby, a VM) belongs on
TETSU and is PROPOSE-only.

COMPOSITION. A separate module on purpose, so it does not clobber
covenant_highway.py while the sync-fabric and auto-onboard branches also grow it.
covenant_highway imports this and calls register(DETECTORS, REMEDIES) once, at
import, as its single hook.

USE
    python covenant_failover.py              # sense: redundancy state here
    python covenant_failover.py --map        # the machine-readable service map
    python covenant_failover.py --prove      # live: stand up a cross-OS beacon
                                             #   pair and show failover both ways
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

# String-equal to covenant_highway's constants. Defined here (not imported) so a
# plain `import covenant_failover` never pulls the highway in -- the highway
# imports US, and a cycle at module load is a fragility we do not need.
AUTO_REVERSIBLE = "AUTO_REVERSIBLE"
PROPOSE_ONLY = "PROPOSE_ONLY"
PRESENT = "PRESENT"
ABSENT = "ABSENT"
UNKNOWN = "UNKNOWN"

_NOWIN = 0x08000000 if os.name == "nt" else 0          # CREATE_NO_WINDOW (A203: no console pops up)
_DETACHED = 0x00000008 if os.name == "nt" else 0       # DETACHED_PROCESS: the beacon outlives us

ARM_MARKER = os.path.join(HERE, "ops", "REDUNDANCY_ARMED")
SPOF_REMIND_MARKER = os.path.join(HERE, "ops", "REDUNDANCY_SPOF_REMIND")
BEACON = os.path.join(HERE, "covenant_beacon.py")
BEACON_WIN_PORT = 8771
BEACON_WSL_PORT = 8772
GITHOST_STANDBY = os.path.join(HERE, "covenant_githost_standby.py")
GITHOST_STANDBY_PORT = 8089


# ----------------------------------------------------------------- space-wise placement
#
# The operator, 2026-11-02: "install is fine towards mutual benefit just use space wisely
# between pc laptop n phone for optimization." Placement is the optimization: heavy,
# always-on redundancy goes to TETSU (32 GB headroom); the laptop ("Sales") runs at ~3 GB
# free with a ram_guard holding the model's room, so it carries only LIGHT or COLD standbys;
# the phone is lightest. A HOT instance (always running) is only auto-started on a host where
# it fits; a COLD standby (started on demand, stopped when not needed) is space-free until a
# failover needs it. This encodes "use space wisely" so the engine never starves the model.

HOSTS = {
    # light_cap_mb: the biggest HOT instance this host will auto-start (bigger => provision on TETSU).
    # op_floor_gb: free RAM to leave after starting it, so the host (and the model's loader/ram_guard)
    # stays responsive. A heavy instance is refused by SIZE, which is how "heavy goes to TETSU" is enforced.
    "laptop": {"policy": "light-only", "light_cap_mb": 512, "op_floor_gb": 0.5,
               "note": "RAM-tight (~3 GB free); the model's room is protected -- light or cold only"},
    "tetsu":  {"policy": "heavy-ok",
               "note": "32 GB, RTX 5060 Ti -- the home for heavy, always-on redundant instances and VMs"},
    "phone":  {"policy": "light-only", "light_cap_mb": 128, "op_floor_gb": 0.2,
               "note": "Galaxy S25+ (Termux), intermittent -- lightest, witness-class only"},
}
LOCAL_HOST = "laptop"              # this machine (Sales / covenant-pc)


def _free_local_gb():
    """Free physical RAM on THIS machine, GB, or None. Lazy import keeps covenant_model out
    of a plain `import covenant_failover` and off the DRY staged path unless this is called."""
    try:
        import covenant_model
        return covenant_model.free_gb()
    except Exception:                                        # noqa: BLE001
        return None


def placement_ok(inst, free_gb=None):
    """May a HOT instance be auto-started on its host without starving the model? True/False,
    with a reason. Cold standbys and non-local hosts are always ok here (a cold standby is
    space-free until used; another host's budget is that host's call, not the laptop's)."""
    if not inst.get("hot", True):
        return True, "cold standby: space-free until a failover starts it"
    host = inst.get("host")
    if host != LOCAL_HOST:
        return True, "on %s, not the laptop -- that host's budget is its own call" % host
    h = HOSTS.get(host) or {}
    if h.get("policy") == "heavy-ok":
        return True, "host policy heavy-ok"
    ram_mb = inst.get("ram_mb", 0)
    cap = h.get("light_cap_mb")
    if cap is not None and ram_mb > cap:
        return False, ("%s is heavy (~%d MB > %d MB cap for %s) -- provision on TETSU instead (PROPOSE)"
                       % (inst.get("name"), ram_mb, cap, host))
    free = _free_local_gb() if free_gb is None else free_gb
    if free is None:
        return False, "free RAM unreadable -- will not start a hot instance that might starve the model"
    need_gb = (ram_mb / 1024.0) + h.get("op_floor_gb", 0.5)
    if free < need_gb:
        return False, ("%s has %.2f GB free; a hot %s needs ~%.2f GB incl. the operational floor -- "
                       "provision on TETSU instead (PROPOSE)" % (host, free, inst.get("name"), need_gb))
    return True, "fits: %.2f GB free >= ~%.2f GB needed" % (free, need_gb)


# --------------------------------------------------------------- the service map
#
# The machine-readable twin of ops/PARALLEL_OS_REDUNDANCY_MAP_2026-11-02.md. FO1
# pins that every service named in the doc appears here. Each instance is tagged
# by the OS ENVIRONMENT it runs in, because the whole question is cross-ENVIRONMENT
# survival, not cross-process.
#
#   require_redundant  the fleet expects this to survive the loss of one env.
#   min_environments   distinct live environments for "healthy" (default 2).
#   instances[].env    windows | wsl-ubuntu | tetsu | phone
#   instances[].provisioned  True once a standby actually exists and we can (re)start it.
#   probe              {"type":"http","url":...} (any HTTP answer = alive) or {"type":"none"}.
#   failover_class     how its redundancy is (or would be) brought up.

def _http_probe(url, timeout=3):
    """ANY HTTP response -- a 404 included -- means the process is ALIVE (git_host_down's
    rule). Only no answer at all (a transport failure) is down. Returns True/False."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            r.read(64)
        return True
    except Exception as e:                                    # noqa: BLE001
        return hasattr(e, "code")        # HTTPError => the server answered => alive


def _probe_instance(inst, probe=None):
    """Is this one instance alive? probe is injectable (tests pass a dict/function);
    by default an HTTP probe for http instances, False-but-UNKNOWN for unprobeable ones."""
    if probe is not None:
        if callable(probe):
            return probe(inst)
        # a dict keyed by instance id, value True/False
        return bool(probe.get(_inst_id(inst)))
    p = inst.get("probe") or {}
    if p.get("type") == "http":
        return _http_probe(p["url"])
    return None                           # cannot probe here -> UNKNOWN for this instance


def _inst_id(inst):
    return "%s/%s@%s" % (inst.get("name") or "?", inst.get("env") or "?", inst.get("host") or "?")


SERVICES = {
    "headscale": {
        "desc": "our Tailscale control plane -- the mesh coordinator",
        "require_redundant": True, "min_environments": 2,
        "failover_class": PROPOSE_ONLY,          # a standby needs install+config on another host
        "instances": [
            {"name": "headscale", "kind": "primary", "env": "wsl-ubuntu", "host": "laptop",
             "provisioned": True, "probe": {"type": "http", "url": "http://127.0.0.1:8080/health"}},
        ],
    },
    "git_host": {
        "desc": "self-hosted smart-HTTP git (clone/push over the mesh)",
        # COLD failover: a Windows read-only standby over a local mirror, started on demand when
        # the WSL host is unreachable (start_githost_standby). Liveness is covenant_highway's
        # git_host_down; this is no longer a bare SPOF -- it has a cross-OS cold standby.
        "require_redundant": True, "redundancy_model": "cold", "failover_class": AUTO_REVERSIBLE,
        "instances": [
            {"name": "git_http_server", "kind": "primary", "env": "wsl-ubuntu", "host": "laptop",
             "provisioned": True, "hot": True, "ram_mb": 30, "probe": {"type": "http",
             "url": "http://127.0.0.1:8088/covenant.git/info/refs?service=git-upload-pack"}},
            {"name": "git_http_server_win", "kind": "redundant", "env": "windows", "host": "laptop",
             "provisioned": True, "hot": False, "ram_mb": 40, "launch": "windows-githost",
             "port": GITHOST_STANDBY_PORT, "probe": {"type": "http",
             "url": "http://127.0.0.1:%d/covenant.git/info/refs?service=git-upload-pack" % GITHOST_STANDBY_PORT}},
        ],
    },
    "unison_feed": {
        "desc": "fleet sync feed (:8800/unison) + own_git (:8400)",
        "require_redundant": True, "min_environments": 2, "failover_class": PROPOSE_ONLY,
        "instances": [
            {"name": "unison_feed", "kind": "primary", "env": "windows", "host": "laptop",
             "provisioned": True, "probe": {"type": "http", "url": "http://127.0.0.1:8800/unison"}},
        ],
    },
    "pc_node": {
        "desc": "judge/API covenant node (5000/5020/5060)",
        "require_redundant": True, "min_environments": 2, "failover_class": PROPOSE_ONLY,
        "instances": [
            {"name": "pc_node", "kind": "primary", "env": "windows", "host": "laptop",
             "provisioned": True, "probe": {"type": "http", "url": "http://127.0.0.1:5000/health"}},
            {"name": "tetsu_node", "kind": "redundant", "env": "tetsu", "host": "tetsu",
             "provisioned": False, "probe": {"type": "none"}},
        ],
    },
    "model": {
        "desc": "the model + LIMB SMOL/PHI consult limbs",
        "require_redundant": True, "min_environments": 1, "failover_class": PROPOSE_ONLY,
        "instances": [
            {"name": "tetsu_model", "kind": "primary", "env": "tetsu", "host": "tetsu",
             "provisioned": True, "probe": {"type": "none"}},
        ],
    },
    "teacher": {
        "desc": "practice loop + teacher queue feeding students",
        "require_redundant": False, "min_environments": 1, "failover_class": PROPOSE_ONLY,
        "instances": [
            {"name": "teacher", "kind": "primary", "env": "windows", "host": "laptop",
             "provisioned": True, "probe": {"type": "none"}},
        ],
    },
    # The one service this module actually provisions as a live cross-OS pair.
    # DARK until ops/REDUNDANCY_ARMED exists (RAM budget).
    "beacon": {
        "desc": "the redundancy read-API itself -- a provisioned cross-OS pair",
        "require_redundant": True, "min_environments": 2, "redundancy_model": "hot",
        "failover_class": AUTO_REVERSIBLE, "arm_gated": True,
        "instances": [
            {"name": "beacon-win", "kind": "primary", "env": "windows", "host": "laptop",
             "provisioned": True, "hot": True, "ram_mb": 15, "launch": "windows", "port": BEACON_WIN_PORT,
             "probe": {"type": "http", "url": "http://127.0.0.1:%d/beacon" % BEACON_WIN_PORT}},
            {"name": "beacon-wsl", "kind": "redundant", "env": "wsl-ubuntu", "host": "laptop",
             "provisioned": True, "hot": True, "ram_mb": 15, "launch": "wsl-ubuntu", "port": BEACON_WSL_PORT,
             "probe": {"type": "http", "url": "http://127.0.0.1:%d/beacon" % BEACON_WSL_PORT}},
        ],
    },
}


def armed():
    """True once the operator writes ops/REDUNDANCY_ARMED. Until then the beacon
    pair is not expected up and never alarms (it is not auto-started either)."""
    return os.path.exists(ARM_MARKER)


def _service_active(name, svc):
    """Is this service's redundancy expected to be LIVE right now? arm-gated services
    (the beacon) only when armed."""
    if not svc.get("require_redundant"):
        return False
    if svc.get("arm_gated") and not armed():
        return False
    return True


def _configured_for_redundancy(svc):
    """A service is CONFIGURED for redundancy when it declares >=2 provisioned
    instances across distinct environments -- i.e. a standby actually EXISTS on a
    different OS/host. A pair is inherently two environments, so this never depends
    on min_environments: one provisioned instance (or several that are not yet
    provisioned, like a TETSU standby still to be stood up) is a SPOF, not a
    degraded pair, and belongs in the spof bucket."""
    envs = {i["env"] for i in svc["instances"] if i.get("provisioned")}
    return len(envs) >= 2


def live_environments(svc, probe=None):
    """Distinct ENVIRONMENTS with a live instance. Unprobeable instances (probe
    None) are not counted live -- unknown is not alive (rule 9/P20)."""
    out = set()
    for inst in svc["instances"]:
        if _probe_instance(inst, probe) is True:
            out.add(inst["env"])
    return out


def live_endpoint(service, probe=None):
    """The endpoint a client should use for `service` right now: the primary if
    live, else the first live redundant instance, else None (DARK -- never a
    silent 'ok'). This is the failover resolver."""
    svc = SERVICES.get(service)
    if not svc:
        return None
    ordered = sorted(svc["instances"], key=lambda i: 0 if i.get("kind") == "primary" else 1)
    for inst in ordered:
        if _probe_instance(inst, probe) is True:
            url = (inst.get("probe") or {}).get("url")
            return {"instance": inst["name"], "env": inst["env"], "host": inst["host"], "url": url}
    return None


# --------------------------------------------------------------- the three senses

def detect_redundancy_degraded(health=None, services=None, probe=None, now=None, **kw):
    """A service that HAS a provisioned redundant pair has lost an environment --
    fewer distinct live environments than it needs. PRESENT only for CONFIGURED,
    ACTIVE services (so a never-armed beacon and the bare SPOFs never cry wolf);
    known SPOFs ride in measured['spof'] as information, not as an alarm."""
    services = SERVICES if services is None else services
    degraded, healthy, spof, inactive, unmeasurable, cold = [], [], [], [], [], []
    for name, svc in services.items():
        if not svc.get("require_redundant"):
            continue
        if not _configured_for_redundancy(svc):
            spof.append({"service": name, "desc": svc.get("desc"), "class": svc.get("failover_class"),
                         "envs": sorted({i["env"] for i in svc["instances"]})})
            continue
        if svc.get("redundancy_model") == "cold":
            # COLD failover (e.g. git_host): liveness is covenant_highway's own detector and the
            # failover is an on-demand standby -- not a hot pair, so never "degraded" for a cold
            # standby that is simply not running. Recorded for visibility.
            cold.append({"service": name, "standby": sorted({i["env"] for i in svc["instances"]
                                                             if not i.get("hot", True)})})
            continue
        if not _service_active(name, svc):
            inactive.append({"service": name, "why": "arm-gated, not armed" if svc.get("arm_gated")
                             else "not active"})
            continue
        prov = [i for i in svc["instances"] if i.get("provisioned")]
        results = [(i, _probe_instance(i, probe)) for i in prov]
        # P20 / rule 9: a configured pair whose liveness CANNOT be read (every provisioned
        # instance unprobeable) is UNKNOWN, never ABSENT -- a broken instrument must not read
        # as "redundancy fine". Only count a pair healthy/degraded when at least one instance
        # gave a real up/down answer.
        if all(r is None for _, r in results):
            unmeasurable.append({"service": name, "why": "no provisioned instance is probeable here"})
            continue
        envs = {i["env"] for i, r in results if r is True}
        need = svc.get("min_environments", 2)
        entry = {"service": name, "live_environments": sorted(envs), "need": need,
                 "down": [{"name": i["name"], "env": i["env"]} for i, r in results if r is not True]}
        if len(envs) < need:
            degraded.append(entry)
        else:
            healthy.append(entry)
    measured = {"degraded": degraded, "healthy": healthy, "spof": spof, "inactive": inactive,
                "unmeasurable": unmeasurable, "cold_failover": cold}
    if degraded:
        measured["why"] = "; ".join(
            "%s has %d/%d live environments (down: %s)" % (
                d["service"], len(d["live_environments"]), d["need"],
                ", ".join("%s@%s" % (x["name"], x["env"]) for x in d["down"]) or "?")
            for d in degraded)
    elif unmeasurable:
        measured["why"] = "redundancy liveness unreadable for: " + ", ".join(u["service"] for u in unmeasurable)
    if degraded:
        return {"state": PRESENT, "measured": measured}
    if unmeasurable:
        return {"state": UNKNOWN, "measured": measured}
    return {"state": ABSENT, "measured": measured}


def _wsl_alive(run=None, timeout=6):
    """Is the control host's WSL distro up? `wsl.exe -d Ubuntu -e true` returns 0 when
    the distro is running/startable. None where wsl.exe is absent (not the control host,
    or CI) -- unknown, never 'down'."""
    runner = run or (lambda cmd: subprocess.run(cmd, capture_output=True, timeout=timeout,
                                                creationflags=_NOWIN))
    try:
        r = runner(["wsl.exe", "-d", "Ubuntu", "-e", "true"])
    except FileNotFoundError:
        return None
    except Exception:                                         # noqa: BLE001
        return None
    return getattr(r, "returncode", 1) == 0


def _headscale_marker():
    """The Startup launcher marks this machine as the control host -- the one place WSL
    services are EXPECTED up. A clone / CI / a non-control node has no marker."""
    appdata = os.environ.get("APPDATA") or ""
    if not appdata:
        return ""
    return os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs",
                        "Startup", "CovenantHeadscale.vbs")


def detect_environment_down(health=None, environments=None, probe=None, marker=None,
                            wsl=None, **kw):
    """An OS environment the fleet depends on is not answering. ALARM-ONLY: booting or
    re-provisioning an OS is PROPOSE-only and RAM-heavy, so a person decides. Only
    environments EXPECTED up here are judged -- the control host's WSL (marked by the
    headscale Startup launcher). A machine without the marker reads UNKNOWN for WSL, never
    down, so a clone never alarms. TETSU legitimately sleeps and is reported as info, not
    an alarm, unless a caller passes it in `environments`."""
    if environments is not None:                             # test / explicit override
        down = [e for e in environments if e.get("up") is False]
        unknown = [e for e in environments if e.get("up") is None]
        measured = {"down": [e["name"] for e in down], "unknown": [e["name"] for e in unknown]}
        if down:
            measured["why"] = "expected-up environment(s) not answering: " + ", ".join(measured["down"])
        return {"state": PRESENT if down else ABSENT, "measured": measured}
    mk = _headscale_marker() if marker is None else marker
    if not mk or not os.path.exists(mk):
        return {"state": UNKNOWN, "measured": {"why": "not the control host (no headscale launcher) -- "
                                               "WSL is not expected up here"}}
    up = _wsl_alive(run=wsl)
    if up is None:
        return {"state": UNKNOWN, "measured": {"why": "wsl.exe not available to probe the distro"}}
    if up:
        return {"state": ABSENT, "measured": {"wsl-ubuntu": "up"}}
    return {"state": PRESENT, "measured": {
        "why": "the control host's WSL/Ubuntu is down -- headscale and the git host live only there",
        "environment": "wsl-ubuntu", "host": "laptop"}}


def detect_spof_unremediated(health=None, services=None, remind=None, **kw):
    """A known single-point-of-failure still has no redundant instance anywhere. OFF by
    default -- the redundancy map already documents the SPOFs and a constant alarm helps no
    one. PRESENT only when the operator opts in with ops/REDUNDANCY_SPOF_REMIND, so the
    PROPOSE_ONLY remedy (propose_provision_redundancy) has a path to fire and be tested."""
    services = SERVICES if services is None else services
    on = os.path.exists(SPOF_REMIND_MARKER) if remind is None else bool(remind)
    try:
        spof = [{"service": n, "desc": s.get("desc")} for n, s in services.items()
                if s.get("require_redundant") and not _configured_for_redundancy(s)]
    except Exception as e:                                    # noqa: BLE001
        # P20 / rule 9: a service registry it cannot enumerate is UNKNOWN, never "no SPOFs".
        return {"state": UNKNOWN, "measured": {"why": "service registry unreadable: %s" % e}}
    measured = {"spof": spof, "reminder_on": on}
    if on and spof:
        measured["why"] = "no redundant instance for: " + ", ".join(s["service"] for s in spof)
    return {"state": PRESENT if (on and spof) else ABSENT, "measured": measured}


# --------------------------------------------------------------- the two repairs

def _launch_windows_beacon(inst, dry_run):
    port = inst.get("port") or BEACON_WIN_PORT
    if dry_run:
        return True, "would start the Windows beacon on 127.0.0.1:%d" % port
    if not os.path.exists(BEACON):
        return False, "covenant_beacon.py not found at %s" % BEACON
    subprocess.Popen([sys.executable, BEACON, "--port", str(port), "--instance", inst["name"],
                      "--env", "windows", "--host", "127.0.0.1"],
                     creationflags=_NOWIN | _DETACHED, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    return True, "started"


def _wsl_beacon_path():
    """covenant_beacon.py as WSL sees it (/mnt/c/...). None where wslpath is absent."""
    try:
        r = subprocess.run(["wsl.exe", "-d", "Ubuntu", "-e", "wslpath", "-a", BEACON],
                           capture_output=True, text=True, timeout=10, creationflags=_NOWIN)
        p = (r.stdout or "").strip()
        return p or None
    except Exception:                                         # noqa: BLE001
        return None


def _launch_wsl_beacon(inst, dry_run):
    port = inst.get("port") or BEACON_WSL_PORT
    if dry_run:
        return True, "would start the WSL/Ubuntu beacon on 0.0.0.0:%d (reachable at 127.0.0.1:%d)" % (port, port)
    wp = _wsl_beacon_path()
    if not wp:
        return False, "cannot resolve the beacon path inside WSL (wslpath unavailable)"
    # setsid detaches it from this one-shot wsl invocation so it outlives the call; disown +
    # a short sleep keep the launching shell alive just long enough for the child to daemonize
    # (without it, WSL reaps the child before it binds -- measured). --host 0.0.0.0 so the WSL2
    # NAT forwards 127.0.0.1:<port> on the Windows side.
    cmd = ("setsid python3 '%s' --port %d --instance '%s' --env wsl-ubuntu --host 0.0.0.0 "
           ">/tmp/covenant_beacon_%d.log 2>&1 </dev/null & disown; sleep 1.5") % (
               wp, port, inst["name"], port)
    subprocess.run(["wsl.exe", "-d", "Ubuntu", "--", "bash", "-lc", cmd],
                   capture_output=True, timeout=20, creationflags=_NOWIN)
    return True, "started"


def _start_instance(inst, dry_run):
    launch = inst.get("launch")
    if launch == "windows":
        return _launch_windows_beacon(inst, dry_run)
    if launch == "wsl-ubuntu":
        return _launch_wsl_beacon(inst, dry_run)
    return False, "no known launcher for %s (provision it first -- PROPOSE_ONLY)" % inst.get("name")


def remedy_start_redundant_instance(measured, dry_run=True):
    """STATELESS: (re)start an ALREADY-PROVISIONED standby that is down, on its own OS.
    Reversible, touches nothing in NEVER_AUTOMATIC -- the same class as restart_headscale.
    Only ever starts an instance we provisioned AND know how to launch (today: the beacon
    pair); anything else is PROPOSE-only and declined here. Starting a NEW environment is
    never this remedy."""
    m = measured or {}
    degraded = m.get("degraded") or []
    if not degraded:
        return False, "nothing degraded to bring back"
    started, failed, skipped = [], [], []
    for d in degraded:
        svc = SERVICES.get(d["service"]) or {}
        if svc.get("failover_class") != AUTO_REVERSIBLE:
            skipped.append("%s: redundancy is PROPOSE-only (needs provisioning on another host)" % d["service"])
            continue
        down_names = {x["name"] for x in d.get("down") or []}
        for inst in svc["instances"]:
            if inst["name"] not in down_names or not inst.get("provisioned") or not inst.get("launch"):
                continue
            # SPACE-WISE (the operator, 2026-11-02): never auto-start a hot instance that would
            # starve the model on the laptop -- propose TETSU instead.
            fits, why = placement_ok(inst)
            if not fits:
                skipped.append("%s/%s@%s: %s" % (d["service"], inst["name"], inst["env"], why))
                continue
            ok, msg = _start_instance(inst, dry_run)
            tag = "%s/%s@%s" % (d["service"], inst["name"], inst["env"])
            if dry_run:
                (started if ok else failed).append("%s: %s" % (tag, msg))
                continue
            if not ok:
                failed.append("%s: %s" % (tag, msg))
                continue
            # verify it ANSWERS before claiming a fix (rule 8: a green never observed is not green)
            alive = False
            for _ in range(6):
                time.sleep(2)
                if _probe_instance(inst) is True:
                    alive = True
                    break
            (started if alive else failed).append("%s: %s" % (tag, "started and answering" if alive
                                                              else "started but not answering within ~12 s"))
    if dry_run:
        return (bool(started), "; ".join(started + failed + skipped) or "nothing to start")
    if not started:
        return False, "; ".join(failed + skipped) or "nothing started"
    return (not failed), "; ".join(started + failed + skipped)


def _githost_standby_serving(port=GITHOST_STANDBY_PORT, timeout=3):
    return _http_probe("http://127.0.0.1:%d/covenant.git/info/refs?service=git-upload-pack" % port, timeout)


def remedy_start_githost_standby(measured, dry_run=True):
    """STATELESS: bring up the READ-ONLY Windows git-host cold standby when the WSL git host is
    UNREACHABLE (not merely a crashed process -- that is restart_git_host's job). Serves clone/
    fetch from the local mirror until the primary returns; it refuses push, so there is no split
    brain and the primary stays the only master. AUTO_REVERSIBLE, touches nothing in
    NEVER_AUTOMATIC. Space-wise: a cold standby, started only on real failover, ~40 MB.

    It DECLINES while WSL is alive, so it does not double up with restart_git_host on an ordinary
    process restart, and it serves the mirror AS-IS without refreshing (the primary is down, so a
    refresh cannot reach it; the mirror is kept fresh on a schedule while the primary is up)."""
    if _githost_standby_serving():
        return False, "the Windows git-host standby is already serving on 127.0.0.1:%d" % GITHOST_STANDBY_PORT
    if _wsl_alive() is True:
        return False, ("WSL is up -- a crashed git process is restart_git_host's job; the Windows "
                       "read standby is for when WSL itself is unreachable")
    if dry_run:
        return True, ("would start the read-only Windows git-host standby on 127.0.0.1:%d from the local "
                      "mirror (clone/fetch only; push stays on the primary)" % GITHOST_STANDBY_PORT)
    if not os.path.exists(GITHOST_STANDBY):
        return False, "covenant_githost_standby.py not found at %s" % GITHOST_STANDBY
    subprocess.Popen([sys.executable, GITHOST_STANDBY, "--serve", "--port", str(GITHOST_STANDBY_PORT)],
                     creationflags=_NOWIN | _DETACHED, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    for _ in range(6):                                       # ~12 s to come up and answer info/refs
        time.sleep(2)
        if _githost_standby_serving():
            return True, "the Windows git-host read-only standby is serving clone/fetch on 127.0.0.1:%d" % GITHOST_STANDBY_PORT
    return False, "started the standby but it did not answer info/refs within ~12 s"


def remedy_propose_provision_redundancy(measured, dry_run=True):
    """PROPOSE_ONLY, permanently. Standing up a redundant instance on another host or OS
    installs software / changes system state -- never the engine's to do. The proposal
    names the SPOFs and points at ops/PARALLEL_OS_PROPOSE_2026-11-02.md, where the operator
    has the exact steps. apply_remedy refuses this class before this body is ever entered;
    the text here is only what the refusal carries."""
    m = measured or {}
    spof = m.get("spof") or []
    names = ", ".join(s["service"] for s in spof) or "the known SPOFs"
    return False, ("provision a redundant instance for %s on a different host/OS (TETSU-heavy) -- "
                   "see ops/PARALLEL_OS_PROPOSE_2026-11-02.md. PROPOSE_ONLY: installs/VMs are the "
                   "operator's call." % names)


DETECTORS = {
    "redundancy_degraded": detect_redundancy_degraded,
    "environment_down": detect_environment_down,
    "spof_unremediated": detect_spof_unremediated,
}

REMEDIES = {
    "start_redundant_instance": {
        "fn": remedy_start_redundant_instance, "klass": AUTO_REVERSIBLE,
        "for": ["redundancy_degraded"], "kind": "stateless", "noise_s": 900,
        "touches": ["an already-provisioned standby service instance (the beacon) on its own OS"],
        "benefit": {"gains": ["a critical service keeps a live instance on a second OS after one dies",
                              "the fleet survives the loss of one environment without a person"],
                    "cost": ["a few MB and one port for the restarted standby",
                             "a few seconds before the standby answers"],
                    "irreversible": []}},
    "start_githost_standby": {
        "fn": remedy_start_githost_standby, "klass": AUTO_REVERSIBLE,
        "for": ["git_host_down"], "kind": "stateless", "noise_s": 900,
        "touches": ["the read-only Windows git-host standby process (clone/fetch only)"],
        "benefit": {"gains": ["clone/fetch survives the loss of the laptop's WSL/Ubuntu -- the git host "
                              "stops being a single-OS point of failure",
                              "a cross-OS read fallback, served from a local mirror, with no split brain"],
                    "cost": ["~40 MB for the standby while the primary is down; reads may be as fresh as "
                             "the mirror's last update, never staler than the primary was"],
                    "irreversible": []}},
    "propose_provision_redundancy": {
        "fn": remedy_propose_provision_redundancy, "klass": PROPOSE_ONLY,
        "for": ["spof_unremediated"], "kind": "needs a person",
        "touches": ["standing up a redundant instance on another host/OS (install + config)"],
        "benefit": {"gains": ["a single-point-of-failure gains a live standby on a different OS/host"],
                    "cost": ["an install and some always-on resources on the chosen host (TETSU)",
                             "the operator's time to approve and run the steps"],
                    "irreversible": []}},
}


def register(detectors, remedies):
    """The highway's single hook: merge our senses and repairs into its registries.
    Idempotent -- re-registering the same names is a no-op overwrite with identical values."""
    detectors.update(DETECTORS)
    remedies.update(REMEDIES)
    return sorted(DETECTORS), sorted(REMEDIES)


# --------------------------------------------------------------- live cross-OS proof

def _kill_windows_port(port):
    """Best-effort: end whatever Windows process listens on `port` (the beacon we started)."""
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                             timeout=15, creationflags=_NOWIN).stdout or ""
    except Exception:                                         # noqa: BLE001
        return
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[1].endswith(":%d" % port) and "LISTEN" in line.upper():
            subprocess.run(["taskkill", "/F", "/PID", parts[-1]], capture_output=True,
                           timeout=15, creationflags=_NOWIN)


def _kill_wsl_beacon(port):
    try:
        subprocess.run(["wsl.exe", "-d", "Ubuntu", "--", "pkill", "-f",
                        "covenant_beacon.py --port %d" % port], capture_output=True,
                       timeout=15, creationflags=_NOWIN)
    except Exception:                                         # noqa: BLE001
        pass


def prove(verbose=True):
    """Stand up the real cross-OS beacon pair and show failover BOTH WAYS. Returns a dict
    record. Needs Windows + a reachable WSL/Ubuntu; returns {'skipped': why} otherwise."""
    svc = SERVICES["beacon"]
    win = next(i for i in svc["instances"] if i["env"] == "windows")
    wsl = next(i for i in svc["instances"] if i["env"] == "wsl-ubuntu")
    if _wsl_alive() is not True:
        return {"skipped": "WSL/Ubuntu not reachable -- the cross-OS proof needs both OSes"}
    rec = {"steps": []}

    def step(name, ok, detail):
        rec["steps"].append({"step": name, "ok": bool(ok), "detail": detail})
        if verbose:
            print("  [%s] %s -- %s" % ("ok" if ok else "XX", name, detail))

    # The beacon ships DARK (arm-gated); arm it for the duration of the proof so the detector
    # treats the pair as expected-up, then disarm. If the operator had already armed it, leave
    # the marker in place.
    _pre_armed = armed()
    if not _pre_armed:
        try:
            os.makedirs(os.path.dirname(ARM_MARKER), exist_ok=True)
            with open(ARM_MARKER, "w", encoding="utf-8") as fh:
                fh.write("armed by covenant_failover --prove at %s\n" % time.strftime("%Y-%m-%dT%H:%M:%S"))
        except OSError:
            pass
    try:
        _kill_windows_port(win["port"]); _kill_wsl_beacon(wsl["port"]); time.sleep(1)
        _start_instance(win, dry_run=False); _start_instance(wsl, dry_run=False)
        for _ in range(8):
            time.sleep(2)
            if _probe_instance(win) and _probe_instance(wsl):
                break
        both = _probe_instance(win) is True and _probe_instance(wsl) is True
        step("both up (Windows + WSL/Ubuntu)", both,
             "win=%s wsl=%s" % (_probe_instance(win), _probe_instance(wsl)))
        ep = live_endpoint("beacon")
        step("resolver prefers the primary", ep and ep["env"] == "windows", json.dumps(ep))
        d = detect_redundancy_degraded()
        step("redundancy_degraded ABSENT when paired", d["state"] == ABSENT, d["state"])

        # --- kill the Windows primary: the WSL/Linux standby must take over ---
        _kill_windows_port(win["port"]); time.sleep(2)
        ep = live_endpoint("beacon")
        step("primary down -> resolver serves the WSL/Linux standby, which ANSWERS",
             ep and ep["env"] == "wsl-ubuntu" and _probe_instance(wsl) is True, json.dumps(ep))
        d = detect_redundancy_degraded()
        step("redundancy_degraded PRESENT with one env down", d["state"] == PRESENT,
             (d["measured"].get("why") or "")[:160])

        # --- start_redundant_instance brings the Windows instance back ---
        ok, msg = remedy_start_redundant_instance(d["measured"], dry_run=False)
        step("start_redundant_instance restarts the down standby", ok, msg[:200])
        d2 = detect_redundancy_degraded()
        step("redundancy_degraded ABSENT again after restart", d2["state"] == ABSENT, d2["state"])

        # --- the other direction: kill the WSL standby, Windows keeps serving ---
        _kill_wsl_beacon(wsl["port"]); time.sleep(2)
        ep = live_endpoint("beacon")
        step("WSL standby down -> resolver serves Windows, still available",
             ep and ep["env"] == "windows" and _probe_instance(win) is True, json.dumps(ep))
    finally:
        _kill_windows_port(win["port"]); _kill_wsl_beacon(wsl["port"])
        if not _pre_armed:
            try:
                os.remove(ARM_MARKER)
            except OSError:
                pass
    rec["ok"] = all(s["ok"] for s in rec["steps"])
    return rec


def prove_githost(verbose=True):
    """Live: stand up the Windows git-host cold standby and show a REAL cross-OS git clone
    failover. Returns a record. Needs Windows + git; {'skipped': why} otherwise."""
    if os.name != "nt":
        return {"skipped": "the git-host standby proof runs on the Windows control host"}
    import shutil
    import tempfile
    inst = next(i for i in SERVICES["git_host"]["instances"] if i["env"] == "windows")
    port = inst["port"]
    rec = {"steps": []}

    def step(name, ok, detail):
        rec["steps"].append({"step": name, "ok": bool(ok), "detail": detail})
        if verbose:
            print("  [%s] %s -- %s" % ("ok" if ok else "XX", name, detail))

    def _rmtree(p):
        # Windows makes git's object files read-only; plain rmtree fails on them.
        def _onerr(fn, path, exc):
            try:
                os.chmod(path, 0o700); fn(path)
            except Exception:                                # noqa: BLE001
                pass
        shutil.rmtree(p, onerror=_onerr)

    clone_dir = tempfile.mkdtemp(prefix="covenant_githost_proof_")
    os.rmdir(clone_dir)                                       # git clone wants to create it (or an empty dir)
    proc = None
    try:
        import covenant_githost_standby as GS
        ok, msg = GS.refresh()
        step("mirror provisioned/refreshed from the primary", ok, msg)
        proc = subprocess.Popen([sys.executable, GITHOST_STANDBY, "--serve", "--port", str(port)],
                                creationflags=_NOWIN | _DETACHED, stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
        up = False
        for _ in range(8):
            time.sleep(1.5)
            if _githost_standby_serving(port):
                up = True
                break
        step("Windows standby serving info/refs", up, "127.0.0.1:%d" % port)
        # resolver: with the PRIMARY injected down, git_host resolves to the Windows standby
        ep = live_endpoint("git_host", probe=lambda i: i["env"] == "windows")
        step("primary down -> resolver serves the Windows git-host standby",
             ep and ep["env"] == "windows", json.dumps(ep))
        # a REAL clone from the Windows standby (a different OS than the WSL primary)
        if os.path.isdir(clone_dir):
            _rmtree(clone_dir)
        r = subprocess.run(["git", "clone", "-q", "http://127.0.0.1:%d/covenant.git" % port, clone_dir],
                           capture_output=True, text=True, timeout=120)
        head = ""
        if r.returncode == 0:
            head = subprocess.run(["git", "-C", clone_dir, "rev-parse", "HEAD"], capture_output=True,
                                  text=True, timeout=20).stdout.strip()
        step("REAL git clone from the Windows standby", r.returncode == 0 and bool(head),
             "HEAD %s" % head[:12] if head else (r.stderr or "")[:120])
        # push is refused (read-only; no split brain)
        refused = _http_probe("http://127.0.0.1:%d/covenant.git/git-receive-pack" % port) is False
        # a 403 is an HTTPError -> _http_probe returns True (answered); check the code explicitly
        try:
            urllib.request.urlopen(urllib.request.Request(
                "http://127.0.0.1:%d/covenant.git/git-receive-pack" % port, method="POST"), timeout=4)
            code = 200
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception:                                    # noqa: BLE001
            code = None
        step("push (receive-pack) refused -- read-only, no split brain", code == 403, "HTTP %s" % code)
    except Exception as e:                                    # noqa: BLE001
        step("exception", False, "%s: %s" % (type(e).__name__, e))
    finally:
        if proc is not None:
            try:
                proc.terminate()
            except Exception:                                # noqa: BLE001
                pass
        _kill_windows_port(port)
        if os.path.isdir(clone_dir):
            _rmtree(clone_dir)
    rec["ok"] = all(s["ok"] for s in rec["steps"]) and bool(rec["steps"])
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description="cross-OS/host service redundancy for the highway")
    ap.add_argument("--map", action="store_true", help="print the machine-readable service map")
    ap.add_argument("--prove", action="store_true", help="live cross-OS failover proof (needs WSL)")
    ap.add_argument("--prove-git", action="store_true", help="live cross-OS git-host failover proof")
    a = ap.parse_args(argv)
    if a.map:
        print(json.dumps(SERVICES, indent=2))
        return 0
    if a.prove:
        print("covenant_failover --prove: live cross-OS beacon failover")
        rec = prove()
        if rec.get("skipped"):
            print("SKIPPED:", rec["skipped"])
            return 0
        print("\nRESULT:", "ALL STEPS PASSED" if rec["ok"] else "SOME STEPS FAILED")
        return 0 if rec["ok"] else 1
    if a.prove_git:
        print("covenant_failover --prove-git: live cross-OS git-host failover")
        rec = prove_githost()
        if rec.get("skipped"):
            print("SKIPPED:", rec["skipped"])
            return 0
        print("\nRESULT:", "ALL STEPS PASSED" if rec["ok"] else "SOME STEPS FAILED")
        return 0 if rec["ok"] else 1
    # default: sense here
    for name, fn in DETECTORS.items():
        try:
            r = fn()
        except Exception as e:                                # noqa: BLE001
            r = {"state": UNKNOWN, "measured": {"error": "%s: %s" % (type(e).__name__, e)}}
        print("%-22s %-8s %s" % (name, r["state"], json.dumps(r["measured"])[:160]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
