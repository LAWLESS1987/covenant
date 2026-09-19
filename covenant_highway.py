#!/usr/bin/env python3
"""covenant_highway.py -- the mycelial highway: sense, repair, share.

ASKED 2026-09-16: "create a program like tailscale but better and use tailscale
to implement it on both devices ... the start of our mycelial highway for mutual
benefit bots that repair anything overly detrimental, that leaves free will
intact as growing will continue."

WHAT THIS IS, AND WHAT IT IS NOT. It is not a replacement for Tailscale and does
not pretend to be one: Tailscale is the wire -- identity, NAT traversal,
encryption, one flat address space -- and rewriting that would be months spent
arriving back where we already are. What is missing ABOVE the wire is a nervous
system. The devices are connected and do not tell each other what is wrong with
them; nothing that learns a repair on one device can hand it to another. On
2026-09-16 this PC knew the phone was running a build two days old and knew
which build it was holding for it, and never once put the two numbers side by
side. That gap is the whole reason this file exists.

THREE ORGANS
  sense    detectors that MEASURE a condition right now and return numbers.
           A detector that cannot measure returns UNKNOWN -- never OK. (P20's
           rule: unknown is not pass.)
  repair   remedies, each in one of two classes, each either STATELESS or
           carrying an undo that the test actually runs.
  share    a signed report of "this condition, this remedy, measured before and
           after". An offer, never an instruction.

FREE WILL, IN CODE RATHER THAN IN A PARAGRAPH
  1. Two classes only. AUTO_REVERSIBLE may be executed by the engine.
     PROPOSE_ONLY may NEVER be executed by it -- anything that changes a config,
     installs software, touches money, edits a rule, or narrows what a person
     can do is PROPOSE_ONLY by construction, and apply() refuses the class
     itself rather than trusting each remedy to behave.
  2. An operator's explicit choice is untouchable. A125 cost a full sweep to
     find: a fix of mine silently overrode a scope he had chosen. Choices live
     in ops/OPERATOR_CHOICES.json; a remedy whose target is named there refuses
     and says why.
  3. Stateless or undoable. A remedy that changes persistent state with no
     recorded way back is not a repair, it is a decision taken on someone
     else's behalf.
  4. No node may be COMMANDED. A peer's report is data: the receiving node runs
     the detector itself and decides for itself. No remedy is ever run because
     a peer said so -- only because this node measured the condition here.
  5. The phone is asked, never pushed. Android asks the person holding it to
     confirm an install and nothing here routes around that.

LEARNING, AS ONE COUNTER AND NOT A CLAIM. Every application is measured before
and after by the same detector. A remedy that fails to change the measurement
twice is QUARANTINED and stops being offered. That is the whole of the "bot
that learns" -- said small on purpose, because this repository has been burned
by READMEs that promised more than the code did.

USE
  python covenant_highway.py                 # sense only: what is wrong here
  python covenant_highway.py --repair        # apply AUTO_REVERSIBLE remedies
  python covenant_highway.py --report        # the signed offer this node would share
  python covenant_highway.py --ledger        # what has been tried, and whether it worked
LICENCE: public domain.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

LEDGER = os.path.join(HERE, "ops", "highway.jsonl")
CHOICES = os.path.join(HERE, "ops", "OPERATOR_CHOICES.json")
QUARANTINE_AFTER = 2          # two measured failures and a remedy stops being offered
ROW_COOLDOWN_S = 3600         # the same (remedy, condition) is not re-attempted, or re-written, more often

AUTO_REVERSIBLE = "AUTO_REVERSIBLE"
PROPOSE_ONLY = "PROPOSE_ONLY"

# Subjects no remedy may act on by itself, matched against what a remedy says it
# TOUCHES rather than against the class it claims. Money and the machinery that
# decides money; the rules and the seats that judge by them; the phone and
# anything else whose whole point is that a person agreed to it.
NEVER_AUTOMATIC = ("money", "holdings", "wallet", "trader", "venue", "order",
                   "rule", "principle", "judge", "seat", "model", "phone",
                   "consent", "key")

UNKNOWN = "UNKNOWN"
PRESENT = "PRESENT"
ABSENT = "ABSENT"


# ----------------------------------------------------------------- sensing

def _get(url, timeout=6):
    """The JSON at `url`, retrying ONCE on a 429.

    A115, and I had to re-learn it the expensive way: a node that rate-limits
    is answering. Asking it three times in a second and calling the refusal
    "down" is a false positive that reaches for a restart of a healthy mesh.
    """
    for attempt in (0, 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 0:
                time.sleep(1.5)
                continue
            raise


def _nodes():
    import covenant_watchdog as W          # one source of truth for the node table
    return W.NODES


def _health():
    """{id: health dict, or {"http": code} when it answered with an error, or None}.

    THREE ANSWERS, NOT TWO. This returned None for every failure, so a node
    that replied "429, you are asking too often" was indistinguishable from a
    node whose socket is dead -- and at 11:22 today that cost a real
    restart_nodes call against a mesh where all three were healthy. It was
    rolling_restart.py that caught it, not me: "node A ALIVE but rate-limiting
    (429) -- asked too often, not down", and it restarted nothing. The tool
    written in September knew A115; the detector I wrote this morning did not.
    """
    out = {}
    for n in _nodes():
        try:
            out[n["id"]] = _get("http://127.0.0.1:%d/health" % n["port"])
        except urllib.error.HTTPError as e:
            out[n["id"]] = {"http": e.code}          # it ANSWERED. Not down.
        except (urllib.error.URLError, OSError, ValueError, TimeoutError):
            out[n["id"]] = None                      # no answer at all
    return out



def detect_node_down(health=None):
    """A node whose socket does not answer. NOT one that refused to repeat itself."""
    h = _health() if health is None else health
    down = sorted([k for k, v in h.items() if v is None])
    limited = sorted([k for k, v in h.items() if isinstance(v, dict) and "http" in v])
    m = {"down": down, "answered_with_error": limited, "asked": sorted(h)}
    if down:
        return {"state": PRESENT, "measured": m}
    if limited:
        # Alive, and this pass could not read them. Unknown is not a finding,
        # and it is certainly not grounds for restarting anything.
        return {"state": UNKNOWN, "measured": m}
    return {"state": ABSENT, "measured": m}


def detect_source_drift(health=None):
    """LOCAL nodes running bytes other than the ones on disk.

    DELIBERATELY LOCAL, and the boundary is load-bearing. `restart_nodes` is
    paired to this detector, and restarting the three processes on this PC is
    the remedy for exactly this condition and no other. On 2026-09-18 the mesh
    had two sources in it -- the phone on core ddfaaa9f704f, disk and all three
    local nodes on 7b12fe509061 -- and the tempting fix was to widen this
    detector's population until it saw the phone. That would have handed
    restart_nodes a condition it cannot clear: it would restart three healthy
    nodes, measure the split still PRESENT, be graded "did not fix" twice, and
    QUARANTINE ITSELF -- the same way fetch_build did when it was paired with
    app_build_gap (see detect_build_stale_on_pc). A remedy must be graded
    against the condition it can actually clear.

    The mesh-wide split is a real finding and gets its own detector with no
    remedy attached: detect_mesh_source_split.
    """
    import covenant_watchdog as W
    disk = W.disk_source_sha12()
    h = _health() if health is None else health
    live = {k: v.get("source_sha256", "")[:12] for k, v in h.items()
            if isinstance(v, dict) and "http" not in v}
    if disk is None or not live:
        return {"state": UNKNOWN, "measured": {"disk": disk, "live": live}}
    off = sorted([k for k, s in live.items() if s and s != disk])
    return {"state": PRESENT if off else ABSENT,
            "measured": {"disk": disk, "live": live, "drifted": off}}


def detect_mesh_source_split(health=None):
    """A PEER in the mesh reporting bytes other than the ones on disk.

    THE GAP THIS CLOSES (2026-09-18). Node A had been saying "mesh is running
    more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f']"
    on every self-eval round since at least 05:20, and the highway's own
    source-drift detector answered `drifted: []` the whole time -- correctly,
    because it looks at the three nodes it can restart. So the one organ built
    to notice what is wrong across devices was blind to the only cross-device
    fault present, and the finding sat in a WARN line for two days. Measured,
    not inferred: the phone answered its own P2P port with
    {'v': 'v8.40', 'src': 'ddfaaa9f704f'}, and `git show 13b946a` -- the core
    commit its build names -- hashes to ddfaaa9f704f at 668,276 bytes.

    NO REMEDY IS ATTACHED, on purpose. Nothing on this PC can clear it: the
    fix is a new APK installed on a phone, and Android asks the person holding
    it (free will, rule 5). A detector with no remedy is not a gap -- it is the
    honest shape for a condition whose repair belongs to somebody else. What it
    buys is that the condition is now a NUMBER in sense(), not prose in a
    warning nobody re-reads.

    THE REFERENCE IS THE RUNNING MESH, NOT DISK, and getting that wrong would
    have made this useless. The first draft compared each peer against
    `disk_source_sha12()` -- but a phone can only ever run a RELEASED BUILD,
    and disk moves ahead of every build the moment anyone edits the core. That
    detector would have read PRESENT for ever, including the instant after the
    phone updated perfectly, and an alert whose condition cannot become false
    is one nobody reads (M34). What CAN converge is the mesh agreeing with
    itself, so the reference is the source the local nodes are actually
    running -- the same denominator node A's own A20 warning uses. Disk versus
    the local nodes is a different condition and already has its own detector
    (source_drift) and its own remedy.

    WHAT IT CANNOT SEE: `mesh.by_source` (A20) carries the last source each
    peer reported; the age lives beside it in `heard_s_ago` and is reported
    here, but a peer that has gone silent keeps its last reading for ever, so
    PRESENT means "a peer has reported a different source", never "two sources
    are live right now". It is also blind to any peer that has never answered a
    local node, and to a disagreement between two peers neither of which has
    spoken to this PC.
    """
    h = _health() if health is None else health
    running, peers, ages = {}, {}, {}
    for k, v in h.items():
        if not isinstance(v, dict) or "http" in v:
            continue
        if v.get("source_sha256"):
            running[k] = str(v["source_sha256"])[:12]
        mesh = v.get("mesh") or {}
        for src, whos in (mesh.get("by_source") or {}).items():
            for who in (whos if isinstance(whos, list) else [whos]):
                peers[str(who)[:64]] = str(src)[:12]
        for who, age in (mesh.get("heard_s_ago") or {}).items():
            if isinstance(age, (int, float)):
                who = str(who)[:64]
                ages[who] = min(ages.get(who, age), age)
    ours = sorted(set(running.values()))
    if not ours:
        return {"state": UNKNOWN,
                "measured": {"running": running, "peers": peers,
                             "why": "no local node reported its own source"}}
    if not peers:
        return {"state": UNKNOWN,
                "measured": {"running": running, "peers": peers,
                             "why": "no peer has reported a source to any local node"}}
    off = sorted([w for w, s in peers.items() if s and s not in ours])
    return {"state": PRESENT if off else ABSENT,
            "measured": {"running": ours, "peers": peers, "drifted": off,
                         "heard_s_ago": {w: ages[w] for w in off if w in ages},
                         "note": "no remedy: a peer's bytes are changed on the peer, by its owner"}}


def detect_height_lag(health=None):
    h = _health() if health is None else health
    hs = {k: v.get("chain_height") for k, v in h.items()
          if isinstance(v, dict) and "http" not in v}
    vals = [v for v in hs.values() if isinstance(v, int)]
    if len(vals) < 2:
        return {"state": UNKNOWN, "measured": {"heights": hs}}
    gap = max(vals) - min(vals)
    return {"state": PRESENT if gap > 1 else ABSENT, "measured": {"heights": hs, "gap": gap}}


def detect_app_build_gap(health=None):
    """A phone holding a build older than the one this PC has fetched.

    NOW CARRIES WHETHER THE PHONE ASKED (2026-09-18). The gap alone cannot say
    which end is stuck, and for 46.6 h it did not: build 0.1.552 was fetched
    here at 07:41, the manifest signed cleanly, the phone's signed /checkin
    arrived every ten minutes -- and the PC had no record of a single ask at
    /app/latest, because the node keeps no access log at all (grep across
    logs/ finds 0 for /app/latest AND 0 for `checkin`, while
    ops/phone_checkins.jsonl holds 615 rows). So `last_ask` comes from the
    witness ledger covenant_app_update.note_request writes.

    Read it exactly this way: `never` means NOTHING HAS ASKED SINCE THE LEDGER
    BEGAN (2026-09-18), not that nothing ever asked. An ask recorded `refused`
    means the fault is this PC's signature; no ask at all, with check-ins
    arriving, means the fault is on the phone. Those need opposite fixes, which
    is the whole reason the field is here.
    """
    try:
        import covenant_daily_plan as dp
    except Exception as e:                                       # noqa: BLE001
        return {"state": UNKNOWN, "measured": {"error": "%s: %s" % (type(e).__name__, e)}}
    alerts, _infos = dp.build_report()
    ask = {"last_ask": "never (since the witness ledger began)"}
    try:
        import covenant_app_update as AU
        rows = AU.requests_tail(1, route="/app/latest")
        if rows:
            ask = {"last_ask": rows[-1].get("t"), "outcome": rows[-1].get("outcome"),
                   "signer": rows[-1].get("signer"), "detail": rows[-1].get("detail")}
    except Exception as e:                                       # noqa: BLE001
        ask = {"last_ask": "unreadable: %s" % type(e).__name__}
    return {"state": PRESENT if alerts else ABSENT,
            "measured": dict(ask, alerts=alerts)}


def detect_app_install_futile(health=None):
    """The phone takes the whole build and stays on the old one.

    SEPARATE FROM app_build_gap ON PURPOSE, and the separation is the finding.
    "The phone is behind" was true for 46.6 h while the cause changed
    underneath it twice -- first the phone never asked, then it asked and was
    refused at the signature, then (2026-09-18) it asked, was served, and
    downloaded 45 MB every ten minutes without ever installing. One condition
    covering three faults with three different fixes is a condition nobody can
    act on, which is the same lesson detect_build_stale_on_pc was split out for.

    This one is narrow enough to act on: the bytes arrive whole and the version
    does not move. The fix is not on this PC at all -- the installed build
    predates the SecurityException fix, so its installer throws on every
    attempt -- which is exactly why the only remedy paired here is the one that
    needs a person.

    WHAT IT CANNOT SEE: everything the phone does not report. An install that
    succeeded and rolled back looks identical from here to one that never ran,
    and nothing before the witness ledger began (2026-09-18) is visible at all.
    """
    try:
        import covenant_app_update as AU
        f = AU.install_futility()
    except Exception as e:                                       # noqa: BLE001
        return {"state": UNKNOWN, "measured": {"error": "%s: %s" % (type(e).__name__, e)}}
    if "could not be measured" in str(f.get("why", "")):
        return {"state": UNKNOWN, "measured": f}
    return {"state": PRESENT if f.get("futile") else ABSENT, "measured": f}


def detect_log_bloat(health=None, limit_mb=512):
    """A log file eating the disk. Measured in bytes, not guessed at."""
    big = {}
    d = os.path.join(HERE, "logs")
    try:
        for n in os.listdir(d):
            if not n.endswith(".log"):
                continue
            mb = os.path.getsize(os.path.join(d, n)) / 1048576.0
            if mb >= limit_mb:
                big[n] = round(mb, 1)
    except OSError as e:
        return {"state": UNKNOWN, "measured": {"error": str(e)}}
    return {"state": PRESENT if big else ABSENT, "measured": {"over_%dmb" % limit_mb: big}}


def detect_build_stale_on_pc(health=None, hours=24):
    """This PC has not looked for a newer app build in `hours`.

    SEPARATE FROM app_build_gap, and the separation was learned the hard way.
    fetch_build was first paired with app_build_gap -- "the phone is behind" --
    so every time it ran, the phone was still behind afterwards (fetching is
    not installing), the outcome was recorded "did not fix", and the remedy
    quarantined ITSELF after two correct runs. The effectiveness counter was
    working exactly as designed on a pairing that was wrong: a remedy must be
    graded against the condition it can actually clear.
    """
    try:
        import covenant_app_update as AU
        d = AU.latest() or {}
    except Exception as e:                                       # noqa: BLE001
        return {"state": UNKNOWN, "measured": {"error": "%s: %s" % (type(e).__name__, e)}}
    if not d:
        return {"state": PRESENT, "measured": {"fetched": None, "why": "no build fetched yet"}}
    stamp = str(d.get("fetched", ""))
    try:
        import datetime
        age_h = (time.time() - datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%S%z").timestamp()) / 3600.0
    except (ValueError, TypeError):
        return {"state": UNKNOWN, "measured": {"fetched": stamp, "why": "unparseable timestamp"}}
    return {"state": PRESENT if age_h > hours else ABSENT,
            "measured": {"fetched": stamp, "age_hours": round(age_h, 1), "limit_hours": hours,
                         "have": d.get("sha7")}}


def detect_phone_build_behind_core(health=None):
    """The newest app build predates the core that is on main now.

    THE GAP THIS CLOSES. covenant-phone's workflow triggers on a push to
    covenant-phone -- and the APK it produces is built from a checkout of the
    PUBLIC core at main. So every change to the core leaves the phone's build
    behind it, and nothing ever rebuilds: today's work would have sat here
    forever while the phone auto-updated faithfully to a build made before it.
    A delivery pipeline whose first step nobody triggers is not a pipeline.
    """
    import subprocess
    try:
        import covenant_app_update as AU
        d = AU.latest() or {}
    except Exception as e:                                       # noqa: BLE001
        return {"state": UNKNOWN, "measured": {"error": "%s: %s" % (type(e).__name__, e)}}
    if not d.get("built"):
        return {"state": UNKNOWN, "measured": {"why": "no build fetched to compare against"}}
    ref = "origin/main"
    try:
        p = subprocess.run(["git", "log", "-1", "--format=%cI", ref], cwd=HERE,
                           capture_output=True, text=True, timeout=60)
        if p.returncode != 0:
            ref = "HEAD"
            p = subprocess.run(["git", "log", "-1", "--format=%cI", ref], cwd=HERE,
                               capture_output=True, text=True, timeout=60)
        head = (p.stdout or "").strip()
    except Exception as e:                                       # noqa: BLE001
        return {"state": UNKNOWN, "measured": {"error": "%s: %s" % (type(e).__name__, e)}}
    import datetime
    try:
        head_t = datetime.datetime.fromisoformat(head).timestamp()
        built_t = datetime.datetime.strptime(d["built"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=datetime.timezone.utc).timestamp()
    except (ValueError, TypeError) as e:
        return {"state": UNKNOWN, "measured": {"head": head, "built": d.get("built"), "error": str(e)}}
    return {"state": PRESENT if head_t > built_t else ABSENT,
            "measured": {"core_committed": head, "ref": ref, "build_built": d["built"],
                         "build": d.get("sha7"), "behind_by_min": round((head_t - built_t) / 60.0, 1)}}


def detect_manifest_stale(health=None):
    """MANIFEST.sha256 no longer describes the tree it claims to.

    WHY IT IS WORTH A DETECTOR. The pre-commit hook rewrites the manifest only
    when IT changed a file, and deliberately not on every commit: verify_bundle
    hashes the WORKING TREE, so on a partial commit that would record a
    manifest describing content the commit does not contain. The consequence is
    that a normal commit leaves the manifest one step behind, the sweep's
    integrity phase reports FAIL, and every run ends "gates BLOCKED" -- which
    is A60's defect at the top of the report: a permanent red teaches its
    reader to skip the line where a real one would appear.
    """
    import subprocess
    try:
        p_ = subprocess.run([sys.executable, os.path.join(HERE, "verify_bundle.py")],
                            cwd=HERE, capture_output=True, text=True, timeout=300)
    except Exception as e:                                       # noqa: BLE001
        return {"state": UNKNOWN, "measured": {"error": "%s: %s" % (type(e).__name__, e)}}
    changed = [l.split(None, 1)[1].strip() for l in (p_.stdout or "").splitlines()
               if l.startswith("CHANGED/MISSING")]
    return {"state": PRESENT if p_.returncode != 0 else ABSENT,
            "measured": {"rc": p_.returncode, "changed": changed[:10], "n_changed": len(changed)}}


def detect_held_core_drift(health=None):
    """A held copy of the core claiming the live version with different bytes.

    P18 V3. Re-broken by every core change until someone copies the file, which
    is exactly the class of chore that gets forgotten -- it went red on GitHub
    thirty-seven commits in a row once.
    """
    import subprocess
    try:
        p = subprocess.run([sys.executable, os.path.join(HERE, "covenant_sync_held_core.py"), "--check"],
                           cwd=HERE, capture_output=True, text=True, timeout=120)
    except Exception as e:                                       # noqa: BLE001
        return {"state": UNKNOWN, "measured": {"error": "%s: %s" % (type(e).__name__, e)}}
    return {"state": PRESENT if p.returncode != 0 else ABSENT,
            "measured": {"rc": p.returncode, "said": (p.stdout or p.stderr or "").strip()[:200]}}


def _watchdog_module_files():
    """covenant_watchdog.py and every covenant_* module it imports.

    Read from the source rather than hardcoded, so a new import is covered the
    day it is added and not the day someone remembers this list.
    """
    import re
    src = os.path.join(HERE, "covenant_watchdog.py")
    files = [src]
    try:
        text = io.open(src, encoding="utf-8").read()
    except OSError:
        return files
    for name in sorted(set(re.findall(r"import\s+(covenant_[a-z0-9_]+)", text))):
        f = os.path.join(HERE, name + ".py")
        if os.path.exists(f):
            files.append(f)
    return files


def detect_watchdog_stale(health=None):
    """The running watchdog is older than the code it runs.

    TWO MISTAKES ARE BURIED HERE, both mine, both caught by running the thing.

    The first draft imported the watchdog in THIS process and compared that
    module's hash to the file. A fresh import always matches, so it would have
    reported ABSENT every time, including twice today when the running watchdog
    really was stale. A guard that measures itself is the 2026-09-09 fake-guard
    defect, written within the hour of writing that rule down.

    The second was narrower and worse. Comparing only covenant_watchdog.py to
    the process start missed the thing that actually bit: Python caches
    imports, so a watchdog started at 06:44 went on executing the
    covenant_highway it loaded THEN -- through six commits of fixes, still
    pairing fetch_build with a condition fetching cannot clear, re-quarantining
    it every 66 seconds while the corrected file sat on disk. `import X` inside
    the loop re-binds a cached module; it does not re-read the file. So the
    question is not "is the watchdog's own file newer" but "is ANY file this
    process runs newer than the process".

    A touched-but-unedited file reads as stale, which is the harmless direction.
    """
    import subprocess
    files = _watchdog_module_files()
    try:
        newest, newest_name = max((os.path.getmtime(f), os.path.basename(f)) for f in files)
    except (OSError, ValueError) as e:
        return {"state": UNKNOWN, "measured": {"error": str(e)}}
    ps = ("Get-CimInstance Win32_Process -Filter \"name like '%python%'\" |"
          " Where-Object { $_.CommandLine -like '*covenant_watchdog.py*' } |"
          " ForEach-Object { $_.CreationDate.ToUniversalTime().ToString('o') }")
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           cwd=HERE, capture_output=True, text=True, timeout=60)
        stamps = [x.strip() for x in (p.stdout or "").splitlines() if x.strip()]
    except Exception as e:                                       # noqa: BLE001
        return {"state": UNKNOWN, "measured": {"error": "%s: %s" % (type(e).__name__, e)}}
    if not stamps:
        # No watchdog at all is a different condition with a different remedy;
        # this detector does not get to call that "fine".
        return {"state": UNKNOWN, "measured": {"running": 0, "why": "no watchdog process found"}}
    import datetime
    try:
        started = min(datetime.datetime.fromisoformat(s).timestamp() for s in stamps)
    except ValueError as e:
        return {"state": UNKNOWN, "measured": {"stamps": stamps, "error": str(e)}}
    return {"state": PRESENT if newest > started else ABSENT,
            "measured": {"newest_file": newest_name, "written": round(newest, 1),
                         "process_started": round(started, 1), "running": len(stamps),
                         "watched_files": len(files), "stale_by_s": round(newest - started, 1)}}


def detect_sweep_red(health=None):
    """The newest full sweep says FAIL.

    WHY THIS DETECTOR EXISTS. Every other detector here watches a piece of
    INFRASTRUCTURE -- a node, a log, a hash, the watchdog. None of them watches
    the one signal that actually defines "green": the sweep's own verdict. So
    on 2026-09-17 the sweep read FAIL at 11:48 and FAIL again at 12:38 with two
    suites measuring nothing, and nothing in this file noticed, because every
    remedy it owns was correctly reporting healthy. The loop could heal the
    machine and not the thing the machine is for.

    The cause that day was a node that died at boot on an ACL check, which THIS
    FILE ALREADY HAD A REMEDY FOR. It was never told.

    DISCOVERY, NOT A FILENAME LIST (rule 2). The sweep has been written to
    ONE_RUN.txt, ONE_SWEEP.txt and SWEEP_*.txt at different times, and a
    hardcoded list cannot find the artifact added after the list was written --
    which is exactly the artifact a freshness check exists to catch. So every
    *.txt at the top level is filtered by CONTENT: does it carry a verdict line
    and a suite count? That is what makes it a sweep.
    """
    import glob
    import re
    # A VERDICT, NOT THE WORD "RESULT" (2026-09-18). The content filter asked
    # only whether the words `RESULT:` and `suites run` appeared, and took the
    # newest match by mtime. A `covenant_one.py --check` transcript carries both
    # and ends `RESULT: INCOMPLETE` -- no sweep, no tally -- so running the gates
    # for convenience wrote a newer file that this detector then PREFERRED and
    # could not read, and the one detector that watches whether the sweep is
    # green went UNKNOWN while a real ONE_SWEEP.txt sat beside it. Measured the
    # same afternoon, on a file I had just created.
    #
    # So the filter is the verdict regex itself. An artifact that does not state
    # PASS or FAIL is not a sweep result, whatever words it contains, and it is
    # named in `skipped` rather than silently passed over -- a filter that
    # discards without saying so is how this went unnoticed for an hour.
    verdict_re = re.compile(r"^\s*RESULT:\s*(PASS|FAIL)", re.M)
    newest, skipped = None, []
    for p in glob.glob(os.path.join(HERE, "*.txt")):
        try:
            with io.open(p, encoding="utf-8", errors="replace") as fh:
                txt = fh.read()
        except OSError:
            continue
        if "suites run" not in txt:
            continue                       # a description, not the measurement
        if not verdict_re.search(txt):
            skipped.append(os.path.basename(p))
            continue                       # e.g. a --check run: INCOMPLETE
        mt = os.path.getmtime(p)
        if newest is None or mt > newest[0]:
            newest = (mt, p, txt)

    if newest is None:
        return {"state": UNKNOWN,
                "measured": {"why": "no sweep artifact on disk states PASS or FAIL",
                             "skipped_no_verdict": sorted(skipped)}}

    mt, path, txt = newest
    verdict = "UNKNOWN"
    m = re.search(r"^\s*RESULT:\s*(PASS|FAIL)", txt, re.M)
    if m:
        verdict = m.group(1)
    unclean = []
    m = re.search(r"^\s*suites not clean\s+\d+\s*->\s*(.+)$", txt, re.M)
    if m:
        unclean = [s.strip() for s in m.group(1).split(",") if s.strip()]
    failed = None
    m = re.search(r"^\s*checks failed\s+(\d+)", txt, re.M)
    if m:
        failed = int(m.group(1))

    measured = {"verdict": verdict, "artifact": os.path.basename(path),
                "age_d": round((time.time() - mt) / 86400.0, 2),
                "unclean": unclean, "checks_failed": failed}

    if verdict == "FAIL":
        return {"state": PRESENT, "measured": measured}
    if verdict == "PASS":
        return {"state": ABSENT, "measured": measured}
    # A sweep whose verdict could not be parsed is not a pass. Rule 9: say so.
    return {"state": UNKNOWN, "measured": measured}


DETECTORS = {
    "node_down": detect_node_down,
    "sweep_red": detect_sweep_red,
    "source_drift": detect_source_drift,
    "mesh_source_split": detect_mesh_source_split,
    "height_lag": detect_height_lag,
    "app_build_gap": detect_app_build_gap,
    "app_install_futile": detect_app_install_futile,
    "build_stale_on_pc": detect_build_stale_on_pc,
    "phone_build_behind_core": detect_phone_build_behind_core,
    "log_bloat": detect_log_bloat,
    "held_core_drift": detect_held_core_drift,
    "manifest_stale": detect_manifest_stale,
    "watchdog_stale": detect_watchdog_stale,
}


def sense(only=None, health=None):
    """{detector: {state, measured}} -- every detector, measured now."""
    health = _health() if health is None else health
    out = {}
    for name, fn in DETECTORS.items():
        if only and name not in only:
            continue
        try:
            out[name] = fn(health=health)
        except Exception as e:                                   # noqa: BLE001
            out[name] = {"state": UNKNOWN, "measured": {"error": "%s: %s" % (type(e).__name__, e)}}
    return out


# ----------------------------------------------------------------- repairing

def _operator_choices():
    """{target: why} -- things the operator chose, which no remedy may touch."""
    try:
        with open(CHOICES, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def remedy_restart_nodes(measured, dry_run=True):
    """STATELESS: the nodes come back on the source that is on disk.

    Changes no file and no database -- rolling_restart.py takes at most one node
    down at a time and proves it is back before touching the next.
    """
    if dry_run:
        return True, "would run rolling_restart.py"
    import subprocess
    p = subprocess.run([sys.executable, os.path.join(HERE, "rolling_restart.py")],
                       cwd=HERE, capture_output=True, text=True, timeout=900)
    return p.returncode == 0, (p.stdout or "")[-400:]


def remedy_fetch_build(measured, dry_run=True):
    """UNDOABLE: fetches the newest green app build into ops/app/.

    It only ADDS a file and rewrites latest.json; the previous apk stays on disk,
    so the undo is to restore the previous manifest. It installs nothing, on this
    machine or any other.
    """
    if dry_run:
        return True, "would run covenant_app_update.fetch()"
    import covenant_app_update as AU
    before = AU.latest() or {}
    lines = []
    AU.fetch(say=lines.append)
    after = AU.latest() or {}
    return after.get("sha7") != before.get("sha7") or bool(after), "; ".join(lines[-3:])


def remedy_rotate_log(measured, dry_run=True):
    """UNDOABLE: renames an oversized log aside; the undo renames it back."""
    names = []
    for k, v in (measured or {}).items():
        if k.startswith("over_") and isinstance(v, dict):
            names = sorted(v)
    if not names:
        return False, "nothing over the limit"
    done = []
    for n in names:
        src = os.path.join(HERE, "logs", n)
        dst = src + "." + time.strftime("%Y%m%d%H%M%S")
        if dry_run:
            done.append("would move %s -> %s" % (n, os.path.basename(dst)))
            continue
        os.replace(src, dst)
        done.append("%s -> %s (undo: rename back)" % (n, os.path.basename(dst)))
    return True, "; ".join(done)


def remedy_resync_held_core(measured, dry_run=True):
    """UNDOABLE: copies the live core over the held copies (P18 V3).

    Writes only files git tracks, so the undo is `git checkout -- <path>`. It
    never touches a .PRE-vX.Y.py backup; that refusal lives in the tool itself.
    """
    import subprocess
    if dry_run:
        return True, "would run covenant_sync_held_core.py"
    p = subprocess.run([sys.executable, os.path.join(HERE, "covenant_sync_held_core.py")],
                       cwd=HERE, capture_output=True, text=True, timeout=300)
    return p.returncode == 0, ((p.stdout or "") + (p.stderr or "")).strip()[-300:]


def remedy_restart_watchdog(measured, dry_run=True):
    """STATELESS: the watchdog comes back running the file that is on disk.

    RECURSION, said out loud: when the highway runs INSIDE the watchdog this
    remedy would kill its own process mid-round. The caller passes
    exclude={"restart_watchdog"} there, and run_once() does it by default --
    a rule enforced by the caller, not by this function pretending to know who
    is calling it.
    """
    import subprocess
    if dry_run:
        return True, "would stop the running watchdog and start it from disk"
    # %% throughout: this string is %-formatted below, and a bare '%python%'
    # in the WMI filter blew up the first --repair run with "unsupported
    # format character 'p'".
    ps = ("$w=@(Get-CimInstance Win32_Process -Filter \"name like '%%python%%'\")"
          " | Where-Object { $_.CommandLine -like '*covenant_watchdog.py*' };"
          " $w | ForEach-Object { Stop-Process -Id $_.ProcessId -Force };"
          " Start-Sleep -Seconds 2;"
          " Start-Process -FilePath '%s' -ArgumentList '%s','--interval','60'"
          " -WorkingDirectory '%s' -WindowStyle Hidden"
          " -RedirectStandardOutput '%s' -RedirectStandardError '%s'"
          % (sys.executable, os.path.join(HERE, "covenant_watchdog.py"), HERE,
             os.path.join(HERE, "logs", "watchdog-stdout.log"),
             os.path.join(HERE, "logs", "watchdog-stderr.log")))
    p = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       cwd=HERE, capture_output=True, text=True, timeout=300)
    return p.returncode == 0, ((p.stdout or "") + (p.stderr or "")).strip()[-200:]


def remedy_dispatch_phone_build(measured, dry_run=True):
    """ASYNCHRONOUS: asks the build runner for an APK carrying the core on main.

    It touches a build server and nothing else -- no device, no install, no
    money. The cost is minutes on his Actions account, declared below. The
    build takes about ten minutes, so this remedy is marked `async`: grading it
    a second after it starts is the exact mistake that quarantined fetch_build.
    """
    import covenant_app_update as AU
    import covenant_github_judge as gh
    if dry_run:
        return True, "would dispatch android.yml on %s" % AU.REPO
    # A141: same as covenant_app_update.fetch -- the A21 gate closed this too,
    # and a remedy that cannot get a credential reports "nothing done this
    # pass" forever while phone_build_behind_core stays PRESENT. Dispatching a
    # build of the operator's own app from the operator's own PC is the
    # maintenance they scheduled. Same residual: AU.REPO is hardcoded, so on a
    # clone this targets the owner's repository (A142).
    gh.allow_credential_store("covenant_highway.dispatch_phone_build -- the "
                              "operator's own app build, on the operator's own PC")
    tok = gh.token()
    if not tok:
        return False, "no GitHub credential on this PC"
    body = json.dumps({"ref": "main"}).encode()
    req = urllib.request.Request(
        "https://api.github.com/repos/%s/actions/workflows/android.yml/dispatches" % AU.REPO,
        data=body, method="POST",
        headers={"Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json", "User-Agent": "covenant-highway"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status in (200, 201, 204), "dispatch accepted (HTTP %d); the build takes ~10 min" % r.status
    except urllib.error.HTTPError as e:
        return False, "dispatch refused: HTTP %d %s" % (e.code, e.read()[:120].decode("utf-8", "replace"))
    except Exception as e:                                       # noqa: BLE001
        return False, "%s: %s" % (type(e).__name__, e)


def remedy_rehash_bundle(measured, dry_run=True):
    """UNDOABLE: rewrite MANIFEST.sha256 -- but only over a clean tree.

    The hook's reasoning is the constraint: verify_bundle hashes the WORKING
    TREE, so writing the manifest while tracked files are modified records a
    claim about content no commit contains. So this refuses unless the only
    tracked modification is the manifest itself. On a dirty tree it says so and
    leaves the condition standing, which is the honest outcome -- a person is
    mid-change and the manifest is theirs to settle.
    """
    import subprocess
    p_ = subprocess.run(["git", "status", "--porcelain"], cwd=HERE,
                        capture_output=True, text=True, timeout=120)
    dirty = [l[3:].strip() for l in (p_.stdout or "").splitlines()
             if l[:2].strip() and not l.startswith("??")]
    # ops/SELF_EVAL.md is appended hourly by the watchdog and is excluded from
    # the manifest for exactly that reason; it is not a change in flight.
    dirty = [f for f in dirty if f not in ("MANIFEST.sha256", "ops/SELF_EVAL.md")]
    if dirty:
        return False, ("the tree has uncommitted tracked changes (%s) -- a manifest written "
                       "now would describe content no commit contains" % ", ".join(dirty[:4]))
    if dry_run:
        return True, "would run verify_bundle.py --write over a clean tree"
    r = subprocess.run([sys.executable, os.path.join(HERE, "verify_bundle.py"), "--write"],
                       cwd=HERE, capture_output=True, text=True, timeout=300)
    return r.returncode == 0, ((r.stdout or "") + (r.stderr or "")).strip()[-160:]


def remedy_schedule_watchdog_restart(measured, dry_run=True):
    """ASYNCHRONOUS, and the only remedy the watchdog may use on itself.

    restart_watchdog kills its caller, so the scheduled pass excludes it --
    which left the watchdog stale after every commit that touched a module it
    imports, waiting for a person. That is the opposite of the point.

    This hands the job to a DETACHED process that waits five seconds and then
    does the stop-and-start, so the round that asked for it finishes normally
    and the replacement happens a moment later. Being killed is not a hazard
    for the watchdog -- rolling_restart and the guard already do exactly that,
    and it writes its state as it goes rather than at the end.
    """
    import subprocess
    # 2026-09-16: the kill was reliable and the START was not. Four times that
    # day covenant_watchdog_guard.py found "no live watchdog PID" with a gap of
    # 200-294s -- meaning this remedy had killed the watchdog and left NOTHING
    # running until the guard noticed, three to five minutes later, with the
    # nodes unwatched the whole time. logs/watchdog-stderr.log was created and
    # stayed 0 bytes, which is what a -Redirect that opens but never gets a
    # process looks like: covenant_prod.bat starts the watchdog under a cmd
    # wrapper holding those same log files with >>, and Start-Process cannot
    # always take the handle straight after the kill.
    #
    # The check above (rc after 0.5s) proves the RESTARTER launched. It cannot
    # prove a watchdog exists, because by then this process is gone. So the
    # verification moves inside the script: start, wait, count; if none is
    # alive, start again WITHOUT the redirects, which is the part that fails;
    # then write what actually happened to logs/watchdog_restart_last.json so
    # a failure is observable instead of silent. Verify the effect, not the
    # invocation -- the rule this file states and this remedy was missing.
    inner = (" $py='%s'; $wd='%s'; $here='%s'; $out='%s'; $err='%s';"
             " $marker='%s'; $fb=0;"
             " Start-Sleep -Seconds 5;"
             " $w=@(Get-CimInstance Win32_Process -Filter \"name like '%%python%%'\")"
             " | Where-Object { $_.CommandLine -like '*covenant_watchdog.py*' };"
             " $w | ForEach-Object { Stop-Process -Id $_.ProcessId -Force };"
             " Start-Sleep -Seconds 2;"
             " try { Start-Process -FilePath $py -ArgumentList $wd,'--interval','60'"
             " -WorkingDirectory $here -WindowStyle Hidden"
             " -RedirectStandardOutput $out -RedirectStandardError $err }"
             " catch { };"
             " Start-Sleep -Seconds 4;"
             " $a=@(Get-CimInstance Win32_Process -Filter \"name like '%%python%%'\")"
             " | Where-Object { $_.CommandLine -like '*covenant_watchdog.py*' };"
             " if ($a.Count -eq 0) { $fb=1;"
             "   try { Start-Process -FilePath $py -ArgumentList $wd,'--interval','60'"
             "   -WorkingDirectory $here -WindowStyle Hidden } catch { };"
             "   Start-Sleep -Seconds 4;"
             "   $a=@(Get-CimInstance Win32_Process -Filter \"name like '%%python%%'\")"
             "   | Where-Object { $_.CommandLine -like '*covenant_watchdog.py*' } };"
             " $o=[ordered]@{"
             " at=((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'));"
             " alive=$a.Count; fallback_used=$fb };"
             " $o | ConvertTo-Json -Compress | Set-Content -Path $marker"
             " -Encoding utf8"
             % (sys.executable, os.path.join(HERE, "covenant_watchdog.py"), HERE,
                os.path.join(HERE, "logs", "watchdog-stdout.log"),
                os.path.join(HERE, "logs", "watchdog-stderr.log"),
                os.path.join(HERE, "logs", "watchdog_restart_last.json")))
    if dry_run:
        return True, "would schedule a detached restart in 5s"
    # CREATE_NO_WINDOW, not DETACHED_PROCESS, and the difference is not
    # cosmetic: the first version used DETACHED_PROCESS and the child never ran
    # at all -- measured with a marker file, twice -- while this function
    # cheerfully returned "scheduled". A remedy that reports success it has not
    # observed is the failure mode this whole file exists to avoid, so the
    # spawn is now CHECKED: half a second later, a process that has already
    # exited is reported as the failure it is.
    try:
        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", inner], cwd=HERE,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as e:                                       # noqa: BLE001
        return False, "%s: %s" % (type(e).__name__, e)
    time.sleep(0.5)
    rc = proc.poll()
    if rc is not None:
        return False, "the restarter exited immediately (rc %s) -- nothing was scheduled" % rc
    return True, "restart scheduled in 5s (pid %d); this round finishes first" % proc.pid


def remedy_install_on_phone(measured, dry_run=True):
    """PROPOSE_ONLY, permanently. The person holding the phone confirms an
    install; nothing here may do it for them, and the engine refuses this class
    outright rather than trusting this function to behave."""
    return False, "a person taps this one: open /m on the phone"


# MUTUAL BENEFIT IS DECLARED, NOT INFERRED. Every remedy says who gains, who
# bears the cost, and what cannot be taken back. Declared data can be wrong and
# can be argued with; a number derived by this file from its own assumptions
# would only sound objective. The proposal a PROPOSE_ONLY remedy raises carries
# this block verbatim, so the person deciding reads the cost in the same breath
# as the benefit.
MAX_TARGETED_RERUN = 5     # more than this is a broken tree, not a gap


def remedy_rerun_unclean(measured, dry_run=True):
    """Re-run ONLY the suites that measured nothing. Never the whole sweep.

    THE LINE THIS MUST NOT CROSS, and the operator was asked to hold me to it:
    this remedy may restart the WORLD; it may never edit a CHECK. It runs
    processes. It does not open a test, does not move a threshold, does not
    mark a suite deliberately-off. Restarting a downed node fixes reality;
    editing a suite fixes the scoreboard, and only one of those is repair.

    WHY TARGETED. The full sweep is ~14 minutes; the suites that produced no
    tally are seconds. A loop that repays the whole bill to close a small gap
    is the token waste the operator named on 2026-09-17. It heals the gap.

    WHY IT MAY REPORT FAILURE AND THAT IS CORRECT. If the suites are still
    unclean afterwards the cause is not transient, and this says so rather than
    retrying. A self-healing loop that cannot fail honestly is a loop that
    launders red into green by repetition.

    NEVER writes to ONE_RUN.txt or ONE_SWEEP.txt. Those are G12's evidence of
    when the suites last ran, and a targeted re-run of two suites is not that.
    Overwriting them with a partial run destroyed G12's evidence once already.
    """
    unclean = [s for s in (measured.get("unclean") or []) if s.endswith(".py")]
    if not unclean:
        return False, ("the sweep is red but named no unclean suite -- the "
                       "cause is checks that FAILED, and a re-run is not the "
                       "answer to a real failure")
    if len(unclean) > MAX_TARGETED_RERUN:
        return False, ("%d unclean suites is a broken tree, not a gap -- "
                       "refusing to paper over it: %s"
                       % (len(unclean), ", ".join(unclean[:MAX_TARGETED_RERUN])))
    if dry_run:
        return True, "would re-run only: %s" % ", ".join(unclean)

    import subprocess
    out = os.path.join(HERE, "ops", "sweep_heal_last.txt")
    try:
        p = subprocess.run([sys.executable, os.path.join(HERE, "covenant_one.py"),
                            "--only"] + unclean + ["--out", out],
                           cwd=HERE, capture_output=True, text=True, timeout=1800)
    except Exception as e:                                       # noqa: BLE001
        return False, "the re-run could not be started: %s: %s" % (type(e).__name__, e)

    import re
    txt = (p.stdout or "") + (p.stderr or "")
    still = []
    m = re.search(r"^\s*suites not clean\s+\d+\s*->\s*(.+)$", txt, re.M)
    if m:
        still = [s.strip() for s in m.group(1).split(",") if s.strip()]
    # BOTH readings, always. The red is recorded beside the green, so the loop
    # can never make itself look good by forgetting what it found.
    was = ", ".join(unclean)
    if still:
        return False, ("was unclean: %s | still unclean after a targeted "
                       "re-run: %s -- not transient, and not mine to fix"
                       % (was, ", ".join(still)))
    return True, ("was unclean: %s | clean on a targeted re-run -- the sweep's "
                  "reading was transient. Full verdict still needs a full "
                  "sweep; this only closes the gap." % was)


REMEDIES = {
    "rerun_unclean": {"fn": remedy_rerun_unclean, "klass": AUTO_REVERSIBLE,
                      "for": ["sweep_red"], "kind": "stateless",
                      "touches": ["ops/sweep_heal_last.txt"],
                      "benefit": {"gains": ["a suite that measured NOTHING is made to measure",
                                            "red that is transient clears; red that is real is named"],
                                  "cost": ["the seconds those suites take, never the full ~14 min sweep"],
                                  "irreversible": []}},
    "restart_nodes": {"fn": remedy_restart_nodes, "klass": AUTO_REVERSIBLE,
                      "for": ["source_drift", "node_down"], "kind": "stateless",
                      "touches": ["nodes"],
                      "benefit": {"gains": ["the mesh runs the code that is on disk",
                                            "a node that is down answers again"],
                                  "cost": ["one node unreachable for a few seconds, one at a time"],
                                  "irreversible": []}},
    "fetch_build": {"fn": remedy_fetch_build, "klass": AUTO_REVERSIBLE,
                    "for": ["build_stale_on_pc", "phone_build_behind_core"],
                    "async_for": ["phone_build_behind_core"], "kind": "undoable",
                    "undo": "restore the previous ops/app/latest.json",
                    "touches": ["ops/app"],
                    "benefit": {"gains": ["the newest build is here when the phone asks"],
                                "cost": ["~45 MB of disk and one authenticated download"],
                                "irreversible": []}},
    "rotate_log": {"fn": remedy_rotate_log, "klass": AUTO_REVERSIBLE,
                   "for": ["log_bloat"], "kind": "undoable",
                   "undo": "rename the rotated file back", "touches": ["logs"],
                   "benefit": {"gains": ["the disk stops filling", "the log stays readable"],
                               "cost": ["a reader must look in the rotated file for older lines"],
                               "irreversible": []}},
    "resync_held_core": {"fn": remedy_resync_held_core, "klass": AUTO_REVERSIBLE,
                         "for": ["held_core_drift"], "kind": "undoable",
                         "undo": "git checkout -- pending-v8.38/covenant_unified_v8.py",
                         "touches": ["held copies of the core"],
                         "benefit": {"gains": ["P18 stops failing on a copy nobody made",
                                               "one version names one set of bytes again"],
                                     "cost": ["a tracked file is rewritten; git holds the previous bytes"],
                                     "irreversible": []}},
    "restart_watchdog": {"fn": remedy_restart_watchdog, "klass": AUTO_REVERSIBLE,
                         "for": ["watchdog_stale"], "kind": "stateless",
                         "touches": ["the watchdog process"],
                         "benefit": {"gains": ["the checks that are deployed are the checks running (P14)"],
                                     "cost": ["a gap of a few seconds with nothing watching the nodes"],
                                     "irreversible": []}},
    "dispatch_phone_build": {"fn": remedy_dispatch_phone_build, "klass": AUTO_REVERSIBLE,
                             "for": ["phone_build_behind_core"], "kind": "stateless",
                             "async": True, "cooldown_s": 86400,
                             "touches": ["the build runner"],
                             "benefit": {"gains": ["an APK carrying the core that is on main",
                                                   "the phone's auto-update has something newer to find"],
                                         "cost": ["about ten minutes of his GitHub Actions account"],
                                         "irreversible": []}},
    "rehash_bundle": {"fn": remedy_rehash_bundle, "klass": AUTO_REVERSIBLE,
                      "for": ["manifest_stale"], "kind": "undoable",
                      "undo": "git checkout -- MANIFEST.sha256",
                      "touches": ["the delivery manifest"],
                      "benefit": {"gains": ["the sweep's integrity phase means something again",
                                            "\"gates BLOCKED\" stops being permanent furniture"],
                                  "cost": ["one tracked file rewritten, to be carried by the next commit"],
                                  "irreversible": []}},
    "schedule_watchdog_restart": {"fn": remedy_schedule_watchdog_restart,
                                  "klass": AUTO_REVERSIBLE, "for": ["watchdog_stale"],
                                  "kind": "stateless", "async": True,
                                  "touches": ["the watchdog process"],
                                  "benefit": {"gains": ["the watchdog runs the modules that are on disk, without a person"],
                                              "cost": ["a few seconds with nothing watching the nodes"],
                                              "irreversible": []}},
    "install_on_phone": {"fn": remedy_install_on_phone, "klass": PROPOSE_ONLY,
                         "for": ["app_build_gap", "app_install_futile"], "kind": "needs a person",
                         "touches": ["the phone"],
                         "benefit": {"gains": ["the phone stops running a build that cannot update itself",
                                               "the mesh stops running two sources (A20)"],
                                     "cost": ["a person's attention, and a moment of the phone's node being down"],
                                     "irreversible": ["an installed build replaces the one that is there"]}},
}


def quarantined(name, ledger=None):
    """A remedy measured failing QUARANTINE_AFTER times is not offered.

    Reset by a measured success, or by an explicit `recalibrated` row -- see
    recalibrate(). Never by deleting history: a counter you can clear by
    forgetting is not a counter.
    """
    fails = 0
    for row in read_ledger(ledger):
        if row.get("remedy") != name:
            continue
        if row.get("outcome") in ("fixed", "recalibrated"):
            fails = 0
        elif row.get("outcome") == "did not fix":
            fails += 1
    return fails >= QUARANTINE_AFTER


def recalibrate(name, why, ledger=None):
    """Clear a quarantine that measured the wrong thing, on the record.

    The first live pass quarantined fetch_build after two runs that both did
    exactly what they should: it was being graded against app_build_gap -- "the
    phone is behind" -- which fetching cannot clear. The counter was right
    about the pairing and wrong about the remedy. This writes WHY the count no
    longer applies, so the reset is auditable rather than invisible; the
    failures stay in the file above it.
    """
    return write_ledger({"t": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "at": round(time.time(), 1),
                         "remedy": name, "outcome": "recalibrated", "why": why}, ledger)


def _recent_identical(name, detector, ledger=None, within_s=None):
    """The last row for this (remedy, detector) if it is younger than the cooldown.

    The first hour of live running wrote the same proposal row every 66 seconds,
    twenty-four times, each one re-loading the judge to re-ask a question whose
    answer had not changed. A ledger that repeats itself is a ledger nobody
    reads, and an alert nobody reads is A60's defect. Repeats are skipped, not
    written, and the condition still surfaces through run_once's return.
    """
    within_s = ROW_COOLDOWN_S if within_s is None else within_s
    now = time.time()
    for row in reversed(read_ledger(ledger)):
        if row.get("remedy") == name and row.get("detector") == detector:
            return row if (now - float(row.get("at", 0))) < within_s else None
    return None


def ask_the_covenant(sentence):
    """What this covenant's own seat says about doing a thing, in its own words.

    Not a vote and not permission: the deployed student is a compressed model
    and its own verdict text says to treat a finding as a flag to review. It is
    here because a proposal that cites the covenant should cite the covenant
    that is RUNNING, measured now, rather than a paragraph a session wrote.
    HELD is reported as held -- an "I don't know" that is read as a No is how
    an abstention becomes a veto (A132's neighbourhood).
    """
    try:
        import covenant_judge_fallback as FB
        import covenant_unified_v8 as cov
        j = FB.FallbackJudge()
        v = j.evaluate({"action": sentence}, cov.DIVINE_PRINCIPLES)
        if getattr(v, "not_understood", False):
            verdict = "held -- no finding"
        elif getattr(v, "is_violation", False) or getattr(v, "violates", False):
            verdict = "flagged for review"
        else:
            verdict = "clean"
        return {"seat": getattr(v, "judge_id", "?"), "verdict": verdict,
                "said": str(getattr(v, "reasoning", ""))[:240],
                "principles_put_to_it": len(cov.DIVINE_PRINCIPLES)}
    except Exception as e:                                       # noqa: BLE001
        return {"seat": "unavailable", "verdict": UNKNOWN,
                "said": "%s: %s" % (type(e).__name__, e), "principles_put_to_it": 0}


def propose(name, condition, detector, r=None):
    """The fields a PROPOSE_ONLY remedy contributes to its ledger row."""
    r = r or REMEDIES.get(name) or {}
    sentence = "%s: %s, because %s was measured %s here" % (
        name, (r.get("kind") or "?"), detector, (condition or {}).get("state", UNKNOWN))
    return {
        "outcome": "proposed",
        "why": "class %s is never executed by the engine -- a person decides" % r.get("klass"),
        "measured": (condition or {}).get("measured", {}),
        "mutual_benefit": r.get("benefit", {}),
        "covenant": ask_the_covenant(sentence),
        "undo": r.get("undo", "n/a (stateless)" if r.get("kind") == "stateless" else "none on record"),
    }


def apply_remedy(name, condition, detector, dry_run=True, ledger=None, choices=None,
                 cooldown_s=None):
    """Run one remedy against one measured condition. Returns a ledger row.

    Every refusal is a row too: a refusal nobody can see is indistinguishable
    from a bug that swallowed the work.
    """
    r = REMEDIES.get(name)
    row = {"t": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "at": round(time.time(), 1),
           "remedy": name, "detector": detector, "dry_run": bool(dry_run)}
    if not r:
        row.update(outcome="refused", why="no such remedy")
        return write_ledger(row, ledger)

    # WHO GAINED AND WHO PAID -- ON EVERY ROW, NOT ONLY THE REFUSALS.
    #
    # The operator, 2026-09-17: "Its only dangerous without mutual benefit."
    # That is a sharper test than the one this file was using. A quiet repair
    # is not dangerous because it is quiet; it is dangerous when it is
    # ASYMMETRIC -- when the system keeps running and the operator carries a
    # false belief, having never been told the price.
    #
    # Measured here the same day: a REFUSAL called propose() and carried gains,
    # cost and who pays. An APPLICATION recorded only outcome="fixed". So this
    # loop stated the price when nothing happened and withheld it when
    # something did -- the exact asymmetry, sitting inside the mechanism
    # written to prevent it. The benefit now rides every row, so a repair that
    # succeeded can still be audited for what it cost.
    # AND IT IS MARKED AS A CLAIM, BECAUSE IT IS ONE.
    #
    # The operator, 2026-09-17, on whether a thing is dangerous: "That's my
    # call." He is right, and it lands on this dict. Every gains/cost line in
    # REMEDIES was written by me, and so was every klass -- the judgment that a
    # remedy is safe enough to run without asking him. A benefit stated in a
    # ledger row reads as a finding. It is not. It is an assertion awaiting his
    # ratification, and the difference matters precisely here, because a system
    # that grades its own benefit and then acts on that grade has closed the
    # loop his authority is supposed to sit inside.
    #
    # This is CLAUDE.md rule 5 in the one place it costs something: a
    # denominator can be measured, what COUNTS cannot. Whether the gain is
    # worth the cost is scope, and scope is his.
    #
    # ops/OPERATOR_CHOICES.json is the lever and it is currently EMPTY. Nothing
    # in this file is presently constrained by anything he has written down.
    if isinstance(r.get("benefit"), dict):
        row["benefit"] = dict(r["benefit"], claimed_by="claude, not ratified")

    # The cooldown comes FIRST, before any work: a repeat within the hour costs
    # a subprocess, a model load, or a download, and buys a line identical to
    # the one above it.
    # A remedy may ask for a longer budget than the default hour. The first one
    # to need it is dispatch_phone_build: the hourly default would ask for up
    # to twenty-four ten-minute CI runs a day on his account, which is his
    # money spent by my scheduler. Once a day is what the thing is actually
    # for -- the core does not change hourly, and nothing is waiting on it
    # faster than a person can tap an install.
    # A DECLARED BUDGET IS NOT NOISE SUPPRESSION. cooldown_s=0 means "a person
    # typed --repair, do not make them wait an hour for a line they have
    # already read" -- and it used to skip a remedy's OWN budget too, which is
    # how one manual run of mine asked the build runner for a second
    # ten-minute job inside twenty minutes. A budget a caller can wave away is
    # not a budget; the hour is mine to skip, the day is not.
    declared = r.get("cooldown_s")
    if cooldown_s is None:
        eff = declared if declared is not None else ROW_COOLDOWN_S
    elif declared is not None:
        eff = max(cooldown_s, declared)
    else:
        eff = cooldown_s
    prev = None if eff == 0 else _recent_identical(name, detector, ledger, eff)
    if prev is not None:
        out = dict(prev)
        out["repeat"] = True
        return out

    # INVARIANT 1 -- the class, refused by the ENGINE, and then REFERRED.
    #
    # "when 1 happens refer to the covenant or meta data in it and mutual
    # benefit" (2026-09-16). A bare "refused: PROPOSE_ONLY" tells the person
    # nothing they can act on, and a refusal that explains nothing is how a
    # safety rule turns into a wall. So the refusal is the START of a proposal:
    # what was actually measured, what the covenant's own seat says about doing
    # it, and who gains and who pays -- in the same row.
    if r["klass"] != AUTO_REVERSIBLE:
        row.update(propose(name, condition, detector, r))
        return write_ledger(row, ledger)

    # INVARIANT 1b -- THE LINE THAT DOES NOT MOVE (2026-09-16).
    #
    # The class is a label on a dict, and a label is one careless edit away from
    # being wrong. These subjects are refused on what a remedy TOUCHES, whatever
    # class it claims: money and the things that decide money, the rules and the
    # seats that judge by them, and any act whose entire point is that a person
    # consented to it. Flip install_on_phone to AUTO_REVERSIBLE and it still
    # refuses here -- H1i proves exactly that.
    #
    # This is not timidity. An engine that can quietly widen its own remit is
    # not repairing the system, it is replacing the person in it, and "leaves
    # free will intact" was the requirement, not the decoration.
    crossed = sorted({w for w in NEVER_AUTOMATIC
                      for t in r.get("touches", []) if w in t.lower()})
    if crossed:
        row.update(propose(name, condition, detector, r))
        row["why"] = ("touches %s -- refused whatever class it claims; a person decides"
                      % ", ".join(crossed))
        return write_ledger(row, ledger)

    # INVARIANT 2 -- an operator's explicit choice.
    choices = _operator_choices() if choices is None else choices
    clash = sorted(set(r.get("touches", [])) & set(choices))
    if clash:
        row.update(outcome="refused",
                   why="the operator chose %s: %s" % (clash[0], choices[clash[0]]))
        return write_ledger(row, ledger)

    # INVARIANT 3 -- stateless, or an undo on record.
    if r.get("kind") != "stateless" and not r.get("undo"):
        row.update(outcome="refused", why="changes state with no undo on record")
        return write_ledger(row, ledger)

    if quarantined(name, ledger):
        row.update(outcome="refused", why="quarantined: measured not fixing it %d times" % QUARANTINE_AFTER)
        return write_ledger(row, ledger)

    before = (condition or {}).get("state")
    ok, detail = r["fn"]((condition or {}).get("measured"), dry_run=dry_run)
    row.update(ran=bool(ok), detail=str(detail)[:400], before=before)
    if dry_run:
        row.update(outcome="dry run", after=before)
        return write_ledger(row, ledger)
    # A remedy can be synchronous for one condition and asynchronous for
    # another. fetch_build clears build_stale_on_pc the moment it runs, but it
    # clears phone_build_behind_core only once the runner has finished making
    # the build -- so the same function must be graded differently depending on
    # which condition it was called for. Without this, the hourly retry while
    # CI is still building would record two "did not fix" and quarantine it:
    # fault 1 of the first live hour, reproduced in a new costume.
    if r.get("async") or detector in (r.get("async_for") or ()):
        # GRADED BY THE NEXT PASS, not by this one. A build takes ten minutes;
        # measuring a second after the dispatch would record "did not fix"
        # every time and quarantine a remedy that works -- which is precisely
        # what happened to fetch_build in this file's first live hour. An
        # outcome of "started" is not counted as a failure by quarantined().
        row.update(after=before, outcome="started",
                   note="asynchronous -- the condition is re-measured next pass")
        return write_ledger(row, ledger)
    after = DETECTORS[detector]()["state"] if detector in DETECTORS else UNKNOWN
    row.update(after=after,
               outcome="fixed" if (before == PRESENT and after == ABSENT) else "did not fix")
    return write_ledger(row, ledger)


# ----------------------------------------------------------------- the ledger

def read_ledger(path=None):
    out = []
    try:
        with open(path or LEDGER, encoding="utf-8") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def write_ledger(row, path=None):
    path = path or LEDGER
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


# ----------------------------------------------------------------- sharing

def run_once(dry_run=False, exclude=("restart_watchdog",), ledger=None, health=None,
             cooldown_s=None):
    """One sense-and-repair pass. (alerts, infos) in the watchdog's shape.

    `exclude` defaults to the watchdog's own restart because the intended caller
    IS the watchdog: a remedy that kills its caller mid-round is not a repair.
    Run from a shell, pass exclude=() and it will restart the watchdog too.
    """
    alerts, infos = [], []
    conditions = sense(health=health)
    # PAUSED MEANS NO ACTION, NOT NO SIGHT (2026-09-16, the operator's
    # instruction: "ensure they all running independent so you can pause tasks
    # for restart and update"). The sensing above has already happened and is
    # still reported; what stops here is every repair. A pause that also
    # blinded the pass would make updating the highway cost the operator his
    # visibility, which is the opposite of the point.
    try:
        import covenant_pause as _p
        is_paused, why = _p.paused("highway")
    except Exception:                                            # noqa: BLE001
        is_paused, why = False, ""
    if is_paused:
        present = sorted(k for k, v in conditions.items() if v["state"] == PRESENT)
        infos.append("highway: PAUSED (%s) -- sensing only. Present now: %s"
                     % (why, ", ".join(present) or "nothing"))
        return alerts, infos
    for name, c in sorted(conditions.items()):
        if c["state"] == UNKNOWN:
            infos.append("highway: %s could not be measured -- %s"
                         % (name, json.dumps(c["measured"])[:120]))
            continue
        if c["state"] != PRESENT:
            continue
        acted = False
        for rname, r in REMEDIES.items():
            if name not in r["for"] or rname in (exclude or ()):
                continue
            row = apply_remedy(rname, c, name, dry_run=dry_run, ledger=ledger,
                               cooldown_s=cooldown_s)
            acted = True
            if row.get("repeat"):
                # SAY THAT NOTHING HAPPENED. The cooldown returns the previous
                # row, and this used to print ITS detail as though it had just
                # happened -- "dispatch accepted (HTTP 204)" for a dispatch
                # made four hours earlier, with no new build and no new cost.
                # An accurate ledger under a report that misreads it is still a
                # system that lies to its operator.
                infos.append("highway: %s still present; %s last %s at %s -- nothing done this pass"
                             % (name, rname, row.get("outcome", "?"), row.get("t", "?")))
                continue
            if row["outcome"] == "fixed":
                infos.append("highway: %s was present; %s fixed it" % (name, rname))
            elif row["outcome"] == "proposed":
                alerts.append("highway: %s is present and %s is not mine to run -- %s"
                              % (name, rname, row.get("why", "")))
            elif row["outcome"] == "dry run":
                infos.append("highway: %s present; %s would run (dry)" % (name, rname))
            else:
                alerts.append("highway: %s is present and %s %s -- %s"
                              % (name, rname, row["outcome"], row.get("why", row.get("detail", ""))[:120]))
        if not acted:
            held_back = [n for n, rr in REMEDIES.items()
                         if name in rr["for"] and n in (exclude or ())]
            if held_back:
                alerts.append("highway: %s is present; %s could fix it but this caller "
                              "excluded it" % (name, ", ".join(held_back)))
            else:
                # CARRY THE MEASUREMENT (2026-09-18). A detector with no remedy
                # is the honest shape for a condition somebody else has to fix
                # -- and this line used to name only the condition, so the one
                # alert a person can actually act on arrived with none of the
                # numbers needed to act. mesh_source_split says which peer is
                # on which source and when it was last heard; "nothing here
                # repairs it" without that is a nudge, not a finding.
                alerts.append("highway: %s is present and nothing here repairs it -- %s"
                              % (name, json.dumps(c["measured"])[:400]))
    return alerts, infos


def standing(ledger=None):
    """What each remedy CLAIMED, set against what actually happened when it ran.

    THE OPERATOR, 2026-09-17: "Students surpass teachers children parents is
    ideal. But respect remains."

    The commit before this one marked every benefit claim `claimed_by "claude,
    not ratified"`, which was honest and stopped one step short. A claim handed
    over with no way to check it is not deference; it asks the operator to take
    my word, which is the same asymmetry in a humbler voice. So the claims are
    made AUDITABLE against the ledger's own record of outcomes.

    THE SHAPE THIS GROWS ON is already in A126: a seat may hold, may differ by
    temperament, may be right where the trunk is wrong -- and false clears stay
    at zero. It may surpass. It may never clear itself. Standing here works the
    same way: a remedy earns it by being MEASURABLY RIGHT, never by being
    trusted more as time passes.

    WHAT THIS DELIBERATELY IS NOT. Nothing in this file reads standing() to
    decide anything, and test_p25 pins that a perfect record cannot change one
    decision apply_remedy makes. A record that bought its own authority would
    be a student grading its own theft. This is evidence FOR the operator's
    ratification, and the ratification stays his.

      EARNED    it ran, and every graded run fixed the condition
      MIXED     it ran, and sometimes it did not fix it
      FAILING   it ran, and never fixed it
      UNPROVEN  never graded -- the honest answer, not a bad one (rule 9)
    """
    rows = read_ledger(ledger)
    out = {}
    for name, r in sorted(REMEDIES.items()):
        mine = [x for x in rows if x.get("remedy") == name]
        graded = [x for x in mine if not x.get("dry_run")
                  and x.get("outcome") in ("fixed", "did not fix")]
        fixed = sum(1 for x in graded if x.get("outcome") == "fixed")
        missed = len(graded) - fixed
        if not graded:
            verdict = "UNPROVEN"
        elif missed == 0:
            verdict = "EARNED"
        elif fixed == 0:
            verdict = "FAILING"
        else:
            verdict = "MIXED"
        b = r.get("benefit") or {}
        out[name] = {"verdict": verdict, "graded": len(graded), "fixed": fixed,
                     "did_not_fix": missed,
                     "started_ungraded": sum(1 for x in mine
                                             if x.get("outcome") == "started"),
                     "refused": sum(1 for x in mine
                                    if x.get("outcome") == "refused"),
                     "claimed": list(b.get("gains") or []),
                     "claimed_cost": list(b.get("cost") or []),
                     "ratified": False}
    return out


def report(node_id=None, health=None, ledger=None):
    """What this node offers the mesh: what it senses, and what has worked here.

    Deliberately narrow. Detector names and states, remedy outcomes, nothing
    read out of a file and nothing about money, holdings, keys or people. A
    report is an OFFER; the receiving node re-measures before it believes a word
    of it.
    """
    import covenant_unified_v8 as cov
    conditions = sense(health=health)
    worked = {}
    for row in read_ledger(ledger):
        if row.get("dry_run") or row.get("outcome") not in ("fixed", "did not fix"):
            continue
        w = worked.setdefault(row["remedy"], {"fixed": 0, "did not fix": 0, "for": row.get("detector")})
        w[row["outcome"]] += 1
    return {
        "node": node_id or os.environ.get("COVENANT_NODE_ID") or "pc",
        "at": round(time.time(), 1),
        "source": cov.CORE_SOURCE_SHA12,
        "conditions": {k: v["state"] for k, v in conditions.items()},
        "remedies_that_worked_here": worked,
        "offer": "data, not an instruction -- measure it yourself before acting",
    }


def ingest(peer_report, dry_run=True, ledger=None, cooldown_s=None):
    """Take a peer's offer and decide LOCALLY. Returns what this node did.

    INVARIANT 4: nothing here runs because a peer said so. For every condition
    the peer reports, this node runs its OWN detector; only a condition present
    HERE is even a candidate, and then only an AUTO_REVERSIBLE remedy runs.
    """
    acted = []
    out = {"from": (peer_report or {}).get("node", "?"), "did": acted}
    for name, state in ((peer_report or {}).get("conditions") or {}).items():
        if name not in DETECTORS:
            acted.append({"condition": name, "action": "ignored", "why": "no such detector here"})
            continue
        if state != PRESENT:
            continue
        local = DETECTORS[name]()
        if local["state"] != PRESENT:
            acted.append({"condition": name, "action": "declined",
                          "why": "the peer has it; this node measured %s" % local["state"]})
            continue
        for rname, r in REMEDIES.items():
            if name in r["for"] and r["klass"] == AUTO_REVERSIBLE:
                row = apply_remedy(rname, local, name, dry_run=dry_run, ledger=ledger,
                                   cooldown_s=cooldown_s)
                acted.append({"condition": name, "action": row["outcome"], "remedy": rname})
                break
        else:
            acted.append({"condition": name, "action": "raised", "why": "no AUTO_REVERSIBLE remedy"})
    return out


# ----------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description="the mycelial highway: sense, repair, share")
    ap.add_argument("--repair", action="store_true", help="apply AUTO_REVERSIBLE remedies (default is dry run)")
    ap.add_argument("--report", action="store_true", help="print the signed-shape offer this node would share")
    ap.add_argument("--ledger", action="store_true", help="print what has been tried here")
    ap.add_argument("--standing", action="store_true",
                    help="what each remedy CLAIMED, against what happened when it ran")
    a = ap.parse_args(argv)

    if a.standing:
        st = standing()
        print("What this system claimed for itself, and what the record says.")
        print("Evidence for the operator's ratification. It is not authority,")
        print("and nothing here changes a single decision the loop makes.\n")
        print("%-26s %-9s %6s %7s  %s"
              % ("remedy", "verdict", "fixed", "missed", "claimed gain"))
        for k, v in st.items():
            print("%-26s %-9s %6d %7d  %s"
                  % (k, v["verdict"], v["fixed"], v["did_not_fix"],
                     (v["claimed"][0][:44] if v["claimed"] else "-")))
        print("\nUNPROVEN is not a failing grade. It means never graded, which")
        print("is the honest answer and the one a tool that resolves everything")
        print("would hide.")
        return 0
    if a.ledger:
        for row in read_ledger()[-40:]:
            print("%s  %-14s %-14s %s" % (row.get("t", "?"), row.get("remedy", "?"),
                                          row.get("outcome", "?"), row.get("why", row.get("detail", ""))[:90]))
        return 0
    if a.report:
        print(json.dumps(report(), indent=1))
        return 0

    conditions = sense()
    print("SENSE")
    for k, v in sorted(conditions.items()):
        print("  %-16s %-8s %s" % (k, v["state"], json.dumps(v["measured"])[:110]))
    present = [k for k, v in conditions.items() if v["state"] == PRESENT]
    if not present:
        print("\nnothing detrimental measured here")
        return 0
    print("\nREPAIR" + ("" if a.repair else "  (dry run -- pass --repair to act)"))
    for name in present:
        for rname, r in REMEDIES.items():
            if name in r["for"]:
                # cooldown_s=0: a person typing --repair has asked for it now,
                # and the hourly suppressor exists for the scheduled pass, not for them.
                row = apply_remedy(rname, conditions[name], name, dry_run=not a.repair,
                                   cooldown_s=0)
                # A REPEATED ROW IS NOT A THING THAT JUST HAPPENED, and this
                # printer said it was. run_once was fixed for exactly this on
                # 2026-09-18 -- "an accurate ledger under a report that misreads
                # it is still a system that lies to its operator" -- and the
                # same misreading was left standing here, in the reader a person
                # actually types.
                #
                # It is not cosmetic and it is not hypothetical: `cooldown_s=0`
                # waives the hour but NOT a remedy's own declared budget
                # (eff = max(0, 86400) for dispatch_phone_build, deliberately,
                # because that budget is his Actions minutes). So a plain
                # `python covenant_highway.py` printed
                #     dispatch_phone_build  started  dispatch accepted (HTTP 204)
                # for a dispatch made THIRTEEN HOURS EARLIER at 07:32, with no
                # new row in ops/highway.jsonl -- and a reader who trusted the
                # line would believe a build had just been asked for when none
                # had. Measured here on 2026-09-18 at 20:47, by me, before I
                # noticed the ledger disagreed with the screen.
                if row.get("repeat"):
                    print("  %-16s %-14s %-10s %s" % (
                        name, rname, "held",
                        "within its budget -- nothing done this pass; last %s at %s"
                        % (row.get("outcome", "?"), row.get("t", "?"))))
                    continue
                print("  %-16s %-14s %-10s %s" % (name, rname, row["outcome"],
                                                  row.get("why", row.get("detail", ""))[:80]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
