#!/usr/bin/env python3
"""mobile/usb_link.py -- the phone on a USB-C cable: install the app, and tunnel
the node's ports so phone and PC peer over the cable with no Wi-Fi, no firewall
rule and no address to discover.

WHY (asked 2026-09-12: "can we set it up to download via c to c port ...
tethered")

  Every other route to the phone needed something that kept failing: a QR the
  camera would not read, a browser download and an "unknown sources" prompt,
  a Wi-Fi peer address and an inbound firewall rule that was never added (the
  only rule on this PC is for TCP 7443). A data cable and Android's own debug
  bridge need none of that:

    adb reverse tcp:15001 tcp:5001   phone's 127.0.0.1:15001 -> this PC's 5001
                                     (node A's peer port), so the phone node
                                     peers with  PC_PEER=127.0.0.1:15001
    adb forward tcp:15000 tcp:5000   this PC's 127.0.0.1:15000 -> the phone's
                                     5000, so http://127.0.0.1:15000/health is
                                     the phone node, readable from here

  15001 rather than 5001 on the phone side because the phone node's OWN peer
  port is 5001 (PHONE_PORT 5000, plus one); binding the tunnel there would
  collide with it. 15000 rather than 5000 on the PC side because node A holds
  5000 here. Neither tunnel crosses Windows Firewall: adb opens the PC-side
  socket itself, from this machine, to localhost.

WHAT IT NEEDS ON THE PHONE, once: Settings > About phone > Software information,
tap "Build number" seven times; then Settings > Developer options > USB
debugging ON. Plug in a DATA cable (some USB-C cables are charge-only). The
first time, the phone shows "Allow USB debugging?" with this PC's fingerprint;
tick "Always allow" and OK. Until that is accepted `adb devices` lists the
phone as `unauthorized`, and this script says so rather than failing.

WHAT IT NEEDS ON THE PC: Google's platform-tools (adb). If tools/platform-tools/
is absent this script offers to download platform-tools-latest-windows.zip from
https://dl.google.com/android/repository/ (7.7 MB, measured 2026-09-12) and
unpack it there; the folder is gitignored, nothing is installed system-wide and
PATH is not touched. Pass --no-download to refuse and point at your own adb
with --adb.

USE
  python mobile/usb_link.py status            what adb sees (devices, states)
  python mobile/usb_link.py link              set both tunnels, then read the
                                              phone node's /health through them
  python mobile/usb_link.py install FILE.apk  install (or update) the app
  python mobile/usb_link.py unlink            remove the tunnels

WHAT IT NEVER DOES: grant permissions on install (no -g), read or print
anything from the phone but device serial and state, touch this PC's nodes,
or change any setting on either machine.

EXIT 0 done; 2 no usable device (and it says why); 3 adb missing and not
downloaded; 4 the adb command itself failed (its output is shown).
LICENCE: public domain.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(HERE, "tools", "platform-tools")
PT_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
PT_MB = 7.7                                   # measured 2026-09-12 (Content-Length 8,044,989)

PHONE_SIDE_TO_PC = ("15001", "5001")           # adb reverse: phone localhost -> PC
PC_SIDE_TO_PHONE = ("15000", "5000")           # adb forward: PC localhost -> phone
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def say(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------- adb itself

def find_adb(explicit=None):
    """The adb to use: --adb, else tools/platform-tools, else PATH. None if none."""
    cands = []
    if explicit:
        cands.append(explicit)
    cands.append(os.path.join(TOOLS, "adb.exe" if os.name == "nt" else "adb"))
    import shutil
    on_path = shutil.which("adb")
    if on_path:
        cands.append(on_path)
    for c in cands:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def download_adb():
    """Fetch Google's platform-tools into tools/platform-tools. Says what it is
    doing and from where BEFORE doing it; verifies the zip before unpacking."""
    say("adb is not here. Downloading Google's platform-tools:")
    say("  %s  (about %.1f MB)" % (PT_URL, PT_MB))
    say("  -> %s" % TOOLS)
    os.makedirs(os.path.dirname(TOOLS), exist_ok=True)
    req = urllib.request.Request(PT_URL, headers={"User-Agent": "covenant-usb-link"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    if len(data) < 1_000_000:
        raise RuntimeError("download too small to be platform-tools (%d bytes)" % len(data))
    z = zipfile.ZipFile(io.BytesIO(data))
    bad = z.testzip()
    if bad is not None:
        raise RuntimeError("zip failed integrity check at %s" % bad)
    if not any(n.endswith("platform-tools/adb.exe") or n.endswith("platform-tools/adb") for n in z.namelist()):
        raise RuntimeError("zip does not contain platform-tools/adb")
    z.extractall(os.path.dirname(TOOLS))
    say("unpacked %d entries" % len(z.namelist()))
    return find_adb()


def ensure_adb(explicit=None, allow_download=True):
    adb = find_adb(explicit)
    if adb:
        return adb
    if not allow_download:
        say("adb not found (tools/platform-tools/, PATH, or --adb) and --no-download was given.")
        return None
    return download_adb()


def run_adb(adb, *args, timeout=120):
    """(returncode, stdout+stderr). Never raises on a non-zero exit."""
    p = subprocess.run([adb] + list(args), capture_output=True, text=True,
                       timeout=timeout, creationflags=NO_WINDOW)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# ---------------------------------------------------------------- devices

def devices(adb):
    """[(serial, state)] from `adb devices -l`. States adb uses: device,
    unauthorized, offline, no permissions, recovery, sideload."""
    rc, out = run_adb(adb, "devices", "-l")
    rows = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices") or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            rows.append((parts[0], parts[1]))
    return rows


def explain(rows):
    """What the device list means, in words a person can act on."""
    if not rows:
        return ("no phone seen over USB. Plug in a DATA cable (charge-only cables show "
                "nothing), unlock the phone, and check Settings > Developer options > "
                "USB debugging is ON. If the phone offers a USB mode, choose "
                "'File transfer'.")
    states = {}
    for serial, state in rows:
        states.setdefault(state, []).append(serial)
    if "device" in states and len(states["device"]) == 1:
        return "ready: one phone authorised (%s)" % states["device"][0]
    if "unauthorized" in states:
        return ("the phone is connected but has NOT authorised this PC: look at the "
                "phone for 'Allow USB debugging?', tick 'Always allow from this computer', "
                "tap OK, then run this again.")
    if "offline" in states:
        return ("adb reports the phone offline: unplug and replug the cable, or toggle "
                "USB debugging off and on.")
    if "device" in states:
        return ("more than one authorised device (%s); unplug the others -- this script "
                "refuses to guess." % ", ".join(states["device"]))
    return "device state(s) %s; adb cannot use the phone in that state" % sorted(states)


def the_one(adb):
    """The single authorised phone's serial, or None (after explaining)."""
    rows = devices(adb)
    say("devices: " + (", ".join("%s (%s)" % r for r in rows) if rows else "none"))
    say(explain(rows))
    ready = [s for s, st in rows if st == "device"]
    return ready[0] if len(ready) == 1 else None


# ---------------------------------------------------------------- commands

def cmd_status(adb):
    return 0 if the_one(adb) else 2


def cmd_link(adb):
    serial = the_one(adb)
    if not serial:
        return 2
    ph, pc = PHONE_SIDE_TO_PC
    rc, out = run_adb(adb, "-s", serial, "reverse", "tcp:%s" % ph, "tcp:%s" % pc)
    if rc:
        say("adb reverse failed:\n" + out.strip()); return 4
    say("phone 127.0.0.1:%s  ->  this PC's :%s   (the phone node peers with PC_PEER=127.0.0.1:%s)" % (ph, pc, ph))
    pcp, php = PC_SIDE_TO_PHONE
    rc, out = run_adb(adb, "-s", serial, "forward", "tcp:%s" % pcp, "tcp:%s" % php)
    if rc:
        say("adb forward failed:\n" + out.strip()); return 4
    say("this PC 127.0.0.1:%s  ->  the phone's :%s   (http://127.0.0.1:%s/health is the phone node)" % (pcp, php, pcp))
    # read the phone node through the tunnel; not running yet is a normal state
    try:
        with urllib.request.urlopen("http://127.0.0.1:%s/health" % pcp, timeout=5) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        say("phone node: %s  height %s  peers %s  judge %s"
            % (d.get("node_id"), d.get("chain_height"), d.get("peers"), d.get("judge")))
    except Exception as e:                                        # noqa: BLE001
        say("phone node not answering yet (%s). On the phone, start it peered over the cable:"
            % type(e).__name__)
        say("  PC_PEER=127.0.0.1:%s sh mobile/covenant_phone.sh     (Termux)  -- or start the app" % ph)
    say("tunnels last until the cable is unplugged or `unlink`; the phone's own ports are untouched")
    return 0


def cmd_install(adb, apk):
    if not apk or not os.path.isfile(apk):
        say("install needs the path to an .apk that exists (got %r)" % apk); return 2
    serial = the_one(adb)
    if not serial:
        return 2
    say("installing %s (%.1f MB) ..." % (os.path.basename(apk), os.path.getsize(apk) / 1048576))
    rc, out = run_adb(adb, "-s", serial, "install", "-r", apk, timeout=600)
    say(out.strip())
    if rc or "Success" not in out:
        say("install did not report Success. If the phone said 'Install via USB' is off, "
            "turn it on under Developer options and run this again.")
        return 4
    return 0


def cmd_unlink(adb):
    rc1, o1 = run_adb(adb, "reverse", "--remove-all")
    rc2, o2 = run_adb(adb, "forward", "--remove-all")
    say("tunnels removed" if not (rc1 or rc2) else (o1 + o2).strip())
    return 0 if not (rc1 or rc2) else 4


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    explicit = None
    allow_download = True
    if "--no-download" in argv:
        argv.remove("--no-download"); allow_download = False
    if "--adb" in argv:
        i = argv.index("--adb"); explicit = argv[i + 1]; del argv[i:i + 2]
    if not argv or argv[0] not in ("status", "link", "install", "unlink"):
        say(__doc__); return 2
    adb = ensure_adb(explicit, allow_download)
    if not adb:
        return 3
    say("adb: " + adb)
    cmd = argv[0]
    if cmd == "status":
        return cmd_status(adb)
    if cmd == "link":
        return cmd_link(adb)
    if cmd == "install":
        return cmd_install(adb, argv[1] if len(argv) > 1 else None)
    return cmd_unlink(adb)


if __name__ == "__main__":
    sys.exit(main())
