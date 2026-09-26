#!/usr/bin/env python3
"""covenant_cloud.py -- his own cloud storage: Syncthing between his devices, over the
tailnet only, with a nightly hash check the highway can see.

HIS WORDS, 2026-09-25: "can we create our own free secure cloud storage?" -> "do so".
And the same evening: "everything we do must be designed to run independently".

WHAT IT IS.
  * Syncthing 2.1.5 (tools/syncthing/, untracked; its release signature checked against
    Syncthing's published key when it was fetched). Open source, peer to peer.
  * Its identity and config live in ops/syncthing/ (untracked: it holds the device key).
  * It listens ONLY on this PC's tailnet address. Relays, NAT punching, global and local
    discovery and usage reporting are off: a device reaches it over Tailscale's WireGuard
    or not at all. Each device connection is also Syncthing's own TLS, keyed per device.
  * One folder, "Covenant Cloud" (C:\\Users\\Lawre\\CovenantCloud by default), with staggered
    versioning kept 30 days: a delete or overwrite on one device is recoverable on the
    others from .stversions. Without that, a delete on the phone would sync as a delete.
  * It runs as the Windows task CovenantCloud (at logon, no window), owned by Task
    Scheduler, never by a session shell.

WHAT IT IS NOT. A PC and a phone in one house are two copies, not a cloud: a fire or a
theft takes both. A third copy somewhere else is the real durability; `share_encrypted`
is the step for a device he does not fully trust (it stores only ciphertext) and is
not run until such a device exists.

THE CHECK (`verify`, nightly). Hashes every file, compares with the last run, and writes
counts to ops/cloud_check.json and names only to ops/cloud_manifest.json -- both
untracked, because file names are his and this repository is public. A file whose bytes
changed while its size and time did not is SILENT damage, the one thing a sync tool will
happily copy everywhere; the highway raises it.

    python covenant_cloud.py setup      harden the config, create the folder (idempotent)
    python covenant_cloud.py status     running? which devices, connected, in sync?
    python covenant_cloud.py accept     accept devices waiting from the tailnet, share the folder
    python covenant_cloud.py verify     the hash check
    python covenant_cloud.py qr FILE    this PC's device ID as a QR image, to scan on the phone
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ST_BIN = os.path.join(HERE, "tools", "syncthing", "syncthing-windows-amd64-v2.1.5", "syncthing.exe")
HOME = os.environ.get("COVENANT_CLOUD_HOME") or os.path.join(HERE, "ops", "syncthing")
CONFIG = os.path.join(HOME, "config.xml")
FOLDER_ID = "covenant-cloud"
FOLDER_LABEL = "Covenant Cloud"
FOLDER_PATH = os.environ.get("COVENANT_CLOUD_DIR") or os.path.join(os.path.expanduser("~"), "CovenantCloud")
GUI = "http://127.0.0.1:8384"
CHECK = os.environ.get("COVENANT_CLOUD_CHECK") or os.path.join(HERE, "ops", "cloud_check.json")
MANIFEST = os.environ.get("COVENANT_CLOUD_MANIFEST") or os.path.join(HERE, "ops", "cloud_manifest.json")
# No address is written here (2026-09-26 OPSEC sweep: this repository is public).
# `tailscale ip -4` is asked first; COVENANT_TAILNET_IP is the fallback; with neither,
# setup refuses rather than listen anywhere else.
PC_TAILNET_IP = os.environ.get("COVENANT_TAILNET_IP", "")
SKIP_DIRS = {".stfolder", ".stversions"}


def tailnet_ip():
    for exe in ("tailscale", r"C:\Program Files\Tailscale\tailscale.exe"):
        try:
            out = subprocess.run([exe, "ip", "-4"], capture_output=True, text=True, timeout=10).stdout.strip().splitlines()
            if out and out[0].startswith("100."):
                return out[0].strip()
        except (OSError, subprocess.SubprocessError):
            continue
    return PC_TAILNET_IP if PC_TAILNET_IP.startswith("100.") else None


def _opt(opts, tag, value):
    el = opts.find(tag)
    if el is None:
        el = ET.SubElement(opts, tag)
    el.text = str(value)


def setup(config=CONFIG, folder_path=FOLDER_PATH, say=print):
    """Harden the generated config and add the one folder. Idempotent. Returns what it set."""
    tree = ET.parse(config)
    root = tree.getroot()
    me = root.find("device")
    my_id = me.get("id")
    me.set("name", "Lawless PC")
    ip = tailnet_ip()
    if not ip:
        raise RuntimeError("tailscale did not give this PC's tailnet address and COVENANT_TAILNET_IP is not set; refusing to choose a listen address")
    opts = root.find("options")
    for el in opts.findall("listenAddress"):
        opts.remove(el)
    ET.SubElement(opts, "listenAddress").text = "tcp://%s:22000" % ip
    for tag, val in (("globalAnnounceEnabled", "false"), ("localAnnounceEnabled", "false"), ("relaysEnabled", "false"),
                     ("natEnabled", "false"), ("urAccepted", "-1"), ("crashReportingEnabled", "false"),
                     ("startBrowser", "false")):
        _opt(opts, tag, val)
    gui = root.find("gui")
    gui.find("address").text = "127.0.0.1:8384"
    gui.find("apikey").text = secrets.token_urlsafe(24)             # rotated: the first key was printed in a session transcript
    folder = next((f for f in root.findall("folder") if f.get("id") == FOLDER_ID), None)
    if folder is None:
        folder = ET.SubElement(root, "folder", {"id": FOLDER_ID, "label": FOLDER_LABEL, "path": folder_path,
                                                 "type": "sendreceive", "rescanIntervalS": "3600", "fsWatcherEnabled": "true",
                                                 "fsWatcherDelayS": "10", "ignorePerms": "false", "autoNormalize": "true"})
        ET.SubElement(folder, "filesystemType").text = "basic"
        ET.SubElement(folder, "device", {"id": my_id, "introducedBy": ""})
        ET.SubElement(folder, "minDiskFree", {"unit": "%"}).text = "1"
        v = ET.SubElement(folder, "versioning", {"type": "staggered"})
        ET.SubElement(v, "param", {"key": "maxAge", "val": str(30 * 86400)})
        ET.SubElement(v, "cleanupIntervalS").text = "3600"
    os.makedirs(folder_path, exist_ok=True)
    tree.write(config, encoding="utf-8", xml_declaration=False)
    say("cloud: config hardened (listen tcp://%s:22000 only; relays, NAT, discovery, reporting off); folder %s at %s"
        % (ip, FOLDER_ID, folder_path))
    return {"device_id": my_id, "listen": "tcp://%s:22000" % ip, "folder": folder_path}


def device_id(config=CONFIG):
    return ET.parse(config).getroot().find("device").get("id")


def _apikey(config=CONFIG):
    return ET.parse(config).getroot().find("gui").find("apikey").text


def _api(path, method="GET", body=None, config=CONFIG, raw=False):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(GUI + path, data=data, method=method,
                                 headers={"X-API-Key": _apikey(config), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        b = r.read()
    return b if raw else (json.loads(b.decode("utf-8")) if b else None)


def running():
    try:
        with urllib.request.urlopen(GUI + "/rest/noauth/health", timeout=3) as r:
            return json.loads(r.read().decode()).get("status") == "OK"
    except Exception:                                             # noqa: BLE001
        return False


def accept(say=print):
    """Accept devices waiting FROM THE TAILNET (a 100.x address) and share the folder with each.
    Anything waiting from elsewhere is listed, not accepted."""
    pending = _api("/rest/cluster/pending/devices") or {}
    done, left = [], []
    for dev, info in pending.items():
        addr = str((info or {}).get("address", ""))
        host = addr.split("//")[-1].rsplit(":", 1)[0].strip("[]")
        if not host.startswith("100."):
            left.append((dev, addr))
            continue
        _api("/rest/config/devices/%s" % dev, "PUT", {"deviceID": dev, "name": (info or {}).get("name") or "phone",
                                                       "addresses": ["tcp://%s:22000" % host], "autoAcceptFolders": False})
        f = _api("/rest/config/folders/%s" % FOLDER_ID)
        if not any(d.get("deviceID") == dev for d in f.get("devices", [])):
            f["devices"].append({"deviceID": dev})
            _api("/rest/config/folders/%s" % FOLDER_ID, "PUT", f)
        done.append((dev, host))
        say("cloud: accepted %s from %s and shared %s" % (dev[:7], host, FOLDER_LABEL))
    for dev, addr in left:
        say("cloud: NOT accepted %s (from %s, not the tailnet)" % (dev[:7], addr))
    return {"accepted": done, "left": left}


def status():
    if not running():
        return {"running": False}
    me = device_id()
    conns = (_api("/rest/system/connections") or {}).get("connections", {})
    stats = _api("/rest/stats/device") or {}
    devices = []
    for d in (_api("/rest/config/folders/%s" % FOLDER_ID) or {}).get("devices", []):
        dev = d.get("deviceID")
        if dev == me:
            continue
        comp = _api("/rest/db/completion?folder=%s&device=%s" % (FOLDER_ID, dev)) or {}
        devices.append({"id": dev[:7], "connected": bool((conns.get(dev) or {}).get("connected")),
                        "last_seen": (stats.get(dev) or {}).get("lastSeen"), "completion": comp.get("completion")})
    return {"running": True, "device_id": me, "folder": FOLDER_PATH, "copies_elsewhere": len(devices), "devices": devices}


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(folder=FOLDER_PATH, manifest=MANIFEST, check=CHECK, status_fn=None, now=None):
    """Hash every file; compare with the last manifest; write counts (check) and names (manifest)."""
    now = time.time() if now is None else now
    try:
        with open(manifest, encoding="utf-8") as fh:
            old = json.load(fh).get("files", {})
    except (OSError, ValueError):
        old = {}
    new, counts, silent = {}, {"files": 0, "bytes": 0, "added": 0, "changed": 0, "silent": 0, "missing": 0}, []
    for d, dirs, files in os.walk(folder):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            p = os.path.join(d, f)
            rel = os.path.relpath(p, folder).replace(os.sep, "/")
            try:
                st = os.stat(p)
                digest = _sha(p)
            except OSError:
                continue
            new[rel] = {"sha256": digest, "size": st.st_size, "mtime": int(st.st_mtime)}
            counts["files"] += 1
            counts["bytes"] += st.st_size
            o = old.get(rel)
            if o is None:
                counts["added"] += 1
            elif o["sha256"] != digest:
                if o["size"] == st.st_size and o["mtime"] == int(st.st_mtime):
                    counts["silent"] += 1
                    silent.append(rel)
                else:
                    counts["changed"] += 1
    counts["missing"] = sum(1 for k in old if k not in new)
    try:
        st = (status_fn or status)()
    except Exception as e:                                        # noqa: BLE001
        st = {"running": None, "error": "%s: %s" % (type(e).__name__, str(e)[:120])}
    os.makedirs(os.path.dirname(manifest), exist_ok=True)
    with open(manifest, "w", encoding="utf-8") as fh:
        json.dump({"at": now, "folder": folder, "files": new, "silent": silent}, fh)
    result = {"at": now, "counts": counts, "sync": st}
    with open(check, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1)
    return result


def summary_line(r):
    c, s = r["counts"], r.get("sync") or {}
    devs = s.get("devices") or []
    return ("cloud: %d files, %d bytes; +%d added, %d changed, %d missing, %d SILENTLY changed; syncthing %s; copies elsewhere %d (%s)"
            % (c["files"], c["bytes"], c["added"], c["changed"], c["missing"], c["silent"],
               {True: "running", False: "NOT running", None: "unknown"}.get(s.get("running")), len(devs),
               ", ".join("%s %s %s%%" % (d["id"], "connected" if d["connected"] else "offline", d.get("completion")) for d in devs) or "none paired yet"))


def qr(out):
    png = _api("/qr/?text=%s" % device_id(), raw=True)
    with open(out, "wb") as fh:
        fh.write(png)
    return out


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    cmd = a[0] if a else "status"
    if cmd == "setup":
        print(json.dumps(setup(), indent=1))
    elif cmd == "status":
        print(json.dumps(status(), indent=1))
    elif cmd == "accept":
        print(json.dumps(accept(), indent=1))
    elif cmd == "verify":
        print(summary_line(verify()))
    elif cmd == "qr":
        print(qr(a[1] if len(a) > 1 else os.path.join(HERE, "ops", "cloud_pc_qr.png")))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
